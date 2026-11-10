"""Measured citation momentum. Annual provider aggregates are never observations."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.identity import normalize_openalex
from src.openalex_cache import CitationSample
from src.semanticscholar_history import SemanticScholarSample


class CitationVelocity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["openalex", "semanticscholar"] = "openalex"
    paper_id: str
    provider_id: str | None = None
    status: Literal[
        "ok",
        "single_snapshot",
        "no_observations",
        "stale",
        "identity_changed",
        "no_eligible_window",
    ]
    current_at: datetime | None = None
    baseline_at: datetime | None = None
    elapsed_days: float | None = None
    raw_delta: int | None = None
    raw_velocity: float | None = None
    positive_velocity: float | None = None
    provider_correction: bool = False


def citation_velocity(
    samples: list[CitationSample] | list[SemanticScholarSample],
    paper_id: str,
    *,
    now: datetime,
    ttl: timedelta,
    provider_id: str | None = None,
    provider: Literal["openalex", "semanticscholar"] = "openalex",
) -> CitationVelocity:
    if now.utcoffset() is None or ttl.total_seconds() <= 0:
        raise ValueError("Velocity requires aware current time and positive freshness TTL")
    if provider not in ("openalex", "semanticscholar"):
        raise ValueError("Unknown citation provider")

    def identity(value):
        if provider == "openalex":
            return normalize_openalex(value)
        return value.lower() if value and re.fullmatch(r"[a-fA-F0-9]{40}", value) else None

    if any(not identity(sample.provider_id) for sample in samples):
        raise ValueError("Observation identifiers do not match the selected provider")
    relevant = sorted(
        (sample for sample in samples if sample.paper_id == paper_id),
        key=lambda sample: sample.observed_at,
    )
    if any(sample.observed_at > now for sample in relevant):
        raise ValueError("Future observations cannot support measured velocity")
    if len({sample.observed_at for sample in relevant}) != len(relevant):
        raise ValueError("Duplicate observation timestamps require reconciliation")
    result = CitationVelocity(
        provider=provider, paper_id=paper_id, status="no_observations", provider_id=provider_id
    )
    if not relevant:
        return result
    current = relevant[-1]
    result.provider_id = current.provider_id
    result.current_at = current.observed_at
    if provider_id and identity(provider_id) != identity(current.provider_id):
        result.status = "identity_changed"
        return result
    if now - current.observed_at >= ttl:
        result.status = "stale"
        return result
    if len(relevant) == 1:
        result.status = "single_snapshot"
        return result
    # A provider remap starts a new comparable segment, even if an old ID reappears.
    boundary = max(
        (
            index
            for index, sample in enumerate(relevant)
            if identity(sample.provider_id) != identity(current.provider_id)
        ),
        default=-1,
    )
    comparable = relevant[boundary + 1 : -1]
    eligible = [
        (sample, (current.observed_at - sample.observed_at).total_seconds() / 86400)
        for sample in comparable
    ]
    eligible = [(sample, days) for sample, days in eligible if 7 <= days <= 45]
    if not eligible:
        result.status = "identity_changed" if boundary >= 0 else "no_eligible_window"
        return result
    # Equal distance chooses the newer baseline, giving a deterministic shorter window.
    baseline, days = min(eligible, key=lambda item: (abs(item[1] - 30), item[1]))
    delta = current.citation_count - baseline.citation_count
    result.status = "ok"
    result.baseline_at = baseline.observed_at
    result.elapsed_days = days
    result.raw_delta = delta
    result.raw_velocity = delta / days
    result.positive_velocity = max(0, result.raw_velocity)
    result.provider_correction = delta < 0
    return result
