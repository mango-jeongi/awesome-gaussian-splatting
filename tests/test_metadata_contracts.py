"""Reviewed field ownership and non-fabricated date precision regression tests."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.contracts import FieldEvidence
from src.enricher import MultiProviderEnricher
from src.schema import PaperDatabase, PaperRecord
from src.seed import load_local_papers

NOW = datetime(2026, 11, 8, tzinfo=UTC)


def approved(field, value):
    return {
        field: [
            FieldEvidence(source="manual", value=value, reviewed_by="maintainer", reviewed_at=NOW)
        ]
    }


def test_reviewed_fields_survive_provider_updates():
    original = PaperRecord(
        id="stable",
        arxiv_id="2308.04079",
        title="A reviewed splatting method",
        venue="Reviewed Venue",
        code_url="https://example.org/reviewed",
        published_date="2023-08-08",
        published_date_precision="day",
        metadata_evidence={
            **approved("venue", "Reviewed Venue"),
            **approved("code_url", "https://example.org/reviewed"),
            **approved("published_date", "2023-08-08"),
        },
    )
    incoming = PaperRecord(
        arxiv_id="2308.04079",
        title=original.title,
        venue="Regex guess",
        code_url="https://example.org/provider",
        published_date="2023-09-01",
        published_date_precision="day",
        updated_date="2026-11-08",
    )
    db = PaperDatabase(papers=[original], total_count=1)
    assert db.upsert([incoming]) == 0
    result = db.papers[0]
    assert (result.venue, result.code_url, result.published_date, result.month) == (
        original.venue,
        original.code_url,
        original.published_date,
        8,
    )
    assert result.updated_date == "2026-11-08"
    assert result.id == "stable"


def test_contradictory_review_evidence_is_atomic():
    original = PaperRecord(
        id="stable",
        title="Reviewed metadata paper",
        venue="Approved",
        metadata_evidence=approved("venue", "Approved"),
    )
    candidate = PaperRecord(
        id="stable",
        title=original.title,
        venue="Different approval",
        metadata_evidence=approved("venue", "Different approval"),
    )
    db = PaperDatabase(papers=[original], total_count=1)
    before = db.model_dump()
    with pytest.raises(ValueError, match="adjudication"):
        db.upsert([PaperRecord(title="Another valid addition"), candidate])
    assert db.model_dump() == before


def test_independent_preprint_and_proceedings_dates():
    paper = PaperRecord(
        title="Independent publication dates",
        published_date="2023-08-08",
        published_date_precision="day",
        publication_date="2024-06-01",
        publication_date_precision="month",
        publication_year=2024,
        doi="10.1000/proceedings",
        arxiv_doi="10.48550/arxiv.2308.04079",
    )
    assert paper.year == 2023
    assert paper.publication_year == 2024
    assert paper.doi != paper.arxiv_doi
    with pytest.raises(ValidationError, match="disagree"):
        PaperRecord(
            title="Conflicting proceedings year",
            publication_date="2024-06-01",
            publication_year=2025,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"published_date": "2024-02-15", "published_date_precision": "month"},
        {"published_date": "2024-02-01", "published_date_precision": "year"},
        {"published_date": "20240101"},
        {"publication_date": "20240101"},
        {"updated_date": "2024-02-30"},
        {"published_date": "1800-01-01"},
    ],
)
def test_invalid_date_and_precision_combinations(kwargs):
    with pytest.raises(ValidationError):
        PaperRecord(title="Invalid date fixture", **kwargs)


def test_evidence_requires_aware_review_and_matching_value():
    with pytest.raises(ValidationError):
        FieldEvidence(source="manual", value="CVPR", reviewed_by="maintainer")
    with pytest.raises(ValidationError):
        FieldEvidence(
            source="manual",
            value="CVPR",
            reviewed_by="maintainer",
            reviewed_at=datetime(2026, 11, 8),
        )
    with pytest.raises(ValidationError, match="disagrees"):
        PaperRecord(
            title="Evidence conflict fixture",
            venue="Other",
            metadata_evidence=approved("venue", "CVPR"),
        )
    with pytest.raises(ValidationError, match="Unknown evidence"):
        PaperRecord(
            title="Unknown evidence field",
            metadata_evidence={"nonexistent": [FieldEvidence(source="manual", value=1)]},
        )


def test_source_date_can_correct_legacy_month_but_seed_does_not_discard_days():
    original = PaperRecord(
        id="stable",
        arxiv_id="2308.04079",
        title="Source date correction",
        published_date="2023-08-08",
    )
    seed = PaperRecord(
        arxiv_id=original.arxiv_id,
        source="manual",
        title=original.title,
        published_date="2023-01-01",
        published_date_precision="year",
    )
    result = original.merge_metadata(seed)
    assert result.published_date == "2023-08-08"
    source = PaperRecord(
        arxiv_id=original.arxiv_id,
        source="arxiv",
        title=original.title,
        published_date="2023-09-02",
        published_date_precision="day",
    )
    result = result.merge_metadata(source)
    assert (result.published_date, result.month, result.date_placement) == (
        "2023-09-02",
        9,
        "observed",
    )


def test_seed_metadata_precision_without_filename_dates(tmp_path):
    root = Path(__file__).resolve().parents[1]
    enricher = MultiProviderEnricher(root / "config" / "taxonomy.yaml")
    path = tmp_path / "success.json"
    path.write_text(
        json.dumps(
            [
                {
                    "title": "Gaussian Splatting Month Fixture",
                    "year": 2025,
                    "month": 7,
                    "file": "202507 - Month Fixture.pdf",
                },
                {
                    "title": "Gaussian Splatting Year Fixture",
                    "year": 2024,
                    "file": "202411 - Year Fixture.pdf",
                },
            ]
        ),
        encoding="utf-8",
    )
    month, year = load_local_papers(path, enricher)
    assert (month.published_date, month.published_date_precision, month.date_placement) == (
        "2025-07-01",
        "month",
        "month_start",
    )
    assert (year.published_date, year.published_date_precision, year.date_placement) == (
        "2024-01-01",
        "year",
        "year_start",
    )
    assert month.source == year.source == "manual"
    path.write_text(
        json.dumps([{"title": "Gaussian Splatting Missing Date", "file": "202507 - Filename.pdf"}]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="reviewed publication year"):
        load_local_papers(path, enricher)


def test_retag_preserves_reviewed_categories_tags_and_explicit_missing_code():
    paper = PaperRecord(
        title="Gaussian Splatting CUDA robotics fixture",
        abstract="A medical Gaussian splatting renderer for robot SLAM.",
        categories=["Foundations & Acceleration"],
        tags=["Foundations"],
        code_url=None,
        comment="Code: https://github.com/example/provider",
        metadata_evidence={
            **approved("categories", ["Foundations & Acceleration"]),
            **approved("tags", ["Foundations"]),
            **approved("code_url", None),
        },
    )
    enricher = MultiProviderEnricher(
        Path(__file__).resolve().parents[1] / "config" / "taxonomy.yaml"
    )
    updated = enricher.enrich(paper, use_llm=False)
    assert updated.categories == paper.categories
    assert updated.primary_category == paper.primary_category
    assert updated.tags == paper.tags
    assert updated.code_url is None


@pytest.mark.parametrize("source", ["cvf", "arxiv"])
def test_arxiv_doi_cannot_claim_unverified_conference_publication_identity(source):
    original = PaperRecord(
        id="conference",
        arxiv_id="2501.00001",
        source=source,
        title="Gaussian Splatting conference method",
        venue="CVPR 2025",
        publication_year=2025,
        publication_date_precision="year",
        metadata_evidence={
            "venue": [
                FieldEvidence(
                    source="cvf_official_proceedings",
                    value="CVPR 2025",
                    source_url="https://openaccess.thecvf.com/content/CVPR2025/html/fixture.html",
                    observed_at=NOW,
                )
            ]
        },
    )
    incoming = PaperRecord(
        arxiv_id="2501.00001",
        source="arxiv",
        title=original.title,
        doi="10.1000/later-journal",
        updated_date="2026-11-08",
    )
    with pytest.raises(ValueError, match="conference DOI.*source verification"):
        original.merge_metadata(incoming)
    assert original.doi is None
    from src.ingestion import prepare_ingestion
    from src.relevance import RelevancePolicy

    db = PaperDatabase(papers=[original], total_count=1)
    candidate, report = prepare_ingestion(
        db,
        [incoming],
        RelevancePolicy(),
        MultiProviderEnricher(Path(__file__).resolve().parents[1] / "config/taxonomy.yaml"),
    )
    assert candidate.model_dump() == db.model_dump()
    assert report["outcomes"] == {"include": 0, "exclude": 0, "review": 1}
    assert "publication source verification" in report["dispositions"][0]["reason"]
    confirmed = original.model_copy(update={"doi": incoming.doi})
    assert confirmed.merge_metadata(incoming).doi == incoming.doi
