import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import yaml

from src.manual_operations import download_reviewed_pdf, prepare_reviewed_import
from src.schema import PaperDatabase, PaperRecord
from src.storage import _encode
from src.workers.queue import ExtractedCandidate, ExtractionResult, job_key
from src.workers.review import CandidateDecision, ExtractionReview, import_review

PDF = b"%PDF-fixture source"
SHA = hashlib.sha256(PDF).hexdigest()
URL = "https://arxiv.org/pdf/2308.04079.pdf"
NOW = datetime(2026, 11, 9, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "url",
    [
        "http://arxiv.org/pdf/1",
        "https://127.0.0.1/x",
        "https://arxiv.org.evil.example/x",
        "https://user:pass@arxiv.org/x",
        "https://arxiv.org:444/x",
        "https://arxiv.org/x?token=private",
    ],
)
def test_unapproved_url_rejected_before_network(tmp_path, url):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("Unexpected network"))
    ) as client:
        with pytest.raises(ValueError, match="canonical public PDF"):
            download_reviewed_pdf(url, tmp_path / "pdf", SHA, client=client)
    assert not (tmp_path / "pdf").exists()


def test_redirect_cannot_leave_allowlist_even_with_following_client(tmp_path):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://private.example/secret"})

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        with pytest.raises(ValueError, match="canonical public PDF"):
            download_reviewed_pdf(URL, tmp_path / "pdf", SHA, client=client)
    assert seen == [URL]


def test_approved_redirect_digest_and_source_report(tmp_path):
    def handler(request):
        return (
            httpx.Response(302, headers={"Location": "https://arxiv.org/pdf/2308.04079.pdf"})
            if request.url.host == "export.arxiv.org"
            else httpx.Response(200, content=PDF)
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = download_reviewed_pdf(
            URL.replace("arxiv.org", "export.arxiv.org"), tmp_path / "pdf", SHA, client=client
        )
    assert report == {"pdf_sha256": SHA, "bytes": len(PDF), "requests": 2}
    assert (tmp_path / "pdf").read_bytes() == PDF


@pytest.mark.parametrize("failure", ["digest", "oversize", "deadline"])
def test_failed_download_preserves_prior_file_and_removes_partial(tmp_path, failure):
    target = tmp_path / "pdf"
    target.write_bytes(b"prior verified bytes")
    ticks = iter([0, 0, 2])
    options = (
        {"clock": lambda: next(ticks), "max_seconds": 1}
        if failure == "deadline"
        else {"max_bytes": 5}
        if failure == "oversize"
        else {}
    )
    expected = "0" * 64 if failure == "digest" else SHA
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=PDF))
    ) as client:
        with pytest.raises(ValueError):
            download_reviewed_pdf(URL, target, expected, client=client, **options)
    assert target.read_bytes() == b"prior verified bytes"
    assert not (tmp_path / "pdf.partial").exists()


def reviewed_inputs(tmp_path):
    data = tmp_path / "papers.json"
    PaperDatabase(papers=[PaperRecord(id="p", title="Fixture", pdf_url=URL)]).save(data)
    inputs = tmp_path / "extraction/review-inputs"
    inputs.mkdir(parents=True)
    result = ExtractionResult(
        job_key=job_key("p", SHA, "fixture-v1"),
        paper_id="p",
        pdf_sha256=SHA,
        extractor_version="fixture-v1",
        completed_at=NOW,
        page_count=1,
        candidates=[
            ExtractedCandidate(
                kind="numeric_cell", page=1, bbox=(0, 0, 10, 10), raw_value="31.4", confidence=0.5
            )
        ],
    )
    result_path = inputs / "pilot.result.json"
    result_path.write_bytes(_encode(result.model_dump(mode="json")))
    review = ExtractionReview(
        expected_content_sha256=hashlib.sha256(
            _encode(PaperDatabase.load(data).model_dump(mode="json"))
        ).hexdigest(),
        expected_result_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest(),
        source_url=URL,
        decisions=[
            CandidateDecision(
                candidate_index=0,
                disposition="accepted",
                reason="Fixture source checked",
                source_checked=True,
                reviewed_by="Fixture reviewer",
                reviewed_at=NOW + timedelta(hours=1),
                dataset="A",
                split="test",
                metric="PSNR",
                unit="dB",
                row_label="Method",
                column_label="PSNR",
                accepted_value="31.4",
            )
        ],
    )
    (inputs / "pilot.review.json").write_bytes(_encode(review.model_dump(mode="json")))
    return data, result_path, review


def test_materialize_then_review_preview_apply_replay_never_changes_corpus(tmp_path):
    data, result, review = reviewed_inputs(tmp_path)
    before = data.read_bytes()
    pdf = tmp_path / "temporary.pdf"
    ledger = tmp_path / "extraction/reviewed.json"
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=PDF))
    ) as client:
        prepared = prepare_reviewed_import(data, "pilot", pdf, client=client)
    assert (
        prepared["paper_id"] == "p" and not prepared["canonical_modified"] and not ledger.exists()
    )
    args = dict(
        data_path=data,
        ledger_path=ledger,
        result_path=result,
        pdf_path=pdf,
        review=review,
        now=NOW + timedelta(hours=2),
    )
    assert import_review(**args, dry_run=True)["accepted"] == 1 and not ledger.exists()
    assert import_review(**args)["accepted"] == 1
    stable = ledger.read_bytes()
    assert import_review(**args)["unchanged"] == 1 and ledger.read_bytes() == stable
    assert data.read_bytes() == before


def test_changed_result_and_unsafe_key_never_fetch_source(tmp_path):
    data, result, _ = reviewed_inputs(tmp_path)
    result.write_bytes(result.read_bytes() + b" ")
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("Unexpected network"))
    ) as client:
        with pytest.raises(ValueError, match="result bytes changed"):
            prepare_reviewed_import(data, "pilot", tmp_path / "pdf", client=client)
        with pytest.raises(ValueError, match="import key"):
            prepare_reviewed_import(data, "../pilot", tmp_path / "pdf", client=client)


@pytest.mark.parametrize("filename", ["manual-backfill.yml", "manual-worker-import.yml"])
def test_manual_writer_inputs_lock_parent_guard_checks_and_checkpoint_order(filename):
    workflow = yaml.load(
        (ROOT / ".github/workflows" / filename).read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    assert (
        "schedule" not in workflow["on"]
        and workflow["on"]["workflow_dispatch"]["inputs"]["mode"]["default"] == "preview"
    )
    assert workflow["concurrency"] == {"group": "repository-writer", "cancel-in-progress": "false"}
    steps = next(iter(workflow["jobs"].values()))["steps"]
    operation = next(s for s in steps if s.get("id") == "operation")
    run = operation["run"]
    assert "${{ inputs." not in run and operation["env"]
    assert "--dry-run" in run and "git fetch origin feed" in run and "EXPECTED_FEED=" in run
    for check in [
        "src.cli build",
        "src.cli validate",
        "ruff check .",
        "ruff format --check .",
        "pytest -v",
    ]:
        assert check in run
    commit = next(s["run"] for s in steps if "git add --all" in s.get("run", ""))
    assert (
        "EXPECTED_FEED" in commit
        and "git push origin HEAD:feed" in commit
        and "--force" not in commit
    )
    assert "data/ingestion/backfill" in commit and "data/extraction/reviewed.json" in commit
    assert steps[-1]["if"] == "steps.operation.outputs.status != '0'"
    assert not any("deploy-pages" in s.get("uses", "") for s in steps)


def test_review_provenance_must_match_canonical_source_before_fetch(tmp_path):
    data, result, review = reviewed_inputs(tmp_path)
    review.source_url = "https://arxiv.org/abs/9999.99999"
    (result.parent / "pilot.review.json").write_bytes(_encode(review.model_dump(mode="json")))
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("Unexpected network"))
    ) as client:
        with pytest.raises(ValueError, match="canonical source"):
            prepare_reviewed_import(data, "pilot", tmp_path / "pdf", client=client)
