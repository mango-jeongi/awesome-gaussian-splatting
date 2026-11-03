"""Pydantic v2 Schema-on-Read models for the 3DGS One Big Table (OBT)."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

PaperSource = Literal["arxiv", "ieee", "cvf", "acm", "manual", "huggingface"]


class CategoryRule(BaseModel):
    """Declarative domain category definition loaded from config/taxonomy.yaml."""

    name: str
    slug: str
    description: str
    keywords: list[str] = Field(default_factory=list)


class TaxonomyConfig(BaseModel):
    """Root configuration model for domain categories and technical tag rules."""

    default_category: str = "Foundations & Acceleration"
    emergent_tag_min_count: int = 2
    categories: list[CategoryRule] = Field(default_factory=list)
    technical_tags: dict[str, list[str]] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> TaxonomyConfig:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls.model_validate(raw)


class PaperRecord(BaseModel):
    """Canonical One Big Table (OBT) schema for a research paper record.

    Designed for Schema-on-Read resilience across both arXiv preprints and
    non-arXiv publications (IEEE, CVF, ACM, manual curations).
    """

    id: str = Field(
        default="",
        description="Canonical unique identifier (arXiv ID if available, else DOI or deterministic title hash).",
    )
    arxiv_id: str | None = Field(
        default=None,
        description="Clean versionless arXiv identifier (e.g., '2308.04079') if sourced from arXiv.",
    )
    doi: str | None = Field(
        default=None,
        description="Digital Object Identifier if published in a peer-reviewed venue.",
    )
    source: PaperSource = Field(
        default="arxiv",
        description="Primary ingestion source discriminator.",
    )
    title: str = Field(..., min_length=3, description="Sanitized paper title.")
    authors: list[str] = Field(
        default_factory=lambda: ["Unknown"],
        description="Ordered list of author names.",
    )
    first_author: str = Field(
        default="Unknown",
        description="Formatted primary author display string (e.g., 'Kerbl et al.').",
    )
    published_date: str = Field(
        default="",
        description="ISO 8601 publication date (YYYY-MM-DD).",
    )
    updated_date: str | None = Field(
        default=None,
        description="ISO 8601 last-updated date (YYYY-MM-DD).",
    )
    year: int = Field(default=2024, ge=1990, le=2100)
    month: int = Field(default=1, ge=1, le=12)
    venue: str | None = Field(
        default=None,
        description="Conference or journal venue (e.g., 'SIGGRAPH 2023', 'CVPR 2025').",
    )

    # Action URLs
    paper_url: str = Field(
        default="",
        description="Primary landing page URL (arXiv abs URL, DOI link, or publisher page).",
    )
    pdf_url: str | None = Field(
        default=None,
        description="Direct PDF link if available.",
    )
    code_url: str | None = Field(
        default=None,
        description="Official GitHub/GitLab code repository URL.",
    )
    project_url: str | None = Field(
        default=None,
        description="Interactive project webpage URL (e.g., *.github.io).",
    )

    # Content & Enrichment
    abstract: str = Field(default="", description="Full abstract text.")
    tldr: str = Field(
        default="",
        description="Concise 1-2 sentence technical takeaway.",
    )
    primary_category: str = Field(
        default="Foundations & Acceleration",
        description="Primary 3DGS taxonomy category.",
    )
    categories: list[str] = Field(
        default_factory=lambda: ["Foundations & Acceleration"],
        description="All assigned 3DGS taxonomy categories.",
    )
    tags: list[str] = Field(
        default_factory=lambda: ["3DGS"],
        description="Canonical and emergent technical tags for filtering.",
    )
    primary_arxiv_category: str | None = Field(
        default=None,
        description="Original arXiv category code (e.g., 'cs.CV', 'cs.GR').",
    )
    comment: str | None = Field(
        default=None,
        description="Raw author comment field from arXiv.",
    )

    @field_validator("title", "abstract", "tldr", mode="before")
    @classmethod
    def clean_whitespace(cls, v: object) -> str:
        if v is None:
            return ""
        text = str(v).replace("\n", " ").replace("\r", " ")
        return re.sub(r"\s+", " ", text).strip()

    @field_validator("arxiv_id", mode="before")
    @classmethod
    def normalize_arxiv_id(cls, v: object) -> str | None:
        if not v:
            return None
        s = str(v).strip()
        s = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", s)
        s = re.sub(r"\.pdf$", "", s)
        s = re.sub(r"v\d+$", "", s)
        return s or None

    @model_validator(mode="after")
    def populate_derived_fields(self) -> PaperRecord:
        # Derive canonical ID if missing
        if not self.id:
            if self.arxiv_id:
                self.id = self.arxiv_id
            elif self.doi:
                self.id = f"doi:{self.doi.lower().strip()}"
            else:
                norm_title = re.sub(r"[^a-z0-9]+", "", self.title.lower())
                digest = hashlib.sha1(norm_title.encode("utf-8")).hexdigest()[:10]
                self.id = f"paper:{self.year}-{digest}"

        # Derive URLs for arXiv records if missing
        if self.arxiv_id:
            if not self.paper_url:
                self.paper_url = f"https://arxiv.org/abs/{self.arxiv_id}"
            if not self.pdf_url:
                self.pdf_url = f"https://arxiv.org/pdf/{self.arxiv_id}.pdf"

        # Derive first_author display string
        if not self.authors:
            self.authors = ["Unknown"]
        if not self.first_author or self.first_author == "Unknown":
            lead = self.authors[0].strip()
            if "et al" in lead.lower():
                self.first_author = lead
            else:
                last_name = lead.split()[-1] if lead else "Unknown"
                self.first_author = f"{last_name} et al." if len(self.authors) > 1 else last_name

        # Ensure published_date aligns with year/month
        if self.published_date and re.match(r"^\d{4}-\d{2}-\d{2}$", self.published_date):
            self.year = int(self.published_date[:4])
            self.month = int(self.published_date[5:7])
        else:
            self.published_date = f"{self.year:04d}-{self.month:02d}-01"

        # Ensure categories & tags are deduplicated and non-empty
        if not self.categories:
            self.categories = [self.primary_category]
        else:
            seen_cats: list[str] = []
            for c in self.categories:
                if c and c not in seen_cats:
                    seen_cats.append(c)
            self.categories = seen_cats or [self.primary_category]
            self.primary_category = self.categories[0]

        seen_tags: list[str] = []
        for t in self.tags:
            clean_t = t.strip()
            if clean_t and clean_t not in seen_tags:
                seen_tags.append(clean_t)
        self.tags = seen_tags or ["3DGS"]

        # Fallback TL;DR from first sentence of abstract
        if not self.tldr and self.abstract:
            first_sent = re.split(r"(?<=[.!?])\s+", self.abstract)[0]
            self.tldr = first_sent[:240] + ("..." if len(first_sent) > 240 else "")

        return self

    def to_bibtex(self) -> str:
        """Generate a clean BibTeX citation entry for this paper."""
        first_word = (
            re.sub(r"[^a-zA-Z0-9]", "", self.title.split()[0].lower()) if self.title else "paper"
        )
        author_slug = re.sub(r"[^a-zA-Z0-9]", "", self.first_author.split()[0].lower())
        cite_key = f"{author_slug}{self.year}{first_word}"
        author_bibtex = " and ".join(self.authors)
        venue_str = self.venue or (
            f"arXiv preprint arXiv:{self.arxiv_id}" if self.arxiv_id else "Preprint"
        )
        lines = [
            f"@article{{{cite_key},",
            f"  title={{{self.title}}},",
            f"  author={{{author_bibtex}}},",
            f"  journal={{{venue_str}}},",
            f"  year={{{self.year}}},",
        ]
        if self.paper_url:
            lines.append(f"  url={{{self.paper_url}}},")
        lines.append("}")
        return "\n".join(lines)


class PaperDatabase(BaseModel):
    """Top-level container for `data/papers.json` One Big Table."""

    schema_version: str = "1.0.0"
    last_updated: str = Field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    total_count: int = 0
    papers: list[PaperRecord] = Field(default_factory=list)

    def upsert(self, records: list[PaperRecord]) -> int:
        """Idempotently upsert records by canonical ID or normalized title, returning number of new records added."""
        by_id: dict[str, PaperRecord] = {p.id: p for p in self.papers}
        by_norm_title: dict[str, str] = {
            re.sub(r"[^a-z0-9]+", "", p.title.lower()): p.id for p in self.papers
        }
        added = 0
        for rec in records:
            norm_t = re.sub(r"[^a-z0-9]+", "", rec.title.lower())
            existing_id = rec.id if rec.id in by_id else by_norm_title.get(norm_t)
            if existing_id and existing_id in by_id:
                existing = by_id[existing_id]
                # Prefer record with arxiv_id or richer metadata
                merged = existing.model_copy(
                    update={
                        "arxiv_id": rec.arxiv_id or existing.arxiv_id,
                        "doi": rec.doi or existing.doi,
                        "venue": rec.venue or existing.venue,
                        "code_url": rec.code_url or existing.code_url,
                        "project_url": rec.project_url or existing.project_url,
                        "pdf_url": rec.pdf_url or existing.pdf_url,
                        "paper_url": rec.paper_url or existing.paper_url,
                        "abstract": rec.abstract
                        if len(rec.abstract) > len(existing.abstract)
                        else existing.abstract,
                        "tldr": rec.tldr or existing.tldr,
                        "categories": list(dict.fromkeys(rec.categories + existing.categories)),
                        "tags": list(dict.fromkeys(rec.tags + existing.tags)),
                    }
                )
                by_id[existing_id] = PaperRecord.model_validate(merged.model_dump())
            else:
                by_id[rec.id] = rec
                by_norm_title[norm_t] = rec.id
                added += 1

        # Sort newest first, then alphabetically by title
        self.papers = sorted(
            by_id.values(),
            key=lambda p: (p.published_date, p.year, p.month, p.title.lower()),
            reverse=True,
        )
        self.total_count = len(self.papers)
        self.last_updated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return added

    @classmethod
    def load(cls, path: str | Path) -> PaperDatabase:
        p = Path(path)
        if not p.exists():
            return cls()
        with open(p, encoding="utf-8") as f:
            return cls.model_validate_json(f.read())

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.total_count = len(self.papers)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2) + "\n")
