"""Read-only, input-fenced coverage of current corpus and configured source evidence."""

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from src.backfill import HistoricalCrawler, HistoricalState, submitted_query
from src.extractors.citations import apply_cached_citations
from src.graph import graph_projection
from src.huggingface_cache import hf_ttl
from src.momentum import citation_velocity
from src.observations import SignalStore
from src.openalex_cache import OpenAlexCache, refresh_ttl
from src.public import compact
from src.releases import safe_name, sha
from src.schema import PaperDatabase
from src.semanticscholar_history import SemanticScholarHistory, history_path
from src.storage import _encode
from src.workers.coverage import ExtractionCoverage
from src.workers.review import ReviewedExtractionStore


class SnapshotInputs:
    """Keep exact consumed bytes and fence additions, removals and changed inputs."""

    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.payloads = {}
        self.missing = set()
        self.bytes_read = 0

    def target(self, name):
        path = self.root / safe_name(name)
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("Coverage input escapes repository")
        for part in [path, *path.parents]:
            if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
                raise ValueError("Coverage inputs cannot contain links")
            if part == self.root:
                break
        return path

    def read(self, name, *, optional=False):
        name = safe_name(name)
        if name in self.payloads:
            return self.payloads[name]
        path = self.target(name)
        if not path.exists() and optional:
            self.missing.add(name)
            return None
        if not path.is_file() or path.stat().st_size > 80_000_000:
            raise ValueError("Coverage input missing, invalid or oversized: " + name)
        with path.open("rb") as stream:
            raw = stream.read(80_000_001)
        self.bytes_read += len(raw)
        if len(raw) > 80_000_000 or self.bytes_read > 300_000_000 or len(self.payloads) >= 10000:
            raise ValueError("Coverage snapshot exceeds input budget")
        self.payloads[name] = raw
        return raw

    def json(self, name, *, optional=False):
        import json

        raw = self.read(name, optional=optional)
        return json.loads(raw) if raw is not None else None

    def component(self, base, item):
        name = (Path(base) / safe_name(item["path"])).as_posix()
        raw = self.read(name)
        if sha(raw) != item["sha256"]:
            raise ValueError("Coverage component checksum mismatch")
        return raw

    def finish(self):
        for name, raw in self.payloads.items():
            path = self.target(name)
            if not path.is_file() or path.stat().st_size != len(raw):
                raise ValueError("Coverage input changed during snapshot: " + name)
            with path.open("rb") as stream:
                if stream.read(len(raw) + 1) != raw:
                    raise ValueError("Coverage input changed during snapshot: " + name)
        if any(self.target(name).exists() for name in self.missing):
            raise ValueError("Coverage optional input appeared during snapshot")
        return {name: sha(raw) for name, raw in sorted(self.payloads.items())}


def _database(inputs, name):
    raw = inputs.read(name)
    import json

    manifest = json.loads(raw)
    if manifest.get("schema_version") == "2.0.0":
        base = Path(name).parent
        for item in [
            *manifest["shards"],
            manifest["aliases"],
            manifest["archive"],
            *manifest["signals"].values(),
        ]:
            inputs.component(base, item)
        # Reuse all shard/order/month/alias/compatibility validation; the final
        # input fence also covers every component consumed by this loader.
        return PaperDatabase.load(inputs.target(name))
    db = PaperDatabase.model_validate_json(raw)
    from src.storage import _inventory

    _inventory(db)
    return db


def _providers(inputs, db, now):
    raw = inputs.read("data/signals/openalex-cache.json", optional=True)
    oa = OpenAlexCache.model_validate_json(raw) if raw is not None else OpenAlexCache()
    if raw is None:
        oa.signals = db._signal_stores.get("openalex", oa.signals)
    stores = {"openalex": oa.signals}
    for name in ("huggingface", "semanticscholar"):
        raw = inputs.read(f"data/signals/{name}.json", optional=True)
        store = (
            SignalStore.model_validate_json(raw) if raw is not None else SignalStore(provider=name)
        )
        if store.provider != name:
            raise ValueError("Coverage signal provider mismatch")
        stores[name] = store
    raw = inputs.read(
        history_path(Path("data/signals/semanticscholar.json")).as_posix(), optional=True
    )
    s2 = (
        SemanticScholarHistory.model_validate_json(raw)
        if raw is not None
        else SemanticScholarHistory()
    )
    ids = {paper.id for paper in db.papers}
    result = {}
    for provider, store in stores.items():
        active = {key: value for key, value in store.observations.items() if key in ids}
        samples = (
            oa.history
            if provider == "openalex"
            else s2.samples
            if provider == "semanticscholar"
            else []
        )
        histories = defaultdict(list)
        for sample in samples:
            histories[sample.paper_id].append(sample)
        fresh = stale = zeros = 0
        velocity = Counter()
        for paper in db.papers:
            observation = active.get(paper.id)
            if observation and any(
                stamp and stamp > now
                for stamp in (observation.fetched_at, observation.last_attempt_at)
            ):
                raise ValueError("Future provider observation cannot support coverage")
            ttl = (
                refresh_ttl(paper, oa, now)
                if provider == "openalex"
                else hf_ttl(observation, now)
                if provider == "huggingface"
                else timedelta(days=7)
            )
            if observation and observation.fetched_at and observation.values:
                stale += int(observation.stale(now, ttl))
                fresh += int(not observation.stale(now, ttl))
                zeros += int(observation.values.get("citation_count") == 0)
            if provider != "huggingface":
                value = citation_velocity(
                    histories[paper.id],
                    paper.id,
                    now=now,
                    ttl=ttl,
                    provider_id=observation.provider_id if observation else None,
                    provider=provider,
                )
                velocity[value.status] += 1
        result[provider] = {
            "active_denominator": len(ids),
            "cached_active_entries": len(active),
            "outside_active_cache_entries": len(store.observations) - len(active),
            "latest_attempt_statuses": dict(
                sorted(Counter(o.status for o in active.values()).items())
            ),
            "fresh_successful_values": fresh,
            "stale_successful_values": stale,
            "unobserved": len(ids) - len(active),
            "verified_observed_zero_citations": zeros,
            "velocity_statuses": dict(sorted(velocity.items())),
        }
    return oa, result


def _seed(inputs, db):
    ledger = inputs.json("data/reviews/seed-reconciliation.json", optional=True)
    if ledger is None:
        return {"status": "unavailable"}
    rows = ledger["rows"]
    if len({row["old_id"] for row in rows}) != len(rows) or ledger["baseline_records"] != len(rows):
        raise ValueError("Coverage seed inventory mismatch")
    counts = dict(Counter(row["disposition"] for row in rows))
    if counts != ledger["summary"] or set(counts) - {
        "retained",
        "archived",
        "merged",
        "unresolved_review",
    }:
        raise ValueError("Coverage seed dispositions disagree with summary")
    papers = {paper.id: paper for paper in db.papers}
    stale = []
    for row in rows:
        if row["disposition"] == "retained":
            paper = papers.get(row["canonical_id"])
            if (
                not row.get("reviewed")
                or paper is None
                or sha(_encode(paper.model_dump(mode="json")))
                != row.get("reviewed_canonical_record_sha256")
            ):
                stale.append(row["old_id"])
    return {
        "status": "recorded_ledger",
        "declared_current_records": ledger.get("current_records"),
        "declared_current_count_matches": ledger.get("current_records") == len(db.papers),
        "total": len(rows),
        "summary": counts,
        "canonical_binding_current": ledger["source_content_sha256"]
        == sha(_encode(db.model_dump(mode="json"))),
        "stale_retained_record_bindings": stale,
        "unresolved": [
            {"old_id": row["old_id"], "title": row["title"]}
            for row in rows
            if row["disposition"] == "unresolved_review"
        ],
        "review_basis": "Stored source-review decisions; not independent reinspection",
    }


def _extraction(inputs, db):
    raw = inputs.read("data/extraction/coverage.json", optional=True)
    ids = {paper.id for paper in db.papers}
    result = {
        "status": "unavailable",
        "active_denominator": len(ids),
        "unobserved_active": len(ids),
    }
    if raw is not None:
        coverage = ExtractionCoverage.model_validate_json(raw)
        observed = ids & coverage.records.keys()
        states = dict(Counter(coverage.records[key]["state"] for key in observed))
        if set(coverage.summary) - {"processed", "queued", "unavailable", "unsupported"}:
            raise ValueError("Unknown extraction coverage state")
        if dict(Counter(row["state"] for row in coverage.records.values())) != coverage.summary:
            raise ValueError("Coverage extraction summary disagrees with records")
        result.update(
            status="recorded_inventory",
            canonical_binding_current=coverage.source_content_sha256
            == sha(_encode(db.model_dump(mode="json"))),
            states=states,
            unobserved_active=len(ids - observed),
            outside_active_records=len(coverage.records.keys() - ids),
        )
    raw = inputs.read("data/extraction/reviewed.json", optional=True)
    reviewed = (
        ReviewedExtractionStore.model_validate_json(raw)
        if raw is not None
        else ReviewedExtractionStore()
    )
    active = [row for row in reviewed.records.values() if row.paper_id in ids]
    accepted = [row for row in active if row.decision.disposition == "accepted"]
    result.update(
        accepted_numeric_cells=sum(row.original.kind == "numeric_cell" for row in accepted),
        papers_with_accepted_numeric_cells=len(
            {row.paper_id for row in accepted if row.original.kind == "numeric_cell"}
        ),
        accepted_figures=sum(row.original.kind == "figure" for row in accepted),
        rejected_candidates=sum(row.decision.disposition == "rejected" for row in active),
        review_basis="Stored review ledger; not independent human benchmark or source reinspection",
        scope="Queued source tasks are not downloaded PDFs or completed parser jobs",
    )
    return result


def _history(inputs, entries, now):
    result = []
    for entry in entries:
        name = safe_name(entry["checkpoint"])
        state = HistoricalState.model_validate_json(inputs.read(name))
        if state.query_digest != state.spec.digest:
            raise ValueError("Historical query digest mismatch")
        crawler = HistoricalCrawler(state.spec, inputs.target(name).parent, source=None)
        crawler.state = state
        crawler._validate_structure()
        ids = set()
        for key, interval in state.slices.items():
            if interval.query != submitted_query(state.spec.query, interval.start, interval.end):
                raise ValueError("Historical slice query mismatch")
            for ref in [*interval.pages, *([interval.probe] if interval.probe else [])]:
                inputs.component(Path(name).parent, ref.model_dump())
            for page in crawler._cached_pages(key):
                if page.fetched_at > now:
                    raise ValueError("Future cached source page cannot support coverage")
                ids.update(
                    record.id
                    for record in page.records
                    if state.spec.since <= page.published_at[record.id] < state.spec.until
                )
        row = {
            "checkpoint": name,
            "spec": state.spec.model_dump(mode="json"),
            "query_digest": state.query_digest,
            "status": state.status,
            "slice_statuses": dict(Counter(s.status for s in state.slices.values())),
            "verified_unique_candidates": len(ids),
            "cached_pages_verified": True,
            "intervals": [
                {
                    "slice_id": key,
                    "start": s.start.isoformat(),
                    "end": s.end.isoformat(),
                    "status": s.status,
                }
                for key, s in sorted(state.slices.items())
            ],
            "scope": "Literal frozen query and cutoff only; not all NeRF literature or continuing updates",
        }
        if entry.get("application_report"):
            application = inputs.json(entry["application_report"])
            dispositions = application["dispositions"]
            if (
                len({r["source_id"] for r in dispositions}) != len(dispositions)
                or {r["source_id"] for r in dispositions} != ids
                or application["unique_candidates"] != len(ids)
            ):
                raise ValueError(
                    "Historical application does not cover verified candidate inventory"
                )
            outcomes = dict(Counter(r["outcome"] for r in dispositions))
            if outcomes != application["outcomes"]:
                raise ValueError("Historical application outcomes disagree with rows")
            row["application_outcomes"] = outcomes
            row["application_policy_digest"] = application["policy_digest"]
        result.append(row)
    return result


def coverage_snapshot(root, *, data_path=None, now=None):
    now = now or datetime.now(UTC)
    if now.utcoffset() is None:
        raise ValueError("Coverage requires an aware evaluation time")
    inputs = SnapshotInputs(root)
    data = Path(data_path).resolve() if data_path else inputs.root / "data/papers.json"
    name = data.relative_to(inputs.root).as_posix()
    db = _database(inputs, name)
    source_model = sha(_encode(db.model_dump(mode="json")))
    raw = inputs.read("config/sources.yaml", optional=True)
    sources = yaml.safe_load(raw) if raw is not None else {}
    sources = sources or {}
    cells = sources.get("editions", [])
    keys = [(cell["venue"], cell["year"], cell["track"]) for cell in cells]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate venue inventory cells")
    evidence = {}
    for cell in cells:
        for item in cell.get("evidence", []):
            if item.get("evidence_file"):
                name = safe_name(item["evidence_file"])
                body = inputs.json(name)
                evidence[name] = {
                    key: body[key]
                    for key in (
                        "listing_records",
                        "verified_records",
                        "pending_records",
                        "failed_records",
                        "selection_mode",
                        "selected_metadata_complete",
                        "venue_inventory_reconciled",
                        "corpus_modified",
                    )
                    if key in body
                }
    oa, providers = _providers(inputs, db, now)
    projected = db.model_copy(deep=True)
    stats = apply_cached_citations(projected, oa)
    graph = graph_projection(projected)
    manifest = inputs.json("docs/data/manifest.json", optional=True)
    public = {"status": "unavailable"}
    if manifest is not None:
        base = {key: value for key, value in manifest.items() if key != "build_digest"}
        if sha(compact(base)) != manifest["build_digest"]:
            raise ValueError("Invalid public manifest build digest")
        public = {
            "status": "manifest_metadata_only",
            "build_digest": manifest["build_digest"],
            "canonical_projection_matches": manifest["source_sha256"]
            == sha(compact(projected.model_dump(mode="json"))),
            "declared_total_count": manifest["total_count"],
            "declared_total_edges": manifest["total_edges"],
            "artifact_integrity": "Not checked by coverage; use release verification",
        }
    result = {
        "schema_version": 1,
        "observed_at": now.isoformat(),
        "scope": "Read-only repository evidence; zero provider requests; no phase completion claim",
        "canonical": {
            "active": len(db.papers),
            "archived": len(db.archive),
            "with_arxiv_id": sum(bool(p.arxiv_id) for p in db.papers),
            "without_arxiv_id": sum(not p.arxiv_id for p in db.papers),
            "canonical_zeros_without_intrinsic_observation_freshness": sum(
                p.citation_count == 0 for p in db.papers
            ),
            "source_model_sha256": source_model,
        },
        "seed": _seed(inputs, db),
        "providers": providers,
        "venues": {
            "cells": len(cells),
            "statuses": dict(Counter(c["status"] for c in cells)),
            "coverage_statuses": dict(Counter(c["coverage"] for c in cells)),
            "inventory": cells,
            "latest_evidence_summaries": evidence,
            "scope": "Inventory fields are declarations; bound evidence summaries describe latest completed invocations. Process liveness and in-flight progress are not inferred",
        },
        "historical_discovery": _history(inputs, sources.get("historical_runs", []), now),
        "extraction": _extraction(inputs, db),
        "graph": {
            **graph["coverage"],
            "connected_active_records": stats["connected_papers"],
            "isolated_active_records": len(db.papers) - stats["connected_papers"],
            "provenance_statuses": dict(
                Counter(n["provenance_status"] for n in graph["nodes"].values())
            ),
            "scope": "Current owned cache-backed projection; no canonical writes",
        },
        "public": public,
    }
    result["input_sha256"] = inputs.finish()
    result["missing_optional_inputs"] = sorted(inputs.missing)
    return result


def write_coverage_report(root, output, report):
    """Create a new report outside canonical/generated inputs; never overwrite."""
    output = Path(output).resolve()
    root = Path(root).resolve()
    if output.is_relative_to(root) and not output.is_relative_to(root / "reports"):
        raise ValueError("Store coverage reports under reports or outside the repository")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(_encode(report))
