"""Snapshot-bound human review of extraction candidates, separate from bibliographic data."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from src.file_lock import exclusive_file
from src.schema import PaperDatabase
from src.storage import _atomic_write, _encode
from src.workers.queue import ExtractedCandidate, ExtractionResult, StrictModel


class CandidateDecision(StrictModel):
    candidate_index: int = Field(ge=0)
    disposition: Literal["accepted", "rejected"]
    reason: str = Field(min_length=1)
    source_checked: Literal[True]
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    dataset: str | None = None
    split: str | None = None
    metric: str | None = None
    unit: str | None = None
    row_label: str | None = None
    column_label: str | None = None
    accepted_value: str | None = None
    caption: str | None = None
    reuse_basis: str | None = None

    @field_validator("reviewed_by", "reason")
    @classmethod
    def nonblank_review(cls, value):
        if not value.strip():
            raise ValueError("Review identity and reason cannot be blank")
        return value

    @model_validator(mode="after")
    def aware_review(self):
        if self.reviewed_at.utcoffset() is None:
            raise ValueError("Review requires an aware timestamp")
        return self


class ExtractionReview(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    expected_content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_result_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_url: str = Field(min_length=1)
    decisions: list[CandidateDecision] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_decisions(self):
        if len({decision.candidate_index for decision in self.decisions}) != len(self.decisions):
            raise ValueError("Duplicate candidate decisions")
        return self


class ReviewedCandidate(StrictModel):
    paper_id: str
    job_key: str
    pdf_sha256: str
    result_sha256: str
    source_url: str
    original: ExtractedCandidate
    decision: CandidateDecision

    @model_validator(mode="after")
    def accepted_context(self):
        if self.decision.disposition != "accepted":
            return self
        fields = (
            ("dataset", "split", "metric", "unit", "row_label", "column_label", "accepted_value")
            if self.original.kind == "numeric_cell"
            else ("caption", "reuse_basis")
        )
        for field in fields:
            value = getattr(self.decision, field)
            if not value or value.strip().lower() in ("unknown", "unavailable", "?", "tbd"):
                raise ValueError(f"Accepted {self.original.kind} requires reviewed {field}")
        return self


class ReviewedExtractionStore(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    records: dict[str, ReviewedCandidate] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_keys(self):
        for key, record in self.records.items():
            if key != f"{record.job_key}:{record.decision.candidate_index}":
                raise ValueError("Reviewed candidate key mismatch")
        return self


def import_review(
    *,
    data_path: Path,
    ledger_path: Path,
    result_path: Path,
    pdf_path: Path,
    review: ExtractionReview,
    dry_run: bool = False,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(UTC)
    review = ExtractionReview.model_validate(review.model_dump())
    if now.utcoffset() is None:
        raise ValueError("Import requires aware time")
    raw = result_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != review.expected_result_sha256:
        raise ValueError("Reviewed result bytes changed")
    result = ExtractionResult.model_validate_json(raw)
    source_digest = hashlib.sha256()
    with pdf_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            source_digest.update(chunk)
    if source_digest.hexdigest() != result.pdf_sha256:
        raise ValueError("Reviewed PDF digest mismatch")
    # Same canonical writer lock as metadata publication, then the extraction ledger lock.
    with exclusive_file(str(data_path) + ".writer.lock", resource="repository writer"):
        with exclusive_file(
            str(ledger_path) + ".writer.lock", resource="reviewed extraction writer"
        ):
            db = PaperDatabase.load(data_path)
            if result.paper_id not in {paper.id for paper in db.papers}:
                raise ValueError("Reviewed paper is not active")
            actual = hashlib.sha256(_encode(db.model_dump(mode="json"))).hexdigest()
            store = (
                ReviewedExtractionStore.model_validate_json(ledger_path.read_bytes())
                if ledger_path.exists()
                else ReviewedExtractionStore()
            )
            added = 0
            candidate = store.model_copy(deep=True)
            for decision in review.decisions:
                if decision.reviewed_at > now or decision.reviewed_at < result.completed_at:
                    raise ValueError("Review must follow extraction and cannot be in the future")
                if decision.candidate_index >= len(result.candidates):
                    raise ValueError("Candidate index outside result")
                record = ReviewedCandidate(
                    paper_id=result.paper_id,
                    job_key=result.job_key,
                    pdf_sha256=result.pdf_sha256,
                    result_sha256=digest,
                    source_url=review.source_url,
                    original=result.candidates[decision.candidate_index],
                    decision=decision,
                )
                key = f"{result.job_key}:{decision.candidate_index}"
                if key in store.records:
                    if store.records[key] != record:
                        raise ValueError("Conflicting reviewed decision requires adjudication")
                    continue
                if review.expected_content_sha256 != actual:
                    raise ValueError("Review corpus snapshot is stale")
                candidate.records[key] = record
                added += 1
            payload = _encode(candidate.model_dump(mode="json"))
            if not dry_run and added:
                _atomic_write(ledger_path, payload)
            return {
                "dry_run": dry_run,
                "added": added,
                "unchanged": len(review.decisions) - added,
                "accepted": sum(
                    record.decision.disposition == "accepted"
                    for record in candidate.records.values()
                ),
                "rejected": sum(
                    record.decision.disposition == "rejected"
                    for record in candidate.records.values()
                ),
                "corpus_modified": False,
                "source_content_sha256": actual,
            }
