"""Deterministic source-separated discovery snapshots from recorded inputs."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.observations import SignalStore
from src.openalex_cache import OpenAlexCache, refresh_ttl
from src.ranking import RankingConfig, rank_trending
from src.semanticscholar_history import SemanticScholarHistory, history_path


def public_trending(db, source: Path, config: RankingConfig):
    oa = OpenAlexCache.load(source / "openalex-cache.json")
    if not (source / "openalex-cache.json").exists():
        oa.signals = db._signal_stores.get("openalex", oa.signals)
    s2 = SignalStore.load(source / "semanticscholar.json", "semanticscholar")
    if not (source / "semanticscholar.json").exists():
        s2 = db._signal_stores.get("semanticscholar", s2)
    hf = SignalStore.load(source / "huggingface.json", "huggingface")
    history = SemanticScholarHistory.load(history_path(source / "semanticscholar.json"))
    stamps = [datetime.fromisoformat(db.last_updated)]
    for store in (oa.signals, s2, hf):
        stamps.extend(o.last_attempt_at for o in store.observations.values() if o.last_attempt_at)
    stamps.extend(s.observed_at for s in oa.history)
    stamps.extend(s.observed_at for s in history.samples)
    if any(stamp.utcoffset() is None for stamp in stamps):
        raise ValueError("Public ranking requires aware input timestamps")
    as_of = max(stamps).astimezone(UTC)
    velocity_fields = [
        "provider_id",
        "status",
        "current_at",
        "baseline_at",
        "elapsed_days",
        "raw_delta",
        "raw_velocity",
        "provider_correction",
    ]
    providers = {}
    expiries = [as_of + timedelta(days=1)]
    paper_by_id = {paper.id: paper for paper in db.papers}
    for provider in ("openalex", "semanticscholar"):
        report = rank_trending(
            db.papers,
            oa,
            hf,
            now=as_of,
            config=config,
            provider=provider,
            citation_store=s2,
            citation_history=history.samples,
        )
        for row in report["papers"]:
            if row["score"] is None:
                continue
            expiries.append(
                datetime.fromisoformat(row["original_date"]).replace(tzinfo=UTC)
                + timedelta(days=config.max_age_days + 1)
            )
            if "upvotes" in row["weights_used"]:
                expiries.append(
                    datetime.fromisoformat(row["upvotes_observed_at"])
                    + timedelta(days=config.hf_ttl_days)
                )
            if "velocity" in row["weights_used"]:
                ttl = (
                    refresh_ttl(paper_by_id[row["paper_id"]], oa, as_of)
                    if provider == "openalex"
                    else timedelta(days=7)
                )
                expiries.append(datetime.fromisoformat(row["velocity"]["current_at"]) + ttl)
        projected = {}
        for row in report["papers"]:
            value = {
                key: item for key, item in row.items() if key not in ("paper_id", "original_date")
            }
            if row["velocity"] is not None:
                value["velocity"] = [row["velocity"][field] for field in velocity_fields]
            projected[row["paper_id"]] = value
        providers[provider] = {"papers": projected}
    return {
        "schema_version": "1.0.0",
        "velocity_fields": velocity_fields,
        "as_of": as_of.isoformat(),
        "valid_until": min(expiries).isoformat(),
        "config": config.model_dump(mode="json"),
        "interpretation": "Discovery ranking, not scientific quality",
        "providers": providers,
    }
