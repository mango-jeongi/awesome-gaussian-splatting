"""Bounded historical discovery and canonical import orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import Field, model_validator

from src.backfill import (
    HistoricalCrawler,
    HistoricalSpec,
    PageRef,
    RequestAudit,
    SourceModel,
    submitted_query,
)
from src.enricher import MultiProviderEnricher
from src.extractors.arxiv import ArxivExtractor, ArxivIntegrityError
from src.file_lock import exclusive_file
from src.ingestion import prepare_ingestion
from src.relevance import RelevancePolicy
from src.schema import PaperDatabase, PaperRecord
from src.storage import _atomic_write, _digest, _encode, _read_component


class HistoricalRequest(SourceModel):
    query: str = Field(min_length=1)
    comparator_query: str = Field(min_length=1)
    query_version: str = "gs-query-v1"
    policy_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    until: datetime
    since: datetime | None = None
    page_size: int = 100
    max_slice_results: int = 1000

    @model_validator(mode="after")
    def validate_request(self):
        validated = HistoricalSpec(
            **self.model_dump(exclude={"since"}), since=self.since or self.until
        )
        self.until = validated.until
        if self.since is not None:
            self.since = validated.since
        return self

    @property
    def digest(self):
        return _digest(_encode(self.model_dump(mode="json")))


class DiscoveryProbe(SourceModel):
    request_digest: str
    query: str
    total: int = Field(ge=0)
    fetched_at: datetime
    records: list[PaperRecord] = Field(max_length=1)
    published_at: dict[str, datetime]

    @model_validator(mode="after")
    def validate_inventory(self):
        if len(self.records) != min(1, self.total) or set(self.published_at) != {
            record.id for record in self.records
        }:
            raise ValueError("Discovery probe inventory is inconsistent")
        return self


class SessionState(SourceModel):
    request: HistoricalRequest
    request_digest: str
    earliest_probe: PageRef | None = None
    comparator_probe: PageRef | None = None
    requests: list[RequestAudit] = Field(default_factory=list)


class BackfillSession:
    def __init__(
        self,
        request: HistoricalRequest,
        directory: str | Path,
        source: ArxivExtractor,
        policy: RelevancePolicy,
        data_path: str | Path,
        taxonomy_path: str | Path,
    ):
        if request.policy_digest != policy.digest:
            raise ValueError("Backfill policy does not match its frozen request")
        self.request, self.directory, self.source, self.policy = (
            request,
            Path(directory),
            source,
            policy,
        )
        self.data_path, self.taxonomy_path = Path(data_path), Path(taxonomy_path)
        self.setup_path = self.directory / "setup.json"
        self.state = None
        self.remaining = 0
        self.setup_attempts = 0

    def _save(self):
        payload = _encode(self.state.model_dump(mode="json"))
        if not self.setup_path.exists() or self.setup_path.read_bytes() != payload:
            _atomic_write(self.setup_path, payload)

    def _load(self, resume):
        if self.setup_path.exists():
            if not resume:
                raise ValueError("Backfill run exists; use --resume or a new run directory")
            self.state = SessionState.model_validate_json(self.setup_path.read_bytes())
            if (
                self.state.request_digest != self.request.digest
                or self.state.request != self.request
            ):
                raise ValueError(
                    "Backfill query, policy, or cutoff changed; use a new run directory"
                )
            for audit in self.state.requests:
                if audit.status == "started":
                    audit.status = "interrupted"
        else:
            self.state = SessionState(request=self.request, request_digest=self.request.digest)
            self._save()

    def _read_probe(self, reference, query):
        probe = DiscoveryProbe.model_validate(
            _read_component(self.setup_path, reference.model_dump())
        )
        if (
            probe.request_digest != self.request.digest
            or probe.query != query
            or reference.start != 0
            or reference.count != len(probe.records)
        ):
            raise ArxivIntegrityError("Stored discovery probe changed")
        return probe

    def _probe(self, kind, query):
        if self.remaining < 1:
            return None
        audit = RequestAudit(slice_id=kind, start=0, attempt_budget=min(3, self.remaining))
        self.state.requests.append(audit)
        self._save()
        try:
            page = self.source.fetch_page(
                query=query,
                start=0,
                page_size=1,
                sort_by="submittedDate",
                sort_order="ascending",
                max_attempts=audit.attempt_budget,
            )
            audit.attempts = page.attempts
            self.setup_attempts += page.attempts
            self.remaining -= page.attempts
            if not 1 <= page.attempts <= audit.attempt_budget or page.start != 0:
                raise ArxivIntegrityError("Discovery probe request contract changed")
            probe = DiscoveryProbe(
                request_digest=self.request.digest,
                query=query,
                total=page.total,
                fetched_at=datetime.now(UTC),
                records=list(page.records),
                published_at=page.published_at,
            )
            payload = _encode(probe.model_dump(mode="json"))
            digest = _digest(payload)
            relative = f"discovery/{kind}.{digest}.json"
            _atomic_write(self.directory / relative, payload)
            reference = PageRef(path=relative, sha256=digest, start=0, count=len(page.records))
            if kind == "earliest":
                self.state.earliest_probe = reference
            else:
                self.state.comparator_probe = reference
            audit.status, audit.rows = "succeeded", len(page.records)
            audit.finished_at = datetime.now(UTC)
            self._save()
            return probe
        except Exception as error:
            if audit.attempts is None:
                audit.attempts = getattr(error, "attempts", None)
                if audit.attempts is not None:
                    self.setup_attempts += audit.attempts
                    self.remaining -= audit.attempts
            audit.status, audit.error = "error", f"{type(error).__name__}: {str(error)[:240]}"
            audit.finished_at = datetime.now(UTC)
            self._save()
            raise

    def run(self, *, max_requests=100, resume=False, dry_run=False):
        if type(max_requests) is not int or max_requests < 1:
            raise ValueError("Request budget must be positive")
        # Validate the input before spending any provider budget, then reload at import.
        PaperDatabase.load(self.data_path)
        self.remaining, self.setup_attempts = max_requests, 0
        with exclusive_file(self.directory / ".session.run.lock"):
            self._load(resume)
            since = self.request.since
            earliest = None
            if since is None:
                earliest = (
                    self._read_probe(self.state.earliest_probe, self.request.query)
                    if self.state.earliest_probe
                    else self._probe("earliest", self.request.query)
                )
                if earliest is None:
                    return {
                        "source_complete": False,
                        "corpus_written": False,
                        "budget_exhausted": True,
                    }
                since = (
                    min(
                        next(iter(earliest.published_at.values())).replace(
                            day=1, hour=0, minute=0, second=0, microsecond=0
                        ),
                        self.request.until,
                    )
                    if earliest.records
                    else self.request.until
                )
            spec = HistoricalSpec(**self.request.model_dump(exclude={"since"}), since=since)
            crawler = HistoricalCrawler(spec, self.directory / "crawl", self.source)
            if self.remaining or spec.since == spec.until:
                source_report = crawler.run(max_requests=max(1, self.remaining))
                self.remaining -= source_report["invocation_requests"]
            else:
                self._save()
                return {
                    "source_complete": False,
                    "corpus_written": False,
                    "budget_exhausted": True,
                    "setup_requests": self.setup_attempts,
                    "effective_since": since.isoformat(),
                    "run_directory": str(self.directory),
                }
            report = {
                "run_directory": str(self.directory),
                "query_digest": spec.digest,
                "source_complete": source_report["status"] == "complete",
                "source": source_report,
                "setup_requests": self.setup_attempts,
                "corpus_written": False,
                "dry_run": dry_run,
                "effective_since": since.isoformat(),
                "cutoff": spec.until.isoformat(),
                "lower_bound_method": "provided"
                if self.request.since is not None
                else "earliest_matching_month",
                "global_matching_count_at_earliest_probe": earliest.total if earliest else None,
            }
            if not report["source_complete"]:
                report["budget_exhausted"] = True
                return report
            comparator_query = submitted_query(self.request.comparator_query, since, spec.until)
            comparator = None
            if since < spec.until:
                comparator = (
                    self._read_probe(self.state.comparator_probe, comparator_query)
                    if self.state.comparator_probe
                    else self._probe("comparator", comparator_query)
                )
            report["comparator_reported_count_inclusive_api_bounds"] = (
                comparator.total if comparator else None
            )
            report["comparator_status"] = (
                "observed"
                if comparator
                else ("empty_interval" if since == spec.until else "budget_pending")
            )
            db = PaperDatabase.load(self.data_path)
            candidate, import_report = prepare_ingestion(
                db, crawler.records(), self.policy, MultiProviderEnricher(self.taxonomy_path)
            )
            import_report["query_digest"] = spec.digest
            payload = _encode(import_report)
            digest = _digest(payload)
            plan_path = self.directory / "imports" / f"{digest}.json"
            if not plan_path.exists():
                _atomic_write(plan_path, payload)
            changed = (
                import_report["source_content_sha256"] != import_report["result_content_sha256"]
            )
            if changed and not dry_run:
                candidate.save(self.data_path)
                report["corpus_written"] = True
            receipt = {
                "status": "prepared" if dry_run else ("applied" if changed else "unchanged"),
                "plan_sha256": digest,
                "source_content_sha256": import_report["source_content_sha256"],
                "result_content_sha256": import_report["result_content_sha256"],
            }
            receipt_path = self.directory / "imports" / f"{digest}.receipt.json"
            receipt_payload = _encode(receipt)
            if not receipt_path.exists() or receipt_path.read_bytes() != receipt_payload:
                _atomic_write(receipt_path, receipt_payload)
            report.update(
                outcomes=import_report["outcomes"],
                operations=import_report["operations"],
                inserted_canonical_records=import_report["inserted_canonical_records"],
                relevance_review_pending=import_report["outcomes"]["review"],
                import_plan=str(plan_path),
                total_invocation_requests=self.setup_attempts
                + source_report["invocation_requests"],
            )
            self._save()
            return report
