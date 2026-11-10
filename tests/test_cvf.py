import pytest

from src.extractors.cvf import parse_listing, parse_publication

LISTING = """<dt class="ptitle"><a href="/content/CVPR2025/html/Example_Method_paper.html">Gaussian Splatting &amp; Methods</a></dt><dd><input name="query_author" value="Alice Example"></dd>"""
PAPER = """<meta name="citation_title" content="Gaussian Splatting &amp; Methods"><meta name="citation_author" content="Example, Alice"><meta name="citation_publication_date" content="2025"><meta name="citation_conference_title" content="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition"><meta name="citation_pdf_url" content="https://openaccess.thecvf.com/content/CVPR2025/papers/Example_Method_paper.pdf"><a href="https://arxiv.org/abs/2408.00001v2">arXiv</a>"""


def test_official_listing_and_publication_preserve_edition_year_separately():
    entries = parse_listing(LISTING, venue="CVPR", year=2025)
    assert entries[0].authors == ["Alice Example"]
    paper = parse_publication(PAPER, entries[0])
    assert paper.venue_year == 2025 and paper.arxiv_id == "2408.00001"
    assert not hasattr(paper, "published_date")
    assert paper.title == "Gaussian Splatting & Methods"


@pytest.mark.parametrize(
    "html",
    [
        LISTING + LISTING,
        LISTING.replace("CVPR2025", "CVPR2024"),
        LISTING.replace("openaccess", "other").replace(
            "/content/", "https://other.example/content/"
        ),
        LISTING.replace('name="query_author"', 'name="other"'),
    ],
)
def test_listing_integrity_failures(html):
    with pytest.raises(ValueError):
        parse_listing(html, venue="CVPR", year=2025)


@pytest.mark.parametrize(
    "html",
    [
        PAPER.replace('content="2025"', 'content="2024"'),
        PAPER.replace("Example, Alice", "Other, Bob"),
        PAPER.replace("CVPR2025/papers/Example_Method", "CVPR2025/papers/Wrong_Method"),
        PAPER.replace("Pattern Recognition", "Pattern Recognition Workshops"),
    ],
)
def test_publication_identity_year_track_failures(html):
    row = parse_listing(LISTING, venue="CVPR", year=2025)[0]
    with pytest.raises(ValueError):
        parse_publication(html, row)


def test_publication_candidate_does_not_move_existing_arxiv_date():
    from datetime import UTC, datetime

    from src.extractors.cvf import publication_candidate
    from src.schema import PaperDatabase, PaperRecord

    row = parse_listing(LISTING, venue="CVPR", year=2025)[0]
    record = publication_candidate(
        parse_publication(PAPER, row), observed_at=datetime(2026, 11, 9, tzinfo=UTC)
    )
    assert record.publication_year == 2025 and record.published_date_precision == "year"
    existing = PaperRecord(
        id="stable",
        arxiv_id="2408.00001",
        title=record.title,
        authors=record.authors,
        published_date="2024-08-01",
        published_date_precision="day",
        date_placement="observed",
    )
    db = PaperDatabase(papers=[existing], total_count=1)
    db.upsert([record])
    assert len(db.papers) == 1 and db.papers[0].id == "stable"
    assert db.papers[0].published_date == "2024-08-01" and db.papers[0].publication_year == 2025
