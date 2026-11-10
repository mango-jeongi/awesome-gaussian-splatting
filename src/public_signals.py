"""Small source-labelled count projections; never publish provider response caches."""

from pathlib import Path

from src.observations import SignalStore
from src.openalex_cache import OpenAlexCache


def public_signals(db, source: Path):
    stores = {
        "openalex": OpenAlexCache.load(source / "openalex-cache.json").signals
        if (source / "openalex-cache.json").exists()
        else db._signal_stores.get("openalex", SignalStore(provider="openalex")),
        "semanticscholar": SignalStore.load(source / "semanticscholar.json", "semanticscholar")
        if (source / "semanticscholar.json").exists()
        else db._signal_stores.get("semanticscholar", SignalStore(provider="semanticscholar")),
    }
    rows = {}
    for paper in db.papers:
        rows[paper.id] = {}
        for provider, store in stores.items():
            observation = store.observations.get(paper.id)
            usable = (
                observation
                and observation.fetched_at
                and observation.status not in ("unknown", "ambiguous", "not_found")
            )
            rows[paper.id][provider] = {
                "status": observation.status if observation else "unknown",
                "citation_count": observation.values.get("citation_count") if usable else None,
                "influential_citation_count": observation.values.get("influential_citation_count")
                if usable and provider == "semanticscholar"
                else None,
                "fetched_at": observation.fetched_at.isoformat()
                if observation and observation.fetched_at
                else None,
            }
    return {"schema_version": "1.0.0", "default_provider": "openalex", "papers": rows}
