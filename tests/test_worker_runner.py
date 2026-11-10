import hashlib
import subprocess
import sys
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.workers.pdf_parser import extract
from src.workers.queue import ExtractionJob, ExtractionLimits, ExtractionQueue, job_key
from src.workers.runner import cache_pdf, worker_pass


def test_invalid_or_oversized_cache_input(tmp_path):
    source = tmp_path / "input.bin"
    source.write_bytes(b"not pdf")
    with pytest.raises(ValueError):
        cache_pdf(source, tmp_path / "cache", ExtractionLimits())
    source.write_bytes(b"%PDF-" + b"x" * 20)
    with pytest.raises(ValueError):
        cache_pdf(source, tmp_path / "cache", ExtractionLimits(max_bytes=10))


def test_missing_pdf_runs_only_once_per_pass(tmp_path):
    queue = ExtractionQueue(tmp_path / "queue")
    job = queue.enqueue("p", "a" * 64, "test-v1", "fixture")
    report = worker_pass(queue, tmp_path / "cache", max_jobs=3)
    assert report == {"claimed": 1, "review-required": 0, "failed": 1}
    assert queue.load().jobs[job.key].attempts == 1
    assert queue.load().jobs[job.key].failure_code == "pdf_unavailable"


def test_subprocess_timeout_is_bounded_retryable(tmp_path, monkeypatch):
    queue = ExtractionQueue(tmp_path / "queue")
    digest = "a" * 64
    job = queue.enqueue(
        "p", digest, "test-v1", "fixture", limits=ExtractionLimits(timeout_seconds=1)
    )
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / f"{digest}.pdf").write_bytes(b"%PDF-invalid")

    def timeout(command, **kwargs):
        assert kwargs["timeout"] == 1
        assert kwargs["stderr"] == subprocess.DEVNULL
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(subprocess, "run", timeout)
    assert worker_pass(queue, cache, max_jobs=2)["failed"] == 1
    state = queue.load().jobs[job.key]
    assert state.failure_code == "timeout" and state.attempts == 1


def test_candidate_values_keep_exact_source_coordinates(tmp_path, monkeypatch):
    from src.workers import pdf_parser

    payload = b"%PDF-fixture-only-parser-double"
    source = tmp_path / "input.pdf"
    source.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    job = ExtractionJob(
        key=job_key("p", digest, "test-v1"),
        paper_id="p",
        pdf_sha256=digest,
        extractor_version="test-v1",
        source_url="fixture",
        updated_at=datetime.now(UTC),
    )
    table = SimpleNamespace(
        extract=lambda: [["Method", "PSNR"], ["Baseline", "31.40"]],
        rows=[
            SimpleNamespace(cells=[(0, 0, 10, 10), (10, 0, 20, 10)]),
            SimpleNamespace(cells=[(0, 10, 10, 20), (10, 10, 20, 20)]),
        ],
    )
    page = SimpleNamespace(
        page_number=1, find_tables=lambda: [table], images=[], close=lambda: None
    )

    class PDF:
        pages = [page]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setitem(sys.modules, "pdfplumber", SimpleNamespace(open=lambda stream: PDF()))
    monkeypatch.setattr(pdf_parser, "extractor_version", lambda: "test-v1")
    result = extract(job, source)
    assert len(result.candidates) == 1
    cell = result.candidates[0]
    assert cell.raw_value == "31.40" and cell.bbox == (10, 10, 20, 20)
    assert cell.row_label == "Baseline" and cell.column_label == "PSNR"
    assert cell.unit is None and cell.metric is None and cell.review_required
