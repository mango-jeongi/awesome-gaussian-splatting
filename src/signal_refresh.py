"""One bounded due-provider pass, preserving adapter caches and retry eligibility."""

from datetime import UTC, datetime
from pathlib import Path

from src.extractors.huggingface_client import HFPapersClient
from src.extractors.openalex import OpenAlexClient
from src.extractors.semanticscholar import SemanticScholarClient, refresh_semanticscholar
from src.huggingface_cache import refresh_huggingface
from src.openalex_cache import refresh_openalex


def refresh_signals(
    papers,
    provider: str,
    cache: Path,
    *,
    max_requests=10,
    max_seconds=120,
    limit=100,
    cache_only=False,
    require_key=False,
    api_key=None,
    now=None,
):
    if provider not in ("openalex", "semanticscholar", "huggingface"):
        raise ValueError("Unknown signal provider")
    if not 0 <= max_requests <= 1000 or not 0 < max_seconds <= 3600 or not 0 <= limit <= 5000:
        raise ValueError("Signal refresh budgets are out of range")
    now = now or datetime.now(UTC)
    if now.utcoffset() is None:
        raise ValueError("Signal refresh requires aware time")
    base = {"provider": provider, "observed_at": now.isoformat(), "cache_only": cache_only}
    if require_key and provider != "huggingface" and not api_key and not cache_only:
        return {**base, "status": "skipped", "reason": "missing_credential", "requests": 0}
    options = {"max_requests": max_requests, "max_seconds": max_seconds}
    if provider == "openalex":
        client = OpenAlexClient(api_key=api_key, **options)
        refresh = refresh_openalex
    elif provider == "semanticscholar":
        client = SemanticScholarClient(api_key=api_key, **options)
        refresh = refresh_semanticscholar
    else:
        client = HFPapersClient(**options)
        refresh = refresh_huggingface
    sampling = {"sample_history": True} if provider != "huggingface" else {}
    with client:
        report = refresh(
            papers,
            cache,
            client,
            limit=limit,
            cache_only=cache_only,
            now=now,
            **sampling,
        )
    remaining = max(0, report["due"] - report["attempted"])
    failed = report.get("error", 0) + report.get("rate_limited", 0)
    status = (
        "cache_only"
        if cache_only
        else "degraded"
        if failed
        else "deferred"
        if remaining
        else "complete"
    )
    return {**base, **report, "remaining_due": remaining, "status": status}
