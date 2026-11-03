"""Unit tests for Pydantic v2 Schema-on-Read OBT models (arXiv and non-arXiv records)."""

from pathlib import Path

from src.schema import PaperDatabase, PaperRecord, TaxonomyConfig


def test_arxiv_paper_record_normalization() -> None:
    rec = PaperRecord(
        arxiv_id="https://arxiv.org/abs/2308.04079v2",
        title="3D Gaussian Splatting\n  for Real-Time   Radiance Field Rendering",
        authors=["Bernhard Kerbl", "Georgios Kopanas"],
        published_date="2023-08-08",
        abstract="We introduce three key elements that allow us to achieve state-of-the-art visual quality.",
    )
    assert rec.arxiv_id == "2308.04079"
    assert rec.id == "2308.04079"
    assert rec.title == "3D Gaussian Splatting for Real-Time Radiance Field Rendering"
    assert rec.first_author == "Kerbl et al."
    assert rec.year == 2023
    assert rec.month == 8
    assert rec.paper_url == "https://arxiv.org/abs/2308.04079"
    assert rec.pdf_url == "https://arxiv.org/pdf/2308.04079.pdf"
    assert "state-of-the-art" in rec.tldr


def test_non_arxiv_schema_on_read_resilience() -> None:
    """Verify non-arXiv papers (e.g., IEEE/manual with DOI or title-only) validate cleanly."""
    rec = PaperRecord(
        source="ieee",
        doi="10.1109/TVCG.2024.123456",
        title="Efficient Representation of 3D Spatial Data for Defense-Related Applications",
        authors=["Kahl"],
        year=2025,
        month=11,
        abstract="Investigates compact 3D spatial representations for tactical situational awareness.",
    )
    assert rec.arxiv_id is None
    assert rec.id == "doi:10.1109/tvcg.2024.123456"
    assert rec.first_author == "Kahl"
    assert rec.published_date == "2025-11-01"
    assert "@article{kahl2025efficient" in rec.to_bibtex()


def test_database_idempotent_upsert(tmp_path: Path) -> None:
    db = PaperDatabase()
    r1 = PaperRecord(
        arxiv_id="2308.04079",
        title="3D Gaussian Splatting for Real-Time Radiance Field Rendering",
        authors=["Bernhard Kerbl"],
        published_date="2023-08-08",
        abstract="Short abstract.",
    )
    r2_enriched = PaperRecord(
        arxiv_id="2308.04079",
        title="3D Gaussian Splatting for Real-Time Radiance Field Rendering",
        authors=["Bernhard Kerbl"],
        published_date="2023-08-08",
        venue="SIGGRAPH 2023",
        code_url="https://github.com/graphdeco-inria/gaussian-splatting",
        abstract="Longer enriched abstract with full technical details.",
        tags=["3DGS", "CUDA"],
    )

    added_first = db.upsert([r1])
    assert added_first == 1
    assert db.total_count == 1

    added_second = db.upsert([r2_enriched])
    assert added_second == 0
    assert db.total_count == 1
    assert db.papers[0].venue == "SIGGRAPH 2023"
    assert db.papers[0].code_url == "https://github.com/graphdeco-inria/gaussian-splatting"
    assert "CUDA" in db.papers[0].tags

    out_file = tmp_path / "papers.json"
    db.save(out_file)
    reloaded = PaperDatabase.load(out_file)
    assert reloaded.total_count == 1


def test_taxonomy_yaml_loads() -> None:
    tax_path = Path(__file__).resolve().parent.parent / "config" / "taxonomy.yaml"
    tax = TaxonomyConfig.from_yaml(tax_path)
    assert len(tax.categories) >= 6
    assert "3DGS" in tax.technical_tags
    assert "SLAM" in tax.technical_tags
