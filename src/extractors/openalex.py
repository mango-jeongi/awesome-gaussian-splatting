"""Bounded OpenAlex transport and strict work parsing shared by enrichment adapters."""

from __future__ import annotations

import random
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.identity import normalize_arxiv, normalize_doi, normalize_openalex


class OpenAlexFailure(RuntimeError):
    def __init__(self, reason: str, *, retry_after: float | None = None):
        super().__init__(f"OpenAlex deferred: {reason}")
        self.reason = reason
        self.retry_after = retry_after


class OpenAlexWork(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    id: str
    doi: str | None = None
    title: str | None = None
    cited_by_count: int = Field(ge=0)
    referenced_works: list[str]
    publication_year: int | None = None
    authorships: list[dict[str, Any]] = Field(default_factory=list)
    primary_location: dict[str, Any] | None = None
    locations: list[dict[str, Any]] = Field(default_factory=list)
    type: str | None = None

    @field_validator("id")
    @classmethod
    def valid_id(cls, value):
        normalized = normalize_openalex(value)
        if not normalized or value != f"https://openalex.org/{normalized}":
            raise ValueError("Invalid work identity")
        return value

    @field_validator("referenced_works")
    @classmethod
    def valid_references(cls, values):
        if any(not normalize_openalex(value) for value in values):
            raise ValueError("Invalid reference identity")
        return sorted(set(values))

    def doi_aliases(self) -> set[str]:
        values = {normalize_doi(self.doi)}
        for location in self.locations:
            url = location.get("landing_page_url")
            if not isinstance(url, str):
                continue
            if re.match(r"^https?://(?:dx\.)?doi\.org/", url, re.I):
                values.add(normalize_doi(url))
            elif re.match(
                r"^https?://arxiv\.org/abs/(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?$", url, re.I
            ):
                values.add(f"10.48550/arxiv.{normalize_arxiv(url)}")
        return {value for value in values if value}


class OpenAlexClient:
    """One bounded executor. Auth/budget failures latch for the remainder of a run.

    Budget is enforced by request/time ceilings and provider remaining-budget headers.
    Dollar spend is recorded from server metadata; no guessed request price is used.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        max_requests: int = 100,
        max_seconds: float = 300,
        max_attempts: int = 3,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        jitter: Callable[[], float] = random.random,
    ):
        if not 0 <= max_requests <= 10000 or max_seconds <= 0 or not 1 <= max_attempts <= 3:
            raise ValueError("Invalid OpenAlex request limits")
        self.max_requests, self.max_seconds, self.max_attempts = (
            max_requests,
            max_seconds,
            max_attempts,
        )
        self.sleep, self.clock, self.jitter = sleep, clock, jitter
        self.started = clock()
        self.requests = 0
        self.cost_usd = 0.0
        self.remaining: float | None = None
        self.stopped: str | None = None
        self.next_request = self.started
        headers = {"User-Agent": "AwesomeGaussianSplatting/2.0 (research metadata pipeline)"}
        if api_key:
            if any(char in api_key for char in "\r\n"):
                raise ValueError("Invalid OpenAlex credential")
            headers["Authorization"] = f"Bearer {api_key}"
        self.http = httpx.Client(
            base_url="https://api.openalex.org",
            headers=headers,
            timeout=httpx.Timeout(20, connect=10),
            transport=transport,
            follow_redirects=False,
        )

    def close(self):
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _wait(self, delay: float):
        if delay > 60 or self.clock() - self.started + delay >= self.max_seconds:
            raise OpenAlexFailure("retry_deadline", retry_after=delay)
        if delay > 0:
            self.sleep(delay)

    @staticmethod
    def _retry_delay(response: httpx.Response, fallback: float) -> float:
        raw = response.headers.get("Retry-After")
        if raw is None:
            return fallback
        try:
            return max(0.0, float(raw))
        except ValueError:
            try:
                stamp = parsedate_to_datetime(raw)
                if stamp.utcoffset() is None:
                    return fallback
                return max(0.0, (stamp - datetime.now(UTC)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                return fallback

    def request(self, params: dict[str, str | int]) -> dict[str, Any]:
        for attempt in range(self.max_attempts):
            if self.stopped:
                raise OpenAlexFailure(self.stopped)
            if (
                self.requests >= self.max_requests
                or self.clock() - self.started >= self.max_seconds
            ):
                raise OpenAlexFailure("run_budget")
            self._wait(max(0, self.next_request - self.clock()))
            if self.clock() - self.started >= self.max_seconds:
                raise OpenAlexFailure("run_budget")
            self.requests += 1
            try:
                response = self.http.get("/works", params=params)
            except httpx.HTTPError:
                self.next_request = self.clock() + 1
                if attempt + 1 == self.max_attempts:
                    raise OpenAlexFailure("transport") from None
                self._wait(2**attempt + self.jitter())
                continue
            self.next_request = self.clock() + 1  # deliberately below keyed/keyless limits
            try:
                remaining = float(response.headers["X-RateLimit-Remaining"])
                if remaining < 0 or remaining != remaining:
                    raise ValueError
                self.remaining = remaining
            except (KeyError, ValueError):
                pass
            if response.status_code in (401, 403):
                self.stopped = "authentication"
                raise OpenAlexFailure(self.stopped)
            if response.status_code == 429 or response.status_code >= 500:
                delay = self._retry_delay(response, 2**attempt + self.jitter())
                if self.remaining is not None and self.remaining <= 0:
                    self.stopped = "account_budget"
                    raise OpenAlexFailure(self.stopped, retry_after=delay)
                self.next_request = self.clock() + max(1, delay)
                if attempt + 1 == self.max_attempts:
                    raise OpenAlexFailure(
                        "rate_limited" if response.status_code == 429 else "server",
                        retry_after=delay,
                    )
                self._wait(delay)
                continue
            if response.status_code != 200:
                raise OpenAlexFailure("http_status")
            try:
                payload = response.json()
                meta = payload["meta"]
                if not isinstance(meta, dict) or not isinstance(payload["results"], list):
                    raise ValueError
                cost = meta.get("cost_usd", 0)
                if type(cost) not in (int, float) or cost < 0 or not float(cost) < float("inf"):
                    raise ValueError
                self.cost_usd += cost
            except (ValueError, KeyError, TypeError):
                raise OpenAlexFailure("invalid_response") from None
            if self.remaining is not None and self.remaining <= 0:
                self.stopped = "account_budget"  # current successful response is still usable
            return payload
        raise OpenAlexFailure("attempt_budget")

    def by_dois(self, dois: list[str]) -> dict[str, list[OpenAlexWork]]:
        normalized = sorted({normalize_doi(value) for value in dois if normalize_doi(value)})
        if len(normalized) > 40 or any(
            not value.startswith("10.") or "|" in value or "," in value for value in normalized
        ):
            raise ValueError("Expected at most 40 exact DOI identifiers")
        if not normalized:
            return {}
        found: dict[str, list[OpenAlexWork]] = {value: [] for value in normalized}
        page, total, seen = 1, None, set()
        while True:
            payload = self.request(
                {"filter": "doi:" + "|".join(normalized), "per_page": 100, "page": page}
            )
            count = payload["meta"].get("count")
            if type(count) is not int or count < 0 or (total is not None and count != total):
                raise OpenAlexFailure("pagination_count")
            total = count
            try:
                works = [OpenAlexWork.model_validate(raw) for raw in payload["results"]]
            except ValueError:
                raise OpenAlexFailure("invalid_work") from None
            for work in works:
                matched_dois = work.doi_aliases() & found.keys()
                if not matched_dois or work.id in seen:
                    raise OpenAlexFailure("identity_or_pagination")
                seen.add(work.id)
                for doi in matched_dois:
                    found[doi].append(work)
            if len(seen) == total:
                return found
            if len(seen) > total or len(works) != 100 or page >= 100:
                raise OpenAlexFailure("incomplete_pagination")
            page += 1
