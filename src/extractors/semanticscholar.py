"""Semantic Scholar counts and references kept separate from OpenAlex observations."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.extractors.openalex import OpenAlexClient
from src.file_lock import exclusive_file
from src.identity import normalize_arxiv, normalize_doi
from src.observations import SignalStore, citation_sampling_ttl, refresh_order
from src.schema import PaperRecord
from src.semanticscholar_history import SemanticScholarHistory, SemanticScholarSample, history_path


class SemanticScholarFailure(RuntimeError):
    def __init__(self, reason: str, retry_after: float = 3600):
        super().__init__(f"Semantic Scholar deferred: {reason}")
        self.reason, self.retry_after = reason, retry_after


class SemanticScholarPaper(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    paperId: str = Field(pattern=r"^[a-fA-F0-9]{40}$")
    title: str
    externalIds: dict[str, Any]
    citationCount: int = Field(ge=0)
    influentialCitationCount: int | None = Field(default=None, ge=0)
    referenceCount: int = Field(ge=0)
    references: list[dict[str, Any]]


def lookup_id(paper: PaperRecord) -> str | None:
    if paper.arxiv_id:
        return f"ARXIV:{normalize_arxiv(paper.arxiv_id)}"
    doi = normalize_doi(paper.doi or paper.arxiv_doi)
    return f"DOI:{doi}" if doi else None


def exact_match(paper: PaperRecord, work: SemanticScholarPaper) -> bool:
    arxiv = work.externalIds.get("ArXiv")
    doi = work.externalIds.get("DOI")
    if (
        arxiv is not None
        and not isinstance(arxiv, str)
        or doi is not None
        and not isinstance(doi, str)
    ):
        return False
    if paper.arxiv_id and arxiv:
        return normalize_arxiv(paper.arxiv_id) == normalize_arxiv(arxiv)
    expected = {normalize_doi(paper.doi), normalize_doi(paper.arxiv_doi)} - {None}
    return bool(doi and normalize_doi(doi) in expected)


class SemanticScholarClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        max_requests: int = 100,
        max_seconds: float = 300,
        max_attempts: int = 3,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if max_requests < 0 or max_seconds <= 0 or not 1 <= max_attempts <= 3:
            raise ValueError("Invalid Semantic Scholar limits")
        headers = {}
        if api_key:
            if re.search(r"[\r\n]", api_key):
                raise ValueError("Invalid Semantic Scholar credential")
            headers["x-api-key"] = api_key
        self.http = httpx.Client(
            base_url="https://api.semanticscholar.org/graph/v1/",
            headers=headers,
            timeout=20,
            transport=transport,
            follow_redirects=False,
        )
        self.clock, self.sleep = clock, sleep
        self.started = clock()
        self.next_request = self.started
        self.requests = 0
        self.max_requests, self.max_seconds, self.max_attempts = (
            max_requests,
            max_seconds,
            max_attempts,
        )
        self.stopped = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.http.close()

    def batch(self, ids: list[str]) -> list[SemanticScholarPaper | None]:
        if not ids:
            return []
        if len(ids) > 40 or any(not value.startswith(("DOI:", "ARXIV:")) for value in ids):
            raise ValueError("Expected at most 40 exact DOI/arXiv identifiers")
        for attempt in range(self.max_attempts):
            if self.stopped:
                raise SemanticScholarFailure("authentication")
            wait = max(0, self.next_request - self.clock())
            if wait > 60:
                raise SemanticScholarFailure("retry_deadline", wait)
            if (
                self.requests >= self.max_requests
                or self.clock() - self.started + wait >= self.max_seconds
            ):
                raise SemanticScholarFailure("run_budget")
            if wait > 60:
                raise SemanticScholarFailure("retry_deadline", wait)
            if wait:
                self.sleep(wait)
            self.requests += 1
            try:
                response = self.http.post(
                    "paper/batch",
                    params={
                        "fields": "title,externalIds,citationCount,influentialCitationCount,referenceCount,references.paperId,references.externalIds"
                    },
                    json={"ids": ids},
                )
            except httpx.HTTPError:
                self.next_request = self.clock() + 2**attempt
                if attempt + 1 == self.max_attempts or self.requests >= self.max_requests:
                    raise SemanticScholarFailure("transport") from None
                continue
            self.next_request = self.clock() + 1
            if response.status_code in (401, 403):
                self.stopped = True
                raise SemanticScholarFailure("authentication")
            if response.status_code == 429 or response.status_code >= 500:
                delay = OpenAlexClient._retry_delay(response, 2**attempt)
                self.next_request = self.clock() + max(1, delay)
                if attempt + 1 == self.max_attempts or self.requests >= self.max_requests:
                    raise SemanticScholarFailure(
                        "rate_limited" if response.status_code == 429 else "server", delay
                    )
                continue
            if response.status_code != 200:
                raise SemanticScholarFailure("http_status")
            try:
                payload = response.json()
                if not isinstance(payload, list) or len(payload) != len(ids):
                    raise ValueError
                return [
                    SemanticScholarPaper.model_validate(item) if item is not None else None
                    for item in payload
                ]
            except (ValueError, TypeError):
                raise SemanticScholarFailure("invalid_response") from None
        raise SemanticScholarFailure("attempt_budget")


def refresh_semanticscholar(
    papers: list[PaperRecord],
    path: Path,
    client: SemanticScholarClient,
    *,
    sample_history: bool = False,
    limit: int = 100,
    cache_only: bool = False,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(UTC)
    if now.utcoffset() is None or limit < 0:
        raise ValueError("Refresh requires aware time and nonnegative limit")
    with exclusive_file(path.with_suffix(".run.lock"), resource="Semantic Scholar refresh"):
        store = SignalStore.load(path, "semanticscholar")
        history = SemanticScholarHistory.load(history_path(path))
        due = [
            paper
            for paper in papers
            if paper.id not in store.observations
            or store.observations[paper.id].due(
                now,
                citation_sampling_ttl(
                    paper,
                    store.observations.get(paper.id),
                    timedelta(days=7),
                    now,
                    sample_history,
                ),
            )
        ]
        due = refresh_order(due, store.observations)
        report = {
            "provider": "semanticscholar",
            "due": len(due),
            "attempted": 0,
            "ok": 0,
            "not_found": 0,
            "ambiguous": 0,
            "error": 0,
            "rate_limited": 0,
            "requests": 0,
        }
        if cache_only:
            return report
        selected = due[:limit]
        for start in range(0, len(selected), 40):
            batch = selected[start : start + 40]
            mapped = [paper for paper in batch if lookup_id(paper)]
            for paper in batch:
                if lookup_id(paper) is None:
                    store.apply(
                        paper.id, status="ambiguous", now=now, retry_after=timedelta(days=7)
                    )
                    report["ambiguous"] += 1
                    report["attempted"] += 1
            try:
                works = client.batch([lookup_id(paper) for paper in mapped])
            except SemanticScholarFailure as failure:
                if failure.reason == "run_budget":
                    if report["attempted"]:
                        store.save(path)
                    break
                status = (
                    "rate_limited"
                    if failure.reason in ("rate_limited", "retry_deadline")
                    else "error"
                )
                for paper in mapped:
                    store.apply(
                        paper.id,
                        status=status,
                        now=now,
                        retry_after=timedelta(seconds=max(3600, failure.retry_after)),
                    )
                    report[status] += 1
                    report["attempted"] += 1
                store.save(path)
                break
            for paper, work in zip(mapped, works, strict=True):
                status = (
                    "not_found"
                    if work is None
                    else "ok"
                    if exact_match(paper, work)
                    else "ambiguous"
                )
                previous = store.observations.get(paper.id)
                if status == "ok" and (
                    (
                        previous
                        and previous.provider_id
                        and previous.provider_id.lower() != work.paperId.lower()
                    )
                    or (
                        history.provider_id_for(paper.id)
                        and history.provider_id_for(paper.id) != work.paperId.lower()
                    )
                ):
                    status = "ambiguous"
                if status == "ok":
                    refs = sorted(
                        {
                            ref["paperId"]
                            for ref in work.references
                            if isinstance(ref.get("paperId"), str)
                            and re.fullmatch(r"[a-fA-F0-9]{40}", ref["paperId"])
                        }
                    )
                    values = {
                        "citation_count": work.citationCount,
                        "references": refs,
                        "references_complete": len(refs) == work.referenceCount,
                        "reference_count": work.referenceCount,
                        "external_ids": work.externalIds,
                    }
                    if work.influentialCitationCount is not None:
                        values["influential_citation_count"] = work.influentialCitationCount
                    store.apply(
                        paper.id,
                        status="ok",
                        now=now,
                        provider_id=previous.provider_id
                        if previous and previous.provider_id
                        else work.paperId.lower(),
                        values=values,
                    )
                    history.record(
                        SemanticScholarSample(
                            paper_id=paper.id,
                            provider_id=work.paperId,
                            observed_at=now,
                            citation_count=work.citationCount,
                            influential_citation_count=work.influentialCitationCount,
                        )
                    )
                else:
                    store.apply(paper.id, status=status, now=now, retry_after=timedelta(days=7))
                report[status] += 1
                report["attempted"] += 1
            # History goes first: a crash before cache save safely replays the
            # batch and keeps the first genuine observation of that UTC date.
            if any(history.provider_id_for(paper.id) for paper in mapped):
                history.save(history_path(path))
            store.save(path)
        report["requests"] = client.requests
        return report
