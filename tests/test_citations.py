"""Tests for OpenAlex citation enrichment and internal cross-paper knowledge graph."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.extractors.citations import (
    OpenAlexCitationClient,
    _is_title_similar,
    build_citation_knowledge_graph,
)
from src.schema import PaperDatabase, PaperRecord


def test_title_similarity_matching():
    """Verify robust title comparison ignoring punctuation and minor subtitle variants."""
    t1 = "3D Gaussian Splatting for Real-Time Radiance Field Rendering"
    t2 = "3D Gaussian Splatting for Real-Time Radiance Field Rendering (SIGGRAPH 2023)"
    t3 = "pixelSplat: 3D Gaussian Splats from Image Pairs"
    t4 = "pixelSplat: 3D Gaussian Splats from Image Pairs for Scalable Generalizable 3D Reconstruction"
    t_diff = "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis"

    assert _is_title_similar(t1, t2)
    assert _is_title_similar(t3, t4)
    assert not _is_title_similar(t1, t_diff)


def test_internal_citation_knowledge_graph():
    """Verify bidirectional knowledge graph construction from referenced_works."""
    # Create synthetic network:
    # A (Foundational 3DGS) <- cited by B and C
    # B (2DGS)              <- cited by C, references A
    # C (Dynamic 4DGS)      <- references A and B
    paper_a = PaperRecord(
        id="2308.04079",
        arxiv_id="2308.04079",
        title="3D Gaussian Splatting for Real-Time Radiance Field Rendering",
        openalex_id="https://openalex.org/W1",
        referenced_works=[],
    )
    paper_b = PaperRecord(
        id="2403.17888",
        arxiv_id="2403.17888",
        title="2D Gaussian Splatting for Geometrically Accurate Radiance Fields",
        openalex_id="https://openalex.org/W2",
        referenced_works=["https://openalex.org/W1"],
    )
    paper_c = PaperRecord(
        id="2311.16911",
        arxiv_id="2311.16911",
        title="Real-Time 4D Gaussian Splatting",
        openalex_id="https://openalex.org/W3",
        referenced_works=["https://openalex.org/W1", "https://openalex.org/W2"],
    )

    db = PaperDatabase(papers=[paper_a, paper_b, paper_c], total_count=3)
    stats = build_citation_knowledge_graph(db)

    assert stats["total_nodes"] == 3
    assert stats["total_edges"] == 3
    assert stats["connected_papers"] == 3

    # Verify outgoing references within DB
    assert paper_a.db_references == []
    assert paper_b.db_references == ["2308.04079"]
    assert set(paper_c.db_references) == {"2308.04079", "2403.17888"}

    # Verify incoming citations within DB
    assert set(paper_a.db_citations) == {"2403.17888", "2311.16911"}
    assert paper_a.db_citation_count == 2

    assert paper_b.db_citations == ["2311.16911"]
    assert paper_b.db_citation_count == 1

    assert paper_c.db_citations == []
    assert paper_c.db_citation_count == 0


def test_openalex_client_batch_parsing():
    """Verify batch DOI querying and response mapping."""
    client = OpenAlexCitationClient()
    mock_payload = {
        "results": [
            {
                "id": "https://openalex.org/W4385318467",
                "doi": "https://doi.org/10.48550/arxiv.2308.04079",
                "cited_by_count": 6071,
                "referenced_works": ["https://openalex.org/W100", "https://openalex.org/W101"],
            }
        ]
    }
    client._make_request = MagicMock(return_value=mock_payload)

    paper = PaperRecord(
        id="2308.04079",
        arxiv_id="2308.04079",
        title="3D Gaussian Splatting for Real-Time Radiance Field Rendering",
    )

    results = client.fetch_batch_by_doi([paper])
    assert "2308.04079" in results
    res = results["2308.04079"]
    assert res["citation_count"] == 6071
    assert res["openalex_id"] == "https://openalex.org/W4385318467"
    assert len(res["referenced_works"]) == 2

