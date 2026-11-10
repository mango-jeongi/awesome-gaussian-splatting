"""Measure the complete offline CLI validate/graph/build path on a dense fixture."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from src.schema import PaperDatabase
from src.storage import _encode

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    stage, report = args.workdir.resolve(), args.report.resolve()
    for path in (stage, report):
        if path == ROOT or any(
            protected == path or protected in path.parents
            for protected in (ROOT / "data", ROOT / "docs")
        ):
            parser.error("Use isolated paths outside canonical data and deployed docs")
    stage.mkdir(parents=True, exist_ok=True)
    source = ROOT / "data/papers.json"
    original_hash = sha(source)
    original = PaperDatabase.load(source)
    count = 5000
    ids = [f"2501.{i:05d}" for i in range(count)]
    expected = {}
    papers = []
    for i, key in enumerate(ids):
        targets = {ids[(i + offset) % count] for offset in range(1, 51)}
        if i:
            targets.add(ids[0])
        expected[key] = sorted(targets)
        papers.append(
            original.papers[i % len(original.papers)].model_copy(
                update={
                    "id": key,
                    "arxiv_id": key,
                    "doi": None,
                    "arxiv_doi": None,
                    "openalex_id": None,
                    "metadata_evidence": {},
                    "paper_url": f"https://arxiv.org/abs/{key}",
                    "pdf_url": f"https://arxiv.org/pdf/{key}.pdf",
                    "referenced_works": [
                        f"https://arxiv.org/abs/{target}" for target in sorted(targets)
                    ],
                    "db_references": [],
                    "db_citations": [],
                    "db_citation_count": 0,
                }
            )
        )
    fixture = stage / "papers.json"
    PaperDatabase(papers=papers, total_count=count, last_updated="2026-11-10T00:00:00Z").save(
        fixture
    )
    fixture_hash = sha(fixture)
    prefix = [
        sys.executable,
        "-m",
        "src.cli",
        "--data",
        str(fixture),
        "--readme",
        str(stage / "README.md"),
        "--docs-data",
        str(stage / "docs/papers.json"),
    ]
    timings = []
    started = time.perf_counter()
    for operation in ("validate", "graph", "build", "validate"):
        before = time.perf_counter()
        process = subprocess.run(
            [*prefix, operation],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
            check=True,
        )
        timings.append(
            {
                "operation": operation,
                "seconds": round(time.perf_counter() - before, 4),
                "stdout": process.stdout.strip(),
            }
        )
    elapsed = time.perf_counter() - started
    loaded = PaperDatabase.load(fixture)
    assert {p.id: p.db_references for p in loaded.papers} == expected
    incoming = {key: set() for key in ids}
    for key, targets in expected.items():
        for target in targets:
            incoming[target].add(key)
    assert all(
        set(p.db_citations) == incoming[p.id] and p.db_citation_count == len(incoming[p.id])
        for p in loaded.papers
    )
    assert sha(source) == original_hash
    payload = {
        "scope": "Offline CLI validate, graph, build, validate; includes subprocess startup and disk I/O; excludes fixture preparation and post-run assertions",
        "records": count,
        "directed_edges": sum(map(len, expected.values())),
        "outgoing_incoming_and_counts_exact": True,
        "seconds": round(elapsed, 4),
        "budget_seconds": 60,
        "budget_passed": elapsed <= 60,
        "operations": timings,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "source_canonical_sha256": original_hash,
        "fixture_input_sha256": fixture_hash,
        "fixture_output_sha256": sha(fixture),
        "canonical_modified": False,
        "code_sha256": {
            str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / "src").rglob("*.py"))
        },
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_bytes(_encode(payload))
    print(
        json.dumps(
            {key: payload[key] for key in ("records", "directed_edges", "seconds", "budget_passed")}
        )
    )
    return 0 if elapsed <= 60 else 1


if __name__ == "__main__":
    raise SystemExit(main())
