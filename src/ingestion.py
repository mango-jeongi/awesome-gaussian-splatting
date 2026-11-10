"""Prepare deterministic ingestion and one disposition per source candidate."""

from __future__ import annotations

from src.curation import validate_archive
from src.enricher import MultiProviderEnricher
from src.identity import IdentityIndex, identifier_key, paper_keys
from src.relevance import RelevancePolicy
from src.schema import PaperDatabase, PaperRecord
from src.storage import _digest, _encode


def prepare_ingestion(
    db: PaperDatabase,
    records: list[PaperRecord],
    policy: RelevancePolicy,
    enricher: MultiProviderEnricher,
) -> tuple[PaperDatabase, dict]:
    if len({record.id for record in records}) != len(records):
        raise ValueError("Candidate inventory must contain unique source IDs")
    original = {paper.id: paper.model_dump() for paper in db.papers}
    identity = IdentityIndex(db.papers, db.aliases)
    ledger = validate_archive(db)
    archived = ledger.alias_targets(set(identity.by_id))
    rows, eligible = {}, []
    for record in records:
        decision = policy.decide(record)
        keys = paper_keys(record)
        active = {identity.aliases[key] for key in keys if key in identity.aliases}
        excluded = {
            archived[key] for key in keys if key in archived and archived[key] not in identity.by_id
        }
        outcome, reason = decision.outcome, decision.reason
        if len(active) > 1 or (active and excluded):
            outcome, reason = (
                "review",
                "Candidate identifiers disagree with active/archive identities",
            )
        elif excluded:
            if decision.override and decision.outcome == "include":
                outcome, reason = (
                    "review",
                    "Reviewed inclusion conflicts with an archived exclusion",
                )
            else:
                outcome, reason = "exclude", "Reviewed archived exclusion remains authoritative"
        elif active and outcome == "exclude":
            outcome, reason = (
                "review",
                "Topic exclusion conflicts with an active record; archival requires review",
            )
        row = {
            "source_id": record.id,
            "outcome": outcome,
            "reason": reason,
            "canonical_id": next(iter(active)) if len(active) == 1 else None,
            "operation": "none",
        }
        rows[record.id] = row
        if outcome == "include":
            eligible.append(enricher.enrich(record, use_llm=False))
    candidate = db.model_copy(deep=True)

    def conflict(record, error):
        rows[record.id].update(
            outcome="review",
            reason=f"Identity/metadata review required: {str(error)[:240]}",
            operation="none",
        )

    inserted = candidate.upsert(eligible, on_conflict=conflict) if eligible else 0
    final = IdentityIndex(candidate.papers, candidate.aliases)
    for record in eligible:
        row = rows[record.id]
        if row["outcome"] != "include":
            continue
        target = final.aliases.get(identifier_key(record.id))
        if target is None:
            raise ValueError("Accepted candidate has no canonical identity")
        row["canonical_id"] = target
        if target != record.id and identifier_key(record.id) not in identity.aliases:
            row["operation"] = "merged"
        elif target not in original:
            row["operation"] = "inserted"
        else:
            row["operation"] = (
                "updated" if original[target] != final.by_id[target].model_dump() else "unchanged"
            )
    dispositions = [rows[key] for key in sorted(rows)]
    report = {
        "schema_version": "1.0.0",
        "policy_digest": policy.digest,
        "source_content_sha256": _digest(_encode(db.model_dump(mode="json"))),
        "result_content_sha256": _digest(_encode(candidate.model_dump(mode="json"))),
        "unique_candidates": len(records),
        "inserted_canonical_records": inserted,
        "outcomes": {
            outcome: sum(row["outcome"] == outcome for row in dispositions)
            for outcome in ("include", "exclude", "review")
        },
        "operations": {
            operation: sum(row["operation"] == operation for row in dispositions)
            for operation in ("inserted", "updated", "unchanged", "merged", "none")
        },
        "dispositions": dispositions,
    }
    return candidate, report
