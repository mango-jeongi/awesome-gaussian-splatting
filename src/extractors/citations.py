"""OpenAlex Citation Intelligence & Cross-Paper Knowledge Graph Builder (Phase 3)."""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.parse
import urllib.request
from typing import Any

from src.schema import PaperDatabase, PaperRecord

logger = logging.getLogger(__name__)

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
DEFAULT_USER_AGENT = (
    "AwesomeGaussianSplatting/1.0 (https://github.com/mango-jeongi/awesome-gaussian-splatting; "
    "mailto:academic-research@nps.edu)"
)


def _norm_str(s: str) -> str:
    return re.sub(r"[^\w\s]", "", s.lower()).strip()


def _is_title_similar(t1: str, t2: str) -> bool:
    n1 = _norm_str(t1)
    n2 = _norm_str(t2)
    if not n1 or not n2:
        return False
    return (
        n1 in n2
        or n2 in n1
        or (len(set(n1.split()) & set(n2.split())) / max(len(n1.split()), 1) > 0.6)
    )


class OpenAlexCitationClient:
    """Client for querying citation metrics and reference networks from OpenAlex."""

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout: float = 10.0) -> None:
        self.user_agent = user_agent
        self.timeout = timeout

    def _make_request(self, url: str) -> dict[str, Any] | None:
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
                    return data
            except urllib.error.HTTPError as err:
                if err.code == 429 and attempt == 0:
                    time.sleep(1.5)
                    continue
                logger.warning("OpenAlex HTTP error %s for %s", err.code, url)
                return None
            except Exception as exc:
                logger.warning("OpenAlex request failed for %s: %s", url, exc)
                return None
        return None

    def fetch_batch_by_doi(self, papers: list[PaperRecord]) -> dict[str, dict[str, Any]]:
        """Fetch citation count and referenced works for a batch of papers via DOI filter.

        Returns a mapping of paper_id -> {citation_count, openalex_id, referenced_works, doi}.
        """
        results: dict[str, dict[str, Any]] = {}
        doi_to_paper_id: dict[str, str] = {}

        for p in papers:
            if p.arxiv_id:
                canonical_doi = f"10.48550/arxiv.{p.arxiv_id.lower()}"
                doi_to_paper_id[canonical_doi] = p.id
            elif p.doi:
                norm_doi = p.doi.lower().strip().replace("https://doi.org/", "")
                doi_to_paper_id[norm_doi] = p.id

        if not doi_to_paper_id:
            return results

        filter_dois = "|".join(doi_to_paper_id.keys())
        query_params = urllib.parse.urlencode({"filter": f"doi:{filter_dois}", "per-page": "50"})
        url = f"{OPENALEX_WORKS_URL}?{query_params}"

        payload = self._make_request(url)
        if not payload:
            return results

        for work in payload.get("results", []):
            work_doi = (work.get("doi") or "").lower().replace("https://doi.org/", "").strip()
            paper_id = doi_to_paper_id.get(work_doi)

            if not paper_id:
                for d, pid in doi_to_paper_id.items():
                    if d in work_doi:
                        paper_id = pid
                        break

            if paper_id:
                results[paper_id] = {
                    "citation_count": int(work.get("cited_by_count", 0)),
                    "openalex_id": work.get("id"),
                    "referenced_works": work.get("referenced_works", []),
                    "doi": work_doi or None,
                }

        return results

    def fetch_single_by_title(self, paper: PaperRecord) -> dict[str, Any] | None:
        """Fallback lookup by paper title when no DOI or arXiv ID is present."""
        clean_title = re.sub(r"[^\w\s]", " ", paper.title).strip()
        query_params = urllib.parse.urlencode(
            {"filter": f"title.search:{clean_title}", "per-page": "1"}
        )
        url = f"{OPENALEX_WORKS_URL}?{query_params}"

        payload = self._make_request(url)
        if not payload:
            return None

        results = payload.get("results", [])
        if not results:
            return None

        work = results[0]
        work_title = work.get("title") or ""
        if not _is_title_similar(paper.title, work_title):
            return None

        work_doi = (work.get("doi") or "").lower().replace("https://doi.org/", "").strip()
        return {
            "citation_count": int(work.get("cited_by_count", 0)),
            "openalex_id": work.get("id"),
            "referenced_works": work.get("referenced_works", []),
            "doi": work_doi or None,
        }


def build_citation_knowledge_graph(db: PaperDatabase) -> dict[str, int]:
    """Construct internal directed citation and reference edges across papers in the database.

    Populates:
    - `p.db_references`: list of paper IDs in this database cited by `p`.
    - `p.db_citations`: list of paper IDs in this database that cite `p`.
    - `p.db_citation_count`: number of incoming citations from within this database.
    """
    openalex_map: dict[str, str] = {}
    doi_map: dict[str, str] = {}
    arxiv_map: dict[str, str] = {}

    for p in db.papers:
        if p.openalex_id:
            openalex_map[p.openalex_id] = p.id
            short_id = p.openalex_id.rstrip("/").split("/")[-1]
            openalex_map[short_id] = p.id

        if p.arxiv_id:
            arxiv_map[p.arxiv_id.lower()] = p.id
            doi_map[f"10.48550/arxiv.{p.arxiv_id.lower()}"] = p.id
        if p.doi:
            doi_map[p.doi.lower().strip().replace("https://doi.org/", "")] = p.id

    # Reset internal edges
    for p in db.papers:
        p.db_references = []
        p.db_citations = []
        p.db_citation_count = 0

    total_edges = 0
    for p in db.papers:
        for ref in p.referenced_works:
            target_id = openalex_map.get(ref)
            if not target_id:
                short_ref = ref.rstrip("/").split("/")[-1]
                target_id = openalex_map.get(short_ref)

            if target_id and target_id != p.id and target_id not in p.db_references:
                p.db_references.append(target_id)
                total_edges += 1

    # Invert outgoing references to populate incoming citations
    for p in db.papers:
        for target_id in p.db_references:
            target_paper = db.get(target_id)
            if target_paper and p.id not in target_paper.db_citations:
                target_paper.db_citations.append(p.id)

    # Compute incoming counts and count connected nodes
    connected_papers = 0
    for p in db.papers:
        p.db_citation_count = len(p.db_citations)
        if p.db_citation_count > 0 or len(p.db_references) > 0:
            connected_papers += 1

    return {
        "total_nodes": len(db.papers),
        "total_edges": total_edges,
        "connected_papers": connected_papers,
    }


def enrich_database_citations(
    db: PaperDatabase,
    batch_size: int = 40,
    max_papers: int | None = None,
    client: OpenAlexCitationClient | None = None,
) -> dict[str, int]:
    """Fetch global citation metrics from OpenAlex and build internal knowledge graph."""
    client = client or OpenAlexCitationClient()

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
                if data["referenced_works"]:
                    p.referenced_works = data["referenced_works"]
                if not p.doi and data.get("doi"):
                    p.doi = data["doi"]
                total_enriched += 1

        time.sleep(0.1)

    # 2. Single fetch papers without DOIs (seed papers)
    for p in papers_without_doi:
        single_result = client.fetch_single_by_title(p)
        if single_result:
            p.citation_count = single_result["citation_count"]
            if single_result["openalex_id"]:
                p.openalex_id = single_result["openalex_id"]
            if single_result["referenced_works"]:
                p.referenced_works = single_result["referenced_works"]
            if not p.doi and single_result.get("doi"):
                p.doi = single_result["doi"]
            total_enriched += 1
        time.sleep(0.3)

    # 3. Construct knowledge graph
    graph_stats = build_citation_knowledge_graph(db)
    graph_stats["enriched_papers"] = total_enriched
    return graph_stats
