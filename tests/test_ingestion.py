"""Candidate accounting and conflict review without loss of approved data."""

from datetime import UTC, datetime
from pathlib import Path

from src.contracts import FieldEvidence
from src.curation import archive_paper
from src.enricher import MultiProviderEnricher
from src.ingestion import prepare_ingestion
from src.relevance import RelevancePolicy
from src.schema import PaperDatabase, PaperRecord


def enricher():
    return MultiProviderEnricher(Path(__file__).resolve().parents[1] / "config" / "taxonomy.yaml")


def test_every_candidate_has_one_disposition_and_conflicts_do_not_abort_others():
    kept = PaperRecord(
        id="curated",
        arxiv_id="2401.00001",
        doi="10.1000/kept",
        title="Gaussian Splatting original fixture",
        published_date="2024-01-01",
    )
    db = PaperDatabase(papers=[kept], total_count=1)
    records = [
        PaperRecord(
            arxiv_id="2401.00002",
            title="Gaussian Splatting new accepted fixture",
            published_date="2024-01-02",
        ),
        PaperRecord(
            arxiv_id="2401.00003",
            title="Clinical ultrasound training fixture",
            published_date="2024-01-03",
        ),
        PaperRecord(
            arxiv_id="2401.00004",
            title="Neural radiance field foundation fixture",
            published_date="2024-01-04",
        ),
        PaperRecord(
            arxiv_id="2401.00001",
            doi="10.1000/contradiction",
            title="Gaussian Splatting identifier conflict",
            published_date="2024-01-01",
        ),
    ]
    before = db.model_dump()
    candidate, report = prepare_ingestion(db, records, RelevancePolicy(), enricher())
    assert db.model_dump() == before
    assert candidate.total_count == 2
    assert report["outcomes"] == {"include": 1, "exclude": 1, "review": 2}
    assert len(report["dispositions"]) == len(records)
    assert candidate.get("curated").doi == "10.1000/kept"
    assert candidate.get("2401.00002") is not None
    assert candidate.get("2401.00003") is None
    replay, replayed = prepare_ingestion(candidate, records, RelevancePolicy(), enricher())
    assert replay.model_dump() == candidate.model_dump()
    assert replayed["inserted_canonical_records"] == 0
    assert replayed["operations"]["unchanged"] == 1


def test_archived_exclusion_and_active_topic_disagreement_remain_reviewable():
    db = PaperDatabase(
        papers=[
            PaperRecord(
                id="removed", arxiv_id="2401.00001", title="Gaussian Splatting excluded fixture"
            ),
            PaperRecord(
                id="active", arxiv_id="2401.00002", title="Gaussian Splatting active fixture"
            ),
        ],
        total_count=2,
    )
    archive_paper(
        db,
        "removed",
        disposition="excluded",
        reason="Fixture reviewed exclusion",
        evidence=[FieldEvidence(source="fixture", value="scope exclusion")],
        reviewed_by="fixture reviewer",
        reviewed_at=datetime(2026, 11, 8, tzinfo=UTC),
    )
    records = [
        PaperRecord(arxiv_id="2401.00001", title="Gaussian Splatting source replay"),
        PaperRecord(arxiv_id="2401.00002", title="Unrelated medical source revision"),
    ]
    candidate, report = prepare_ingestion(db, records, RelevancePolicy(), enricher())
    assert candidate.model_dump() == db.model_dump()
    assert report["outcomes"] == {"include": 0, "exclude": 1, "review": 1}
    assert candidate.get("active") is not None
    assert "removed" in candidate.archive


def test_all_conflicting_records_leave_database_unchanged():
    record = PaperRecord(
        id="stable", arxiv_id="2401.00001", doi="10.1000/one", title="Gaussian Splatting fixture"
    )
    db = PaperDatabase(papers=[record], total_count=1)
    bad = PaperRecord(arxiv_id=record.arxiv_id, doi="10.1000/two", title=record.title)
    before = db.model_dump()
    candidate, report = prepare_ingestion(db, [bad], RelevancePolicy(), enricher())
    assert candidate.model_dump() == before
    assert report["outcomes"]["review"] == 1
