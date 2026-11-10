"""Reviewed archival dispositions with lossless records, aliases, and observations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.contracts import FieldEvidence
from src.identity import IdentityConflict, IdentityIndex, identifier_key
from src.observations import Observation
from src.schema import PaperDatabase, PaperRecord


class ArchiveEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    paper: PaperRecord
    disposition: Literal["excluded", "merged"]
    reason: str = Field(min_length=1)
    evidence: list[FieldEvidence] = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    merged_into: str | None = None
    aliases: list[str] = Field(default_factory=list)
    observations: dict[str, Observation] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_disposition(self):
        if self.reviewed_at.utcoffset() is None:
            raise ValueError("Archive review time requires a timezone")
        if self.disposition == "merged":
            if not self.merged_into or self.merged_into == self.paper.id:
                raise ValueError("Merged disposition requires a different canonical target")
        elif self.merged_into is not None:
            raise ValueError("Excluded disposition cannot specify a merge target")
        if any(
            provider != observation.provider for provider, observation in self.observations.items()
        ):
            raise ValueError("Archived observation provider mismatch")
        return self


class ArchiveLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = "1.0.0"
    entries: dict[str, ArchiveEntry] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_keys(self):
        if any(key != entry.paper.id for key, entry in self.entries.items()):
            raise ValueError("Archive key does not match canonical ID")
        return self

    def resolve(self, paper_id: str, active_ids: set[str]) -> str:
        seen = set()
        while paper_id not in active_ids:
            if paper_id in seen:
                raise IdentityConflict("Archive merge cycle")
            seen.add(paper_id)
            entry = self.entries.get(paper_id)
            if entry is None:
                raise IdentityConflict(f"Missing archive merge target: {paper_id}")
            if entry.disposition == "excluded":
                return paper_id
            paper_id = entry.merged_into
        return paper_id

    def alias_targets(self, active_ids: set[str]) -> dict[str, str]:
        if active_ids & self.entries.keys():
            raise IdentityConflict("Paper cannot be both active and archived")
        aliases = {}
        for paper_id, entry in self.entries.items():
            endpoint = self.resolve(paper_id, active_ids)
            for alias in [paper_id, *entry.aliases]:
                key = identifier_key(alias)
                if key in aliases and aliases[key] != endpoint:
                    raise IdentityConflict(f"Conflicting archived alias: {key}")
                aliases[key] = endpoint
        return aliases


def validate_archive(db: PaperDatabase) -> ArchiveLedger:
    ledger = ArchiveLedger(entries=db.archive)
    index = IdentityIndex(db.papers, db.aliases)
    for alias, target in ledger.alias_targets(set(index.by_id)).items():
        if target in index.by_id:
            if index.aliases.get(alias) != target:
                raise IdentityConflict(f"Reviewed merge alias is missing: {alias}")
        elif alias in index.aliases:
            raise IdentityConflict(f"Excluded identifier is still active: {alias}")
    return ledger


def archive_paper(
    db: PaperDatabase,
    paper_id: str,
    *,
    disposition: Literal["excluded", "merged"],
    reason: str,
    evidence: list[FieldEvidence],
    reviewed_by: str,
    reviewed_at: datetime,
    merged_into: str | None = None,
) -> bool:
    """Apply an explicit reviewed disposition transactionally; never decide relevance here."""
    ledger = validate_archive(db)
    index = IdentityIndex(db.papers, db.aliases)
    previous = ledger.entries.get(paper_id)
    paper = index.by_id.get(paper_id) or (previous.paper if previous else None)
    if paper is None:
        raise KeyError(f"Canonical paper is missing: {paper_id}")
    if previous is None and merged_into is not None and merged_into not in index.by_id:
        raise IdentityConflict("New merge target must be active")
    aliases = (
        previous.aliases
        if previous
        else sorted(
            {paper_id, *[key for key, target in index.aliases.items() if target == paper_id]}
        )
    )
    observations = (
        previous.observations
        if previous
        else {
            provider: store.observations[paper_id]
            for provider, store in db._signal_stores.items()
            if paper_id in store.observations
        }
    )
    entry = ArchiveEntry(
        paper=paper.model_copy(deep=True),
        disposition=disposition,
        reason=reason,
        evidence=evidence,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
        merged_into=merged_into,
        aliases=aliases,
        observations=observations,
    )
    if previous is not None:
        if entry != previous:
            raise IdentityConflict("Changing a reviewed archival disposition requires adjudication")
        return False
    candidate = db.model_copy(deep=True)
    candidate.papers = [record for record in candidate.papers if record.id != paper_id]
    candidate.total_count = len(candidate.papers)
    candidate.aliases = {
        alias: (merged_into if target == paper_id else target)
        for alias, target in index.aliases.items()
        if target != paper_id or merged_into is not None
    }
    for store in candidate._signal_stores.values():
        store.observations.pop(paper_id, None)
    ledger.entries[paper_id] = entry
    candidate.archive = ledger.model_dump(mode="json")["entries"]
    validate_archive(candidate)
    from src.extractors.citations import build_citation_knowledge_graph

    build_citation_knowledge_graph(candidate)
    candidate.last_updated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    db.papers = candidate.papers
    db.total_count = candidate.total_count
    db.aliases = candidate.aliases
    db.archive = candidate.archive
    db._signal_stores = candidate._signal_stores
    db.last_updated = candidate.last_updated
    return True


class ArchiveDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    paper_id: str = Field(min_length=1)
    disposition: Literal["excluded", "merged"]
    reason: str = Field(min_length=1)
    evidence: list[FieldEvidence] = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    merged_into: str | None = None


class ArchiveReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = "1.0.0"
    expected_content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    decisions: list[ArchiveDecision] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_decisions(self):
        ids = [decision.paper_id for decision in self.decisions]
        if len(ids) != len(set(ids)):
            raise ValueError("Conflicting or duplicate archive decisions")
        return self


def prepare_archive_review(db: PaperDatabase, review: ArchiveReview) -> tuple[PaperDatabase, dict]:
    """Prepare the complete reviewed transaction against exactly the approved snapshot."""
    from src.storage import _digest, _encode

    digest = _digest(_encode(db.model_dump(mode="json")))
    stale = review.expected_content_sha256 != digest
    if stale and any(decision.paper_id not in db.archive for decision in review.decisions):
        raise IdentityConflict(
            "Review snapshot is stale; regenerate and adjudicate against current data"
        )
    candidate = db.model_copy(deep=True)
    changes = []
    for decision in review.decisions:
        changed = archive_paper(
            candidate, decision.paper_id, **decision.model_dump(exclude={"paper_id"})
        )
        if stale and changed:
            raise IdentityConflict("Stale review cannot apply new changes")
        changes.append(
            {
                "paper_id": decision.paper_id,
                "disposition": decision.disposition,
                "merged_into": decision.merged_into,
                "changed": changed,
            }
        )
    # Sequential graph repairs must not rewrite a later decision's approved
    # original record. Restore snapshots from the transaction input, while
    # retaining repaired active edges and the actual archival disposition.
    original_records = {paper.id: paper for paper in db.papers}
    for change in changes:
        if change["changed"]:
            candidate.archive[change["paper_id"]]["paper"] = original_records[
                change["paper_id"]
            ].model_dump(mode="json")
    validate_archive(candidate)
    return candidate, {
        "source_content_sha256": digest,
        "approved_content_sha256": review.expected_content_sha256,
        "replayed_existing_decisions": stale,
        "active_records": len(candidate.papers),
        "archived_records": len(candidate.archive),
        "decisions": changes,
    }
