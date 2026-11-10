"""Evidence-based identity matching with stable canonical IDs and explicit conflicts."""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING
from urllib.parse import unquote

if TYPE_CHECKING:
    from src.schema import PaperRecord


class IdentityConflict(ValueError):
    """Identifiers disagree or a candidate requires manual adjudication."""


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = unquote(value.strip()).lower()
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value)
    return value or None


def normalize_arxiv(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    value = re.sub(r"^https?://(?:export\.)?arxiv\.org/(?:abs|pdf)/", "", value)
    value = re.sub(r"^arxiv:\s*", "", value)
    value = re.sub(r"\.pdf$", "", value)
    return re.sub(r"v\d+$", "", value) or None


def normalize_openalex(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"^openalex:", "", value, flags=re.I)
    short = value.strip().rstrip("/").rsplit("/", 1)[-1].upper()
    return short if re.fullmatch(r"W\d+", short) else None


def identifier_key(value: str) -> str:
    """Normalize supported provider identifiers; preserve arbitrary canonical IDs."""
    stripped = value.strip()
    if re.match(r"^(?:doi:|https?://(?:dx\.)?doi\.org/|10\.\d+/)", stripped, re.I):
        return f"doi:{normalize_doi(stripped)}"
    if re.match(
        r"^(?:arxiv:|https?://(?:export\.)?arxiv\.org/|\d{4}\.\d{4,5}(?:v\d+)?$|[a-z-]+(?:\.[A-Z]{2})?/\d{7})",
        stripped,
        re.I,
    ):
        return f"arxiv:{normalize_arxiv(stripped)}"
    if re.match(r"^(?:openalex:|https?://openalex\.org/)?W\d+/?$", stripped, re.I):
        return f"openalex:{normalize_openalex(stripped)}"
    return stripped


def paper_keys(paper: PaperRecord) -> set[str]:
    keys = {identifier_key(paper.id)}
    if paper.doi:
        keys.add(f"doi:{normalize_doi(paper.doi)}")
    if paper.arxiv_doi:
        keys.add(f"doi:{normalize_doi(paper.arxiv_doi)}")
    if paper.arxiv_id:
        keys.add(f"arxiv:{normalize_arxiv(paper.arxiv_id)}")
    if paper.openalex_id:
        normalized = normalize_openalex(paper.openalex_id)
        if normalized:
            keys.add(f"openalex:{normalized}")
    return keys


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def _compatible(left: PaperRecord, right: PaperRecord) -> bool:
    for field, normalizer in (("doi", normalize_doi), ("arxiv_id", normalize_arxiv)):
        a, b = normalizer(getattr(left, field)), normalizer(getattr(right, field))
        if a and b and a != b:
            return False
    return True


def author_surnames(authors: list[str]) -> set[str]:
    """Normalize actual family-name evidence; et al. never supplies a surname."""
    result = set()
    for author in authors:
        name = re.sub(r"(?:^|\s+)et\.?\s+al\.?\s*$", "", author.strip(), flags=re.I).strip()
        if not name:
            continue
        name = "".join(
            char
            for char in unicodedata.normalize("NFKD", name.casefold())
            if not unicodedata.combining(char)
        )
        words = re.findall(r"[^\W\d_]+", name, flags=re.UNICODE)
        if not words or any(word in {"unknown", "anonymous"} for word in words):
            continue
        if any(word in {"collaboration", "consortium", "group"} for word in words):
            family = " ".join(words)
        else:
            family_text = name.split(",", 1)[0] if "," in name else name
            family_words = re.findall(r"[^\W\d_]+", family_text, flags=re.UNICODE)
            family = family_words[-1] if family_words else ""
        if family and family not in {"et", "al"}:
            result.add(family)
    return result


def _author_agreement(left: PaperRecord, right: PaperRecord) -> bool:
    return bool(author_surnames(left.authors) & author_surnames(right.authors))


class IdentityIndex:
    def __init__(self, papers: list[PaperRecord], aliases: dict[str, str] | None = None):
        self.by_id = {}
        self.aliases = {}
        self.by_title: dict[str, list[str]] = {}
        for paper in papers:
            self.add(paper)
        for alias, target in (aliases or {}).items():
            self.bind(alias, target)

    def _bindings(self, aliases, target: str) -> dict[str, str]:
        normalized = {identifier_key(alias): target for alias in aliases}
        for key in normalized:
            previous = self.aliases.get(key)
            if previous is not None and previous != target:
                raise IdentityConflict(f"Alias collision for {key}: {previous}, {target}")
        return normalized

    def bind_many(self, aliases, target: str) -> None:
        if target not in self.by_id:
            raise IdentityConflict(f"Alias target is missing: {target}")
        self.aliases.update(self._bindings(aliases, target))

    def bind(self, alias: str, target: str) -> None:
        self.bind_many([alias], target)

    def add(self, paper: PaperRecord) -> None:
        if paper.id in self.by_id:
            raise IdentityConflict(f"Duplicate canonical ID: {paper.id}")
        bindings = self._bindings(paper_keys(paper), paper.id)
        self.by_id[paper.id] = paper
        self.aliases.update(bindings)
        self.by_title.setdefault(title_key(paper.title), []).append(paper.id)

    def match(self, candidate: PaperRecord) -> str | None:
        keys = {identifier_key(key) for key in paper_keys(candidate)}
        exact = {self.aliases[key] for key in keys if key in self.aliases}
        if len(exact) > 1:
            raise IdentityConflict(
                f"Candidate identifiers resolve to multiple papers: {sorted(exact)}"
            )
        if exact:
            target = next(iter(exact))
            if not _compatible(self.by_id[target], candidate):
                raise IdentityConflict(f"Contradictory identifiers for {target}")
            return target
        candidates = self.by_title.get(title_key(candidate.title), [])
        supported = [
            target
            for target in candidates
            if _compatible(self.by_id[target], candidate)
            and abs(self.by_id[target].year - candidate.year) <= 1
            and _author_agreement(self.by_id[target], candidate)
        ]
        if len(supported) == 1:
            return supported[0]
        if candidates:
            raise IdentityConflict(f"Title match requires review: {candidate.id}")
        return None
