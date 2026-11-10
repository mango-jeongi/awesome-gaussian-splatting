"""Publication-location candidates; repository hosting never proves peer review."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.extractors.openalex import OpenAlexWork
from src.identity import normalize_arxiv, normalize_doi, normalize_openalex
from src.schema import PaperRecord


class VenueCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper_id: str
    provider: str = "openalex"
    provider_id: str
    source_id: str
    source_url: str
    venue: str
    source_type: str
    match_method: str
    confidence: str = "provider_publication_location_pending_official_verification"
    reported_work_year: int | None = None
    venue_year: int | None = None
    status: str = "provisional"


def publication_locations(paper: PaperRecord, work: OpenAlexWork) -> list[VenueCandidate]:
    dois = {normalize_doi(paper.doi), normalize_doi(paper.arxiv_doi)} - {None}
    if paper.arxiv_id:
        dois.add("10.48550/arxiv." + normalize_arxiv(paper.arxiv_id))
    if not (dois & work.doi_aliases()):
        return []
    if paper.openalex_id and normalize_openalex(paper.openalex_id) != normalize_openalex(work.id):
        return []
    result = []
    seen = set()
    for location in work.locations:
        source = location.get("source") or {}
        if (
            source.get("type") not in ("journal", "conference")
            or location.get("is_published") is not True
        ):
            continue
        url = location.get("landing_page_url")
        source_id = source.get("id")
        name = source.get("display_name")
        if (
            not isinstance(url, str)
            or not url.startswith(("https://", "http://"))
            or not source_id
            or not name
        ):
            continue
        key = (source_id, url)
        if key in seen:
            continue
        seen.add(key)
        result.append(
            VenueCandidate(
                paper_id=paper.id,
                provider_id=work.id,
                source_id=source_id,
                source_url=url,
                venue=name,
                source_type=source["type"],
                match_method="exact_identifier_with_published_location",
                reported_work_year=work.publication_year,
            )
        )
    return result
