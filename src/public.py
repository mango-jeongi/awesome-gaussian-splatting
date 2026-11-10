"""Deterministic immutable portal projections with bounded detail shards."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from src.identity import IdentityIndex
from src.schema import PaperDatabase
from src.storage import _atomic_write

INDEX_FIELDS = [
    "id",
    "title",
    "first_author",
    "published_date",
    "categories",
    "tags",
    "venue",
    "tldr",
    "arxiv_id",
    "source",
    "paper_url",
    "pdf_url",
    "code_url",
    "project_url",
    "citation_count",
    "db_citation_count",
    "reference_count",
    "detail_path",
    "citation_status",
    "published_date_precision",
    "citation_fetched_at",
]
DATE_PRECISIONS = ("day", "month", "year", "unknown")
DETAIL_LIMIT = 500_000
INDEX_LIMIT = 4_000_000


def compact(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
    ).encode()


def _artifact(root: Path, prefix: str, value: object) -> dict:
    payload = compact(value)
    digest = hashlib.sha256(payload).hexdigest()
    path = f"{prefix}.{digest}.json"
    target = root / path
    if not target.exists() or target.read_bytes() != payload:
        _atomic_write(target, payload)
    return {
        "path": path,
        "sha256": digest,
        "bytes": len(payload),
        "gzip_bytes": len(gzip.compress(payload, mtime=0)),
    }


def _details(
    root: Path, prefix: str, papers: list[dict], pointers: dict[str, str], artifacts: list[dict]
) -> None:
    payload = {paper["id"]: paper for paper in papers}
    if len(compact(payload)) > DETAIL_LIMIT:
        if len(papers) <= 1:
            raise ValueError("Single paper exceeds detail artifact size budget")
        middle = len(papers) // 2
        _details(root, prefix + "-0", papers[:middle], pointers, artifacts)
        _details(root, prefix + "-1", papers[middle:], pointers, artifacts)
        return
    artifact = _artifact(root, prefix, payload)
    artifacts.append(artifact)
    pointers.update({paper["id"]: artifact["path"] for paper in papers})


def build_public(
    db: PaperDatabase, root: str | Path, *, reviewed=None, signals=None, trending=None
) -> dict:
    """Publish artifacts first and switch one manifest last; retain old generations."""
    root = Path(root)
    from src.reviewed_public import reviewed_cells

    cells = reviewed_cells(db, reviewed) if reviewed is not None else {}
    identity = IdentityIndex(db.papers, db.aliases)
    categories = sorted({category for paper in db.papers for category in paper.categories})
    tags = sorted({tag for paper in db.papers for tag in paper.tags})
    category_ids = {value: position for position, value in enumerate(categories)}
    tag_ids = {value: position for position, value in enumerate(tags)}
    groups: dict[str, list[dict]] = {}
    signal_store = db._signal_stores.get("openalex")
    statuses = {}
    citation_values = {}
    for paper in sorted(db.papers, key=lambda paper: paper.id):
        record = paper.model_dump(mode="json")
        observation = signal_store.observations.get(paper.id) if signal_store else None
        status = observation.status if observation else "unknown"
        record["citation_status"] = status
        record["reviewed_benchmark_cells"] = cells.get(paper.id, [])
        record["citation_fetched_at"] = (
            observation.fetched_at.isoformat() if observation and observation.fetched_at else None
        )
        statuses[paper.id] = status
        citation_values[paper.id] = (
            observation.values.get("citation_count")
            if observation and observation.fetched_at is not None
            else (paper.citation_count if paper.citation_count else None)
        )
        if signals is not None:
            source_signal = signals["papers"][paper.id]["openalex"]
            statuses[paper.id] = source_signal["status"]
            citation_values[paper.id] = source_signal["citation_count"]
            record["citation_status"] = source_signal["status"]
            record["citation_fetched_at"] = source_signal["fetched_at"]
        record["citation_count"] = citation_values[paper.id]
        groups.setdefault(paper.published_date[:7], []).append(record)
    pointers: dict[str, str] = {}
    details: list[dict] = []
    for month, records in sorted(groups.items()):
        _details(root, f"details/{month}", records, pointers, details)
    detail_paths = sorted(set(pointers.values()))
    detail_ids = {value: position for position, value in enumerate(detail_paths)}
    rows = []
    search = {}
    for paper in sorted(db.papers, key=lambda paper: paper.id):
        row = [
            paper.id,
            paper.title,
            paper.first_author,
            paper.published_date,
            [category_ids[value] for value in paper.categories],
            [tag_ids[value] for value in paper.tags],
            paper.venue,
            paper.tldr[:210],
            paper.arxiv_id,
            paper.source,
            None
            if paper.arxiv_id and paper.paper_url == f"https://arxiv.org/abs/{paper.arxiv_id}"
            else paper.paper_url,
            None
            if paper.arxiv_id and paper.pdf_url == f"https://arxiv.org/pdf/{paper.arxiv_id}.pdf"
            else paper.pdf_url,
            paper.code_url,
            paper.project_url,
            citation_values[paper.id],
            paper.db_citation_count,
            len(paper.db_references),
            detail_ids[pointers[paper.id]],
            statuses[paper.id],
            DATE_PRECISIONS.index(paper.published_date_precision),
            signals["papers"][paper.id]["openalex"]["fetched_at"] if signals is not None else None,
        ]
        rows.append(row)
        search[paper.id] = (
            f"{paper.title} {' '.join(paper.authors)} {paper.abstract} {paper.tldr} {paper.venue or ''} {paper.id} {' '.join(paper.tags)}".lower()
        )
    index_value = {
        "fields": INDEX_FIELDS,
        "categories": categories,
        "tags": tags,
        "papers": rows,
        "detail_paths": detail_paths,
        "date_precisions": DATE_PRECISIONS,
    }
    if len(compact(index_value)) > INDEX_LIMIT:
        raise ValueError("Compact index exceeds 4 MB budget")
    index = _artifact(root, "index", index_value)
    search_artifact = _artifact(root, "search", search)
    aliases = _artifact(root, "aliases", identity.aliases)
    from src.curation import validate_archive

    ledger = validate_archive(db)
    archive = _artifact(
        root,
        "archive",
        {
            "aliases": ledger.alias_targets(set(identity.by_id)),
            "papers": {
                paper_id: {
                    "id": paper_id,
                    "disposition": entry.disposition,
                    "merged_into": entry.merged_into,
                    "reason": entry.reason,
                    "reviewed_at": entry.reviewed_at.isoformat(),
                }
                for paper_id, entry in ledger.entries.items()
            },
        },
    )
    from src.graph import bounded_graph, graph_projection

    graph = graph_projection(db)
    graph_source = hashlib.sha256(compact(db.model_dump(mode="json"))).hexdigest()
    graph_pointers = {}
    graph_buckets = []
    graph_records = [
        {"id": key, "node": graph["nodes"][key], **adjacency}
        for key, adjacency in graph["adjacency"].items()
    ]
    _details(root, "graph/adjacency", graph_records, graph_pointers, graph_buckets)
    graph_artifacts = {
        "source_sha256": graph_source,
        "direction": graph["direction"],
        "coverage": graph["coverage"],
        "coverage_label": graph["coverage_label"],
        "overview": _artifact(root, "graph/overview", bounded_graph(graph)),
        "index": _artifact(
            root,
            "graph/index",
            {
                "pointers": graph_pointers,
                "nodes": {
                    key: {
                        field: node[field]
                        for field in ("incoming_count", "global_citations", "year", "categories")
                    }
                    for key, node in graph["nodes"].items()
                },
            },
        ),
        "buckets": graph_buckets,
    }
    manifest = {
        "schema_version": "1.0.0",
        "graph": graph_artifacts,
        "last_updated": db.last_updated,
        "total_count": len(db.papers),
        "total_edges": sum(len(paper.db_references) for paper in db.papers),
        "source_sha256": hashlib.sha256(compact(db.model_dump(mode="json"))).hexdigest(),
        "index": index,
        "search": search_artifact,
        "aliases": aliases,
        "archive": archive,
        "details": details,
    }
    if signals is not None:
        if len(compact(signals)) > INDEX_LIMIT:
            raise ValueError("Public provider signal artifact exceeds 4 MB budget")
        manifest["signals"] = _artifact(root, "signals", signals)
    if trending is not None:
        if len(compact(trending)) > INDEX_LIMIT:
            raise ValueError("Public trending artifact exceeds 4 MB budget")
        manifest["trending"] = _artifact(root, "trending", trending)
    manifest["build_digest"] = hashlib.sha256(compact(manifest)).hexdigest()
    path = root / "manifest.json"
    payload = compact(manifest)
    if not path.exists() or path.read_bytes() != payload:
        _atomic_write(path, payload)
    return manifest
