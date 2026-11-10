"""Extraction eligibility and coverage without pretending pending sources were parsed."""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from src.schema import PaperDatabase
from src.storage import _atomic_write, _encode
from src.workers.queue import ExtractionQueue, StrictModel
from src.workers.review import ReviewedExtractionStore


class SourceTask(StrictModel):
    task_id: str
    paper_id: str
    stage: Literal["source_materialization"] = "source_materialization"
    status: Literal["queued"] = "queued"
    locators: list[str] = Field(min_length=1)
    identity_verification_required: Literal[True] = True


class ExtractionCoverage(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    source_content_sha256: str
    extractor_version: str
    records: dict[str, dict]
    source_tasks: dict[str, SourceTask]
    summary: dict[str, int]

    @model_validator(mode="after")
    def valid_inventory(self):
        if sum(self.summary.values()) != len(self.records):
            raise ValueError("Coverage count mismatch")
        for key, task in self.source_tasks.items():
            if key != task.task_id or task.paper_id not in self.records:
                raise ValueError("Orphaned source task")
            if self.records[task.paper_id]["source_task_id"] != key:
                raise ValueError("Source task linkage mismatch")
        return self

    def save(self, path: Path):
        payload = _encode(self.model_dump(mode="json"))
        if not path.exists() or path.read_bytes() != payload:
            _atomic_write(path, payload)


def scan_coverage(
    db: PaperDatabase,
    queues: list[ExtractionQueue],
    *,
    extractor_version: str,
    reviewed: ReviewedExtractionStore | None = None,
    local_sources: dict[str, list[str]] | None = None,
) -> ExtractionCoverage:
    if not extractor_version.strip():
        raise ValueError("Coverage requires explicit extractor version")
    jobs = {}
    for queue in queues:
        for key, job in queue.load().jobs.items():
            if key in jobs and jobs[key] != job:
                raise ValueError("Conflicting duplicate extraction jobs")
            jobs[key] = job
    active = {paper.id for paper in db.papers}
    by_paper = {key: [] for key in active}
    for job in jobs.values():
        if job.paper_id in active and job.extractor_version == extractor_version:
            by_paper[job.paper_id].append(job)
    reviewed = reviewed or ReviewedExtractionStore()
    records = {}
    tasks = {}
    for paper in sorted(db.papers, key=lambda paper: paper.id):
        candidates = sorted(
            by_paper[paper.id], key=lambda job: (job.updated_at, job.key), reverse=True
        )
        # Prefer a valid completed source over a later attempt on another PDF version.
        completed = [job for job in candidates if job.state in ("succeeded", "review-required")]
        job = completed[0] if completed else candidates[0] if candidates else None
        record = {
            "paper_id": paper.id,
            "state": None,
            "reason": None,
            "job_key": job.key if job else None,
            "pdf_sha256": job.pdf_sha256 if job else None,
            "source_task_id": None,
            "extraction_state": job.state if job else None,
            "accepted_cells": 0,
            "rejected_candidates": 0,
            "review_status": "unreviewed",
            "source_version_coverage": "one_verified_PDF" if completed else "not_processed",
        }
        if completed:
            record.update(
                state="processed",
                reason="Durable validated extraction result; candidates require review",
            )
            decisions = [item for item in reviewed.records.values() if item.job_key == job.key]
            if any(
                item.result_sha256 != job.result_sha256 or item.pdf_sha256 != job.pdf_sha256
                for item in decisions
            ):
                raise ValueError("Reviewed decisions do not match acknowledged result")
            record["accepted_cells"] = sum(
                item.decision.disposition == "accepted" and item.original.kind == "numeric_cell"
                for item in decisions
            )
            record["rejected_candidates"] = sum(
                item.decision.disposition == "rejected" for item in decisions
            )
            if decisions:
                record["review_status"] = "partially_reviewed"
        elif job and job.state == "failed":
            record.update(
                state="unsupported",
                reason=f"Attempt budget or configured parser/input limit: {job.failure_code}",
            )
        elif job:
            record.update(state="queued", reason="Durable extraction job pending execution/retry")
        else:
            locators = sorted(
                set(
                    (local_sources or {}).get(paper.id, [])
                    + ([paper.pdf_url] if paper.pdf_url else [])
                )
            )
            if locators:
                task_id = hashlib.sha256(
                    _encode([paper.id, extractor_version, locators])
                ).hexdigest()
                task = SourceTask(task_id=task_id, paper_id=paper.id, locators=locators)
                tasks[task_id] = task
                record.update(
                    state="queued",
                    reason="PDF source materialization and identity verification pending; no parser job claimed",
                    source_task_id=task_id,
                )
            else:
                record.update(
                    state="unavailable",
                    reason="No configured PDF locator or local candidate in this inventory; not a global availability claim",
                )
        records[paper.id] = record
    return ExtractionCoverage(
        source_content_sha256=hashlib.sha256(_encode(db.model_dump(mode="json"))).hexdigest(),
        extractor_version=extractor_version,
        records=records,
        source_tasks=tasks,
        summary=dict(Counter(record["state"] for record in records.values())),
    )
