"""Tests for OpenAlex citation enrichment and internal cross-paper knowledge graph."""

from __future__ import annotations

import httpx

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
    mock_payload = {
        "meta": {"count": 1},
        "results": [
            {
                "id": "https://openalex.org/W4385318467",
                "doi": "https://doi.org/10.48550/arxiv.2308.04079",
                "cited_by_count": 6071,
                "referenced_works": ["https://openalex.org/W100", "https://openalex.org/W101"],
            }
        ],
    }
    client = OpenAlexCitationClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=mock_payload))
    )

    paper = PaperRecord(
        id="2308.04079",
        arxiv_id="2308.04079",
        title="3D Gaussian Splatting for Real-Time Radiance Field Rendering",
    )

    results = client.fetch_batch_by_doi([paper])
    assert "2308.04079" in results
    client.close()
    res = results["2308.04079"]
    assert res["citation_count"] == 6071
    assert res["openalex_id"] == "https://openalex.org/W4385318467"
    assert len(res["referenced_works"]) == 2


def test_graph_mixed_identifiers_and_indexed_inversion(monkeypatch):
    first = PaperRecord(
        id="stable/one",
        title="The first foundational method",
        arxiv_id="2308.04079",
        doi="10.1000/ONE",
        openalex_id="https://openalex.org/W123",
    )
    second = PaperRecord(
        id="stable/two",
        title="The second citing method",
        referenced_works=[
            "W123",
            "https://openalex.org/W123",
            "https://doi.org/10.1000/one",
            "https://arxiv.org/abs/2308.04079v2",
            "10.48550/arxiv.2308.04079",
            "stable/two",
            "W999",
        ],
    )
    db = PaperDatabase(papers=[first, second], total_count=2)

    def forbid_linear_lookup(*args):
        raise AssertionError("Graph inversion must not call db.get")

    monkeypatch.setattr(PaperDatabase, "get", forbid_linear_lookup)
    stats = build_citation_knowledge_graph(db)
    assert first.db_citations == [second.id]
    assert second.db_references == [first.id]
    assert first.db_citation_count == 1
    assert stats["total_edges"] == 1
    assert stats["unmatched_references"] == 1
    assert stats["self_references_omitted"] == 1
    before = db.model_dump()
    assert build_citation_knowledge_graph(db) == stats
    assert db.model_dump() == before


def test_citation_doi_ownership_and_successful_empty_references(monkeypatch):
    import src.extractors.citations as citations
    from src.extractors.citations import enrich_database_citations

    arxiv = PaperRecord(
        arxiv_id="2308.04079", title="A source identified method", referenced_works=["W99"]
    )
    publisher = PaperRecord(id="publisher", title="A proceedings identified method")

    class FixtureClient:
        def fetch_batch_by_doi(self, papers):
            return {
                arxiv.id: {
                    "citation_count": 0,
                    "openalex_id": "W1",
                    "referenced_works": [],
                    "doi": "https://doi.org/10.48550/arxiv.2308.04079",
                }
            }

        def fetch_single_by_title(self, paper):
            return {
                "citation_count": 1,
                "openalex_id": "W2",
                "referenced_works": [],
                "doi": "https://doi.org/10.1000/PUBLISHED",
            }

    monkeypatch.setattr(citations.time, "sleep", lambda seconds: None)
    db = PaperDatabase(papers=[arxiv, publisher], total_count=2)
    enrich_database_citations(db, client=FixtureClient())
    assert arxiv.doi is None
    assert arxiv.arxiv_doi == "10.48550/arxiv.2308.04079"
    assert arxiv.referenced_works == []
    assert publisher.doi == "10.1000/published"
