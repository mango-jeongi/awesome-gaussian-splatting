"""Evaluate a frozen, explicitly annotated relevance fixture without tuning it."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator

from src.backfill import SourceModel
from src.identity import paper_keys
from src.schema import PaperRecord
from src.storage import _digest, _encode

Outcome = Literal["include", "exclude", "review"]
SHA = r"^[a-f0-9]{64}$"
REQUIRED_PHENOMENA = {
    "broad_query_hit",
    "acronym_collision",
    "gs_medical_sensor",
    "nerf_foundation",
    "clear_negative",
}


class ReviewCandidate(SourceModel):
    sample_id: str = Field(pattern=r"^R[0-9]{3,}$")
    stratum: str = Field(min_length=1)
    source_capture_sha256: str = Field(pattern=SHA)
    observed_at: datetime
    source_quality: Literal[
        "official_arxiv_metadata", "official_huggingface_metadata", "legacy_seed_description"
    ]
    paper: dict
    record_sha256: str = Field(pattern=SHA)

    @model_validator(mode="after")
    def valid_record(self):
        if _digest(_encode(self.paper)) != self.record_sha256:
            raise ValueError("Review candidate content hash mismatch")
        PaperRecord.model_validate(self.paper)
        if not self.paper.get("id") or not self.paper.get("title"):
            raise ValueError("Review candidate needs a source ID and title")
        return self


class ReviewPacket(SourceModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    scope: str = Field(min_length=1)
    sampling: str = Field(min_length=1)
    rows: list[ReviewCandidate] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_records(self):
        if len({row.sample_id for row in self.rows}) != len(self.rows):
            raise ValueError("Duplicate review sample ID")
        identifiers = set()
        for row in self.rows:
            keys = paper_keys(PaperRecord.model_validate(row.paper))
            if identifiers.intersection(keys):
                raise ValueError("Repeated exact paper identity in review sample")
            identifiers.update(keys)
        return self


class SupplementalReviewCapture(SourceModel):
    """Retained primary text used for a later, explicitly versioned scope review."""

    reviewed_paper_id: str = Field(min_length=1)
    source_url: str
    observed_at: datetime
    evidence_kind: Literal["official_primary_full_method", "official_primary_abstract"]
    source_body_sha256: str = Field(pattern=SHA)
    source_body_utf8: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_source(self):
        parsed = urlparse(self.source_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Supplemental review needs a public HTTPS primary source")
        if self.observed_at.utcoffset() is None:
            raise ValueError("Supplemental source observation requires a timezone")
        if _digest(self.source_body_utf8.encode("utf-8")) != self.source_body_sha256:
            raise ValueError("Supplemental source body hash mismatch")
        return self


class ReviewAnnotation(SourceModel):
    sample_id: str = Field(pattern=r"^R[0-9]{3,}$")
    record_sha256: str = Field(pattern=SHA)
    outcome: Outcome
    reason: str = Field(min_length=10)
    phenomena: list[str] = Field(min_length=1)
    evidence_basis: Literal[
        "title_and_abstract",
        "explicit_title",
        "legacy_title_and_description",
        "supplemental_primary_source",
    ]
    supplemental_source_sha256: list[Annotated[str, Field(pattern=SHA)]] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def evidence_contract(self):
        if (self.evidence_basis == "supplemental_primary_source") != bool(
            self.supplemental_source_sha256
        ):
            raise ValueError("Supplemental review basis requires explicit source captures")
        if len(set(self.supplemental_source_sha256)) != len(self.supplemental_source_sha256):
            raise ValueError("Duplicate supplemental source capture")
        return self


class ReviewAnnotations(SourceModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    packet_sha256: str = Field(pattern=SHA)
    reviewed_by: str = Field(min_length=1)
    reviewer_kind: Literal["human", "agent"]
    independent_of_policy_author: bool
    reviewed_at: datetime
    scope_definition: str = Field(min_length=20)
    annotations: list[ReviewAnnotation] = Field(min_length=1)
    supersedes_annotations_sha256: Annotated[str, Field(pattern=SHA)] | None = None

    @model_validator(mode="after")
    def versioned_review(self):
        if self.reviewed_at.utcoffset() is None:
            raise ValueError("Annotation review time requires a timezone")
        if (
            any(a.supplemental_source_sha256 for a in self.annotations)
            and not self.supersedes_annotations_sha256
        ):
            raise ValueError(
                "Supplemental annotations must identify their prior annotation version"
            )
        return self


def evaluate_relevance(
    packet_payload: bytes, annotation_payload: bytes, policy, *, source_directory: Path
) -> dict:
    packet = ReviewPacket.model_validate_json(packet_payload)
    labels = ReviewAnnotations.model_validate_json(annotation_payload)
    if labels.packet_sha256 != _digest(packet_payload):
        raise ValueError("Annotation packet hash mismatch")
    annotations = {row.sample_id: row for row in labels.annotations}
    if len(annotations) != len(labels.annotations):
        raise ValueError("Duplicate annotation sample ID")
    if set(annotations) != {row.sample_id for row in packet.rows}:
        raise ValueError("Annotations must cover the exact candidate inventory")
    prior_verified = False
    if labels.supersedes_annotations_sha256:
        prior_payload = (
            source_directory / f"{labels.supersedes_annotations_sha256}.annotations.json"
        ).read_bytes()
        if _digest(prior_payload) != labels.supersedes_annotations_sha256:
            raise ValueError("Prior annotation version hash mismatch")
        prior = ReviewAnnotations.model_validate_json(prior_payload)
        previous = {a.sample_id: a for a in prior.annotations}
        if len(previous) != len(prior.annotations):
            raise ValueError("Duplicate annotation sample ID in prior version")
        if prior.packet_sha256 != labels.packet_sha256 or set(previous) != set(annotations):
            raise ValueError("Prior annotation version has a different candidate inventory")
        if prior.reviewed_at > labels.reviewed_at:
            raise ValueError("Prior annotation version postdates current review")
        for sample_id, annotation in annotations.items():
            old = previous[sample_id]
            if (
                old.record_sha256 != annotation.record_sha256
                or old.phenomena != annotation.phenomena
            ):
                raise ValueError("Scope review must preserve source record and sample composition")
            if old != annotation and not annotation.supplemental_source_sha256:
                raise ValueError("Changed annotation requires supplemental primary evidence")
        prior_verified = True
    captures = {}
    supplemental = {}
    for row in packet.rows:
        for digest in annotations[row.sample_id].supplemental_source_sha256:
            if digest not in supplemental:
                payload = (source_directory / f"{digest}.json").read_bytes()
                if _digest(payload) != digest:
                    raise ValueError("Supplemental review capture hash mismatch")
                supplemental[digest] = SupplementalReviewCapture.model_validate_json(payload)
            source = supplemental[digest]
            if source.reviewed_paper_id != row.paper["id"]:
                raise ValueError("Supplemental review paper identity mismatch")
            if source.observed_at > labels.reviewed_at:
                raise ValueError("Supplemental source postdates annotation review")

        digest = row.source_capture_sha256
        if digest not in captures:
            payload = (source_directory / f"{digest}.json").read_bytes()
            if _digest(payload) != digest:
                raise ValueError("Source capture hash mismatch")
            capture = json.loads(payload)
            records = capture["records"]
            by_id = {record["id"]: record for record in records}
            if len(by_id) != len(records):
                raise ValueError("Duplicate identity in source capture")
            captures[digest] = (
                by_id,
                datetime.fromisoformat(capture.get("observed_at", capture.get("fetched_at", ""))),
            )
        source_records, captured_at = captures[digest]
        source = source_records.get(row.paper["id"])
        if source is None or any(source.get(key) != value for key, value in row.paper.items()):
            raise ValueError("Review candidate differs from captured source record")
        if captured_at != row.observed_at:
            raise ValueError("Review observation does not match source capture time")
    outcomes = ("include", "exclude", "review")
    confusion = {gold: {predicted: 0 for predicted in outcomes} for gold in outcomes}
    rows, phenomena, quality = [], Counter(), Counter()
    for candidate in packet.rows:
        annotation = annotations[candidate.sample_id]
        if annotation.record_sha256 != candidate.record_sha256:
            raise ValueError("Annotation candidate hash mismatch")
        if labels.reviewed_at < candidate.observed_at:
            raise ValueError("Review cannot predate its source capture")
        predicted = policy.decide(PaperRecord.model_validate(candidate.paper))
        confusion[annotation.outcome][predicted.outcome] += 1
        phenomena.update(set(annotation.phenomena))
        quality[candidate.source_quality] += 1
        rows.append(
            {
                "sample_id": candidate.sample_id,
                "source_id": candidate.paper["id"],
                "title": candidate.paper["title"],
                "stratum": candidate.stratum,
                "source_quality": candidate.source_quality,
                "record_sha256": candidate.record_sha256,
                "gold": annotation.outcome,
                "predicted": predicted.outcome,
                "annotation_reason": annotation.reason,
                "policy_reason": predicted.reason,
                "agrees": annotation.outcome == predicted.outcome,
            }
        )
    true_positive = confusion["include"]["include"]
    predicted_includes = sum(confusion[gold]["include"] for gold in outcomes)
    gold_includes = sum(confusion["include"].values())
    precision = true_positive / predicted_includes if predicted_includes else None
    recall = true_positive / gold_includes if gold_includes else None
    required_covered = REQUIRED_PHENOMENA.issubset(phenomena)
    thresholds_met = (
        len(rows) >= 100
        and required_covered
        and precision is not None
        and recall is not None
        and precision >= 0.95
        and recall >= 0.95
    )
    return {
        "schema_version": "1.0.0",
        "packet_sha256": _digest(packet_payload),
        "annotations_sha256": _digest(annotation_payload),
        "policy_digest": policy.digest,
        "scope": packet.scope,
        "sampling": packet.sampling,
        "scope_definition": labels.scope_definition,
        "reviewer": {
            "name": labels.reviewed_by,
            "kind": labels.reviewer_kind,
            "independent_of_policy_author": labels.independent_of_policy_author,
            "reviewed_at": labels.reviewed_at.isoformat(),
        },
        "population_accuracy_claim": False,
        "sample_count": len(rows),
        "source_captures_verified": len(captures),
        "supplemental_source_captures_verified": len(supplemental),
        "supplemental_reviewed_samples": sum(
            bool(a.supplemental_source_sha256) for a in labels.annotations
        ),
        "supersedes_annotations_sha256": labels.supersedes_annotations_sha256,
        "prior_annotations_verified": prior_verified,
        "strata": dict(sorted(Counter(row.stratum for row in packet.rows).items())),
        "source_quality": dict(sorted(quality.items())),
        "phenomena": dict(sorted(phenomena.items())),
        "required_phenomena_covered": required_covered,
        "confusion": confusion,
        "include_precision": precision,
        "include_precision_lower_bound": precision,
        "resolved_label_precision": true_positive
        / (true_positive + confusion["exclude"]["include"])
        if true_positive + confusion["exclude"]["include"]
        else None,
        "include_recall": recall,
        "metric_definition": "Precision denominator includes every automatic include, including unresolved gold review cases. Recall denominator includes every gold include; policy review abstentions are missed includes, not removed from evaluation.",
        "nonconfirmed_includes": predicted_includes - true_positive,
        "false_positive_includes": confusion["exclude"]["include"],
        "unresolved_automatic_includes": confusion["review"]["include"],
        "false_negative_includes": gold_includes - true_positive,
        "unsafe_resolution_of_review": confusion["review"]["include"]
        + confusion["review"]["exclude"],
        "review_rate": sum(confusion[gold]["review"] for gold in outcomes) / len(rows),
        "exact_outcome_accuracy": sum(confusion[value][value] for value in outcomes) / len(rows),
        "precision_recall_thresholds_met": precision is not None
        and recall is not None
        and precision >= 0.95
        and recall >= 0.95,
        "sample_size_threshold_met": len(rows) >= 100,
        "sample_thresholds_met": thresholds_met,
        "limitations": [
            "Purposive sample, not a random population estimate.",
            "Review annotations are scope judgments, not provider metadata corrections or canonical overrides.",
            "Legacy seed descriptions are not independently verified author abstracts.",
            "Passing this fixture alone does not prove historical or venue completeness.",
        ],
        "rows": rows,
    }
