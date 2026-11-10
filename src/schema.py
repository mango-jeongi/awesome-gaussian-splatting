"""Pydantic v2 Schema-on-Read models for the 3DGS One Big Table (OBT)."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator

from src.contracts import DatePlacement, DatePrecision, FieldEvidence
from src.identity import IdentityIndex, normalize_arxiv, normalize_doi, paper_keys

PaperSource = Literal["arxiv", "ieee", "cvf", "acm", "manual", "huggingface"]


def synthesize_tldr(abstract: str) -> str:
    """Distill the core technical contribution from an abstract, stripping generic preamble."""
    if not abstract:
        return ""

    text = re.sub(r"\s+", " ", abstract).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)

    background_markers = (
        "neural radiance field",
        "recently",
        "in recent years",
        "novel view synthesis",
        "has attracted significant attention",
        "has emerged as",
        "have achieved impressive",
        "is a fundamental problem",
        "has demonstrated remarkable",
        "remains challenging",
        "despite the success",
        "although 3d gaussian",
        "3d gaussian splatting (3dgs) has",
        "3d gaussian splatting has revolutionized",
        "recent 3dgs methods",
        "existing 3dgs methods",
        "existing methods",
        "current methods",
    )

    action_markers = (
        "we propose",
        "we introduce",
        "we present",
        "we develop",
        "we design",
        "this paper proposes",
        "this paper introduces",
        "this paper presents",
        "this paper develops",
        "this work proposes",
        "this work introduces",
        "this work presents",
        "this work develops",
        "to address this",
        "to overcome this",
        "to tackle this",
    )

    # 1. Prefer explicit contribution sentence
    candidate = ""
    for s in sentences:
        s_lower = s.lower().strip()
        if any(m in s_lower for m in action_markers):
            candidate = s.strip()
            break

    # 2. Otherwise pick first non-background sentence highlighting capability
    if not candidate:
        for s in sentences:
            s_lower = s.lower().strip()
            if any(s_lower.startswith(bm) or bm in s_lower[:50] for bm in background_markers):
                continue
            if any(
                w in s_lower
                for w in (
                    "achieves",
                    "enables",
                    "allows",
                    "formulates",
                    "demonstrates",
                    "outperforms",
                )
            ):
                candidate = s.strip()
                break

    # 3. Fallback to first non-background sentence or first sentence
    if not candidate:
        non_bg = [
            s.strip()
            for s in sentences
            if not any(s.lower().strip().startswith(bm) for bm in background_markers)
        ]
        candidate = non_bg[0] if non_bg else sentences[0].strip()

    # Clean boilerplate prefixes into concise active summary
    clean = candidate
    clean = re.sub(
        r"^(in this (paper|work|study|letter),?\s+)?we\s+propose\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Proposes ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^(in this (paper|work|study|letter),?\s+)?we\s+introduce\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Introduces ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^(in this (paper|work|study|letter),?\s+)?we\s+present\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Presents ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^(in this (paper|work|study|letter),?\s+)?we\s+develop\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Develops ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^(in this (paper|work|study|letter),?\s+)?we\s+design\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Designs ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^this (paper|work|study)\s+proposes\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Proposes ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^this (paper|work|study)\s+introduces\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Introduces ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^this (paper|work|study)\s+presents\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Presents ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^to (address|tackle|overcome) (this|these) (issue|problem|limitation)s?,?\s+(we\s+)?(propose|introduce|present)\s+",
        "Proposes ",
        clean,
        flags=re.IGNORECASE,
    )

    # Clean trailing fragments
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) > 210:
        cut = clean[:207]
        last_space = cut.rfind(" ")
        clean = (cut[:last_space] if last_space > 120 else cut) + "..."

    if clean and clean[0].islower():
        clean = clean[0].upper() + clean[1:]
    return clean


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

    model_config = ConfigDict(extra="forbid")

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

    published_date_precision: DatePrecision = "unknown"
    date_placement: DatePlacement = "legacy_unknown"
    publication_date: str | None = None
    publication_year: int | None = Field(default=None, ge=1990, le=2100)
    publication_date_precision: DatePrecision = "unknown"
    arxiv_doi: str | None = None
    metadata_evidence: dict[str, list[FieldEvidence]] = Field(default_factory=dict)

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
        default_factory=lambda: ["Foundations"],
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

    # Phase 3: Citation Intelligence & Knowledge Graph
    citation_count: int = Field(
        default=0,
        ge=0,
        description="Total global citations tracked via OpenAlex or academic graphs.",
    )
    influential_citation_count: int = Field(
        default=0,
        ge=0,
        description="Influential citations tracked via academic graphs.",
    )
    openalex_id: str | None = Field(
        default=None,
        description="Canonical OpenAlex Work ID (e.g., 'https://openalex.org/W4385318467').",
    )
    referenced_works: list[str] = Field(
        default_factory=list,
        description="Work IDs/DOIs of papers referenced by this paper.",
    )
    db_citation_count: int = Field(
        default=0,
        ge=0,
        description="Number of papers in this specific 3DGS database that cite this paper.",
    )
    db_citations: list[str] = Field(
        default_factory=list,
        description="IDs of papers in this database citing this paper.",
    )
    db_references: list[str] = Field(
        default_factory=list,
        description="IDs of papers in this database cited by this paper.",
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
        return normalize_arxiv(str(v))

    @field_validator("updated_date", "publication_date")
    @classmethod
    def validate_optional_dates(cls, value: str | None) -> str | None:
        if value is not None:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("Date must be ISO YYYY-MM-DD")
            date.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def populate_derived_fields(self) -> PaperRecord:
        # Derive canonical ID if missing
        if not self.id:
            if self.arxiv_id:
                self.id = self.arxiv_id
            elif self.doi:
                self.id = f"doi:{normalize_doi(self.doi)}"
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
            date.fromisoformat(self.published_date)
            if not 1990 <= int(self.published_date[:4]) <= 2100:
                raise ValueError("Original publication year outside supported range")
            self.year = int(self.published_date[:4])
            self.month = int(self.published_date[5:7])
        else:
            if self.published_date:
                raise ValueError("Original publication date must be ISO YYYY-MM-DD")
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
            if (
                clean_t
                and clean_t not in seen_tags
                and clean_t not in ("3DGS", "Ultrasound & Medical")
            ):
                seen_tags.append(clean_t)
        self.tags = seen_tags or ["Foundations"]

        # Synthesize concise TL;DR from abstract
        if not self.tldr and self.abstract:
            self.tldr = synthesize_tldr(self.abstract)

        return self

    @model_validator(mode="after")
    def validate_metadata_evidence(self) -> PaperRecord:
        original = date.fromisoformat(self.published_date)
        if self.published_date_precision == "month" and original.day != 1:
            raise ValueError("Month-precision placement must use the first day")
        if self.published_date_precision == "year" and (original.month, original.day) != (1, 1):
            raise ValueError("Year-precision placement must use January 1")
        expected = {
            "day": "observed",
            "month": "month_start",
            "year": "year_start",
            "unknown": "legacy_unknown",
        }[self.published_date_precision]
        if self.date_placement == "legacy_unknown":
            self.date_placement = expected
        elif self.date_placement != expected:
            raise ValueError("Date placement disagrees with precision")
        if self.publication_date:
            published = date.fromisoformat(self.publication_date)
            if self.publication_year is not None and self.publication_year != published.year:
                raise ValueError("Proceedings date and year disagree")
            if not 1990 <= published.year <= 2100:
                raise ValueError("Proceedings year outside supported range")
            self.publication_year = published.year
            if self.publication_date_precision == "month" and published.day != 1:
                raise ValueError("Month-precision proceedings date must use the first day")
            if self.publication_date_precision == "year" and (published.month, published.day) != (
                1,
                1,
            ):
                raise ValueError("Year-precision proceedings date must use January 1")
        elif self.publication_date_precision not in ("unknown", "year") or (
            self.publication_date_precision == "year" and self.publication_year is None
        ):
            raise ValueError("Proceedings precision requires date/year evidence")
        for field, entries in self.metadata_evidence.items():
            if field not in type(self).model_fields or field == "metadata_evidence":
                raise ValueError(f"Unknown evidence field: {field}")
            reviewed = [entry for entry in entries if entry.reviewed_at is not None]
            if reviewed:
                latest = max(entry.reviewed_at for entry in reviewed)
                approved = [entry.value for entry in reviewed if entry.reviewed_at == latest]
                if any(value != getattr(self, field) for value in approved):
                    raise ValueError(f"Reviewed evidence disagrees with current field: {field}")
        return self

    def reviewed_fields(self) -> set[str]:
        return {
            field
            for field, entries in self.metadata_evidence.items()
            if any(entry.reviewed_at for entry in entries)
        }

    def protected_fields(self) -> set[str]:
        locked = self.reviewed_fields()
        for group in (
            {"published_date", "year", "month", "published_date_precision", "date_placement"},
            {"publication_date", "publication_year", "publication_date_precision"},
            {"categories", "primary_category"},
            {"authors", "first_author"},
        ):
            if locked & group:
                locked |= group
        return locked

    def with_provider_updates(self, *, update: dict) -> PaperRecord:
        locked = self.protected_fields()
        changes = {field: value for field, value in update.items() if field not in locked}
        return PaperRecord.model_validate(self.model_copy(update=changes).model_dump())

    def merge_metadata(self, incoming: PaperRecord) -> PaperRecord:
        """Provider updates preserve reviewed fields and independent date identities."""
        update = {
            field: getattr(incoming, field) or getattr(self, field)
            for field in (
                "arxiv_id",
                "doi",
                "arxiv_doi",
                "venue",
                "code_url",
                "project_url",
                "pdf_url",
                "paper_url",
                "publication_date",
                "publication_year",
            )
        }
        update.update(
            {
                "abstract": incoming.abstract
                if len(incoming.abstract) > len(self.abstract)
                else self.abstract,
                "tldr": incoming.tldr or self.tldr,
                "categories": list(dict.fromkeys(incoming.categories + self.categories)),
                "tags": list(dict.fromkeys(incoming.tags + self.tags)),
            }
        )
        if incoming.publication_date_precision != "unknown":
            update["publication_date_precision"] = incoming.publication_date_precision
        if incoming.updated_date and (
            not self.updated_date or incoming.updated_date > self.updated_date
        ):
            update["updated_date"] = incoming.updated_date
        if self.authors == ["Unknown"] and incoming.authors != ["Unknown"]:
            update["authors"] = incoming.authors
            update["first_author"] = incoming.first_author
        if incoming.published_date_precision != "unknown" and (
            (incoming.source == "arxiv" and incoming.published_date_precision == "day")
            or (
                self.published_date_precision == "unknown"
                and self.published_date == incoming.published_date
            )
        ):
            for field in (
                "published_date",
                "published_date_precision",
                "date_placement",
                "year",
                "month",
            ):
                update[field] = getattr(incoming, field)
        locked = self.protected_fields()
        update = {field: value for field, value in update.items() if field not in locked}
        evidence = {field: list(entries) for field, entries in self.metadata_evidence.items()}
        for field, entries in incoming.metadata_evidence.items():
            for entry in entries:
                if entry not in evidence.setdefault(field, []):
                    # Reviewed metadata is changed only through an explicit override operation.
                    if (
                        field in locked
                        and entry.reviewed_at is not None
                        and entry.value != getattr(self, field)
                    ):
                        raise ValueError(
                            f"Conflicting reviewed override requires adjudication: {field}"
                        )
                    evidence[field].append(entry)
        update["metadata_evidence"] = evidence
        return PaperRecord.model_validate(self.model_copy(update=update).model_dump())

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

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    last_updated: str = Field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    total_count: int = 0
    papers: list[PaperRecord] = Field(default_factory=list)
    aliases: dict[str, str] = Field(default_factory=dict)
    archive: dict[str, dict] = Field(default_factory=dict)
    _signal_stores: dict = PrivateAttr(default_factory=dict)
    _loaded_path: Path | None = PrivateAttr(default=None)
    _loaded_sha256: str | None = PrivateAttr(default=None)

    def upsert(
        self,
        records: list[PaperRecord],
        *,
        on_conflict: Callable[[PaperRecord, ValueError], None] | None = None,
    ) -> int:
        """Merge evidence-matched records transactionally, preserving stable IDs."""
        before = [paper.model_dump() for paper in self.papers]
        from src.curation import validate_archive
        from src.identity import IdentityConflict

        ledger = validate_archive(self)
        index = IdentityIndex(self.papers, self.aliases)
        archived_aliases = ledger.alias_targets(set(index.by_id))
        by_id = dict(index.by_id)
        added = 0
        accepted = 0
        for rec in records:
            try:
                if any(
                    key in archived_aliases and archived_aliases[key] not in index.by_id
                    for key in paper_keys(rec)
                ):
                    raise IdentityConflict(f"Archived candidate requires explicit review: {rec.id}")
                existing_id = index.match(rec)
                if existing_id and existing_id in by_id:
                    existing = by_id[existing_id]
                    merged = existing.merge_metadata(rec)
                    index.bind_many(paper_keys(rec), existing_id)
                    by_id[existing_id] = merged
                    index.by_id[existing_id] = merged
                else:
                    index.add(rec)
                    by_id[rec.id] = rec
                    added += 1
                accepted += 1
            except ValueError as error:
                if on_conflict is None:
                    raise
                on_conflict(rec, error)

        if not accepted:
            return 0

        # Sort newest first, then alphabetically by title
        self.papers = sorted(
            by_id.values(),
            key=lambda p: (p.published_date, p.year, p.month, p.title.lower()),
            reverse=True,
        )
        self.total_count = len(self.papers)
        self.aliases = dict(sorted(index.aliases.items()))
        if before != [paper.model_dump() for paper in self.papers]:
            self.last_updated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return added

    def get(self, paper_id: str) -> PaperRecord | None:
        """Lookup a paper by canonical ID, arXiv ID, or clean DOI."""
        from src.identity import identifier_key

        index = IdentityIndex(self.papers, self.aliases)
        target = index.aliases.get(identifier_key(paper_id))
        return index.by_id.get(target) if target is not None else None

    @classmethod
    def load(cls, path: str | Path) -> PaperDatabase:
        p = Path(path)
        payload = p.read_bytes()
        raw = json.loads(payload)
        if raw.get("schema_version") == "2.0.0":
            from src.storage import load_store

            return load_store(p)
        if raw.get("schema_version") != "1.0.0":
            raise ValueError("Unsupported database schema")
        db = cls.model_validate(raw)
        from src.curation import validate_archive

        validate_archive(db)
        IdentityIndex(db.papers, db.aliases)
        if db.total_count != len(db.papers):
            raise ValueError("Database count mismatch")
        db._loaded_path = p.resolve()
        db._loaded_sha256 = hashlib.sha256(payload).hexdigest()
        return db

    def save(self, path: str | Path) -> None:
        from src.file_lock import exclusive_file
        from src.storage import ConcurrentWriteError, _atomic_write, _inventory, write_store

        p = Path(path)
        self.total_count = len(self.papers)
        _inventory(self)
        expected = self._loaded_sha256 if self._loaded_path == p.resolve() else None
        is_manifest = p.name == "manifest.json"
        if p.exists():
            is_manifest = is_manifest or json.loads(p.read_bytes()).get("schema_version") == "2.0.0"
        if is_manifest:
            write_store(self, p, expected_sha256=expected)
        else:
            payload = (self.model_dump_json(indent=2) + "\n").encode("utf-8")
            with exclusive_file(str(p) + ".writer.lock"):
                current = p.read_bytes() if p.exists() else None
                actual = hashlib.sha256(current).hexdigest() if current is not None else None
                if expected is not None and actual != expected:
                    raise ConcurrentWriteError("Database changed since load; reload and retry")
                if current != payload:
                    _atomic_write(p, payload)
            self._loaded_path = p.resolve()
            self._loaded_sha256 = hashlib.sha256(payload).hexdigest()
