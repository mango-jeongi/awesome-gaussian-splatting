"""Unified CLI for the Awesome Gaussian Splatting Data Ops pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.backfill_session import BackfillSession, HistoricalRequest
from src.builder import build_artifacts
from src.curation import ArchiveReview, prepare_archive_review
from src.daily import DailySession
from src.enricher import MultiProviderEnricher
from src.environment import load_local_environment
from src.extractors.arxiv import DEFAULT_SEARCH_QUERY, ArxivExtractor
from src.extractors.citations import (
    build_citation_knowledge_graph,
    enrich_database_citations,
)
from src.extractors.openalex import OpenAlexClient
from src.extractors.semanticscholar import SemanticScholarClient, refresh_semanticscholar
from src.file_lock import exclusive_file
from src.identity import normalize_doi
from src.momentum import citation_velocity
from src.observations import SignalStore
from src.openalex_cache import OpenAlexCache, refresh_openalex, refresh_ttl
from src.ranking import RankingConfig, rank_trending
from src.relevance import RelevancePolicy, audit_relevance
from src.relevance_benchmark import evaluate_relevance
from src.schema import PaperDatabase
from src.seed import seed_database
from src.semanticscholar_history import SemanticScholarHistory, history_path
from src.signal_refresh import refresh_signals
from src.storage import _atomic_write, _encode, load_store, write_store

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT_DIR / "data" / "papers.json"
DEFAULT_TAXONOMY = ROOT_DIR / "config" / "taxonomy.yaml"
DEFAULT_README = ROOT_DIR / "README.md"
DEFAULT_DOCS_DATA = ROOT_DIR / "docs" / "papers.json"
DEFAULT_LOCAL_SEED = ROOT_DIR.parent / "scripts" / "success.json"


def utc_bound(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            parsed = parsed.replace(tzinfo=UTC)
        if parsed.utcoffset() is None:
            raise ValueError("Timezone is required")
        return parsed.astimezone(UTC)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Use an ISO UTC/offset timestamp or YYYY-MM-DD UTC boundary"
        ) from None


def cmd_refresh_signals(args: argparse.Namespace) -> int:
    load_local_environment(ROOT_DIR)
    filenames = {
        "openalex": "openalex-cache.json",
        "semanticscholar": "semanticscholar.json",
        "huggingface": "huggingface.json",
    }
    key_names = {"openalex": "OPENALEX_API_KEY", "semanticscholar": "SEMANTIC_SCHOLAR_API_KEY"}
    report = refresh_signals(
        PaperDatabase.load(args.data).papers,
        args.provider,
        args.cache or ROOT_DIR / "data/signals" / filenames[args.provider],
        max_requests=args.max_requests,
        max_seconds=args.max_seconds,
        limit=args.limit,
        cache_only=args.cache_only,
        require_key=args.require_key,
        api_key=os.environ.get(key_names.get(args.provider, "")),
    )
    if args.summary_file:
        with args.summary_file.open("a", encoding="utf-8") as summary:
            summary.write(
                f"- {args.provider}: {report['status']}; "
                f"requests={report['requests']}; attempted={report.get('attempted', 0)}; "
                f"remaining_due={report.get('remaining_due', 'unknown')}; "
                f"reason={report.get('reason', 'none')}.\n"
            )
    print(json.dumps(report, indent=2))
    return 0


def cmd_refresh_semanticscholar(args: argparse.Namespace) -> int:
    load_local_environment(ROOT_DIR)
    db = PaperDatabase.load(args.data)
    papers = [paper for paper in db.papers if not args.paper_id or paper.id == args.paper_id]
    if args.paper_id and not papers:
        raise ValueError("Requested paper is not in the active corpus")
    with SemanticScholarClient(
        api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"),
        max_requests=args.max_requests,
        max_seconds=args.max_seconds,
    ) as client:
        report = refresh_semanticscholar(
            papers, args.cache, client, limit=args.limit, cache_only=args.cache_only
        )
    print(json.dumps(report, indent=2))
    return 0


def cmd_trending(args: argparse.Namespace) -> int:
    db = PaperDatabase.load(args.data)
    cache = OpenAlexCache.load(args.cache)
    hf = SignalStore.load(args.hf_cache, "huggingface")
    report = rank_trending(
        db.papers, cache, hf, now=datetime.now(UTC), config=RankingConfig.load(args.ranking_config)
    )
    if args.output:
        _atomic_write(args.output, _encode(report))
    summary = {}
    for paper in report["papers"]:
        summary[paper["coverage"]] = summary.get(paper["coverage"], 0) + 1
    print(
        json.dumps(
            {
                "coverage": summary,
                "version": report["config"]["version"],
                "output": str(args.output) if args.output else None,
            },
            indent=2,
        )
    )
    return 0


def cmd_momentum(args: argparse.Namespace) -> int:
    db = PaperDatabase.load(args.data)
    now = datetime.now(UTC)
    if args.provider == "openalex":
        cache = OpenAlexCache.load(args.cache or ROOT_DIR / "data/signals/openalex-cache.json")
        samples = cache.history
        observations = cache.signals.observations
    else:
        path = args.cache or ROOT_DIR / "data/signals/semanticscholar.json"
        observations = SignalStore.load(path, "semanticscholar").observations
        samples = SemanticScholarHistory.load(history_path(path)).samples
    records = [
        citation_velocity(
            samples,
            paper.id,
            now=now,
            ttl=refresh_ttl(paper, cache, now)
            if args.provider == "openalex"
            else timedelta(days=7),
            provider=args.provider,
            provider_id=(
                observations[paper.id].provider_id
                if paper.id in observations
                else paper.openalex_id
                if args.provider == "openalex"
                else None
            ),
        )
        for paper in db.papers
    ]
    statuses = {}
    for record in records:
        statuses[record.status] = statuses.get(record.status, 0) + 1
    report = {
        "provider": args.provider,
        "generated_at": now.isoformat(),
        "summary": statuses,
        "papers": [record.model_dump(mode="json") for record in records],
    }
    if args.output:
        _atomic_write(args.output, _encode(report))
    print(
        json.dumps(
            {
                "provider": args.provider,
                "summary": statuses,
                "output": str(args.output) if args.output else None,
            },
            indent=2,
        )
    )
    return 0


def cmd_refresh_openalex(args: argparse.Namespace) -> int:
    load_local_environment(ROOT_DIR)
    db = PaperDatabase.load(args.data)
    papers = db.papers
    if args.paper_id:
        papers = [paper for paper in papers if paper.id == args.paper_id]
        if not papers:
            raise ValueError("Requested paper is not in the active corpus")
    with OpenAlexClient(
        api_key=os.environ.get("OPENALEX_API_KEY"),
        max_requests=args.max_requests,
        max_seconds=args.max_seconds,
    ) as client:
        report = refresh_openalex(
            papers, args.cache, client, cache_only=args.cache_only, limit=args.limit
        )
    print(json.dumps(report, indent=2))
    return 0


def cmd_daily(args: argparse.Namespace) -> int:
    session = DailySession(
        args.state_dir,
        args.data,
        args.taxonomy,
        RelevancePolicy.load(args.overrides),
        ArxivExtractor(),
    )
    report = session.run(
        query=args.query,
        since=args.since,
        until=args.until,
        page_size=args.page_size,
        max_requests=args.max_requests,
        max_seconds=args.max_seconds,
        overlap_days=args.overlap_days,
        dry_run=args.dry_run,
        restart=args.restart,
    )
    print(json.dumps(report, indent=2))
    return 0


def cmd_backfill(args: argparse.Namespace) -> int:
    policy = RelevancePolicy.load(args.overrides)
    request = HistoricalRequest(
        query=args.query,
        comparator_query=args.comparator_query,
        policy_digest=policy.digest,
        since=args.since,
        until=args.until,
        page_size=args.page_size,
        max_slice_results=args.max_slice_results,
    )
    directory = args.run_dir or ROOT_DIR / "data" / "ingestion" / "runs" / request.digest[:16]
    session = BackfillSession(
        request, directory, ArxivExtractor(), policy, args.data, args.taxonomy
    )
    report = session.run(max_requests=args.max_requests, resume=args.resume, dry_run=args.dry_run)
    print(json.dumps(report, indent=2))
    return 0


def cmd_discover_cvf(args: argparse.Namespace) -> int:
    from src.venue_capture import capture_cvf

    if args.listing.stat().st_size > 20_000_000:
        raise ValueError("CVF listing input exceeds 20 MB")
    cache = args.cache or ROOT_DIR / "data/venues" / f"{args.venue.lower()}{args.year}-{args.track}"
    report = capture_cvf(
        args.listing.read_bytes(),
        cache,
        venue=args.venue,
        year=args.year,
        track=args.track,
        policy=RelevancePolicy.load(args.overrides),
        max_requests=args.max_requests,
        max_seconds=args.max_seconds,
        all_metadata=args.all_metadata,
    )
    if args.report:
        _atomic_write(args.report, _encode(report))
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))
    return 0


def cmd_hf_discover(args: argparse.Namespace) -> int:
    from src.extractors.huggingface import candidate_record
    from src.extractors.huggingface_client import HFPapersClient
    from src.huggingface_session import discover_scheduled

    now = datetime.now(UTC)
    with HFPapersClient(max_requests=args.max_requests, max_seconds=args.max_seconds) as client:
        entries, report = discover_scheduled(
            client,
            args.cache,
            until=now.date(),
            lookback=args.lookback,
            limit=args.max_results,
            now=now,
        )
    policy = RelevancePolicy.load(ROOT_DIR / "config/overrides.yaml")
    dispositions = []
    for entry in entries:
        try:
            decision = policy.decide(candidate_record(entry))
            dispositions.append(
                {"id": entry.paper.id, "outcome": decision.outcome, "reason": decision.reason}
            )
        except ValueError:
            dispositions.append(
                {
                    "id": entry.paper.id,
                    "outcome": "review",
                    "reason": "Source publication date requires verification",
                }
            )
    report.update(dispositions=dispositions, policy_digest=policy.digest)
    _atomic_write(args.cache / "latest-report.json", _encode(report))
    if args.preview_report:
        if entries:
            _, _, proposal = prepare_hf_preview(args)
            proposal["proposal_available"] = True
        else:
            proposal = {
                "proposal_available": False,
                "reason": "no_candidates",
                "corpus_modified": False,
            }
        _atomic_write(args.preview_report, _encode(proposal))
    if args.summary_file:
        with args.summary_file.open("a", encoding="utf-8") as summary:
            summary.write(
                f"- HF discovery: {report['phase']}; inventory_complete={report['complete']}; "
                f"requests={report['requests']}; candidates={report['unique_candidates']}; "
                f"window={report['since']}..{report['until']}; failure={report['failure']}; corpus unchanged.\n"
            )
    print(json.dumps(report, indent=2))
    return 0


def prepare_hf_preview(args: argparse.Namespace):
    from src.extractors.huggingface import candidate_record
    from src.extractors.huggingface_contracts import parse_daily
    from src.ingestion import prepare_ingestion

    entries = {}
    observed_times = {}
    discovery = json.loads((args.cache / "latest-report.json").read_bytes())
    limit = discovery["discovery_limit"]
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Invalid HF discovery report limit")
    source_days = []
    for day in discovery["days"]:
        if day["status"] not in ("fetched", "possibly_truncated"):
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day["day"]):
            raise ValueError("Invalid HF discovery day")
        source_day = datetime.fromisoformat(day["day"]).date().isoformat()
        source_days.append(source_day)
        if "response_sha256" in day:
            from src.huggingface_session import frozen_response

            payload = frozen_response(args.cache, source_day, day["response_sha256"], limit)
        else:
            path = args.cache / f"{source_day}-{limit}.json"
            payload = json.loads(path.read_bytes())
        if payload["day"] != source_day or payload["limit"] != limit:
            raise ValueError("HF discovery pointer contract mismatch")
        if payload.get("contract_version") != 2:
            raise ValueError("Refresh outdated HF discovery contract before preview")
        observed_at = datetime.fromisoformat(payload["fetched_at"])
        if observed_at.utcoffset() is None or observed_at > datetime.now(UTC):
            raise ValueError("Invalid HF discovery observation time")
        for entry in parse_daily(payload["entries"]):
            if entry.paper.id not in entries:
                entries[entry.paper.id] = entry
                observed_times[entry.paper.id] = observed_at
    if not entries:
        raise ValueError("No cached HF discovery candidates")
    records = []
    unresolved = []
    for entry in entries.values():
        try:
            records.append(candidate_record(entry, observed_at=observed_times[entry.paper.id]))
        except ValueError:
            unresolved.append(
                {
                    "source_id": entry.paper.id,
                    "outcome": "review",
                    "reason": "Publication date or metadata requires verification",
                }
            )
    db = PaperDatabase.load(args.data)
    candidate, report = prepare_ingestion(
        db,
        records,
        RelevancePolicy.load(ROOT_DIR / "config/overrides.yaml"),
        MultiProviderEnricher(args.taxonomy),
    )
    report.update(
        provider="huggingface", unresolved_source_candidates=unresolved, corpus_modified=False
    )
    report["source_days"] = source_days
    report["discovery_complete"] = discovery["complete"]
    report["source_candidates_sha256"] = hashlib.sha256(
        _encode(
            [
                {
                    "entry": entries[key].model_dump(mode="json"),
                    "observed_at": observed_times[key].isoformat(),
                }
                for key in sorted(entries)
            ]
        )
    ).hexdigest()
    report["result_last_updated"] = candidate.last_updated
    return db, candidate, report


def cmd_hf_preview(args: argparse.Namespace) -> int:
    _, _, report = prepare_hf_preview(args)
    _atomic_write(args.report, _encode(report))
    print(
        json.dumps(
            {
                "outcomes": report["outcomes"],
                "operations": report["operations"],
                "unresolved": len(report["unresolved_source_candidates"]),
                "corpus_modified": False,
            }
        )
    )
    return 0


def cmd_hf_apply(args: argparse.Namespace) -> int:
    from src.huggingface_import import apply_proposal

    db, candidate, report = prepare_hf_preview(args)
    approved = json.loads(args.approved_report.read_bytes())
    prepared, changed = apply_proposal(db, candidate, report, approved)
    if changed and not args.dry_run:
        prepared.save(args.data)
    print(
        json.dumps(
            {"changed": changed, "dry_run": args.dry_run, "written": changed and not args.dry_run}
        )
    )
    return 0


def cmd_hf_refresh(args: argparse.Namespace) -> int:
    from src.extractors.huggingface_client import HFPapersClient
    from src.huggingface_cache import refresh_huggingface

    db = PaperDatabase.load(args.data)
    with HFPapersClient(max_requests=args.max_requests) as client:
        report = refresh_huggingface(
            db.papers, args.cache, client, limit=args.limit, cache_only=args.cache_only
        )
    print(json.dumps(report, indent=2))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Fetch recent papers from active extractors, enrich, and upsert into data/papers.json."""
    db = PaperDatabase.load(args.data)
    enricher = MultiProviderEnricher(args.taxonomy)

    arxiv = ArxivExtractor()
    fetched = arxiv.fetch_recent(max_results=args.max_results)

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


def cmd_citations(args: argparse.Namespace) -> int:
    """Enrich papers with global citation counts from OpenAlex and build internal knowledge graph."""
    db = PaperDatabase.load(args.data)
    stats = enrich_database_citations(
        db,
        batch_size=args.batch_size,
        max_papers=args.limit,
        cache_only=args.cache_only,
        max_requests=args.max_requests,
        max_seconds=args.max_seconds,
    )
    db.save(args.data)
    if args.build:
        build_artifacts(
            data_path=args.data,
            taxonomy_path=args.taxonomy,
            readme_path=args.readme,
            docs_data_path=args.docs_data,
        )
    print(
        f"[citations] Enriched {stats.get('enriched_papers', 0)} papers | "
        f"Knowledge graph: {stats.get('total_edges', 0)} internal citation edges across "
        f"{stats.get('connected_papers', 0)} papers"
    )
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    """Compute and update internal knowledge graph cross-references without network calls."""
    db = PaperDatabase.load(args.data)
    stats = build_citation_knowledge_graph(db)
    db.save(args.data)
    if args.build:
        build_artifacts(
            data_path=args.data,
            taxonomy_path=args.taxonomy,
            readme_path=args.readme,
            docs_data_path=args.docs_data,
        )
    print(
        f"[graph] Built internal knowledge graph: {stats.get('total_edges', 0)} edges "
        f"across {stats.get('connected_papers', 0)}/{stats.get('total_nodes', 0)} papers"
    )
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    if not args.data.is_file():
        raise FileNotFoundError(args.data)
    if args.data.resolve() != args.manifest.resolve():
        with exclusive_file(str(args.data) + ".writer.lock"):
            return _migrate_snapshot(args)
    return _migrate_snapshot(args)


def _migrate_snapshot(args: argparse.Namespace) -> int:
    """Preview or write a lossless snapshot without switching legacy writers."""
    if not args.data.is_file():
        raise FileNotFoundError(args.data)
    db = PaperDatabase.load(args.data)
    raw = json.loads(args.data.read_bytes())
    if "papers" in raw:
        projected = {paper.id: paper.model_dump(mode="json") for paper in db.papers}
        for record in raw["papers"]:
            for field, value in record.items():
                if projected[record["id"]].get(field) != value:
                    raise ValueError(
                        f"Legacy normalization changes {record['id']} field {field}; review required"
                    )
    same_path = args.data.resolve() == args.manifest.resolve()
    if same_path and raw.get("schema_version") == "1.0.0":
        raise ValueError("Legacy input must remain recoverable; select a separate manifest target")
    existing_manifest = None
    if args.manifest.exists() and not same_path:
        current = load_store(args.manifest)
        if current.model_dump() != db.model_dump():
            raise ValueError(
                "Existing v2 target differs from source; migration refuses to replace it"
            )
        # Preserve newer successful provider observations on a harmless rerun.
        existing_manifest = json.loads(args.manifest.read_bytes())
    if existing_manifest is not None:
        manifest = existing_manifest
    elif args.dry_run:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = write_store(db, Path(temporary) / "manifest.json")
    else:
        manifest = write_store(db, args.manifest)
    report = {
        "dry_run": args.dry_run,
        "records": db.total_count,
        "shards": len(manifest["shards"]),
        "content_sha256": manifest["content_sha256"],
        "source_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "ids": [paper.id for paper in db.papers],
        "internal_edges": sum(len(paper.db_references) for paper in db.papers),
        "legacy_zero_citations": sum(paper.citation_count == 0 for paper in db.papers),
        "date_precision_counts": {
            precision: sum(paper.published_date_precision == precision for paper in db.papers)
            for precision in ("day", "month", "year", "unknown")
        },
        "archived_records": len(db.archive),
        "legacy_preprint_doi_in_doi_field": sum(
            (normalize_doi(paper.doi) or "").startswith("10.48550/arxiv.") for paper in db.papers
        ),
        "parity": "exact",
        "legacy_signal_freshness": "unknown",
        "legacy_writers_switched": False,
    }
    if args.report:
        _atomic_write(args.report, _encode(report))
    print(json.dumps({key: value for key, value in report.items() if key != "ids"}, indent=2))
    return 0


def cmd_curate(args: argparse.Namespace) -> int:
    """Preview or apply explicit reviewed archival dispositions atomically."""
    db = PaperDatabase.load(args.data)
    review = ArchiveReview.model_validate_json(args.review_file.read_bytes())
    candidate, report = prepare_archive_review(db, review)
    if not args.dry_run:
        candidate.save(args.data)
    print(json.dumps({"dry_run": args.dry_run, **report}, indent=2))
    return 0


def cmd_evaluate_relevance(args: argparse.Namespace) -> int:
    report = evaluate_relevance(
        args.packet.read_bytes(),
        args.annotations.read_bytes(),
        RelevancePolicy.load(args.overrides),
        source_directory=args.sources,
    )
    payload = _encode(report)
    if args.report is not None:
        if not args.report.exists() or args.report.read_bytes() != payload:
            _atomic_write(args.report, payload)
    print(json.dumps(report, indent=2))
    return 0


def cmd_audit_relevance(args: argparse.Namespace) -> int:
    db = PaperDatabase.load(args.data)
    policy = RelevancePolicy.load(args.overrides)
    baseline_ids = None
    baseline_hash = None
    if args.baseline_revision:
        if not re.fullmatch(r"[a-fA-F0-9]{7,40}", args.baseline_revision):
            raise ValueError("Baseline revision must be a Git commit SHA")
        payload = subprocess.check_output(
            ["git", "-C", str(ROOT_DIR), "show", f"{args.baseline_revision}:data/papers.json"]
        )
        baseline_ids = [record["id"] for record in json.loads(payload)["papers"]]
        baseline_hash = hashlib.sha256(payload).hexdigest()
    report = audit_relevance(db, policy, baseline_ids)
    report["baseline_revision"] = args.baseline_revision
    report["baseline_source_sha256"] = baseline_hash
    _atomic_write(args.output, _encode(report))
    print(
        json.dumps(
            {
                "output": str(args.output),
                "summary": report["summary"],
                "baseline_records": len(report["baseline_dispositions"]),
                "corpus_modified": False,
            },
            indent=2,
        )
    )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate that data/papers.json conforms strictly to the Pydantic v2 OBT schema."""
    if args.manifest:
        db = load_store(args.manifest)
    else:
        if not args.data.is_file():
            raise FileNotFoundError(args.data)
        db = PaperDatabase.load(args.data)
    if len({p.id for p in db.papers}) != len(db.papers):
        print("[validate] Error: duplicate canonical IDs")
        return 1
    if db.total_count != len(db.papers):
        print(f"[validate] Error: total_count ({db.total_count}) != len(papers) ({len(db.papers)})")
        return 1
    print(f"[validate] OK â€” {len(db.papers)} valid PaperRecords in {args.manifest or args.data}")
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

    p_signals = sub.add_parser(
        "refresh-signals", help="Resume a bounded due-provider queue with explicit health"
    )
    p_signals.add_argument(
        "--provider", choices=["openalex", "semanticscholar", "huggingface"], required=True
    )
    p_signals.add_argument("--due", action="store_true", required=True)
    p_signals.add_argument("--cache", type=Path)
    p_signals.add_argument("--summary-file", type=Path)
    p_signals.add_argument("--cache-only", action="store_true")
    p_signals.add_argument("--require-key", action="store_true")
    p_signals.add_argument("--limit", type=int, default=100)
    p_signals.add_argument("--max-requests", type=int, default=10)
    p_signals.add_argument("--max-seconds", type=float, default=120)
    p_signals.set_defaults(func=cmd_refresh_signals)

    p_s2 = sub.add_parser(
        "refresh-semanticscholar", help="Refresh separate Semantic Scholar observations"
    )
    p_s2.add_argument("--cache", type=Path, default=ROOT_DIR / "data/signals/semanticscholar.json")
    p_s2.add_argument("--paper-id")
    p_s2.add_argument("--cache-only", action="store_true")
    p_s2.add_argument("--limit", type=int, default=100)
    p_s2.add_argument("--max-requests", type=int, default=100)
    p_s2.add_argument("--max-seconds", type=float, default=300)
    p_s2.set_defaults(func=cmd_refresh_semanticscholar)

    p_trending = sub.add_parser(
        "trending", help="Report transparent discovery scores and signal coverage"
    )
    p_trending.add_argument(
        "--cache", type=Path, default=ROOT_DIR / "data/signals/openalex-cache.json"
    )
    p_trending.add_argument(
        "--hf-cache", type=Path, default=ROOT_DIR / "data/signals/huggingface.json"
    )
    p_trending.add_argument("--ranking-config", type=Path, default=ROOT_DIR / "config/ranking.yaml")
    p_trending.add_argument("--output", type=Path)
    p_trending.set_defaults(func=cmd_trending)

    p_momentum = sub.add_parser(
        "momentum", help="Report measured provider velocity and explicit unavailability"
    )
    p_momentum.add_argument(
        "--provider", choices=["openalex", "semanticscholar"], default="openalex"
    )
    p_momentum.add_argument(
        "--cache", type=Path, help="Selected provider cache; history uses its sidecar for S2"
    )
    p_momentum.add_argument("--output", type=Path)
    p_momentum.set_defaults(func=cmd_momentum)

    p_oa = sub.add_parser(
        "refresh-openalex", help="Refresh typed provider cache without changing canonical metadata"
    )
    p_oa.add_argument(
        "--cache", type=Path, default=ROOT_DIR / "data" / "signals" / "openalex-cache.json"
    )
    p_oa.add_argument("--cache-only", action="store_true")
    p_oa.add_argument("--paper-id")
    p_oa.add_argument("--limit", type=int, default=100)
    p_oa.add_argument("--max-requests", type=int, default=100)
    p_oa.add_argument("--max-seconds", type=float, default=300)
    p_oa.set_defaults(func=cmd_refresh_openalex)

    p_cvf = sub.add_parser(
        "discover-cvf",
        help="Resume bounded official publication metadata capture from a frozen CVF listing",
    )
    p_cvf.add_argument("--listing", type=Path, required=True)
    p_cvf.add_argument("--venue", choices=["CVPR", "ICCV"], required=True)
    p_cvf.add_argument("--year", type=int, required=True)
    p_cvf.add_argument("--track", choices=["main", "workshop"], default="main")
    p_cvf.add_argument("--cache", type=Path)
    p_cvf.add_argument("--overrides", type=Path, default=ROOT_DIR / "config/overrides.yaml")
    p_cvf.add_argument("--max-requests", type=int, default=10)
    p_cvf.add_argument("--max-seconds", type=float, default=120)
    p_cvf.add_argument(
        "--all-metadata",
        action="store_true",
        help="Capture every listed publication for abstract review in a separately frozen epoch",
    )
    p_cvf.add_argument("--report", type=Path)
    p_cvf.set_defaults(func=cmd_discover_cvf)

    p_hf = sub.add_parser(
        "discover-huggingface",
        help="Cache bounded HF candidates and topic dispositions without canonical import",
    )
    p_hf.add_argument("--cache", type=Path, default=ROOT_DIR / "data/ingestion/huggingface")
    p_hf.add_argument("--max-results", type=int, default=100)
    p_hf.add_argument("--lookback", type=int, default=7)
    p_hf.add_argument("--max-requests", type=int, default=10)
    p_hf.add_argument("--max-seconds", type=float, default=120)
    p_hf.add_argument(
        "--preview-report", type=Path, help="Write a snapshot-bound proposal; never applies it"
    )
    p_hf.add_argument("--summary-file", type=Path)
    p_hf.set_defaults(func=cmd_hf_discover)
    p_hfp = sub.add_parser(
        "preview-huggingface-import",
        help="Prepare identity/relevance import dispositions without canonical writes",
    )
    p_hfp.add_argument("--cache", type=Path, required=True)
    p_hfp.add_argument("--report", type=Path, required=True)
    p_hfp.set_defaults(func=cmd_hf_preview)
    p_hfa = sub.add_parser(
        "apply-huggingface-import",
        help="Apply an exact reviewed HF preview with stale-input protection",
    )
    p_hfa.add_argument("--cache", type=Path, required=True)
    p_hfa.add_argument("--approved-report", type=Path, required=True)
    p_hfa.add_argument("--dry-run", action="store_true")
    p_hfa.set_defaults(func=cmd_hf_apply)
    p_hfr = sub.add_parser("refresh-huggingface", help="Refresh separate HF observations")
    p_hfr.add_argument("--cache", type=Path, default=ROOT_DIR / "data/signals/huggingface.json")
    p_hfr.add_argument("--max-requests", type=int, default=20)
    p_hfr.add_argument("--limit", type=int, default=50)
    p_hfr.add_argument("--cache-only", action="store_true")
    p_hfr.set_defaults(func=cmd_hf_refresh)

    p_eval = sub.add_parser(
        "evaluate-relevance", help="Evaluate exact source-captured, reviewed relevance candidates"
    )
    p_eval.add_argument(
        "--packet", type=Path, default=ROOT_DIR / "tests/fixtures/relevance/candidates.json"
    )
    p_eval.add_argument(
        "--annotations", type=Path, default=ROOT_DIR / "tests/fixtures/relevance/annotations.json"
    )
    p_eval.add_argument(
        "--sources", type=Path, default=ROOT_DIR / "tests/fixtures/relevance/sources"
    )
    p_eval.add_argument("--overrides", type=Path, default=ROOT_DIR / "config/overrides.yaml")
    p_eval.add_argument("--report", type=Path)
    p_eval.set_defaults(func=cmd_evaluate_relevance)

    p_daily = sub.add_parser(
        "daily", help="Resume complete arXiv updated-window scans with a durable watermark"
    )
    p_daily.add_argument("--state-dir", type=Path, default=ROOT_DIR / "data/ingestion/daily")
    p_daily.add_argument("--overrides", type=Path, default=ROOT_DIR / "config/overrides.yaml")
    p_daily.add_argument("--query", default=DEFAULT_SEARCH_QUERY)
    p_daily.add_argument(
        "--since",
        type=utc_bound,
        help="Required first-run coverage boundary; never inferred from corpus timestamps",
    )
    p_daily.add_argument(
        "--until", type=utc_bound, help="Exclusive UTC cutoff frozen on first dispatch"
    )
    p_daily.add_argument("--page-size", type=int, default=100)
    p_daily.add_argument("--max-requests", type=int, default=20)
    p_daily.add_argument("--max-seconds", type=float, default=300)
    p_daily.add_argument("--overlap-days", type=int, default=7)
    p_daily.add_argument("--dry-run", action="store_true")
    p_daily.add_argument(
        "--restart",
        action="store_true",
        help="Archive an unstable scan and retry without advancing coverage",
    )
    p_daily.set_defaults(func=cmd_daily)

    p_ingest = sub.add_parser("ingest", help="Fetch & enrich delta papers from arXiv")
    p_ingest.add_argument("--max-results", type=int, default=50)
    p_ingest.add_argument(
        "--no-llm", action="store_true", help="Disable LLM calls and use deterministic rules only"
    )
    p_ingest.set_defaults(func=cmd_ingest)

    p_backfill = sub.add_parser(
        "backfill", help="Resume frozen-query historical arXiv discovery and deterministic import"
    )
    p_backfill.add_argument(
        "--until",
        type=utc_bound,
        required=True,
        help="Exclusive cutoff; YYYY-MM-DD means start of that UTC day",
    )
    p_backfill.add_argument(
        "--since",
        type=utc_bound,
        help="Explicit lower bound; otherwise discover the earliest matching month",
    )
    p_backfill.add_argument("--query", default=DEFAULT_SEARCH_QUERY)
    p_backfill.add_argument(
        "--comparator-query",
        default='all:"Gaussian Splatting" OR all:"3DGS" OR all:"4DGS" OR all:"2DGS"',
    )
    p_backfill.add_argument(
        "--overrides", type=Path, default=ROOT_DIR / "config" / "overrides.yaml"
    )
    p_backfill.add_argument("--run-dir", type=Path)
    p_backfill.add_argument("--page-size", type=int, default=100)
    p_backfill.add_argument("--max-slice-results", type=int, default=1000)
    p_backfill.add_argument("--max-requests", type=int, default=100)
    p_backfill.add_argument("--resume", action="store_true")
    p_backfill.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch/cache and prepare dispositions without writing canonical data",
    )
    p_backfill.set_defaults(func=cmd_backfill)

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
    p_val.add_argument(
        "--manifest", type=Path, help="Validate a v2 snapshot instead of legacy data"
    )
    p_val.set_defaults(func=cmd_validate)

    p_migrate = sub.add_parser("migrate", help="Preview or write a lossless v2 snapshot")
    p_migrate.add_argument("--dry-run", action="store_true")
    p_migrate.add_argument(
        "--report", type=Path, help="Save the source inventory and exact parity evidence"
    )
    p_migrate.add_argument("--manifest", type=Path, default=ROOT_DIR / "data" / "manifest.json")
    p_migrate.set_defaults(func=cmd_migrate)

    p_audit = sub.add_parser(
        "audit-relevance", help="Prepare auditable topic and seed-disposition proposals"
    )
    p_audit.add_argument("--overrides", type=Path, default=ROOT_DIR / "config" / "overrides.yaml")
    p_audit.add_argument(
        "--output", type=Path, default=ROOT_DIR / "reports" / "relevance-review.json"
    )
    p_audit.add_argument(
        "--baseline-revision", help="Local Git SHA whose seed IDs must all be accounted for"
    )
    p_audit.set_defaults(func=cmd_audit_relevance)

    p_curate = sub.add_parser(
        "curate", help="Preview/apply reviewed, snapshot-bound archival decisions"
    )
    p_curate.add_argument("--review-file", type=Path, required=True)
    p_curate.add_argument("--dry-run", action="store_true")
    p_curate.set_defaults(func=cmd_curate)

    p_cit = sub.add_parser("citations", help="Enrich citation metrics and build knowledge graph")
    p_cit.add_argument("--batch-size", type=int, default=40)
    p_cit.add_argument("--limit", type=int, default=None)
    p_cit.add_argument("--cache-only", action="store_true")
    p_cit.add_argument("--max-requests", type=int, default=100)
    p_cit.add_argument("--max-seconds", type=float, default=300)
    p_cit.add_argument("--build", action="store_true", help="Automatically rebuild README and docs")
    p_cit.set_defaults(func=cmd_citations)

    p_grp = sub.add_parser("graph", help="Compute internal knowledge graph cross-references")
    p_grp.add_argument("--build", action="store_true", help="Automatically rebuild README and docs")
    p_grp.set_defaults(func=cmd_graph)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
