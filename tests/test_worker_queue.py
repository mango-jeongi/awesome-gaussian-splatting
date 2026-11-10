import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from src.workers.queue import (
    ExtractedCandidate,
    ExtractionLimits,
    ExtractionQueue,
    ExtractionResult,
)

NOW = datetime(2026, 11, 9, tzinfo=UTC)
PDF = hashlib.sha256(b"fixture PDF").hexdigest()


def enqueue(queue, **kwargs):
    return queue.enqueue(
        "paper/special:β", PDF, "extract-v1", "https://example.org/paper.pdf", now=NOW, **kwargs
    )


def result(job, **kwargs):
    return ExtractionResult(
        job_key=job.key,
        paper_id=job.paper_id,
        pdf_sha256=job.pdf_sha256,
        extractor_version=job.extractor_version,
        completed_at=NOW,
        page_count=2,
        **kwargs,
    )


def test_identity_noop_and_configuration_immutability(tmp_path):
    queue = ExtractionQueue(tmp_path)
    job = enqueue(queue)
    before = queue.path.read_bytes(), queue.path.stat().st_mtime_ns
    assert enqueue(queue) == job
    assert before == (queue.path.read_bytes(), queue.path.stat().st_mtime_ns)
    with pytest.raises(ValueError, match="immutable"):
        enqueue(queue, limits=ExtractionLimits(max_pages=3))
    changed = queue.enqueue(job.paper_id, "0" * 64, job.extractor_version, job.source_url, now=NOW)
    assert changed.key != job.key


def test_expired_lease_recovered_once_and_old_worker_fenced(tmp_path):
    queue = ExtractionQueue(tmp_path)
    job = enqueue(queue)
    first = queue.claim(now=NOW)
    assert first.attempts == 1
    assert queue.claim(now=NOW + timedelta(seconds=1)) is None
    later = first.lease_expires_at
    second = queue.claim(now=later)
    assert (
        second.key == job.key and second.attempts == 2 and second.lease_token != first.lease_token
    )
    with pytest.raises(ValueError, match="lease"):
        queue.finish(job.key, first.lease_token, result(first), now=later)
    queue.finish(job.key, second.lease_token, result(second), now=later)
    assert queue.claim(now=later) is None
    assert len(list((tmp_path / "results").glob("*.json"))) == 1
    assert queue.load().jobs[job.key].state == "succeeded"


def test_result_before_ack_crash_recovers_without_second_attempt(tmp_path, monkeypatch):
    queue = ExtractionQueue(tmp_path)
    job = enqueue(queue)
    leased = queue.claim(now=NOW)
    original = queue._save

    def crash(state):
        raise OSError("Injected acknowledgment interruption")

    monkeypatch.setattr(queue, "_save", crash)
    with pytest.raises(OSError):
        queue.finish(job.key, leased.lease_token, result(leased), now=NOW)
    assert queue.load().jobs[job.key].state == "leased"
    monkeypatch.setattr(queue, "_save", original)
    assert queue.claim(now=NOW) is None
    recovered = queue.load().jobs[job.key]
    assert recovered.state == "succeeded" and recovered.attempts == 1


def test_partial_numeric_provenance_forces_review(tmp_path):
    queue = ExtractionQueue(tmp_path)
    enqueue(queue)
    job = queue.claim(now=NOW)
    cell = ExtractedCandidate(
        kind="numeric_cell", page=2, bbox=(0, 0, 10, 20), raw_value="31.4", confidence=0.6
    )
    assert cell.unit is None and cell.review_required
    queue.finish(job.key, job.lease_token, result(job, candidates=[cell]), now=NOW)
    assert queue.load().jobs[job.key].state == "review-required"
    with pytest.raises(ValueError):
        ExtractedCandidate(
            kind="numeric_cell", page=1, bbox=(1, 1, 0, 0), raw_value="1", confidence=0.8
        )
    with pytest.raises(ValueError):
        result(job, candidates=[cell.model_copy(update={"page": 3})])


def test_attempt_budget_and_corruption_fail_closed(tmp_path):
    queue = ExtractionQueue(tmp_path)
    enqueue(queue, limits=ExtractionLimits(max_attempts=1))
    leased = queue.claim(now=NOW)
    queue.fail(leased.key, leased.lease_token, "parser_error", now=NOW)
    assert queue.claim(now=NOW) is None
    assert queue.load().jobs[leased.key].state == "failed"
    queue.path.write_text("{broken")
    with pytest.raises(ValueError):
        queue.claim(now=NOW)


def test_oversized_result_and_conflicting_identity_rejected(tmp_path):
    queue = ExtractionQueue(tmp_path)
    enqueue(queue, limits=ExtractionLimits(max_pages=1))
    job = queue.claim(now=NOW)
    with pytest.raises(ValueError):
        queue.finish(job.key, job.lease_token, result(job), now=NOW)
    assert queue.load().jobs[job.key].state == "leased"
    with pytest.raises(ValueError):
        result(job).model_copy(update={"paper_id": "wrong"}).model_validate(
            result(job).model_copy(update={"paper_id": "wrong"}).model_dump()
        )


def test_acknowledged_result_corruption_is_detected(tmp_path):
    queue = ExtractionQueue(tmp_path)
    enqueue(queue)
    job = queue.claim(now=NOW)
    queue.finish(job.key, job.lease_token, result(job), now=NOW)
    path = tmp_path / "results" / f"{job.key}.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="corrupt acknowledged"):
        queue.load()


@pytest.mark.parametrize("code", ["size_limit", "page_limit", "invalid_pdf"])
def test_immutable_source_limit_failure_is_terminal(tmp_path, code):
    queue = ExtractionQueue(tmp_path)
    enqueue(queue)
    job = queue.claim(now=NOW)
    queue.fail(job.key, job.lease_token, code, now=NOW)
    assert queue.load().jobs[job.key].state == "failed"
    assert queue.claim(now=NOW) is None
    assert queue.load().jobs[job.key].attempts == 1
