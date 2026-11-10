import hashlib
from datetime import UTC, datetime

import pytest

from src.schema import PaperDatabase, PaperRecord
from src.workers.coverage import scan_coverage
from src.workers.queue import ExtractionQueue, ExtractionResult


def test_full_active_inventory_pending_and_unavailable(tmp_path):
    db = PaperDatabase(
        papers=[
            PaperRecord(id="p", title="Available method", pdf_url="https://example.org/p.pdf"),
            PaperRecord(id="q", title="No PDF method"),
        ],
        total_count=2,
    )
    report = scan_coverage(db, [], extractor_version="v1")
    assert report.summary == {"queued": 1, "unavailable": 1}
    assert report.records["p"]["job_key"] is None
    assert report.records["p"]["source_task_id"] in report.source_tasks
    assert report.source_tasks[report.records["p"]["source_task_id"]].identity_verification_required
    path = tmp_path / "coverage.json"
    report.save(path)
    before = path.read_bytes(), path.stat().st_mtime_ns
    scan_coverage(db, [], extractor_version="v1").save(path)
    assert before == (path.read_bytes(), path.stat().st_mtime_ns)
    assert "not a global availability" in report.records["q"]["reason"]


def test_processed_requires_valid_result_and_active_version(tmp_path):
    queue = ExtractionQueue(tmp_path / "queue")
    digest = hashlib.sha256(b"fixture").hexdigest()
    job = queue.enqueue("p", digest, "v1", "fixture")
    lease = queue.claim()
    queue.finish(
        job.key,
        lease.lease_token,
        ExtractionResult(
            job_key=job.key,
            paper_id="p",
            pdf_sha256=digest,
            extractor_version="v1",
            completed_at=datetime.now(UTC),
            page_count=1,
        ),
    )
    db = PaperDatabase(papers=[PaperRecord(id="p", title="Processed method")], total_count=1)
    report = scan_coverage(db, [queue], extractor_version="v1")
    assert (
        report.records["p"]["state"] == "processed" and report.records["p"]["accepted_cells"] == 0
    )
    assert scan_coverage(db, [queue], extractor_version="v2").summary == {"unavailable": 1}
    (queue.root / "results" / f"{job.key}.json").write_text("{}")
    with pytest.raises(ValueError):
        scan_coverage(db, [queue], extractor_version="v1")


def test_unsupported_input_and_local_source_review_task(tmp_path):
    queue = ExtractionQueue(tmp_path / "queue")
    job = queue.enqueue("p", "a" * 64, "v1", "fixture")
    lease = queue.claim()
    queue.fail(job.key, lease.lease_token, "size_limit")
    db = PaperDatabase(
        papers=[
            PaperRecord(id="p", title="Oversized method"),
            PaperRecord(id="q", title="Local candidate"),
        ],
        total_count=2,
    )
    report = scan_coverage(
        db, [queue], extractor_version="v1", local_sources={"q": ["file:///local/candidate.pdf"]}
    )
    assert report.summary == {"unsupported": 1, "queued": 1}
    assert "size_limit" in report.records["p"]["reason"]
    assert report.records["q"]["job_key"] is None


@pytest.mark.parametrize("kind", ["queue_file", "missing", "empty_directory"])
def test_coverage_cli_rejects_invalid_queue_without_writing_report(tmp_path, capsys, kind):
    from src.workers.__main__ import main

    queue = tmp_path / "queue"
    if kind == "queue_file":
        queue.write_text('{"schema_version":"1.0.0","jobs":{}}')
    elif kind == "empty_directory":
        queue.mkdir()
    output = tmp_path / "coverage.json"
    with pytest.raises(SystemExit) as error:
        main(
            [
                "coverage",
                "--data",
                str(tmp_path / "not-read.json"),
                "--queue",
                str(queue),
                "--extractor-version",
                "v1",
                "--output",
                str(output),
            ]
        )
    assert error.value.code == 2
    assert "existing queue directory containing queue.json" in capsys.readouterr().err
    assert not output.exists()
