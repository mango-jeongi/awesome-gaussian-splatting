"""Lossless reviewed archival, identity tombstones, and atomic failure cases."""

from datetime import UTC, datetime

import pytest

from src.contracts import FieldEvidence
from src.curation import ArchiveLedger, archive_paper, validate_archive
from src.identity import IdentityConflict
from src.observations import SignalStore
from src.schema import PaperDatabase, PaperRecord

NOW = datetime(2026, 11, 8, tzinfo=UTC)
REVIEW = dict(
    reason="Fixture-only reviewed disposition",
    evidence=[FieldEvidence(source="fixture-review", value="reviewed exclusion evidence")],
    reviewed_by="fixture reviewer",
    reviewed_at=NOW,
)


def database():
    first = PaperRecord(
        id="old/stable", arxiv_id="2308.04079", title="First splatting method", citation_count=11
    )
    second = PaperRecord(id="kept", title="Second method", referenced_works=["2308.04079"])
    third = PaperRecord(id="final", title="Third method")
    db = PaperDatabase(papers=[first, second, third], total_count=3)
    signals = SignalStore(provider="openalex")
    signals.apply(first.id, status="ok", provider_id="W1", values={"citation_count": 11}, now=NOW)
    db._signal_stores["openalex"] = signals
    return db


def test_exclusion_preserves_record_observation_aliases_and_no_resurrection(tmp_path):
    db = database()
    original = db.papers[0].model_dump(mode="json")
    assert archive_paper(db, "old/stable", disposition="excluded", **REVIEW)
    entry = validate_archive(db).entries["old/stable"]
    assert entry.paper.model_dump(mode="json") == original
    assert entry.observations["openalex"].values["citation_count"] == 11
    assert "arxiv:2308.04079" in entry.aliases
    assert "old/stable" not in db._signal_stores["openalex"].observations
    assert db.get("kept").db_references == []
    with pytest.raises(IdentityConflict, match="Archived candidate"):
        db.upsert([PaperRecord(arxiv_id="2308.04079", title="Reingested source title")])
    snapshot = db.model_dump()
    assert not archive_paper(db, "old/stable", disposition="excluded", **REVIEW)
    assert db.model_dump() == snapshot
    for filename in ("papers.json", "v2/manifest.json"):
        path = tmp_path / filename
        db.save(path)
        restored = PaperDatabase.load(path)
        assert restored.model_dump() == db.model_dump()
        assert validate_archive(restored) == validate_archive(db)


def test_reviewed_merge_chains_preserve_routes_and_graph():
    db = database()
    assert archive_paper(db, "old/stable", disposition="merged", merged_into="kept", **REVIEW)
    assert db.get("2308.04079").id == "kept"
    assert db.get("kept").db_references == []  # Redirected self-reference is omitted.
    assert archive_paper(db, "kept", disposition="merged", merged_into="final", **REVIEW)
    ledger = validate_archive(db)
    assert ledger.resolve("old/stable", {"final"}) == "final"
    assert db.get("old/stable").id == "final"
    assert db.get("2308.04079").id == "final"
    assert not archive_paper(db, "old/stable", disposition="merged", merged_into="kept", **REVIEW)


def test_excluding_merge_endpoint_does_not_leave_active_aliases():
    db = database()
    archive_paper(db, "old/stable", disposition="merged", merged_into="kept", **REVIEW)
    archive_paper(db, "kept", disposition="excluded", **REVIEW)
    assert db.get("2308.04079") is None
    assert validate_archive(db).resolve("old/stable", {"final"}) == "kept"


def test_invalid_review_or_missing_target_does_not_modify_database():
    db = database()
    before = db.model_dump()
    with pytest.raises(ValueError):
        archive_paper(db, "old/stable", disposition="excluded", **{**REVIEW, "evidence": []})
    assert db.model_dump() == before
    with pytest.raises(IdentityConflict, match="active"):
        archive_paper(db, "old/stable", disposition="merged", merged_into="missing", **REVIEW)
    assert db.model_dump() == before


def test_cycle_and_active_archive_overlap_fail_validation():
    db = database()
    archive_paper(db, "old/stable", disposition="merged", merged_into="kept", **REVIEW)
    archive_paper(db, "kept", disposition="merged", merged_into="final", **REVIEW)
    ledger = ArchiveLedger(entries=db.archive)
    ledger.entries["kept"].merged_into = "old/stable"
    with pytest.raises(IdentityConflict, match="cycle"):
        ledger.alias_targets({"final"})
    with pytest.raises(IdentityConflict, match="both active"):
        ledger.alias_targets({"final", "old/stable"})


def test_review_file_snapshot_guard_and_cli_preview(tmp_path, capsys):
    import json

    from src.cli import main
    from src.curation import ArchiveReview, prepare_archive_review
    from src.storage import _digest, _encode

    db = database()
    source = tmp_path / "papers.json"
    db.save(source)
    loaded = PaperDatabase.load(source)
    decision = {"paper_id": "old/stable", "disposition": "excluded", **REVIEW}
    review = ArchiveReview(
        expected_content_sha256=_digest(_encode(loaded.model_dump(mode="json"))),
        decisions=[decision],
    )
    path = tmp_path / "review.json"
    path.write_text(review.model_dump_json(), encoding="utf-8")
    before = source.read_bytes()
    assert main(["--data", str(source), "curate", "--review-file", str(path), "--dry-run"]) == 0
    assert source.read_bytes() == before
    assert json.loads(capsys.readouterr().out)["archived_records"] == 1
    assert main(["--data", str(source), "curate", "--review-file", str(path)]) == 0
    assert "old/stable" in PaperDatabase.load(source).archive
    after = source.read_bytes()
    assert main(["--data", str(source), "curate", "--review-file", str(path)]) == 0
    assert source.read_bytes() == after
    stale_review = ArchiveReview(
        expected_content_sha256=review.expected_content_sha256,
        decisions=[{**decision, "paper_id": "kept"}],
    )
    path.write_text(stale_review.model_dump_json(), encoding="utf-8")
    with pytest.raises(IdentityConflict, match="stale"):
        main(["--data", str(source), "curate", "--review-file", str(path)])
    assert source.read_bytes() == after
    candidate, report = prepare_archive_review(loaded, review)
    assert len(loaded.papers) == 3
    assert len(candidate.papers) == 2
    assert report["decisions"][0]["changed"]
    with pytest.raises(ValueError, match="duplicate"):
        ArchiveReview(
            expected_content_sha256=review.expected_content_sha256, decisions=[decision, decision]
        )


@pytest.mark.parametrize("order", [("first", "second"), ("second", "first")])
def test_batch_exclusion_preserves_original_linked_record_snapshots(order):
    from src.curation import ArchiveReview, prepare_archive_review
    from src.storage import _digest, _encode

    first = PaperRecord(
        id="first",
        title="First unrelated paper",
        openalex_id="https://openalex.org/W1",
        referenced_works=["https://openalex.org/W2"],
        db_references=["second"],
    )
    second = PaperRecord(
        id="second",
        title="Second unrelated paper",
        openalex_id="https://openalex.org/W2",
        db_citations=["first"],
        db_citation_count=1,
    )
    db = PaperDatabase(
        papers=[first, second, PaperRecord(id="retained", title="Retained")], total_count=3
    )
    original = {paper.id: paper.model_dump(mode="json") for paper in db.papers}
    review = ArchiveReview(
        expected_content_sha256=_digest(_encode(db.model_dump(mode="json"))),
        decisions=[
            {"paper_id": identifier, "disposition": "excluded", **REVIEW} for identifier in order
        ],
    )
    candidate, _ = prepare_archive_review(db, review)
    assert candidate.total_count == 1
    for identifier in order:
        assert candidate.archive[identifier]["paper"] == original[identifier]
    assert {paper.id: paper.model_dump(mode="json") for paper in db.papers} == original
    replay, report = prepare_archive_review(candidate, review)
    assert replay.model_dump() == candidate.model_dump()
    assert not any(row["changed"] for row in report["decisions"])
