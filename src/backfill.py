"""Resumable, count-reconciled historical arXiv discovery with immutable page caches."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.extractors.arxiv import ArxivExtractor, ArxivIntegrityError, ArxivPage
from src.file_lock import exclusive_file
from src.schema import PaperRecord
from src.storage import _atomic_write, _digest, _encode, _read_component


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def aware_times(self):
        for field in type(self).model_fields:
            value = getattr(self, field)
            values = value.values() if isinstance(value, dict) else [value]
            if any(isinstance(item, datetime) and item.utcoffset() is None for item in values):
                raise ValueError("Source checkpoint timestamps require a timezone")
        return self


class HistoricalSpec(SourceModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1)
    comparator_query: str
    query_version: str = "gs-query-v1"
    policy_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    since: datetime
    until: datetime
    page_size: int = Field(default=100, ge=1, le=1000)
    max_slice_results: int = Field(default=1000, ge=1, le=30000)

    @model_validator(mode="after")
    def validate_bounds(self):
        for value in (self.since, self.until):
            if value.utcoffset() is None:
                raise ValueError("Historical bounds require a timezone")
        self.since, self.until = self.since.astimezone(UTC), self.until.astimezone(UTC)
        if self.since > self.until or self.max_slice_results < self.page_size:
            raise ValueError("Invalid historical bounds or slice budget")
        return self

    @property
    def digest(self) -> str:
        return _digest(_encode(self.model_dump(mode="json")))


def interval_key(start: datetime, end: datetime) -> str:
    return _digest(f"{start.isoformat()}|{end.isoformat()}".encode())[:16]


def query_bounds(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    lower = start.replace(second=0, microsecond=0)
    upper = end.replace(second=0, microsecond=0)
    if upper < end:
        upper += timedelta(minutes=1)
    return lower, upper


def submitted_query(query: str, start: datetime, end: datetime) -> str:
    lower, upper = query_bounds(start, end)
    return f"({query}) AND submittedDate:[{lower:%Y%m%d%H%M} TO {upper:%Y%m%d%H%M}]"


class PageRef(SourceModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    start: int = Field(ge=0)
    count: int = Field(ge=0)


class SliceState(SourceModel):
    model_config = ConfigDict(extra="forbid")
    start: datetime
    end: datetime
    query: str
    status: Literal["pending", "running", "subdivided", "complete", "failed"] = "pending"
    offset: int = Field(default=0, ge=0)
    expected_total: int | None = Field(default=None, ge=0)
    pages: list[PageRef] = Field(default_factory=list)
    probe: PageRef | None = None
    children: list[str] = Field(default_factory=list)
    last_error: str | None = None


class RequestAudit(SourceModel):
    model_config = ConfigDict(extra="forbid")
    slice_id: str
    start: int = Field(ge=0)
    attempt_budget: int = Field(ge=1, le=3)
    status: Literal["started", "succeeded", "error", "interrupted"] = "started"
    attempts: int | None = Field(default=None, ge=0, le=3)
    rows: int | None = Field(default=None, ge=0)
    replay: bool = False
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    error: str | None = None


class HistoricalState(SourceModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0.0"] = "1.0.0"
    spec: HistoricalSpec
    query_digest: str
    roots: list[str] = Field(default_factory=list)
    slices: dict[str, SliceState] = Field(default_factory=dict)
    requests: list[RequestAudit] = Field(default_factory=list)
    status: Literal["running", "complete", "failed"] = "running"


class CachedPage(SourceModel):
    model_config = ConfigDict(extra="forbid")
    query_digest: str
    slice_id: str
    source_start: int
    source_total: int
    fetched_at: datetime
    records: list[PaperRecord]
    published_at: dict[str, datetime]
    updated_at: dict[str, datetime]


class _BudgetExhausted(Exception):
    pass


class HistoricalCrawler:
    """Discovery stage: source pages are durable before a cursor is acknowledged.

    This class does not mutate the canonical corpus. Import can use only the
    validated completed slices and must publish its own candidate dispositions.
    """

    def __init__(self, spec: HistoricalSpec, directory: str | Path, source: ArxivExtractor):
        self.spec, self.directory, self.source = spec, Path(directory), source
        self.checkpoint = self.directory / "checkpoint.json"
        self.state: HistoricalState | None = None
        self.remaining = 0
        self.invocation_requests = 0

    def _save(self):
        payload = _encode(self.state.model_dump(mode="json"))
        if not self.checkpoint.exists() or self.checkpoint.read_bytes() != payload:
            _atomic_write(self.checkpoint, payload)

    def _add_slice(self, start: datetime, end: datetime) -> str:
        key = interval_key(start, end)
        existing = self.state.slices.get(key)
        if existing and (existing.start, existing.end) != (start, end):
            raise ArxivIntegrityError("Historical slice digest collision")
        self.state.slices.setdefault(
            key,
            SliceState(start=start, end=end, query=submitted_query(self.spec.query, start, end)),
        )
        return key

    def _months(self):
        cursor = self.spec.since
        while cursor < self.spec.until:
            following = (
                cursor.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                + timedelta(days=32)
            ).replace(day=1)
            end = min(following, self.spec.until)
            yield cursor, end
            cursor = end

    def _validate_structure(self):
        expected = [interval_key(start, end) for start, end in self._months()]
        if self.state.roots != expected:
            raise ArxivIntegrityError("Historical root inventory does not match frozen bounds")
        visited, active = set(), set()

        def visit(key, start, end):
            if key in active or key in visited:
                raise ArxivIntegrityError("Historical slice graph contains a cycle or shared child")
            interval = self.state.slices.get(key)
            if (
                interval is None
                or key != interval_key(start, end)
                or (interval.start, interval.end) != (start, end)
            ):
                raise ArxivIntegrityError("Historical slice bounds/identity changed")
            active.add(key)
            if interval.children:
                if (
                    len(interval.children) != 2
                    or len(set(interval.children)) != 2
                    or interval.expected_total is None
                    or interval.probe is None
                    or interval.pages
                    or interval.offset
                ):
                    raise ArxivIntegrityError("Invalid source subdivision state")
                left, right = (self.state.slices.get(child) for child in interval.children)
                if (
                    left is None
                    or right is None
                    or left.end != right.start
                    or not start < left.end < end
                ):
                    raise ArxivIntegrityError("Source subdivisions leave a gap or overlap")
                visit(interval.children[0], start, left.end)
                visit(interval.children[1], left.end, end)
                if interval.status == "complete" and any(
                    self.state.slices[child].status != "complete" for child in interval.children
                ):
                    raise ArxivIntegrityError("Parent is complete before its children")
            elif interval.status == "subdivided" or (
                interval.status == "complete"
                and interval.expected_total is not None
                and interval.expected_total > self.spec.max_slice_results
            ):
                raise ArxivIntegrityError("Missing required source subdivision")
            active.remove(key)
            visited.add(key)

        for key, (start, end) in zip(expected, self._months(), strict=True):
            visit(key, start, end)
        if visited != set(self.state.slices):
            raise ArxivIntegrityError("Unreferenced historical slice checkpoints")
        if self.state.status == "complete" and any(
            self.state.slices[key].status != "complete" for key in self.state.roots
        ):
            raise ArxivIntegrityError("Run is complete before its source intervals")

    def _load(self):
        if self.checkpoint.exists():
            self.state = HistoricalState.model_validate_json(self.checkpoint.read_bytes())
            if self.state.query_digest != self.spec.digest or self.state.spec != self.spec:
                raise ValueError(
                    "Query, cutoff, policy, or paging contract changed; use a new run directory"
                )
            self._validate_structure()
            for request in self.state.requests:
                if request.status == "started":
                    request.status = "interrupted"
            for key, interval in self.state.slices.items():
                if interval.query != submitted_query(self.spec.query, interval.start, interval.end):
                    raise ArxivIntegrityError("Stored slice query changed")
                if any(child not in self.state.slices for child in interval.children):
                    raise ArxivIntegrityError("Missing subdivision checkpoint")
                self._cached_pages(key)
            return
        self.state = HistoricalState(spec=self.spec, query_digest=self.spec.digest)
        for start, end in self._months():
            self.state.roots.append(self._add_slice(start, end))
        self._save()

    def _read(self, key: str, reference: PageRef) -> CachedPage:
        page = CachedPage.model_validate(_read_component(self.checkpoint, reference.model_dump()))
        interval = self.state.slices[key]
        if (
            page.query_digest,
            page.slice_id,
            page.source_start,
            len(page.records),
            page.source_total,
        ) != (self.spec.digest, key, reference.start, reference.count, interval.expected_total):
            raise ArxivIntegrityError("Cached page inventory disagrees with checkpoint")
        ids = {record.id for record in page.records}
        if (
            len(ids) != len(page.records)
            or set(page.published_at) != ids
            or set(page.updated_at) != ids
        ):
            raise ArxivIntegrityError("Cached page timestamps/IDs are inconsistent")
        return page

    def _cached_pages(self, key: str) -> list[CachedPage]:
        interval = self.state.slices[key]
        pages, ids, cursor = [], set(), 0
        for reference in interval.pages:
            page = self._read(key, reference)
            if page.source_start != cursor or ids & {record.id for record in page.records}:
                raise ArxivIntegrityError("Repeated or noncontiguous cached source page")
            cursor += len(page.records)
            ids.update(record.id for record in page.records)
            pages.append(page)
        if cursor != interval.offset:
            raise ArxivIntegrityError("Checkpoint cursor exceeds durable page persistence")
        if interval.probe:
            self._read(key, interval.probe)
        if (
            interval.status == "complete"
            and not interval.children
            and cursor != interval.expected_total
        ):
            raise ArxivIntegrityError("Completed source slice is not count reconciled")
        return pages

    def _fetch(self, key: str, start: int, *, replay: bool = False, reserve: int = 0) -> ArxivPage:
        if self.remaining <= reserve:
            raise _BudgetExhausted
        interval = self.state.slices[key]
        audit = RequestAudit(
            slice_id=key,
            start=start,
            replay=replay,
            attempt_budget=min(3, self.remaining - reserve),
        )
        self.state.requests.append(audit)
        self._save()
        try:
            page = self.source.fetch_page(
                query=interval.query,
                start=start,
                page_size=self.spec.page_size,
                sort_by="submittedDate",
                sort_order="ascending",
                max_attempts=audit.attempt_budget,
            )
            self.remaining -= page.attempts
            self.invocation_requests += page.attempts
            audit.attempts, audit.rows = page.attempts, len(page.records)
            if not 1 <= page.attempts <= audit.attempt_budget:
                raise ArxivIntegrityError("Source exceeded its request budget")
            expected = min(self.spec.page_size, max(0, page.total - start))
            if page.start != start or len(page.records) != expected:
                raise ArxivIntegrityError("Source paging contract changed")
            lower, upper = query_bounds(interval.start, interval.end)
            stamps = [page.published_at[record.id] for record in page.records]
            if stamps != sorted(stamps) or any(
                stamp < lower or stamp >= upper + timedelta(minutes=1) for stamp in stamps
            ):
                raise ArxivIntegrityError("Source ignored submitted ordering or date bounds")
            if interval.expected_total is not None and page.total != interval.expected_total:
                raise ArxivIntegrityError("Source total changed during frozen-query paging")
            audit.status = "succeeded"
            audit.finished_at = datetime.now(UTC)
            return page
        except Exception as error:
            if audit.attempts is None:
                audit.attempts = getattr(error, "attempts", None)
                if audit.attempts is not None:
                    self.remaining -= audit.attempts
                    self.invocation_requests += audit.attempts
            audit.status, audit.error = "error", f"{type(error).__name__}: {str(error)[:240]}"
            audit.finished_at = datetime.now(UTC)
            self._save()
            raise

    def _cache(self, key: str, page: ArxivPage) -> PageRef:
        cached = CachedPage(
            query_digest=self.spec.digest,
            slice_id=key,
            source_start=page.start,
            source_total=page.total,
            fetched_at=datetime.now(UTC),
            records=list(page.records),
            published_at=page.published_at,
            updated_at=page.updated_at,
        )
        payload = _encode(cached.model_dump(mode="json"))
        digest = _digest(payload)
        relative = f"pages/{key}/{page.start:08d}.{digest}.json"
        _atomic_write(self.directory / relative, payload)
        return PageRef(path=relative, sha256=digest, start=page.start, count=len(page.records))

    def _walk(self, key: str):
        interval = self.state.slices[key]
        if interval.status == "complete":
            return
        try:
            if interval.children:
                for child in interval.children:
                    self._walk(child)
                raw_ids = {
                    record.id
                    for child in interval.children
                    for page in self._leaf_pages(child)
                    for record in page.records
                }
                if len(raw_ids) != interval.expected_total:
                    raise ArxivIntegrityError(
                        "Subdivided source inventory does not reconcile with parent total"
                    )
                interval.status, interval.last_error = "complete", None
                self._save()
                return
            cached = self._cached_pages(key)
            if cached:
                if self.remaining < 2:
                    raise _BudgetExhausted
                old = cached[-1]
                replay = self._fetch(key, old.source_start, replay=True, reserve=1)
                if {record.id for record in replay.records} != {
                    record.id for record in old.records
                }:
                    raise ArxivIntegrityError(
                        "Replay boundary IDs changed; source slice requires reconciliation"
                    )
                interval.pages[-1] = self._cache(key, replay)
                self._save()
                cached = self._cached_pages(key)
            seen = {record.id for page in cached for record in page.records}
            previous = max(
                (stamp for page in cached for stamp in page.published_at.values()), default=None
            )
            while interval.expected_total is None or interval.offset < interval.expected_total:
                page = self._fetch(key, interval.offset)
                interval.expected_total = page.total
                if page.total > self.spec.max_slice_results:
                    interval.probe = self._cache(key, page)
                    middle = (interval.start + (interval.end - interval.start) / 2).replace(
                        second=0, microsecond=0
                    )
                    if not interval.start < middle < interval.end:
                        raise ArxivIntegrityError(
                            "Dense minimum-sized source interval needs explicit reconciliation"
                        )
                    interval.children = [
                        self._add_slice(interval.start, middle),
                        self._add_slice(middle, interval.end),
                    ]
                    interval.status = "subdivided"
                    self._save()
                    self._walk(key)
                    return
                new_ids = {record.id for record in page.records}
                if seen & new_ids or len(new_ids) != len(page.records):
                    raise ArxivIntegrityError("Repeated source page/IDs; cursor not advanced")
                if (
                    previous is not None
                    and page.records
                    and min(page.published_at.values()) < previous
                ):
                    raise ArxivIntegrityError("Source ordering changed across pages")
                reference = self._cache(key, page)
                interval.pages.append(reference)
                interval.offset += len(page.records)
                seen |= new_ids
                previous = max(page.published_at.values(), default=previous)
                interval.status, interval.last_error = "running", None
                self._save()
            interval.status = "complete"
            self._save()
        except _BudgetExhausted:
            raise
        except Exception as error:
            interval.status = "failed"
            interval.last_error = f"{type(error).__name__}: {str(error)[:240]}"
            self.state.status = "failed"
            self._save()
            raise

    def _leaf_pages(self, key: str) -> list[CachedPage]:
        interval = self.state.slices[key]
        if interval.children:
            return [page for child in interval.children for page in self._leaf_pages(child)]
        return self._cached_pages(key)

    def records(self) -> list[PaperRecord]:
        if self.state is None or self.state.status != "complete":
            raise ValueError("Historical run is incomplete")
        latest = {}
        for key in self.state.roots:
            for page in self._leaf_pages(key):
                for record in page.records:
                    if self.spec.since <= page.published_at[record.id] < self.spec.until:
                        observed = (page.updated_at[record.id], page.fetched_at)
                        if record.id not in latest or observed > latest[record.id][0]:
                            latest[record.id] = (observed, record)
        return [latest[key][1] for key in sorted(latest)]

    def run(self, *, max_requests: int = 100) -> dict:
        if type(max_requests) is not int or max_requests < 1:
            raise ValueError("Request budget must be positive")
        self.remaining, self.invocation_requests = max_requests, 0
        with exclusive_file(self.directory / ".run.lock"):
            self._load()
            if self.state.status != "complete":
                if max_requests < 2 and any(
                    interval.pages and interval.status != "complete"
                    for interval in self.state.slices.values()
                ):
                    raise ValueError(
                        "Resume needs at least two requests to replay a boundary and progress"
                    )
                self.state.status = "running"
                try:
                    for key in self.state.roots:
                        self._walk(key)
                    self.state.status = "complete"
                except _BudgetExhausted:
                    pass
                self._save()
            unknown = [request for request in self.state.requests if request.attempts is None]
            return {
                "status": self.state.status,
                "query_digest": self.spec.digest,
                "invocation_requests": self.invocation_requests,
                "known_total_attempts": sum(
                    request.attempts or 0 for request in self.state.requests
                ),
                "interrupted_attempt_upper_bound": sum(
                    request.attempt_budget for request in unknown
                ),
                "intervals": len(self.state.slices),
                "completed_intervals": sum(
                    interval.status == "complete" for interval in self.state.slices.values()
                ),
                "unique_in_interval": len(self.records())
                if self.state.status == "complete"
                else None,
            }
