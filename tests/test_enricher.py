"""Unit tests for deterministic URL/venue regex extraction and dynamic tag classification."""

from pathlib import Path

from src.enricher import MultiProviderEnricher, extract_urls_and_venue
from src.schema import PaperRecord

TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "config" / "taxonomy.yaml"


def test_extract_urls_and_venue_from_comment_and_abstract() -> None:
    rec = PaperRecord(
        arxiv_id="2403.12345",
        title="SplaTAM: Splat, Track & Map 3D Gaussians for Dense RGB-D SLAM",
        published_date="2024-04-01",
        comment="Accepted to CVPR 2024. Project page: https://spla-tam.github.io/ Code: https://github.com/spla-tam/SplaTAM.git",
        abstract="We present a dense RGB-D SLAM system based on 3D Gaussian Splatting.",
    )
    enriched = extract_urls_and_venue(rec)
    assert enriched.venue == "CVPR 2024"
    assert enriched.code_url == "https://github.com/spla-tam/SplaTAM"
    assert enriched.project_url == "https://spla-tam.github.io/"


def test_deterministic_enricher_categorization_and_tags() -> None:
    enricher = MultiProviderEnricher(TAXONOMY_PATH)
    rec = PaperRecord(
        arxiv_id="2409.99999",
        title="ThermalGaussian: Thermal 3D Gaussian Splatting for Multimodal Scenes",
        published_date="2024-09-15",
        abstract="Recent 3DGS methods cannot handle thermal sensors. In this paper, we propose ThermalGaussian to reconstruct 3D thermal infrared and RGB scenes using joint radiometric splatting.",
    )
    res = enricher.enrich(rec, use_llm=False)
    assert res.primary_category == "Medical, Defense & Multimodal Sensors"
    assert "Thermal & IR" in res.tags
    # Verify word-boundary precision: general reconstruction should NOT trigger Medical & Healthcare
    assert "Medical & Healthcare" not in res.tags
    # Verify TL;DR is distilled from the contribution rather than the generic first sentence
    assert res.tldr.startswith("Proposes ThermalGaussian to reconstruct 3D thermal infrared")


def test_venue_requires_author_comment_and_never_invents_edition_year():
    record = PaperRecord(
        arxiv_id="2412.00001",
        title="Gaussian Splatting fixture",
        published_date="2024-12-01",
        comment="Accepted to CVPR",
        abstract="We compare against an ICCV 2023 method.",
    )
    enriched = extract_urls_and_venue(record)
    assert enriched.venue == "CVPR"
    assert enriched.metadata_evidence["venue"][0].source == "author_comment"
    abstract_only = record.model_copy(update={"comment": None})
    assert extract_urls_and_venue(abstract_only).venue is None
