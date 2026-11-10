"""Provider-labelled observations with successful-value preservation and explicit freshness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.storage import _atomic_write, _encode

Provider = Literal["openalex", "huggingface", "semanticscholar"]
Status = Literal["unknown", "ok", "not_found", "ambiguous", "rate_limited", "error"]


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Provider
    provider_id: str | None = None
    status: Status = "unknown"
    fetched_at: datetime | None = None
    last_attempt_at: datetime | None = None
    next_retry_at: datetime | None = None
    response_schema_version: str = "1"
    values: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_observation(self):
        for timestamp in (self.fetched_at, self.last_attempt_at, self.next_retry_at):
            if timestamp is not None and timestamp.utcoffset() is None:
                raise ValueError("Observation timestamps require a timezone")
        if self.status == "ok" and (not self.provider_id or self.fetched_at is None):
            raise ValueError("Successful observations require provider identity and fetch time")
        if self.status != "unknown" and self.last_attempt_at is None:
            raise ValueError("Attempt status requires an attempt timestamp")
        if self.fetched_at and self.last_attempt_at and self.fetched_at > self.last_attempt_at:
            raise ValueError("Successful fetch cannot follow the last attempt")
        for field in ("citation_count", "influential_citation_count", "upvotes", "stars"):
            value = self.values.get(field)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"Invalid nonnegative integer signal: {field}")
        return self

    def stale(self, now: datetime, ttl: timedelta) -> bool:
        if now.utcoffset() is None or ttl.total_seconds() < 0:
            raise ValueError("Freshness requires aware time and nonnegative TTL")
        observed = self.fetched_at
        if self.status == "not_found" and not self.values:
            observed = self.last_attempt_at
        return observed is None or now - observed >= ttl

    def due(self, now: datetime, ttl: timedelta) -> bool:
        if self.next_retry_at and now < self.next_retry_at:
            return False
        return self.status not in ("ok", "not_found") or self.stale(now, ttl)


class SignalStore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = "1.0.0"
    provider: Provider
    observations: dict[str, Observation] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_provider(self):
        if any(value.provider != self.provider for value in self.observations.values()):
            raise ValueError("Mixed providers in signal store")
        return self

    def apply(
        self,
        paper_id: str,
        *,
        status: Status,
        now: datetime | None = None,
        provider_id: str | None = None,
        values: dict[str, Any] | None = None,
        retry_after: timedelta | None = None,
        response_schema_version: str | None = None,
    ) -> Observation:
        now = now or datetime.now(UTC)
        previous = self.observations.get(paper_id)
        if previous and previous.last_attempt_at and now < previous.last_attempt_at:
            raise ValueError("Out-of-order provider attempt")
        if status == "unknown":
            raise ValueError("Unknown is reserved for legacy imports, not live attempts")
        if status == "ok" and (values is None or not provider_id):
            raise ValueError("Success requires explicit values and identity")
        if status != "ok" and values is not None:
            raise ValueError("Failed/missing attempts cannot replace successful values")
        if retry_after is not None and retry_after.total_seconds() < 0:
            raise ValueError("Retry delay cannot be negative")
        if (
            previous
            and previous.provider_id
            and provider_id
            and previous.provider_id != provider_id
        ):
            raise ValueError("Provider identity remapping requires reviewed migration")
        observation = Observation(
            provider=self.provider,
            provider_id=provider_id or (previous.provider_id if previous else None),
            status=status,
            fetched_at=now if status == "ok" else (previous.fetched_at if previous else None),
            last_attempt_at=now,
            next_retry_at=now + retry_after if retry_after is not None else None,
            values=values if status == "ok" else (previous.values if previous else {}),
            response_schema_version=response_schema_version
            or (previous.response_schema_version if previous else "1"),
        )
        self.observations[paper_id] = observation
        return observation

    @classmethod
    def load(cls, path: str | Path, provider: Provider):
        path = Path(path)
        if not path.exists():
            return cls(provider=provider)
        store = cls.model_validate_json(path.read_bytes())
        if store.provider != provider:
            raise ValueError("Incorrect signal provider")
        return store

    def save(self, path: str | Path) -> None:
        path = Path(path)
        payload = _encode(self.model_dump(mode="json"))
        if not path.exists() or path.read_bytes() != payload:
            _atomic_write(path, payload)


def refresh_order(papers, observations):
    """Oldest attempts first so bounded recurring queues cannot starve later IDs."""
    oldest = datetime.min.replace(tzinfo=UTC)
    return sorted(
        papers,
        key=lambda paper: (
            observations[paper.id].last_attempt_at or oldest
            if paper.id in observations
            else oldest,
            paper.id,
        ),
    )


def citation_sampling_ttl(paper, observation, default, now, sample_history):
    """Sampling cadence is opt-in; missing results retain their normal retry TTL."""
    if not sample_history or observation is None or observation.status != "ok":
        return default
    age = (now.date() - datetime.fromisoformat(paper.published_date).date()).days
    return min(default, timedelta(days=1 if age <= 90 else 7))
