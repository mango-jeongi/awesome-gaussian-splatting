"""ArXiv Atom/XML API extractor for 3D/4D Gaussian Splatting literature."""

from __future__ import annotations

import re
import time
import urllib.parse
import xml.etree.ElementTree as ET

import httpx

from src.extractors.base import BaseExtractor
from src.schema import PaperRecord

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

DEFAULT_SEARCH_QUERY = (
    'all:"Gaussian Splatting" OR all:"3DGS" OR all:"4DGS" OR all:"2DGS" '
    'OR ti:"Gaussian Splat" OR abs:"3D Gaussian"'
)


class ArxivExtractor(BaseExtractor):
    """Queries the official arXiv export API and parses Atom XML feeds into PaperRecords."""

    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(
        self,
        search_query: str = DEFAULT_SEARCH_QUERY,
        timeout: float = 30.0,
        rate_limit_delay: float = 3.0,
    ) -> None:
        self.search_query = search_query
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay

    def fetch_recent(self, max_results: int = 50, start: int = 0) -> list[PaperRecord]:
        """Fetch recent 3DGS preprints sorted by submittedDate descending."""
        params = {
            "search_query": self.search_query,
            "start": str(start),
            "max_results": str(max_results),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        headers = {
            "User-Agent": "awesome-gaussian-splatting/0.1 (Academic Literature Crawler; https://github.com/mango-jeongi/awesome-gaussian-splatting)"
        }

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    resp = client.get(url, headers=headers)
                    resp.raise_for_status()
                    return self.parse_atom_xml(resp.text)
            except Exception as exc:
                last_err = exc
                if attempt < 2:
                    time.sleep(self.rate_limit_delay * (attempt + 1))

        raise RuntimeError(f"Failed to fetch from arXiv API after 3 attempts: {last_err}")

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
                continue

            raw_id = (id_elem.text or "").strip()
            # Skip empty error stub entries returned by arXiv API
            if "api/errors" in raw_id:
                continue

            arxiv_id = re.sub(r"^https?://arxiv\.org/abs/", "", raw_id)
            arxiv_id = re.sub(r"v\d+$", "", arxiv_id).strip()

            title = (title_elem.text or "").strip()
            abstract = (summary_elem.text or "").strip() if summary_elem is not None else ""

            authors: list[str] = []
            for author in entry.findall("atom:author", ATOM_NS):
                name_elem = author.find("atom:name", ATOM_NS)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            pub_raw = (published_elem.text or "").strip() if published_elem is not None else ""
            upd_raw = (updated_elem.text or "").strip() if updated_elem is not None else ""
            pub_date = pub_raw[:10] if len(pub_raw) >= 10 else "2024-01-01"
            upd_date = upd_raw[:10] if len(upd_raw) >= 10 else None

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
                    updated_date=upd_date,
                    abstract=abstract,
                    primary_arxiv_category=prim_cat,
                    comment=comment,
                )
            )

        return records
