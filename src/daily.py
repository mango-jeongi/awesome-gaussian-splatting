"""Durable, two-pass arXiv updated-window ingestion with explicit watermarks.

arXiv has no updated-date range filter. Scan descending to the overlap boundary,
then replay every page before publication. A moving source fails closed; restart
retains the old immutable pages and never advances coverage on partial work.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import Field, model_validator

from src.backfill import SourceModel
from src.enricher import MultiProviderEnricher
from src.extractors.arxiv import ArxivIntegrityError, ArxivRequestFailure
from src.file_lock import exclusive_file
from src.ingestion import prepare_ingestion
from src.schema import PaperDatabase, PaperRecord
from src.storage import _atomic_write, _digest, _encode


class DailyPage(SourceModel):
    start: int = Field(ge=0)
    total: int = Field(ge=0)
    records: list[PaperRecord]
    updated_at: dict[str, datetime]

    @model_validator(mode="after")
    def inventory(self):
        ids = [record.id for record in self.records]
        if len(ids) != len(set(ids)) or set(ids) != set(self.updated_at):
            raise ValueError("Invalid daily source inventory")
        times = [self.updated_at[key] for key in ids]
        if times != sorted(times, reverse=True):
            raise ValueError("Source is not ordered by update time")
        return self


class DailyState(SourceModel):
    version: Literal["daily-updated-v1"] = "daily-updated-v1"
    run_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    query: str
    policy_digest: str
    since: datetime
    until: datetime
    previous_watermark: datetime | None = None
    page_size: int = Field(ge=1, le=1000)
    pages: list[str] = Field(default_factory=list)
    phase: Literal["scan", "verify", "ready", "applied", "unstable"] = "scan"
    verified: int = Field(default=0, ge=0)
    requests: int = Field(default=0, ge=0)
    pending_request: bool = False

    @model_validator(mode="after")
    def bounds(self):
        if self.since >= self.until or self.verified > len(self.pages):
            raise ValueError("Invalid daily scan bounds or verification cursor")
        if self.previous_watermark is not None and self.until <= self.previous_watermark:
            raise ValueError("Daily cutoff must advance the previous watermark")
        if self.phase == "scan" and self.verified:
            raise ValueError("Scanning state cannot have verified pages")
        if self.phase != "scan" and not self.pages:
            raise ValueError("Verification requires durable pages")
        if self.phase in ("ready", "applied") and self.verified != len(self.pages):
            raise ValueError("Publication requires every page to be verified")
        if self.phase == "verify" and self.verified >= len(self.pages):
            raise ValueError("Invalid verification state")
        if any(
            len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
            for value in self.pages
        ):
            raise ValueError("Invalid daily page digest")
        return self


class DailySession:
    def __init__(self, directory, data_path, taxonomy_path, policy, source):
        self.directory = Path(directory)
        self.data_path = Path(data_path)
        self.taxonomy_path = taxonomy_path
        self.policy = policy
        self.source = source

    def _save(self, state):
        _atomic_write(self.directory / "active.json", _encode(state.model_dump(mode="json")))

    def _page(self, digest):
        payload = (self.directory / "pages" / f"{digest}.json").read_bytes()
        if _digest(payload) != digest:
            raise ValueError("Daily page hash mismatch")
        return DailyPage.model_validate_json(payload)

    def run(
        self,
        *,
        query,
        since=None,
        until=None,
        page_size=100,
        max_requests=20,
        max_seconds=300,
        overlap_days=7,
        dry_run=False,
        restart=False,
    ):
        if type(max_requests) is not int or not 1 <= max_requests <= 1000:
            raise ValueError("Request budget must be in [1, 1000]")
        if not 0 < max_seconds <= 3600 or not 1 <= overlap_days <= 30:
            raise ValueError("Invalid time budget or overlap")
        PaperDatabase.load(self.data_path)
        started, used = time.monotonic(), 0
        with exclusive_file(self.directory / ".daily.lock"):
            active = self.directory / "active.json"
            watermark_path = self.directory / "watermark.json"
            watermark = None
            if watermark_path.exists():
                previous = json.loads(watermark_path.read_bytes())
                if previous["query"] != query or previous["policy_digest"] != self.policy.digest:
                    raise ValueError(
                        "Watermark query/policy changed; explicit coverage migration required"
                    )
                watermark = datetime.fromisoformat(previous["until"])
                if watermark.utcoffset() is None:
                    raise ValueError("Watermark requires timezone")
            state = DailyState.model_validate_json(active.read_bytes()) if active.exists() else None
            if state is None or state.phase in ("applied", "unstable") or restart:
                initial_since = since or (state.since if state is not None else None)
                if state is not None:
                    _atomic_write(
                        self.directory / "runs" / f"{state.run_id}.json",
                        _encode(state.model_dump(mode="json")),
                    )
                if watermark is None and initial_since is None:
                    raise ValueError(
                        "First daily scan requires an explicit --since coverage boundary"
                    )
                lower = watermark - timedelta(days=overlap_days) if watermark else initial_since
                if watermark and since is not None:
                    raise ValueError(
                        "--since is only for first initialization; existing watermark controls coverage"
                    )
                cutoff = until or datetime.now(UTC)
                if cutoff.utcoffset() is None or cutoff > datetime.now(UTC):
                    raise ValueError("Daily cutoff must be an aware timestamp at or before now")
                state = DailyState(
                    run_id=uuid4().hex,
                    query=query,
                    policy_digest=self.policy.digest,
                    since=lower,
                    until=cutoff,
                    previous_watermark=watermark,
                    page_size=page_size,
                )
                self._save(state)
            elif (
                state.query != query
                or state.policy_digest != self.policy.digest
                or state.page_size != page_size
                or (since is not None and since != state.since)
                or (until is not None and until != state.until)
            ):
                raise ValueError("Frozen daily request changed; use --restart")
            if watermark not in (state.previous_watermark, state.until):
                raise ValueError("Daily watermark changed during the pending run")
            # A killed dispatch remains charged in cumulative accounting. It is
            # retried at the same cursor; no missing page is acknowledged.
            state.pending_request = False
            pages = [self._page(digest) for digest in state.pages]
            ids = set()
            for index, page in enumerate(pages):
                self._validate_page(page, pages[:index], ids, state.page_size)
                ids.update(record.id for record in page.records)
            while (
                state.phase in ("scan", "verify")
                and used < max_requests
                and time.monotonic() - started < max_seconds
            ):
                offset = (
                    sum(len(page.records) for page in pages)
                    if state.phase == "scan"
                    else pages[state.verified].start
                )
                state.requests += 1
                state.pending_request = True
                self._save(state)  # Charge dispatch before touching the network.
                used += 1
                try:
                    source = self.source.fetch_page(
                        query=state.query,
                        start=offset,
                        page_size=state.page_size,
                        sort_by="lastUpdatedDate",
                        sort_order="descending",
                        max_attempts=1,
                    )
                except ArxivIntegrityError:
                    state.phase = "unstable"
                    state.pending_request = False
                    self._save(state)
                    raise
                except ArxivRequestFailure:
                    state.pending_request = False
                    self._save(state)
                    raise
                page = DailyPage(
                    start=source.start,
                    total=source.total,
                    records=list(source.records),
                    updated_at=source.updated_at,
                )
                state.pending_request = False
                if state.phase == "verify":
                    if page != pages[state.verified]:
                        state.phase = "unstable"
                        self._save(state)
                        raise ArxivIntegrityError(
                            "Daily source changed during replay; next invocation restarts, watermark unchanged"
                        )
                    state.verified += 1
                    if state.verified == len(pages):
                        state.phase = "ready"
                else:
                    try:
                        self._validate_page(page, pages, ids, state.page_size)
                    except ArxivIntegrityError:
                        state.phase = "unstable"
                        self._save(state)
                        raise
                    payload = _encode(page.model_dump(mode="json"))
                    digest = _digest(payload)
                    _atomic_write(self.directory / "pages" / f"{digest}.json", payload)
                    pages.append(page)
                    state.pages.append(digest)
                    ids.update(record.id for record in page.records)
                    if offset + len(page.records) == page.total or (
                        page.records and min(page.updated_at.values()) < state.since
                    ):
                        state.phase = "verify"
                self._save(state)
            report = {
                "source_complete": state.phase == "ready",
                "corpus_written": False,
                "watermark_advanced": False,
                "invocation_requests": used,
                "total_requests": state.requests,
                "phase": state.phase,
                "since": state.since.isoformat(),
                "until": state.until.isoformat(),
                "pages": len(pages),
                "verified_pages": state.verified,
                "dry_run": dry_run,
            }
            if state.phase != "ready":
                return report
            records = [
                record
                for page in pages
                for record in page.records
                if state.since <= page.updated_at[record.id] < state.until
            ]
            db = PaperDatabase.load(self.data_path)
            candidate, receipt = prepare_ingestion(
                db, records, self.policy, MultiProviderEnricher(self.taxonomy_path)
            )
            report["import"] = receipt
            _atomic_write(self.directory / "imports" / f"{state.run_id}.json", _encode(report))
            if dry_run:
                return report
            if receipt["source_content_sha256"] != receipt["result_content_sha256"]:
                candidate.save(self.data_path)
                report["corpus_written"] = True
            persisted = PaperDatabase.load(self.data_path)
            if (
                _digest(_encode(persisted.model_dump(mode="json")))
                != receipt["result_content_sha256"]
            ):
                raise ValueError("Daily canonical write validation failed; watermark unchanged")
            _atomic_write(
                watermark_path,
                _encode(
                    {
                        "until": state.until.isoformat(),
                        "query": query,
                        "policy_digest": self.policy.digest,
                        "run_id": state.run_id,
                    }
                ),
            )
            state.phase = "applied"
            self._save(state)
            report.update(watermark_advanced=True, phase="applied")
            _atomic_write(self.directory / "imports" / f"{state.run_id}.json", _encode(report))
            return report

    @staticmethod
    def _validate_page(page, previous, ids, page_size):
        offset = sum(len(item.records) for item in previous)
        if page.start != offset or len(page.records) != min(page_size, max(0, page.total - offset)):
            raise ArxivIntegrityError("Daily source page offset/count mismatch")
        if previous and (page.total != previous[0].total or not page.records):
            raise ArxivIntegrityError("Daily source count changed; --restart required")
        if ids.intersection(record.id for record in page.records):
            raise ArxivIntegrityError("Daily source repeated an identity; --restart required")
        if previous and page.records and previous[-1].records:
            last = previous[-1].updated_at[previous[-1].records[-1].id]
            if page.updated_at[page.records[0].id] > last:
                raise ArxivIntegrityError("Daily source ordering changed; --restart required")
