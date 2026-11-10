"""Shared HF Papers transport with bounded requests and sanitized outcomes."""

from __future__ import annotations

import time
from datetime import date
from urllib.parse import quote

import httpx

from src.extractors.huggingface_contracts import HFPaper, parse_daily
from src.extractors.openalex import OpenAlexClient
from src.identity import normalize_arxiv


class HFFailure(RuntimeError):
    def __init__(self, reason, retry_after=None):
        super().__init__(f"Hugging Face deferred: {reason}")
        self.reason, self.retry_after = reason, retry_after


class HFPapersClient:
    def __init__(
        self,
        *,
        max_requests=20,
        max_seconds=120,
        transport=None,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        if max_requests < 0 or max_seconds <= 0:
            raise ValueError("Invalid HF budgets")
        self.http = httpx.Client(
            base_url="https://huggingface.co",
            timeout=20,
            follow_redirects=False,
            transport=transport,
        )
        self.clock, self.sleep = clock, sleep
        self.started = clock()
        self.next_request = self.started
        self.max_requests, self.max_seconds = max_requests, max_seconds
        self.requests = 0
        self.stopped = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.http.close()

    def request(self, path, params=None, *, missing=False):
        for attempt in range(3):
            if self.stopped:
                raise HFFailure("authentication")
            wait = max(0, self.next_request - self.clock())
            if wait > 60:
                raise HFFailure("retry_deadline", wait)
            if (
                self.requests >= self.max_requests
                or self.clock() - self.started + wait >= self.max_seconds
            ):
                raise HFFailure("run_budget")
            if wait:
                self.sleep(wait)
            self.requests += 1
            try:
                response = self.http.get(path, params=params)
            except httpx.HTTPError:
                self.next_request = self.clock() + 2**attempt
                if attempt == 2 or self.requests >= self.max_requests:
                    raise HFFailure("transport") from None
                continue
            self.next_request = self.clock() + 1
            if response.status_code in (401, 403):
                self.stopped = True
                raise HFFailure("authentication")
            if response.status_code == 404 and missing:
                return None
            if response.status_code == 429 or response.status_code >= 500:
                delay = OpenAlexClient._retry_delay(response, 2**attempt)
                self.next_request = self.clock() + max(1, delay)
                if attempt == 2 or self.requests >= self.max_requests:
                    raise HFFailure(
                        "rate_limited" if response.status_code == 429 else "server", delay
                    )
                continue
            if response.status_code != 200:
                raise HFFailure("http_status")
            try:
                return response.json()
            except ValueError:
                raise HFFailure("invalid_json") from None
        raise HFFailure("attempt_budget")

    def daily(self, *, day: date | None = None, limit=50):
        if not 1 <= limit <= 100:
            raise ValueError("HF discovery limit must be1..100")
        params = {"limit": limit}
        if day:
            params["date"] = day.isoformat()
        payload = self.request("/api/daily_papers", params)
        try:
            return parse_daily(payload)
        except ValueError:
            raise HFFailure("invalid_contract") from None

    def paper(self, arxiv_id):
        key = normalize_arxiv(arxiv_id)
        # Validate before constructing a provider path.
        try:
            key = HFPaper(id=key, title="Identity validation").id
        except ValueError:
            raise ValueError("Expected arXiv identity") from None
        payload = self.request("/api/papers/" + quote(key, safe=""), missing=True)
        if payload is None:
            return None
        try:
            paper = HFPaper.model_validate(payload)
        except ValueError:
            raise HFFailure("invalid_contract") from None
        if paper.id != key:
            raise HFFailure("identity_mismatch")
        return paper
