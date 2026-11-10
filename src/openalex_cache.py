"""Durable OpenAlex response cache and genuine dated citation observations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.extractors.openalex import OpenAlexClient, OpenAlexFailure, OpenAlexWork
from src.file_lock import exclusive_file
from src.identity import normalize_arxiv, normalize_doi, normalize_openalex
from src.observations import SignalStore, citation_sampling_ttl, refresh_order
from src.schema import PaperRecord
from src.storage import _atomic_write, _encode


class CitationSample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper_id: str
    provider_id: str
    observed_at: datetime
    citation_count: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def validate_time(self):
        if self.observed_at.utcoffset() is None or not normalize_openalex(self.provider_id):
            raise ValueError("Samples require aware time and provider identity")
        return self


class OpenAlexCache(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0.0"] = "1.0.0"
    signals: SignalStore = Field(default_factory=lambda: SignalStore(provider="openalex"))
    works: dict[str, OpenAlexWork] = Field(default_factory=dict)
    history: list[CitationSample] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_cache(self):
        if self.signals.provider != "openalex":
            raise ValueError("Incorrect cache provider")
        if any(key != work.id for key, work in self.works.items()):
            raise ValueError("Cache work key mismatch")
        keys = [
            (sample.paper_id, sample.observed_at.astimezone(UTC).date()) for sample in self.history
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate daily observations")
        return self

    @classmethod
    def load(cls, path: Path):
        return cls.model_validate_json(path.read_bytes()) if path.exists() else cls()

    def save(self, path: Path):
        # Callers serialize the entire load/refresh/save transaction with exclusive_file.
        payload = _encode(self.model_dump(mode="json"))
        if not path.exists() or path.read_bytes() != payload:
            _atomic_write(path, payload)

    def record(self, paper_id: str, work: OpenAlexWork, now: datetime):
        self.signals.apply(
            paper_id,
            status="ok",
            now=now,
            provider_id=work.id,
            values={
                "citation_count": work.cited_by_count,
                "referenced_works": work.referenced_works,
                "doi": normalize_doi(work.doi),
            },
        )
        self.works[work.id] = work
        # Preserve the first genuine observation on each UTC date. Never fabricate old data.
        month_index = now.year * 12 + now.month - 1 - 13
        year, month = divmod(month_index, 12)
        from calendar import monthrange

        cutoff = now.replace(
            year=year, month=month + 1, day=min(now.day, monthrange(year, month + 1)[1])
        )
        self.history = [sample for sample in self.history if sample.observed_at >= cutoff]
        if not any(
            sample.paper_id == paper_id
            and sample.observed_at.astimezone(UTC).date() == now.astimezone(UTC).date()
            for sample in self.history
        ):
            self.history.append(
                CitationSample(
                    paper_id=paper_id,
                    provider_id=work.id,
                    observed_at=now,
                    citation_count=work.cited_by_count,
                )
            )
        self.history.sort(key=lambda sample: (sample.paper_id, sample.observed_at))


def paper_dois(paper: PaperRecord) -> list[str]:
    values = {normalize_doi(paper.doi), normalize_doi(paper.arxiv_doi)}
    if paper.arxiv_id:
        values.add(f"10.48550/arxiv.{normalize_arxiv(paper.arxiv_id)}")
    return sorted(value for value in values if value)


def refresh_ttl(paper: PaperRecord, cache: OpenAlexCache, now: datetime) -> timedelta:
    observation = cache.signals.observations.get(paper.id)
    if observation and observation.status == "not_found":
        return timedelta(days=7)
    age = (now.date() - datetime.fromisoformat(paper.published_date).date()).days
    if observation is None or observation.fetched_at is None or age <= 7:
        return timedelta(days=1)
    return timedelta(days=7 if age <= 90 else 30)


def refresh_openalex(
    papers: list[PaperRecord],
    path: Path,
    client: OpenAlexClient,
    *,
    cache_only: bool = False,
    sample_history: bool = False,
    limit: int = 100,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(UTC)
    if now.utcoffset() is None or limit < 0:
        raise ValueError("Refresh requires aware time and a nonnegative limit")
    with exclusive_file(path.with_suffix(path.suffix + ".run.lock"), resource="OpenAlex refresh"):
        cache = OpenAlexCache.load(path)
        due = [
            paper
            for paper in papers
            if paper.id not in cache.signals.observations
            or cache.signals.observations[paper.id].due(
                now,
                citation_sampling_ttl(
                    paper,
                    cache.signals.observations.get(paper.id),
                    refresh_ttl(paper, cache, now),
                    now,
                    sample_history,
                ),
            )
        ]
        due = refresh_order(due, cache.signals.observations)
        report = {
            "total": len(papers),
            "due": len(due),
            "attempted": 0,
            "ok": 0,
            "not_found": 0,
            "ambiguous": 0,
            "error": 0,
            "rate_limited": 0,
            "requests": 0,
            "cache_only": cache_only,
            "deferred": 0,
        }
        if cache_only:
            return report
        selected = due[:limit]
        # Pack at most 40 DOI identifiers per request, including publication/preprint aliases.
        batches: list[list[PaperRecord]] = []
        for paper in selected:
            if (
                not batches
                or len(
                    set().union(
                        *(set(paper_dois(item)) for item in batches[-1]), set(paper_dois(paper))
                    )
                )
                > 40
            ):
                batches.append([])
            batches[-1].append(paper)
        initial_requests = client.requests
        for batch in batches:
            mapped = [paper for paper in batch if paper_dois(paper)]
            for paper in batch:
                if not paper_dois(paper):
                    # A title search needs reviewed identity evidence, not a guessed first hit.
                    cache.signals.apply(
                        paper.id, status="ambiguous", now=now, retry_after=timedelta(days=7)
                    )
                    report["ambiguous"] += 1
                    report["attempted"] += 1
            if not mapped:
                cache.save(path)
                continue
            try:
                found = client.by_dois([doi for paper in mapped for doi in paper_dois(paper)])
            except OpenAlexFailure as failure:
                if failure.reason == "run_budget":
                    report["deferred"] += len(mapped)
                    break
                status = (
                    "rate_limited"
                    if failure.reason in ("rate_limited", "account_budget", "retry_deadline")
                    else "error"
                )
                for paper in mapped:
                    cache.signals.apply(
                        paper.id,
                        status=status,
                        now=now,
                        retry_after=timedelta(seconds=max(3600, failure.retry_after or 0)),
                    )
                    report[status] += 1
                    report["attempted"] += 1
                cache.save(path)
                if client.stopped or failure.reason == "retry_deadline":
                    break
                continue
            for paper in mapped:
                matches = {
                    work.id: work for doi in paper_dois(paper) for work in found.get(doi, [])
                }
                previous = cache.signals.observations.get(paper.id)
                expected = normalize_openalex(
                    previous.provider_id if previous else paper.openalex_id
                )
                arxiv_conflict = any(
                    paper.arxiv_id
                    and normalize_doi(work.doi)
                    and normalize_doi(work.doi).startswith("10.48550/arxiv.")
                    and normalize_doi(work.doi)
                    != f"10.48550/arxiv.{normalize_arxiv(paper.arxiv_id)}"
                    for work in matches.values()
                )
                if (
                    len(matches) == 1
                    and not arxiv_conflict
                    and (not expected or normalize_openalex(next(iter(matches))) == expected)
                ):
                    cache.record(paper.id, next(iter(matches.values())), now)
                    status = "ok"
                else:
                    status = "ambiguous" if matches else "not_found"
                    cache.signals.apply(
                        paper.id, status=status, now=now, retry_after=timedelta(days=7)
                    )
                    for work in matches.values():
                        cache.works[work.id] = work
                report[status] += 1
                report["attempted"] += 1
            cache.save(path)
        if report["attempted"]:
            cache.save(path)
        report["requests"] = client.requests - initial_requests
        report["deferred"] = len(selected) - report["attempted"]
        report["cost_usd"] = client.cost_usd
        return report
