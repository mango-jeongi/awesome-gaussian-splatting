"""Crash-safe local extraction queue. A lease token fences late worker results."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.file_lock import exclusive_file
from src.storage import _atomic_write, _encode


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ExtractionLimits(StrictModel):
    max_bytes: int = Field(default=50_000_000, gt=0, le=200_000_000)
    max_pages: int = Field(default=100, gt=0, le=1000)
    timeout_seconds: int = Field(default=120, gt=0, le=3600)
    max_attempts: int = Field(default=3, gt=0, le=5)


def job_key(paper_id: str, pdf_sha256: str, extractor_version: str) -> str:
    return hashlib.sha256(_encode([paper_id, pdf_sha256, extractor_version])).hexdigest()


class ExtractionJob(StrictModel):
    key: str
    paper_id: str = Field(min_length=1)
    pdf_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extractor_version: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    limits: ExtractionLimits = Field(default_factory=ExtractionLimits)
    state: Literal[
        "queued", "leased", "succeeded", "failed/retryable", "failed", "review-required"
    ] = "queued"
    attempts: int = Field(default=0, ge=0)
    lease_token: str | None = None
    lease_expires_at: datetime | None = None
    updated_at: datetime
    failure_code: str | None = None
    result_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid_job(self):
        if self.key != job_key(self.paper_id, self.pdf_sha256, self.extractor_version):
            raise ValueError("Job identity digest mismatch")
        if (
            self.updated_at.utcoffset() is None
            or self.lease_expires_at
            and self.lease_expires_at.utcoffset() is None
        ):
            raise ValueError("Queue timestamps require a timezone")
        if (self.state == "leased" and not (self.lease_token and self.lease_expires_at)) or (
            self.state != "leased"
            and (self.lease_token is not None or self.lease_expires_at is not None)
        ):
            raise ValueError("Invalid lease state")
        if self.attempts > self.limits.max_attempts:
            raise ValueError("Attempt budget exceeded")
        if (self.state in ("succeeded", "review-required")) != bool(self.result_sha256):
            raise ValueError("Terminal success requires a durable result digest")
        return self


class ExtractedCandidate(StrictModel):
    kind: Literal["numeric_cell", "figure"]
    page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]
    caption: str | None = None
    table_heading: str | None = None
    dataset: str | None = None
    split: str | None = None
    metric: str | None = None
    unit: str | None = None
    row_label: str | None = None
    column_label: str | None = None
    raw_value: str | None = None
    confidence: float = Field(ge=0, le=1)
    reuse_basis: str | None = None
    review_required: Literal[True] = True

    @model_validator(mode="after")
    def valid_candidate(self):
        x0, y0, x1, y1 = self.bbox
        if min(self.bbox) < 0 or x1 <= x0 or y1 <= y0:
            raise ValueError("Invalid page bounding box")
        if self.kind == "numeric_cell" and not self.raw_value:
            raise ValueError("Numeric candidate requires source text")
        return self


class ExtractionResult(StrictModel):
    job_key: str
    paper_id: str
    pdf_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extractor_version: str
    completed_at: datetime
    page_count: int = Field(ge=1)
    candidates: list[ExtractedCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_result(self):
        if self.job_key != job_key(self.paper_id, self.pdf_sha256, self.extractor_version):
            raise ValueError("Result identity mismatch")
        if self.completed_at.utcoffset() is None:
            raise ValueError("Result requires aware completion time")
        if any(candidate.page > self.page_count for candidate in self.candidates):
            raise ValueError("Candidate page exceeds source pages")
        return self


class QueueState(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    jobs: dict[str, ExtractionJob] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_keys(self):
        if any(key != job.key for key, job in self.jobs.items()):
            raise ValueError("Queue job key mismatch")
        return self


class ExtractionQueue:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "queue.json"
        self.lock = self.root / "queue.run.lock"

    def load(self):
        state = (
            QueueState.model_validate_json(self.path.read_bytes())
            if self.path.exists()
            else QueueState()
        )
        for job in state.jobs.values():
            if not job.result_sha256:
                continue
            path = self._result_path(job.key)
            if (
                not path.exists()
                or hashlib.sha256(path.read_bytes()).hexdigest() != job.result_sha256
            ):
                raise ValueError("Missing or corrupt acknowledged worker result")
            result = ExtractionResult.model_validate_json(path.read_bytes())
            if result.job_key != job.key or result.page_count > job.limits.max_pages:
                raise ValueError("Acknowledged result violates job contract")
        return state

    def _save(self, state):
        payload = _encode(QueueState.model_validate(state.model_dump()).model_dump(mode="json"))
        if not self.path.exists() or self.path.read_bytes() != payload:
            _atomic_write(self.path, payload)

    def enqueue(
        self,
        paper_id: str,
        pdf_sha256: str,
        extractor_version: str,
        source_url: str,
        *,
        limits: ExtractionLimits | None = None,
        now: datetime | None = None,
    ):
        now = now or datetime.now(UTC)
        job = ExtractionJob(
            key=job_key(paper_id, pdf_sha256, extractor_version),
            paper_id=paper_id,
            pdf_sha256=pdf_sha256,
            extractor_version=extractor_version,
            source_url=source_url,
            limits=limits or ExtractionLimits(),
            updated_at=now,
        )
        with exclusive_file(self.lock, resource="extraction queue"):
            state = self.load()
            if job.key in state.jobs:
                old = state.jobs[job.key]
                if old.source_url != source_url or old.limits != job.limits:
                    raise ValueError("Existing job configuration is immutable")
                return old
            state.jobs[job.key] = job
            self._save(state)
            return job

    def _result_path(self, key):
        if len(key) != 64 or any(char not in "0123456789abcdef" for char in key):
            raise ValueError("Invalid job key")
        return self.root / "results" / f"{key}.json"

    def _recover_result(self, job, now):
        path = self._result_path(job.key)
        if not path.exists():
            return False
        result = ExtractionResult.model_validate_json(path.read_bytes())
        if result.job_key != job.key or result.page_count > job.limits.max_pages:
            raise ValueError("Durable result violates job contract")
        job.result_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        job.failure_code = None
        job.state = "review-required" if result.candidates or result.warnings else "succeeded"
        job.lease_token = job.lease_expires_at = None
        job.updated_at = now
        return True

    def claim(
        self, *, now: datetime | None = None, exclude_keys: set[str] | None = None
    ) -> ExtractionJob | None:
        now = now or datetime.now(UTC)
        if now.utcoffset() is None:
            raise ValueError("Claim requires aware time")
        with exclusive_file(self.lock, resource="extraction queue"):
            state = self.load()
            for key in sorted(state.jobs):
                if exclude_keys and key in exclude_keys:
                    continue
                job = state.jobs[key]
                if now < job.updated_at:
                    raise ValueError("Queue time moved backwards")
                if job.state in ("succeeded", "review-required", "failed"):
                    continue
                if self._recover_result(job, now):
                    continue
                if job.state == "leased" and job.lease_expires_at > now:
                    continue
                if job.state == "failed/retryable" and job.failure_code in (
                    "size_limit",
                    "page_limit",
                    "invalid_pdf",
                ):
                    job.state = "failed"
                    continue
                if job.attempts >= job.limits.max_attempts:
                    job.state = "failed"
                    job.failure_code = "attempt_budget"
                    job.lease_token = job.lease_expires_at = None
                    continue
                job.attempts += 1
                job.state = "leased"
                job.lease_token = uuid.uuid4().hex
                job.lease_expires_at = now + timedelta(seconds=job.limits.timeout_seconds + 30)
                job.updated_at = now
                job.failure_code = None
                self._save(state)
                return job.model_copy(deep=True)
            self._save(state)
            return None

    @staticmethod
    def _leased(state, key, token, now):
        job = state.jobs[key]
        if (
            now.utcoffset() is None
            or now < job.updated_at
            or job.state != "leased"
            or job.lease_token != token
            or job.lease_expires_at <= now
        ):
            raise ValueError("Missing, expired, or superseded worker lease")
        return job

    def finish(self, key, token, result: ExtractionResult, *, now: datetime | None = None):
        now = now or datetime.now(UTC)
        with exclusive_file(self.lock, resource="extraction queue"):
            state = self.load()
            job = self._leased(state, key, token, now)
            result = ExtractionResult.model_validate(result.model_dump())
            if (
                result.job_key != key
                or result.page_count > job.limits.max_pages
                or result.completed_at > now
            ):
                raise ValueError("Result does not satisfy the leased job")
            payload = _encode(result.model_dump(mode="json"))
            path = self._result_path(key)
            if path.exists() and path.read_bytes() != payload:
                raise ValueError("Conflicting immutable result")
            if not path.exists():
                _atomic_write(path, payload)
            self._recover_result(job, now)
            self._save(state)

    def fail(
        self,
        key,
        token,
        code: Literal[
            "timeout", "pdf_unavailable", "invalid_pdf", "size_limit", "page_limit", "parser_error"
        ],
        *,
        now: datetime | None = None,
    ):
        now = now or datetime.now(UTC)
        with exclusive_file(self.lock, resource="extraction queue"):
            state = self.load()
            job = self._leased(state, key, token, now)
            job.state = (
                "failed/retryable"
                if job.attempts < job.limits.max_attempts
                and code not in ("size_limit", "page_limit", "invalid_pdf")
                else "failed"
            )
            job.failure_code = code
            job.updated_at = now
            job.lease_token = job.lease_expires_at = None
            self._save(state)
