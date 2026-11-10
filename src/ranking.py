"""Transparent discovery ranking with explicit coverage and observation dates."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.momentum import citation_velocity
from src.observations import SignalStore
from src.openalex_cache import OpenAlexCache, refresh_ttl
from src.schema import PaperRecord


class RankingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["trending-v1"] = "trending-v1"
    formula: Literal["weighted_midrank_exponential_decay"] = "weighted_midrank_exponential_decay"
    weights: dict[str, float] = Field(default_factory=lambda: {"velocity": 0.7, "upvotes": 0.3})
    half_life_days: float = Field(default=30, gt=0, allow_inf_nan=False)
    max_age_days: int = Field(default=90, gt=0)
    hf_ttl_days: float = Field(default=7, gt=0, allow_inf_nan=False)
    percentile: Literal["normalized_midrank_singleton_half"] = "normalized_midrank_singleton_half"

    @model_validator(mode="after")
    def valid_weights(self):
        if set(self.weights) != {"velocity", "upvotes"} or any(
            not math.isfinite(v) or v <= 0 for v in self.weights.values()
        ):
            raise ValueError("Ranking requires positive finite velocity/upvote weights")
        if not math.isclose(sum(self.weights.values()), 1):
            raise ValueError("Ranking weights must sum to one")
        return self

    @classmethod
    def load(cls, path: Path):
        return cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def midranks(values: dict[str, float]) -> dict[str, float]:
    """Map tied average ranks onto [0,1]; a singleton has percentile 0.5."""
    if any(not math.isfinite(value) or value < 0 for value in values.values()):
        raise ValueError("Ranking signals must be finite and nonnegative")
    ordered = sorted(values, key=lambda key: (values[key], key))
    result = {}
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        percentile = ((start + end - 1) / 2) / (len(ordered) - 1) if len(ordered) > 1 else 0.5
        for key in ordered[start:end]:
            result[key] = percentile
        start = end
    return result


def rank_trending(
    papers: list[PaperRecord],
    cache: OpenAlexCache,
    hf: SignalStore,
    *,
    now: datetime,
    config: RankingConfig,
    provider: Literal["openalex", "semanticscholar"] = "openalex",
    citation_store: SignalStore | None = None,
    citation_history: list | None = None,
) -> dict:
    if now.utcoffset() is None or hf.provider != "huggingface":
        raise ValueError("Ranking requires aware time and a separate Hugging Face signal store")
    if len({paper.id for paper in papers}) != len(papers):
        raise ValueError("Duplicate paper identities")
    if provider not in ("openalex", "semanticscholar"):
        raise ValueError("Unknown ranking provider")
    store = cache.signals if provider == "openalex" else citation_store
    history = cache.history if provider == "openalex" else citation_history
    if store is None or store.provider != provider or history is None:
        raise ValueError("Ranking requires a separate selected-provider store and history")
    histories = defaultdict(list)
    for sample in history:
        histories[sample.paper_id].append(sample)
    results = {}
    components: dict[str, dict[str, float]] = {"velocity": {}, "upvotes": {}}
    for paper in papers:
        result = {
            "paper_id": paper.id,
            "coverage": "unavailable",
            "score": None,
            "reason": "date_unverified",
            "age_days": None,
            "original_date": paper.published_date,
            "velocity": None,
            "upvotes_observed_at": None,
            "percentiles": {},
            "weights_used": {},
        }
        results[paper.id] = result
        if paper.published_date_precision != "day":
            continue
        age = (now.date() - datetime.fromisoformat(paper.published_date).date()).days
        result["age_days"] = age
        if not 0 <= age <= config.max_age_days:
            result["reason"] = "outside_age_window"
            continue
        observation = store.observations.get(paper.id)
        velocity = citation_velocity(
            histories[paper.id],
            paper.id,
            now=now,
            ttl=refresh_ttl(paper, cache, now) if provider == "openalex" else timedelta(days=7),
            provider_id=observation.provider_id
            if observation
            else paper.openalex_id
            if provider == "openalex"
            else None,
            provider=provider,
        )
        result["velocity"] = velocity.model_dump(mode="json")
        if velocity.status == "ok" and (
            observation is None or observation.status not in ("ambiguous", "unknown")
        ):
            components["velocity"][paper.id] = velocity.positive_velocity
        upvotes = hf.observations.get(paper.id)
        if upvotes and upvotes.fetched_at:
            result["upvotes_observed_at"] = upvotes.fetched_at.isoformat()
            if upvotes.fetched_at > now:
                raise ValueError("Future HF observations cannot support ranking")
            if (
                upvotes.status not in ("unknown", "ambiguous", "not_found")
                and not upvotes.stale(now, timedelta(days=config.hf_ttl_days))
                and "upvotes" in upvotes.values
            ):
                components["upvotes"][paper.id] = upvotes.values["upvotes"]
        result["reason"] = "no_eligible_signals"
    percentiles = {name: midranks(values) for name, values in components.items()}
    for paper_id, result in results.items():
        available = {
            name: ranks[paper_id] for name, ranks in percentiles.items() if paper_id in ranks
        }
        if not available:
            continue
        total = sum(config.weights[name] for name in available)
        weights = {name: config.weights[name] / total for name in available}
        result.update(
            coverage="complete" if len(available) == 2 else "partial",
            reason=None,
            percentiles=available,
            weights_used=weights,
            score=100
            * sum(weights[name] * value for name, value in available.items())
            * 2 ** (-result["age_days"] / config.half_life_days),
        )
    order = {"complete": 0, "partial": 1, "unavailable": 2}
    ranked = sorted(
        results.values(),
        key=lambda item: (
            order[item["coverage"]],
            -(item["score"] or 0),
            -datetime.fromisoformat(item["original_date"]).toordinal(),
            item["paper_id"],
        ),
    )
    return {
        "provider": provider,
        "generated_at": now.isoformat(),
        "config": config.model_dump(mode="json"),
        "interpretation": "Discovery ranking, not scientific quality",
        "papers": ranked,
    }
