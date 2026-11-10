"""ArXiv Atom/XML API extractor for 3D/4D Gaussian Splatting literature."""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Literal

import httpx

from src.contracts import FieldEvidence
from src.extractors.arxiv_gate import ArxivRateDeferred, ArxivRateGate
from src.extractors.base import BaseExtractor
from src.identity import normalize_arxiv
from src.schema import PaperRecord

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}

DEFAULT_SEARCH_QUERY = (
    'all:"Gaussian Splatting" OR all:"3DGS" OR all:"4DGS" OR all:"2DGS" '
    'OR ti:"Gaussian Splat" OR abs:"3D Gaussian"'
)


class ArxivRequestFailure(RuntimeError):
    def __init__(self, message: str, attempts: int):
        self.attempts = attempts
        super().__init__(message)


class ArxivIntegrityError(ValueError):
    """A source page cannot establish complete interval accounting."""


@dataclass(frozen=True)
class ArxivPage:
    records: tuple[PaperRecord, ...]
    total: int
    start: int
    published_at: dict[str, datetime]
    updated_at: dict[str, datetime]
    attempts: int = 1


def parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value)
    if timestamp.utcoffset() is None:
        raise ValueError("arXiv source timestamps require a timezone")
    return timestamp.astimezone(UTC)


class ArxivExtractor(BaseExtractor):
    """Queries the official arXiv export API and parses Atom XML feeds into PaperRecords."""

    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(
        self,
        search_query: str = DEFAULT_SEARCH_QUERY,
        timeout: float = 30.0,
        rate_limit_delay: float = 3.0,
        gate: ArxivRateGate | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.search_query = search_query
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.gate = gate or ArxivRateGate(interval=rate_limit_delay)
        self.transport = transport

    def fetch_recent(self, max_results: int = 50, start: int = 0) -> list[PaperRecord]:
        """Compatibility single page; complete runs use fetch_page with a ledger."""
        return list(self.fetch_page(start=start, page_size=max_results).records)

    def fetch_ids(self, identifiers: list[str], *, max_attempts: int = 3) -> dict[str, PaperRecord]:
        if (
            not identifiers
            or len(identifiers) > 40
            or any(not isinstance(value, str) for value in identifiers)
        ):
            raise ValueError("Expected1..40 arXiv identifiers")
        normalized = sorted({normalize_arxiv(value) for value in identifiers})
        if any(
            not value or not re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z]{2})?/\d{7})", value)
            for value in normalized
        ):
            raise ValueError("Invalid arXiv lookup identity")
        page = self.fetch_page(
            page_size=len(normalized), max_attempts=max_attempts, _ids=tuple(normalized)
        )
        by_id = {record.arxiv_id: record for record in page.records}
        if set(by_id) != set(normalized) or page.total != len(normalized):
            raise ArxivIntegrityError("Incomplete or contradictory arXiv identifier lookup")
        return by_id

    def fetch_page(
        self,
        *,
        query: str | None = None,
        start: int = 0,
        page_size: int = 100,
        sort_by: Literal["submittedDate", "lastUpdatedDate"] = "submittedDate",
        sort_order: Literal["ascending", "descending"] = "descending",
        max_attempts: int = 3,
        _ids: tuple[str, ...] | None = None,
    ) -> ArxivPage:
        if (
            type(start) is not int
            or start < 0
            or type(page_size) is not int
            or not 1 <= page_size <= 1000
        ):
            raise ValueError("Invalid arXiv page bounds")
        if sort_by not in ("submittedDate", "lastUpdatedDate") or sort_order not in (
            "ascending",
            "descending",
        ):
            raise ValueError("Invalid arXiv ordering")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
            raise ValueError("Invalid arXiv attempt budget")
        params = {
            "search_query": query or self.search_query,
            "start": str(start),
            "max_results": str(page_size),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        if _ids is not None:
            params.pop("search_query", None)
            params["id_list"] = ",".join(_ids)
        headers = {
            "User-Agent": "awesome-gaussian-splatting/0.1 (https://github.com/mango-jeongi/awesome-gaussian-splatting)"
        }
        for attempt in range(1, max_attempts + 1):
            try:
                with (
                    self.gate.connection(),
                    httpx.Client(
                        timeout=self.timeout, follow_redirects=False, transport=self.transport
                    ) as client,
                ):
                    response = client.get(self.BASE_URL, params=params, headers=headers)
                    response.raise_for_status()
                try:
                    return self.parse_page(
                        response.text, requested_start=start, page_size=page_size, attempts=attempt
                    )
                except (ValueError, ET.ParseError) as error:
                    error.attempts = attempt
                    raise
            except httpx.HTTPStatusError as error:
                status = error.response.status_code
                if status not in (429, 500, 502, 503, 504):
                    raise ArxivRequestFailure(
                        f"arXiv HTTP {status}; attempts={attempt}", attempt
                    ) from None
                retry_after = error.response.headers.get("Retry-After")
                try:
                    if retry_after is None:
                        requested = 0.0
                    else:
                        try:
                            requested = float(retry_after)
                        except ValueError:
                            requested = (
                                parsedate_to_datetime(retry_after).timestamp() - self.gate.clock()
                            )
                    if not math.isfinite(requested):
                        raise ValueError("Non-finite retry header")
                    delay = max(self.rate_limit_delay * attempt, requested)
                except (ValueError, TypeError, OverflowError):
                    self.gate.defer(60)
                    raise ArxivRequestFailure(
                        "Malformed arXiv retry header; request deferred", attempt
                    ) from None
                self.gate.defer(delay)
                if delay > 60:
                    deferred = ArxivRateDeferred(delay)
                    deferred.attempts = attempt
                    raise deferred from None
                if attempt == max_attempts:
                    raise ArxivRequestFailure(
                        f"arXiv HTTP {status}; attempts={attempt}", attempt
                    ) from None
            except httpx.TransportError:
                if attempt == max_attempts:
                    raise ArxivRequestFailure(
                        f"arXiv transport failure; attempts={attempt}", attempt
                    ) from None
                self.gate.defer(self.rate_limit_delay * attempt)
        raise RuntimeError("Unreachable arXiv request state")

    @classmethod
    def parse_page(
        cls, xml_text: str, *, requested_start: int, page_size: int, attempts: int = 1
    ) -> ArxivPage:
        root = ET.fromstring(xml_text)
        if root.tag != f"{{{ATOM_NS['atom']}}}feed":
            raise ArxivIntegrityError("Unexpected arXiv response root")
        records = cls.parse_atom_xml(xml_text)
        try:
            total = int(root.findtext("opensearch:totalResults", namespaces=ATOM_NS))
            start = int(root.findtext("opensearch:startIndex", namespaces=ATOM_NS))
            declared_size = int(root.findtext("opensearch:itemsPerPage", namespaces=ATOM_NS))
        except (TypeError, ValueError):
            raise ArxivIntegrityError("Missing/malformed arXiv paging metadata") from None
        if total < 0 or start != requested_start or not 0 <= declared_size <= page_size:
            raise ArxivIntegrityError("arXiv paging metadata disagrees with request")
        expected = min(page_size, max(0, total - start))
        if len(records) != expected or len(records) > declared_size:
            raise ArxivIntegrityError("Short/oversized arXiv page inconsistent with source total")
        published, updated = {}, {}
        for entry in root.findall("atom:entry", ATOM_NS):
            identifier = normalize_arxiv(entry.findtext("atom:id", namespaces=ATOM_NS))
            if identifier in published:
                raise ArxivIntegrityError("Repeated identifier within arXiv page")
            try:
                published[identifier] = parse_timestamp(
                    entry.findtext("atom:published", namespaces=ATOM_NS) or ""
                )
                updated[identifier] = parse_timestamp(
                    entry.findtext("atom:updated", namespaces=ATOM_NS) or ""
                )
            except ValueError:
                raise ArxivIntegrityError("Missing/malformed source timestamp") from None
        return ArxivPage(tuple(records), total, start, published, updated, attempts)

    @classmethod
    def parse_atom_xml(cls, xml_text: str) -> list[PaperRecord]:
        """Parse an arXiv Atom XML response string into validated PaperRecord instances."""
        root = ET.fromstring(xml_text)
        records: list[PaperRecord] = []

        for entry in root.findall("atom:entry", ATOM_NS):
            id_elem = entry.find("atom:id", ATOM_NS)
            title_elem = entry.find("atom:title", ATOM_NS)
            summary_elem = entry.find("atom:summary", ATOM_NS)
            published_elem = entry.find("atom:published", ATOM_NS)
            updated_elem = entry.find("atom:updated", ATOM_NS)

            if id_elem is None or title_elem is None or not (title_elem.text or "").strip():
                raise ValueError("Malformed arXiv entry: missing identifier or title")

            raw_id = (id_elem.text or "").strip()
            if "api/errors" in raw_id:
                raise ValueError("arXiv returned an API error entry")

            arxiv_id = normalize_arxiv(raw_id)
            if not arxiv_id or not re.fullmatch(
                r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z]{2})?/\d{7})", arxiv_id
            ):
                raise ValueError("Malformed arXiv identifier")

            title = (title_elem.text or "").strip()
            abstract = (summary_elem.text or "").strip() if summary_elem is not None else ""

            authors: list[str] = []
            for author in entry.findall("atom:author", ATOM_NS):
                name_elem = author.find("atom:name", ATOM_NS)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            pub_raw = (published_elem.text or "").strip() if published_elem is not None else ""
            upd_raw = (updated_elem.text or "").strip() if updated_elem is not None else ""
            if not pub_raw:
                raise ValueError("arXiv entry lacks original publication time")

            pub_date = parse_timestamp(pub_raw).date().isoformat()
            upd_date = parse_timestamp(upd_raw).date().isoformat() if upd_raw else None

            comment_elem = entry.find("arxiv:comment", ATOM_NS)
            comment = (comment_elem.text or "").strip() if comment_elem is not None else None

            doi_elem = entry.find("arxiv:doi", ATOM_NS)
            doi = (doi_elem.text or "").strip() if doi_elem is not None else None

            prim_cat_elem = entry.find("arxiv:primary_category", ATOM_NS)
            prim_cat = prim_cat_elem.attrib.get("term") if prim_cat_elem is not None else None

            records.append(
                PaperRecord(
                    id=arxiv_id,
                    arxiv_id=arxiv_id,
                    doi=doi,
                    source="arxiv",
                    title=title,
                    authors=authors or ["Unknown"],
                    published_date=pub_date,
                    published_date_precision="day",
                    arxiv_doi=f"10.48550/arxiv.{arxiv_id}",
                    metadata_evidence={
                        "published_date": [
                            FieldEvidence(source="arxiv", source_url=raw_id, value=pub_date)
                        ]
                    },
                    updated_date=upd_date,
                    abstract=abstract,
                    primary_arxiv_category=prim_cat,
                    comment=comment,
                )
            )

        return records
