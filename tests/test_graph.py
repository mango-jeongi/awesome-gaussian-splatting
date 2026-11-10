import json

import pytest

from src.graph import bounded_graph, graph_projection
from src.public import build_public
from src.schema import PaperDatabase, PaperRecord


def database(size=400, dense=False):
    papers = []
    for index in range(size):
        key = f"p{index:04d}"
        refs = (
            [f"p{other:04d}" for other in range(size) if other != index]
            if dense
            else (["p0000"] if index else [])
        )
        papers.append(
            PaperRecord(
                id=key, title=f"Paper {index}", openalex_id=f"W{index + 1}", db_references=refs
            )
        )
    return PaperDatabase(papers=papers, total_count=size)


def test_direction_inversion_and_caps():
    db = database(5000)
    graph = graph_projection(db)
    assert graph["adjacency"]["p0001"]["references"] == ["p0000"]
    assert len(graph["adjacency"]["p0000"]["citations"]) == 4999
    overview = bounded_graph(graph)
    assert len(overview["nodes"]) == 300 and len(overview["edges"]) == 299
    assert overview["nodes"][0]["id"] == "p0000"
    assert overview["omitted_nodes"] == 4700
    one = bounded_graph(graph, center="p0000")
    two = bounded_graph(graph, center="p0000", hops=2)
    assert len(one["nodes"]) == 80 and one["omitted_nodes"] == 4920
    assert len(two["nodes"]) == 150 and two["omitted_nodes"] == 4850
    assert one == bounded_graph(graph, center="p0000")
    assert all(edge["target"] == "p0000" for edge in one["edges"])


def test_dense_edge_budget_and_filters():
    graph = graph_projection(database(160, dense=True))
    overview = bounded_graph(graph)
    assert len(overview["edges"]) == 1200
    assert overview["omitted_edges"] == 160 * 159 - 1200
    for hops, cap in [(1, 200), (2, 400)]:
        ego = bounded_graph(graph, center="p0000", hops=hops)
        assert len(ego["edges"]) == cap and ego["omitted_edges"] > 0
    assert not bounded_graph(graph, category="missing")["nodes"]
    with pytest.raises(KeyError):
        bounded_graph(graph, center="missing")
    with pytest.raises(ValueError):
        bounded_graph(graph, center="p0000", hops=3)


@pytest.mark.parametrize("references", [["p0000"], ["p0001", "p0001"], ["archived"]])
def test_invalid_active_edges_fail(references):
    db = database(2)
    db.papers[0].db_references = references
    with pytest.raises(ValueError):
        graph_projection(db)


def test_public_graph_artifacts_parity_noop(tmp_path):
    db = database(10)
    manifest = build_public(db, tmp_path)
    descriptor = manifest["graph"]
    assert descriptor["source_sha256"] == manifest["source_sha256"]
    assert descriptor["coverage"]["edges"] == 9
    index = json.loads((tmp_path / descriptor["index"]["path"]).read_bytes())
    pointers = index["pointers"]
    assert index["nodes"]["p0000"]["incoming_count"] == 9
    records = {}
    for bucket in descriptor["buckets"]:
        assert bucket["bytes"] <= 500000
        records.update(json.loads((tmp_path / bucket["path"]).read_bytes()))
    assert set(pointers) == set(records) == {p.id for p in db.papers}
    assert records["p0001"]["references"] == ["p0000"]
    assert len(records["p0000"]["citations"]) == 9
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.rglob("*.json")}
    assert build_public(db, tmp_path) == manifest
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.rglob("*.json")}
