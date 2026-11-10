import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from src.schema import PaperDatabase, PaperRecord
from src.storage import _encode
from src.workers.queue import ExtractedCandidate, ExtractionResult, job_key
from src.workers.review import CandidateDecision, ExtractionReview, import_review

NOW = datetime(2026, 11, 9, tzinfo=UTC)


def setup(tmp_path):
    pdf = tmp_path / "source.bin"
    pdf.write_bytes(b"fixture source bytes")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    db = PaperDatabase(papers=[PaperRecord(id="p", title="Fixture method")], total_count=1)
    data = tmp_path / "papers.json"
    db.save(data)
    result = ExtractionResult(
        job_key=job_key("p", digest, "fixture-v1"),
        paper_id="p",
        pdf_sha256=digest,
        extractor_version="fixture-v1",
        completed_at=NOW,
        page_count=1,
        candidates=[
            ExtractedCandidate(
                kind="numeric_cell", page=1, bbox=(0, 0, 10, 10), raw_value="31.4", confidence=0.5
            )
        ],
    )
    path = tmp_path / "result.json"
    path.write_bytes(_encode(result.model_dump(mode="json")))
    decision = CandidateDecision(
        candidate_index=0,
        disposition="accepted",
        reason="Fixture source checked",
        source_checked=True,
        reviewed_by="fixture reviewer",
        reviewed_at=NOW + timedelta(hours=1),
        dataset="Dataset A",
        split="test",
        metric="PSNR",
        unit="dB",
        row_label="Method A",
        column_label="PSNR",
        accepted_value="31.40",
    )
    review = ExtractionReview(
        expected_content_sha256=hashlib.sha256(
            _encode(PaperDatabase.load(data).model_dump(mode="json"))
        ).hexdigest(),
        expected_result_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        source_url="fixture:source",
        decisions=[decision],
    )
    return dict(
        data_path=data,
        ledger_path=tmp_path / "reviewed.json",
        result_path=path,
        pdf_path=pdf,
        review=review,
        now=NOW + timedelta(hours=2),
    )


def test_review_dry_run_apply_replay_preserves_corpus(tmp_path):
    args = setup(tmp_path)
    before = args["data_path"].read_bytes()
    assert import_review(**args, dry_run=True)["added"] == 1
    assert not args["ledger_path"].exists()
    assert import_review(**args)["accepted"] == 1
    ledger = args["ledger_path"].read_bytes(), args["ledger_path"].stat().st_mtime_ns
    assert import_review(**args)["unchanged"] == 1
    assert ledger == (args["ledger_path"].read_bytes(), args["ledger_path"].stat().st_mtime_ns)
    assert args["data_path"].read_bytes() == before
    assert b"31.4" in ledger[0] and b"31.40" in ledger[0]


@pytest.mark.parametrize(
    "field", ["dataset", "split", "metric", "unit", "row_label", "column_label", "accepted_value"]
)
def test_missing_context_cannot_be_accepted(tmp_path, field):
    args = setup(tmp_path)
    setattr(args["review"].decisions[0], field, None)
    with pytest.raises(ValueError):
        import_review(**args)
    assert not args["ledger_path"].exists()


@pytest.mark.parametrize(
    "change", ["pdf", "result", "snapshot", "future", "before_extraction", "index"]
)
def test_changed_source_and_stale_reviews_fail_closed(tmp_path, change):
    args = setup(tmp_path)
    if change == "pdf":
        args["pdf_path"].write_bytes(b"changed")
    elif change == "result":
        args["result_path"].write_bytes(args["result_path"].read_bytes() + b"\n")
    elif change == "snapshot":
        args["review"].expected_content_sha256 = "0" * 64
    elif change == "future":
        args["review"].decisions[0].reviewed_at = NOW + timedelta(days=1)
    elif change == "before_extraction":
        args["review"].decisions[0].reviewed_at = NOW - timedelta(days=1)
    else:
        args["review"].decisions[0].candidate_index = 1
    with pytest.raises(ValueError):
        import_review(**args)
    assert not args["ledger_path"].exists()


def test_rejection_and_conflicting_re_review(tmp_path):
    args = setup(tmp_path)
    decision = args["review"].decisions[0]
    decision.disposition = "rejected"
    decision.unit = None
    assert import_review(**args)["rejected"] == 1
    decision.reason = "Different adjudication"
    with pytest.raises(ValueError, match="Conflicting"):
        import_review(**args)


def test_accepted_figure_requires_caption_and_reuse_basis(tmp_path):
    from src.workers.review import ReviewedCandidate

    args = setup(tmp_path)
    result = ExtractionResult.model_validate_json(args["result_path"].read_bytes())
    figure = ExtractedCandidate(kind="figure", page=1, bbox=(0, 0, 10, 10), confidence=0.3)
    fields = dict(
        paper_id="p",
        job_key=result.job_key,
        pdf_sha256=result.pdf_sha256,
        result_sha256=args["review"].expected_result_sha256,
        source_url="fixture:source",
        original=figure,
        decision=args["review"].decisions[0],
    )
    with pytest.raises(ValueError):
        ReviewedCandidate(**fields)
    fields["decision"].caption = "Figure 1. Fixture source caption"
    with pytest.raises(ValueError):
        ReviewedCandidate(**fields)
    fields["decision"].reuse_basis = "Fixture-only original artwork"
    assert ReviewedCandidate(**fields).decision.disposition == "accepted"
