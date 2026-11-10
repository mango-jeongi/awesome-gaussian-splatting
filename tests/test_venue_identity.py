from datetime import UTC, datetime, timedelta

import pytest

from src.extractors.cvf import CVFPublication
from src.schema import PaperRecord
from src.venue_identity import VenueIdentityReview, metadata_digest, resolve_publication

NOW = datetime(2026, 11, 9, tzinfo=UTC)


def publication():
    return CVFPublication(
        title="Gaussian Splatting Method",
        authors=["Alice Example"],
        abstract="Official author abstract",
        source_url="https://openaccess.thecvf.com/content/CVPR2025/html/Example_Method_paper.html",
        venue="CVPR",
        venue_year=2025,
        track="main",
        pdf_url="https://openaccess.thecvf.com/content/CVPR2025/papers/Example_Method_paper.pdf",
        arxiv_id="2408.00001",
    )


def source(**changes):
    raw = dict(
        id="2408.00001",
        arxiv_id="2408.00001",
        title="Gaussian Splatting Method",
        authors=["Alice Example"],
        published_date="2024-08-01",
        published_date_precision="day",
        date_placement="observed",
        doi="10.1234/later-journal",
    )
    raw.update(changes)
    return PaperRecord(**raw)


def resolve(pub, record, **kwargs):
    return resolve_publication(
        pub, cvf_observed_at=NOW, arxiv=record, arxiv_observed_at=NOW, **kwargs
    )


def test_exact_identity_gets_original_day_without_mixing_publication_version():
    record, audit = resolve(publication(), source())
    assert record.published_date == "2024-08-01" and record.publication_year == 2025
    assert record.published_date_precision == "day" and record.venue == "CVPR 2025"
    assert record.doi is None and record.abstract == "Official author abstract"
    assert record.metadata_evidence["published_date"][0].source == "arxiv_exact_lookup"
    assert audit["status"] == "original_date_verified"


@pytest.mark.parametrize(
    "changes", [{"title": "Instruct: Gaussian Splatting Method"}, {"authors": ["Example Alice"]}]
)
def test_title_and_name_order_variants_need_exact_source_review(changes):
    pub, record = publication(), source(**changes)
    candidate, audit = resolve(pub, record)
    assert candidate is None and audit["status"] == "review"
    review = VenueIdentityReview(
        publication_sha256=metadata_digest(pub),
        arxiv_record_sha256=metadata_digest(record),
        reviewed_by="Fixture reviewer",
        reviewed_at=NOW + timedelta(hours=1),
        reason="Complete source evidence checked",
    )
    candidate, audit = resolve(pub, record, review=review)
    assert candidate.title == pub.title and candidate.authors == pub.authors
    assert audit["status"] == "original_date_verified" and audit["reviewed_identity"]
    changed = record.model_copy(update={"abstract": "Changed source"})
    with pytest.raises(ValueError, match="snapshots changed"):
        resolve(pub, changed, review=review)


def test_wrong_arxiv_id_cannot_be_excused_by_review():
    candidate, audit = resolve(publication(), source(arxiv_id="2408.00002"))
    assert candidate is None and audit["status"] == "review"


@pytest.mark.parametrize(
    "changes",
    [
        {"published_date": "2026-01-01"},
        {
            "published_date_precision": "year",
            "date_placement": "year_start",
            "published_date": "2024-01-01",
        },
    ],
)
def test_date_ambiguity_remains_review(changes):
    candidate, audit = resolve(publication(), source(**changes))
    assert candidate is None and "chronology" in audit["reason"]


def test_no_link_remains_honest_year_precision():
    pub = publication().model_copy(update={"arxiv_id": None})
    record, audit = resolve_publication(pub, cvf_observed_at=NOW)
    assert record.published_date_precision == "year" and record.date_placement == "year_start"
    assert audit["status"] == "publication_year_only"


def test_review_cannot_precede_its_source_observation():
    pub, record = publication(), source()
    review = VenueIdentityReview(
        publication_sha256=metadata_digest(pub),
        arxiv_record_sha256=metadata_digest(record),
        reviewed_by="Fixture reviewer",
        reviewed_at=NOW - timedelta(hours=1),
        reason="Invalid backdated review",
    )
    with pytest.raises(ValueError, match="time is invalid"):
        resolve(pub, record, review=review)
