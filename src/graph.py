"""Deterministic bounded projections of citing-paper -> referenced-paper edges."""

from __future__ import annotations

from src.identity import IdentityIndex, identifier_key, normalize_arxiv
from src.schema import PaperDatabase


def graph_projection(db: PaperDatabase) -> dict:
    identity = IdentityIndex(db.papers, db.aliases)
    for paper in db.papers:
        if paper.arxiv_id:
            identity.bind(f"doi:10.48550/arxiv.{normalize_arxiv(paper.arxiv_id)}", paper.id)
    outgoing = {paper.id: set(paper.db_references) for paper in db.papers}
    incoming = {paper.id: set() for paper in db.papers}
    unmatched = matched = omitted_self = 0
    for paper in db.papers:
        if len(outgoing[paper.id]) != len(paper.db_references) or paper.id in outgoing[paper.id]:
            raise ValueError("Graph contains duplicate or self edges")
        for target in outgoing[paper.id]:
            if target not in incoming:
                raise ValueError("Graph endpoint is not active")
            incoming[target].add(paper.id)
        for ref in {identifier_key(ref) for ref in paper.referenced_works}:
            target = identity.aliases.get(ref)
            if target == paper.id:
                omitted_self += 1
            elif target:
                matched += 1
            else:
                unmatched += 1
    nodes = {}
    for paper in db.papers:
        observation = db._signal_stores.get("openalex")
        observation = observation.observations.get(paper.id) if observation else None
        count = (
            observation.values.get("citation_count")
            if observation and observation.fetched_at
            else paper.citation_count
        )
        nodes[paper.id] = {
            "id": paper.id,
            "title": paper.title,
            "year": paper.year,
            "categories": paper.categories,
            "incoming_count": len(incoming[paper.id]),
            "global_citations": count,
            "provider": "openalex",
            "observed_at": observation.fetched_at.isoformat()
            if observation and observation.fetched_at
            else None,
            "provenance_status": "observed"
            if observation
            and observation.fetched_at
            and observation.values.get("referenced_works") == paper.referenced_works
            else "legacy_unverified",
        }
    return {
        "direction": "citing_to_referenced",
        "coverage_label": "Partial citation lineage",
        "nodes": nodes,
        "adjacency": {
            key: {"references": sorted(outgoing[key]), "citations": sorted(incoming[key])}
            for key in sorted(nodes)
        },
        "coverage": {
            "active_nodes": len(nodes),
            "edges": sum(map(len, outgoing.values())),
            "matched_source_references": matched,
            "unmatched_source_references": unmatched,
            "self_references_omitted": omitted_self,
        },
    }


def bounded_graph(
    graph: dict,
    *,
    center: str | None = None,
    hops: int = 1,
    year: int | None = None,
    category: str | None = None,
) -> dict:
    nodes, adjacency = graph["nodes"], graph["adjacency"]
    eligible = {
        key
        for key, node in nodes.items()
        if (year is None or node["year"] == year)
        and (category is None or category in node["categories"])
    }

    def priority(key):
        node = nodes[key]
        return (-node["incoming_count"], -(node["global_citations"] or 0), key)

    if center is None:
        node_cap, edge_cap = 300, 1200
        candidates = eligible
        selected = sorted(candidates, key=priority)[:node_cap]
    else:
        if center not in nodes:
            raise KeyError(center)
        if hops not in (1, 2):
            raise ValueError("Only one or two hops are supported")
        node_cap, edge_cap = (80, 200) if hops == 1 else (150, 400)
        distances = {center: 0}
        frontier = {center}
        for distance in range(1, hops + 1):
            following = set()
            for key in frontier:
                following.update(adjacency[key]["references"])
                following.update(adjacency[key]["citations"])
            following -= distances.keys()
            following &= eligible
            distances.update({key: distance for key in following})
            frontier = following
        candidates = set(distances)
        selected = sorted(candidates, key=lambda key: (distances[key], priority(key)))[:node_cap]
    selected_set = set(selected)
    edges = sorted(
        (source, target)
        for source in selected
        for target in adjacency[source]["references"]
        if target in selected_set
    )
    return {
        "label": "Most cited in this corpus" if center is None else "Paper citation neighborhood",
        "direction": graph["direction"],
        "coverage_label": graph["coverage_label"],
        "center": center,
        "hops": hops if center is not None else None,
        "nodes": [nodes[key] for key in selected],
        "edges": [
            {"source": source, "target": target, "provider": "openalex"}
            for source, target in edges[:edge_cap]
        ],
        "omitted_nodes": len(candidates) - len(selected),
        "omitted_edges": max(0, len(edges) - edge_cap),
        "node_cap": node_cap,
        "edge_cap": edge_cap,
    }
