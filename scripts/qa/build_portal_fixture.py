"""Build an isolated 5,000-record portal and dense citation acceptance fixture."""

import argparse
import hashlib
import json
import platform
import shutil
import time
from collections import Counter
from pathlib import Path

from src.public import build_public
from src.schema import PaperDatabase
from src.storage import _encode

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/papers.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or any(
        protected == output or protected in output.parents
        for protected in (ROOT / "data", ROOT / "docs")
    ):
        parser.error("Use an isolated output directory outside canonical data and docs")
    started = time.perf_counter()
    source = PaperDatabase.load(args.source)
    if not source.papers:
        parser.error("Source catalog must contain records")
    count = 5000
    ids = [f"2501.{index:05d}" for index in range(count)]
    incoming = {key: [] for key in ids}
    outgoing = {}
    for index, key in enumerate(ids):
        refs = {ids[(index + offset) % count] for offset in range(1, 51)}
        if index:
            refs.add(ids[0])
        outgoing[key] = sorted(refs)
        for target in refs:
            incoming[target].append(key)
    papers = []
    for index, key in enumerate(ids):
        papers.append(
            source.papers[index % len(source.papers)].model_copy(
                update={
                    "id": key,
                    "arxiv_id": key,
                    "doi": None,
                    "arxiv_doi": None,
                    "metadata_evidence": {},
                    "openalex_id": None,
                    "paper_url": f"https://arxiv.org/abs/{key}",
                    "pdf_url": f"https://arxiv.org/pdf/{key}.pdf",
                    "referenced_works": [],
                    "db_references": outgoing[key],
                    "db_citations": sorted(incoming[key]),
                    "db_citation_count": len(incoming[key]),
                }
            )
        )
    db = PaperDatabase.model_validate(
        PaperDatabase(
            papers=papers,
            total_count=count,
            last_updated="2026-11-10T00:00:00Z",
        ).model_dump()
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_bytes((ROOT / "docs/index.html").read_bytes())
    shutil.copytree(ROOT / "docs/assets", output / "assets", dirs_exist_ok=True)
    manifest = build_public(db, output / "data")
    report = {
        "fixture_records": count,
        "fixture": "Current metadata with synthetic IDs; 50 forward ring references per node plus a shared hub",
        "source_canonical_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "portal_artifact_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [ROOT / "docs/index.html", *sorted((ROOT / "docs/assets").glob("*"))]
            if path.is_file()
        },
        "source_records": len(source.papers),
        "code_records": sum(bool(paper.code_url) for paper in papers),
        "year_counts": dict(Counter(str(paper.year) for paper in papers)),
        "directed_edges": sum(map(len, outgoing.values())),
        "build_validate_graph_seconds": round(time.perf_counter() - started, 3),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "index_bytes": manifest["index"]["bytes"],
        "index_gzip_bytes": manifest["index"]["gzip_bytes"],
        "detail_shards": len(manifest["details"]),
        "largest_detail_bytes": max(item["bytes"] for item in manifest["details"]),
        "build_digest": manifest["build_digest"],
        "canonical_modified": False,
    }
    (output / "fixture-measurements.json").write_bytes(_encode(report))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
