"""Unified CLI for the Awesome Gaussian Splatting Data Ops pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.builder import build_artifacts
from src.enricher import MultiProviderEnricher
from src.extractors.arxiv import ArxivExtractor
from src.extractors.huggingface import HuggingFaceExtractor
from src.schema import PaperDatabase
from src.seed import seed_database

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT_DIR / "data" / "papers.json"
DEFAULT_TAXONOMY = ROOT_DIR / "config" / "taxonomy.yaml"
DEFAULT_README = ROOT_DIR / "README.md"
DEFAULT_DOCS_DATA = ROOT_DIR / "docs" / "papers.json"
DEFAULT_LOCAL_SEED = ROOT_DIR.parent / "scripts" / "success.json"


def cmd_ingest(args: argparse.Namespace) -> int:
    """Fetch recent papers from active extractors, enrich, and upsert into data/papers.json."""
    db = PaperDatabase.load(args.data)
    enricher = MultiProviderEnricher(args.taxonomy)

    arxiv = ArxivExtractor()
    fetched = arxiv.fetch_recent(max_results=args.max_results)

    hf = HuggingFaceExtractor()
    fetched.extend(hf.fetch_recent(max_results=args.max_results))

    enriched = [enricher.enrich(rec, use_llm=not args.no_llm) for rec in fetched]
    added = db.upsert(enriched)
    db.save(args.data)
    print(
        f"[ingest] Fetched {len(fetched)} papers | Added {added} new | Total OBT count: {db.total_count}"
    )
    return 0


def cmd_retag(args: argparse.Namespace) -> int:
    """Retroactively re-evaluate all records in data/papers.json against config/taxonomy.yaml."""
    db = PaperDatabase.load(args.data)
    enricher = MultiProviderEnricher(args.taxonomy)
    db.papers = [enricher.enrich(p, use_llm=False) for p in db.papers]
    db.save(args.data)
    print(f"[retag] Re-indexed {len(db.papers)} records against {args.taxonomy}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Compile data/papers.json into README.md and docs/papers.json."""
    build_artifacts(
        data_path=args.data,
        taxonomy_path=args.taxonomy,
        readme_path=args.readme,
        docs_data_path=args.docs_data,
    )
    print(f"[build] Compiled {args.readme} and synced {args.docs_data}")
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    """Seed initial database from local Papers workspace and arXiv backfill."""
    added = seed_database(
        data_path=args.data,
        taxonomy_path=args.taxonomy,
        local_success_json=args.local_seed,
        fetch_arxiv_count=args.max_results,
    )
    build_artifacts(
        data_path=args.data,
        taxonomy_path=args.taxonomy,
        readme_path=args.readme,
        docs_data_path=args.docs_data,
    )
    db = PaperDatabase.load(args.data)
    print(f"[seed] Added {added} records | Total indexed in OBT: {db.total_count}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate that data/papers.json conforms strictly to the Pydantic v2 OBT schema."""
    db = PaperDatabase.load(args.data)
    if db.total_count != len(db.papers):
        print(f"[validate] Error: total_count ({db.total_count}) != len(papers) ({len(db.papers)})")
        return 1
    print(f"[validate] OK — {len(db.papers)} valid PaperRecords in {args.data}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="awesome-3dgs",
        description="Data Ops CLI for the Awesome 3D Gaussian Splatting paper database.",
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    parser.add_argument("--docs-data", type=Path, default=DEFAULT_DOCS_DATA)

    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Fetch & enrich delta papers from arXiv")
    p_ingest.add_argument("--max-results", type=int, default=50)
    p_ingest.add_argument(
        "--no-llm", action="store_true", help="Disable LLM calls and use deterministic rules only"
    )
    p_ingest.set_defaults(func=cmd_ingest)

    p_retag = sub.add_parser(
        "retag", help="Retroactively apply taxonomy.yaml rules across all papers"
    )
    p_retag.set_defaults(func=cmd_retag)

    p_build = sub.add_parser(
        "build", help="Compile README.md and docs/papers.json from data/papers.json"
    )
    p_build.set_defaults(func=cmd_build)

    p_seed = sub.add_parser("seed", help="Seed database from local Papers/success.json and arXiv")
    p_seed.add_argument("--local-seed", type=Path, default=DEFAULT_LOCAL_SEED)
    p_seed.add_argument("--max-results", type=int, default=100)
    p_seed.set_defaults(func=cmd_seed)

    p_val = sub.add_parser("validate", help="Validate data/papers.json against Pydantic v2 schema")
    p_val.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
