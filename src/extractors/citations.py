"""OpenAlex Citation Intelligence & Cross-Paper Knowledge Graph Builder (Phase 3)."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from src.environment import load_local_environment
from src.extractors.openalex import OpenAlexClient
from src.identity import (
    IdentityIndex,
    identifier_key,
    normalize_arxiv,
    normalize_doi,
    normalize_openalex,
)
from src.openalex_cache import OpenAlexCache, paper_dois, refresh_openalex
from src.schema import PaperDatabase, PaperRecord


def _is_title_similar(t1: str, t2: str) -> bool:
    # Candidate-review hint only: never authorizes a provider identity assignment.
    def normalize(value):
        return re.sub(r"[^\w\s]", "", value.lower()).strip()

    left, right = normalize(t1), normalize(t2)
    return bool(left and right and (left in right or right in left))


class OpenAlexCitationClient(OpenAlexClient):
    """Compatibility surface backed by the same bounded, exact-ID transport."""

    def fetch_batch_by_doi(self, papers: list[PaperRecord]) -> dict[str, dict[str, Any]]:
        found = self.by_dois([doi for paper in papers for doi in paper_dois(paper)])
        results = {}
        for paper in papers:
            matches = {work.id: work for doi in paper_dois(paper) for work in found.get(doi, [])}
            if len(matches) != 1:
                continue
            work = next(iter(matches.values()))
            if paper.openalex_id and normalize_openalex(paper.openalex_id) != normalize_openalex(
                work.id
            ):
                continue
            results[paper.id] = {
                "citation_count": work.cited_by_count,
                "openalex_id": work.id,
                "referenced_works": work.referenced_works,
                "doi": normalize_doi(work.doi),
            }
        return results

    def fetch_single_by_title(self, paper: PaperRecord) -> None:
        # Title-only identities remain review-required in the shared cache.
        return None


def build_citation_knowledge_graph(db: PaperDatabase) -> dict[str, int]:
    """Construct internal directed citation and reference edges across papers in the database.

    Populates:
    - `p.db_references`: list of paper IDs in this database cited by `p`.
    - `p.db_citations`: list of paper IDs in this database that cite `p`.
    - `p.db_citation_count`: number of incoming citations from within this database.
    """
    index = IdentityIndex(db.papers, db.aliases)
    for paper in db.papers:
        if paper.arxiv_id:
            index.bind(f"doi:10.48550/arxiv.{normalize_arxiv(paper.arxiv_id)}", paper.id)
    outgoing: dict[str, set[str]] = {paper.id: set() for paper in db.papers}
    incoming: dict[str, set[str]] = {paper.id: set() for paper in db.papers}
    unmatched = 0
    self_references = 0
    for paper in db.papers:
        for reference in {identifier_key(ref) for ref in paper.referenced_works}:
            target = index.aliases.get(reference)
            if target is None:
                unmatched += 1
            elif target == paper.id:
                self_references += 1
            else:
                outgoing[paper.id].add(target)
                incoming[target].add(paper.id)
    for paper in db.papers:
        paper.db_references = sorted(outgoing[paper.id])
        paper.db_citations = sorted(incoming[paper.id])
        paper.db_citation_count = len(incoming[paper.id])
    return {
        "total_nodes": len(db.papers),
        "total_edges": sum(len(edges) for edges in outgoing.values()),
        "connected_papers": sum(
            bool(outgoing[paper.id] or incoming[paper.id]) for paper in db.papers
        ),
        "unmatched_references": unmatched,
        "self_references_omitted": self_references,
    }


def _assign_provider_doi(paper: PaperRecord, value: str | None) -> None:
    """Keep arXiv DataCite identifiers separate from proceedings DOI metadata."""
    normalized = normalize_doi(value)
    if not normalized:
        return
    field = "arxiv_doi" if normalized.startswith("10.48550/arxiv.") else "doi"
    if field == "arxiv_doi" and paper.arxiv_id:
        expected = f"10.48550/arxiv.{normalize_arxiv(paper.arxiv_id)}"
        if normalized != expected:
            raise ValueError("Provider DOI contradicts the paper's arXiv identity")
    if field not in paper.protected_fields() and not getattr(paper, field):
        setattr(paper, field, normalized)


def enrich_database_citations(
    db: PaperDatabase,
    batch_size: int = 40,
    max_papers: int | None = None,
    client: OpenAlexCitationClient | None = None,
    cache_path: Path | None = None,
    cache_only: bool = False,
    max_requests: int = 100,
    max_seconds: float = 300,
) -> dict[str, int]:
    """Fetch global citation metrics from OpenAlex and build internal knowledge graph."""
    if not 1 <= batch_size <= 40:
        raise ValueError("Citation batch size must be between 1 and 40")
    if client is None:
        root = Path(__file__).resolve().parents[2]
        load_local_environment(root)
        cache_path = cache_path or root / "data/signals/openalex-cache.json"
        with OpenAlexClient(
            api_key=os.environ.get("OPENALEX_API_KEY"),
            max_requests=max_requests,
            max_seconds=max_seconds,
        ) as shared:
            report = refresh_openalex(
                db.papers,
                cache_path,
                shared,
                cache_only=cache_only,
                limit=len(db.papers) if max_papers is None else max_papers,
            )
        cache = OpenAlexCache.load(cache_path)
        active = {paper.id for paper in db.papers}
        from src.observations import SignalStore

        signals = db._signal_stores.get("openalex", SignalStore(provider="openalex")).model_copy(
            deep=True
        )
        for key, observation in cache.signals.observations.items():
            if key not in active:
                continue
            previous = signals.observations.get(key)
            if previous:
                if (
                    previous.provider_id
                    and observation.provider_id
                    and normalize_openalex(previous.provider_id)
                    != normalize_openalex(observation.provider_id)
                ):
                    continue
                if previous.last_attempt_at and (
                    not observation.last_attempt_at
                    or previous.last_attempt_at > observation.last_attempt_at
                ):
                    continue
            signals.observations[key] = observation
        db._signal_stores["openalex"] = signals
        for index, paper in enumerate(db.papers):
            observation = signals.observations.get(paper.id)
            if observation is None or observation.fetched_at is None:
                continue
            if paper.openalex_id and normalize_openalex(paper.openalex_id) != normalize_openalex(
                observation.provider_id
            ):
                continue
            updates = {
                key: observation.values[key]
                for key in ("citation_count", "referenced_works")
                if key in observation.values
            }
            updates["openalex_id"] = observation.provider_id
            updated = paper.with_provider_updates(update=updates)
            _assign_provider_doi(updated, observation.values.get("doi"))
            db.papers[index] = updated
        stats = build_citation_knowledge_graph(db)
        return {**stats, "enriched_papers": report["ok"], "provider_refresh": report}

    # Split into papers with DOI/arXiv vs. seed papers needing title search
    papers_with_doi = [p for p in db.papers if p.arxiv_id or p.doi]
    papers_without_doi = [p for p in db.papers if not p.arxiv_id and not p.doi]

    if max_papers is not None:
        papers_with_doi = papers_with_doi[:max_papers]
        papers_without_doi = papers_without_doi[: max(0, max_papers - len(papers_with_doi))]

    total_enriched = 0

    # 1. Batch fetch papers with DOIs
    for i in range(0, len(papers_with_doi), batch_size):
        chunk = papers_with_doi[i : i + batch_size]
        batch_results = client.fetch_batch_by_doi(chunk)

        for p in chunk:
            data = batch_results.get(p.id)
            if data:
                p.citation_count = data["citation_count"]
                if data["openalex_id"]:
                    p.openalex_id = data["openalex_id"]
                if "referenced_works" in data and "referenced_works" not in p.protected_fields():
                    p.referenced_works = data["referenced_works"]
                _assign_provider_doi(p, data.get("doi"))
                total_enriched += 1

        time.sleep(0.1)

    # 2. Single fetch papers without DOIs (seed papers)
    for p in papers_without_doi:
        single_result = client.fetch_single_by_title(p)
        if single_result:
            p.citation_count = single_result["citation_count"]
            if single_result["openalex_id"]:
                p.openalex_id = single_result["openalex_id"]
            if (
                "referenced_works" in single_result
                and "referenced_works" not in p.protected_fields()
            ):
                p.referenced_works = single_result["referenced_works"]
            _assign_provider_doi(p, single_result.get("doi"))
            total_enriched += 1
        time.sleep(0.3)

    # 3. Construct knowledge graph
    graph_stats = build_citation_knowledge_graph(db)
    graph_stats["enriched_papers"] = total_enriched
    return graph_stats
