"""Official CVF listing parser with explicit edition/track boundaries."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, ConfigDict, Field


class CVFListingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3)
    source_url: str
    venue: str
    year: int
    track: str
    authors: list[str] = Field(default_factory=list)


class _Listing(HTMLParser):
    def __init__(self, venue, year, track):
        super().__init__(convert_charrefs=True)
        self.venue, self.year, self.track = venue, year, track
        self.code = f"{venue}{year}" + ("W" if track == "workshop" else "")
        self.in_title = False
        self.in_link = False
        self.parts = []
        self.url = None
        self.current = None
        self.rows = []
        self.title_nodes = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "dt" and "ptitle" in attributes.get("class", "").split():
            if self.in_title:
                raise ValueError("Nested CVF title")
            self.in_title = True
            self.title_nodes += 1
            self.parts = []
            self.url = None
        if self.in_title and tag == "a":
            if self.url is not None:
                raise ValueError("Multiple CVF paper title links")
            url = urljoin("https://openaccess.thecvf.com/", attributes.get("href", ""))
            parsed = urlparse(url)
            if (
                parsed.scheme != "https"
                or parsed.netloc != "openaccess.thecvf.com"
                or not parsed.path.startswith(f"/content/{self.code}/html/")
                or not parsed.path.endswith(".html")
            ):
                raise ValueError("CVF paper is outside requested edition/track")
            self.url = url
            self.in_link = True
        if tag == "input" and self.current and attributes.get("name") == "query_author":
            name = attributes.get("value", "").strip()
            if name:
                self.current.authors.append(name)

    def handle_data(self, data):
        if self.in_title and self.in_link:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a":
            self.in_link = False
        if tag == "dt" and self.in_title:
            if not self.url:
                raise ValueError("Missing CVF paper title URL")
            self.current = CVFListingEntry(
                title=" ".join("".join(self.parts).split()),
                source_url=self.url,
                venue=self.venue,
                year=self.year,
                track=self.track,
            )
            self.rows.append(self.current)
            self.in_title = False


def parse_listing(html, *, venue, year, track="main"):
    if (
        venue not in ("CVPR", "ICCV")
        or track not in ("main", "workshop")
        or not 2020 <= year <= 2026
    ):
        raise ValueError("Unsupported CVF inventory boundary")
    parser = _Listing(venue, year, track)
    parser.feed(html)
    parser.close()
    if parser.in_title or not parser.rows or parser.title_nodes != len(parser.rows):
        raise ValueError("Incomplete CVF listing")
    if len({row.source_url for row in parser.rows}) != len(parser.rows):
        raise ValueError("Duplicate CVF paper URL")
    if any(not row.authors for row in parser.rows):
        raise ValueError("CVF listing author inventory missing")
    return parser.rows


class CVFPublication(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    authors: list[str]
    abstract: str | None = None
    source_url: str
    venue: str
    venue_year: int
    track: str
    pdf_url: str
    arxiv_id: str | None = None
    doi: str | None = None
    match_method: str = "official_listing_and_citation_metadata"
    status: str = "official_publication_metadata_verified"


class _PaperMetadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metadata = {}
        self.links = []
        self.abstract_depth = 0
        self.abstract_parts = []
        self.abstract_count = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "div":
            if attributes.get("id") == "abstract":
                self.abstract_count += 1
                if self.abstract_count > 1:
                    raise ValueError("Duplicate CVF abstract")
            if self.abstract_depth:
                self.abstract_depth += 1
            elif attributes.get("id") == "abstract":
                self.abstract_depth = 1
        if tag == "meta" and attributes.get("name", "").startswith("citation_"):
            self.metadata.setdefault(attributes["name"], []).append(attributes.get("content", ""))
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])

    def handle_data(self, data):
        if self.abstract_depth:
            self.abstract_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "div" and self.abstract_depth:
            self.abstract_depth -= 1


def parse_publication(html, listing: CVFListingEntry):
    import re

    from src.identity import normalize_arxiv, normalize_doi

    source = urlparse(listing.source_url)
    edition = f"{listing.venue}{listing.year}" + ("W" if listing.track == "workshop" else "")
    if (
        source.scheme != "https"
        or source.netloc != "openaccess.thecvf.com"
        or not source.path.startswith(f"/content/{edition}/html/")
    ):
        raise ValueError("Publication source outside official CVF edition")
    parser = _PaperMetadata()
    parser.feed(html)
    parser.close()
    if parser.abstract_depth:
        raise ValueError("Incomplete CVF abstract")
    metadata = parser.metadata

    def singleton(key):
        values = metadata.get(key, [])
        if len(values) != 1 or not values[0].strip():
            raise ValueError("Missing/duplicate CVF citation metadata: " + key)
        return values[0].strip()

    title = singleton("citation_title")

    def normalize(value):
        return re.sub(r"\W+", "", value.casefold())

    if normalize(title) != normalize(listing.title):
        raise ValueError("CVF listing/paper title mismatch")
    year = singleton("citation_publication_date")
    if not re.fullmatch(r"\d{4}", year) or int(year) != listing.year:
        raise ValueError("CVF publication year mismatch")
    conference = singleton("citation_conference_title")
    expected = (
        "Computer Vision and Pattern Recognition"
        if listing.venue == "CVPR"
        else "International Conference on Computer Vision"
    )
    if expected.casefold() not in conference.casefold() or (
        "workshop" in conference.casefold()
    ) != (listing.track == "workshop"):
        raise ValueError("CVF conference/track mismatch")
    authors = []
    for value in metadata.get("citation_author", []):
        if "," in value:
            last, first = value.split(",", 1)
            value = first.strip() + " " + last.strip()
        authors.append(value.strip())
    if not authors or [normalize(value) for value in authors] != [
        normalize(value) for value in listing.authors
    ]:
        raise ValueError("CVF author inventory mismatch")
    pdf = singleton("citation_pdf_url")
    parsed = urlparse(pdf)
    code = f"{listing.venue}{listing.year}" + ("W" if listing.track == "workshop" else "")
    if (
        parsed.scheme != "https"
        or parsed.netloc != "openaccess.thecvf.com"
        or not parsed.path.startswith(f"/content/{code}/papers/")
    ):
        raise ValueError("CVF PDF outside edition/track")
    expected_pdf = source.path.replace("/html/", "/papers/").removesuffix(".html") + ".pdf"
    if parsed.path != expected_pdf:
        raise ValueError("CVF PDF does not match source paper page")
    arxiv = {
        normalize_arxiv(url)
        for url in parser.links
        if re.match(r"^https?://(?:export\.)?arxiv\.org/abs/", url, re.I)
    }
    if len(arxiv) > 1:
        raise ValueError("Conflicting arXiv links on CVF page")
    dois = metadata.get("citation_doi", [])
    if len(dois) > 1:
        raise ValueError("Conflicting CVF DOI metadata")
    return CVFPublication(
        title=title,
        authors=authors,
        abstract=" ".join(" ".join(parser.abstract_parts).split()) or None,
        source_url=listing.source_url,
        venue=listing.venue,
        venue_year=listing.year,
        track=listing.track,
        pdf_url=pdf,
        arxiv_id=next(iter(arxiv), None),
        doi=normalize_doi(dois[0]) if dois else None,
    )


def publication_candidate(publication: CVFPublication, *, observed_at):
    """Keep edition year separate; a new record has only year-level source dating."""
    from src.contracts import FieldEvidence
    from src.schema import PaperRecord

    if observed_at.utcoffset() is None:
        raise ValueError("CVF capture time requires timezone")
    venue = (
        publication.venue
        + " "
        + str(publication.venue_year)
        + (" Workshops" if publication.track == "workshop" else "")
    )
    evidence = {
        "venue": [
            FieldEvidence(
                source="cvf_official_proceedings",
                source_url=publication.source_url,
                value=venue,
                observed_at=observed_at,
            )
        ],
        "publication_year": [
            FieldEvidence(
                source="cvf_official_proceedings",
                source_url=publication.source_url,
                value=publication.venue_year,
                observed_at=observed_at,
            )
        ],
    }
    if publication.abstract:
        evidence["abstract"] = [
            FieldEvidence(
                source="cvf_official_proceedings",
                source_url=publication.source_url,
                value=publication.abstract,
                observed_at=observed_at,
            )
        ]
    if publication.arxiv_id:
        evidence["arxiv_id"] = [
            FieldEvidence(
                source="cvf_official_proceedings",
                source_url=publication.source_url,
                value=publication.arxiv_id,
                observed_at=observed_at,
            )
        ]
    return PaperRecord(
        id="cvf:" + publication.source_url.rsplit("/", 1)[-1].removesuffix(".html"),
        arxiv_id=publication.arxiv_id,
        doi=publication.doi,
        source="cvf",
        title=publication.title,
        abstract=publication.abstract or "",
        authors=publication.authors,
        published_date=f"{publication.venue_year}-01-01",
        published_date_precision="year",
        date_placement="year_start",
        publication_year=publication.venue_year,
        publication_date_precision="year",
        venue=venue,
        paper_url=publication.source_url,
        pdf_url=publication.pdf_url,
        metadata_evidence=evidence,
    )
