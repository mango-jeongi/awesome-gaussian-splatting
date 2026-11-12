"""Independent confusion counts and strict frozen-review evidence contracts."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.relevance import RelevancePolicy
from src.relevance_benchmark import evaluate_relevance
from src.storage import _digest, _encode


class Predictions:
    digest = "a" * 64

    def __init__(self, outcomes):
        self.outcomes = outcomes

    def decide(self, paper):
        return SimpleNamespace(outcome=self.outcomes[paper.id], reason="Controlled test prediction")


def fixture(tmp_path, gold=("include", "include", "exclude", "review")):
    source = {
        "fetched_at": "2024-01-01T00:00:00Z",
        "records": [
            {
                "id": f"2401.{index:05}",
                "arxiv_id": f"2401.{index:05}",
                "title": f"Independently controlled record {index}",
                "authors": ["A. Author"],
                "abstract": "Fixed source text",
                "published_date": "2024-01-01",
                "source": "arxiv",
            }
            for index in range(len(gold))
        ],
    }
    source_payload = _encode(source)
    source_hash = _digest(source_payload)
    directory = tmp_path / "sources"
    directory.mkdir()
    (directory / f"{source_hash}.json").write_bytes(source_payload)
    rows = [
        {
            "sample_id": f"R{index + 1:03}",
            "stratum": "controlled",
            "source_capture_sha256": source_hash,
            "observed_at": source["fetched_at"],
            "source_quality": "official_arxiv_metadata",
            "paper": paper,
            "record_sha256": _digest(_encode(paper)),
        }
        for index, paper in enumerate(source["records"])
    ]
    packet = {
        "scope": "Controlled metric arithmetic fixture",
        "sampling": "Every controlled record",
        "rows": rows,
    }
    packet_payload = _encode(packet)
    labels = {
        "packet_sha256": _digest(packet_payload),
        "reviewed_by": "Test reviewer",
        "reviewer_kind": "human",
        "independent_of_policy_author": True,
        "reviewed_at": "2024-01-02T00:00:00Z",
        "scope_definition": "Explicit controlled labels for checking evaluator arithmetic",
        "annotations": [
            {
                "sample_id": row["sample_id"],
                "record_sha256": row["record_sha256"],
                "outcome": outcome,
                "reason": "Independent test expectation",
                "phenomena": ["controlled"],
                "evidence_basis": "title_and_abstract",
            }
            for row, outcome in zip(rows, gold, strict=True)
        ],
    }
    return packet, labels, directory


def evaluate(packet, labels, directory, predictions=None):
    if predictions is None:
        predictions = ["include"] * len(packet["rows"])
    policy = Predictions(
        {
            row["paper"]["id"]: outcome
            for row, outcome in zip(packet["rows"], predictions, strict=True)
        }
    )
    return evaluate_relevance(_encode(packet), _encode(labels), policy, source_directory=directory)


def test_review_abstentions_count_as_missed_includes_and_unsafe_includes_count(tmp_path):
    packet, labels, directory = fixture(tmp_path)
    report = evaluate(packet, labels, directory, ["include", "review", "include", "include"])
    assert report["include_precision"] == 1 / 3
    assert report["resolved_label_precision"] == 0.5
    assert report["nonconfirmed_includes"] == 2
    assert report["unresolved_automatic_includes"] == 1
    assert report["include_recall"] == 0.5
    assert report["false_positive_includes"] == 1
    assert report["false_negative_includes"] == 1
    assert report["unsafe_resolution_of_review"] == 1
    assert report["exact_outcome_accuracy"] == 0.25
    assert not report["sample_thresholds_met"]  # Small samples cannot satisfy the gate.


def test_undefined_precision_or_recall_never_becomes_a_perfect_score(tmp_path):
    packet, labels, directory = fixture(tmp_path, ("exclude", "exclude"))
    report = evaluate(packet, labels, directory, ["exclude", "exclude"])
    assert report["include_precision"] is None and report["include_recall"] is None
    assert not report["sample_thresholds_met"]


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "record_hash", "packet_hash", "naive_time", "early_review"]
)
def test_annotations_cannot_hide_records_change_inputs_or_forge_review_time(tmp_path, change):
    packet, labels, directory = fixture(tmp_path)
    if change == "missing":
        labels["annotations"].pop()
    elif change == "duplicate":
        labels["annotations"].append(labels["annotations"][0])
    elif change == "record_hash":
        labels["annotations"][0]["record_sha256"] = "0" * 64
    elif change == "packet_hash":
        labels["packet_sha256"] = "0" * 64
    elif change == "naive_time":
        labels["reviewed_at"] = "2024-01-02"
    else:
        labels["reviewed_at"] = "2023-12-31T00:00:00Z"
    with pytest.raises(ValueError):
        evaluate(packet, labels, directory)


def test_corrupt_or_missing_source_capture_fails_closed(tmp_path):
    packet, labels, directory = fixture(tmp_path)
    capture = next(directory.glob("*.json"))
    capture.write_bytes(b"{}")
    with pytest.raises(ValueError, match="capture hash"):
        evaluate(packet, labels, directory)
    capture.unlink()
    with pytest.raises(FileNotFoundError):
        evaluate(packet, labels, directory)


def test_changed_paper_cannot_be_rehashed_away_from_its_original_source(tmp_path):
    packet, labels, directory = fixture(tmp_path)
    row = packet["rows"][0]
    row["paper"]["title"] = "Invented title absent from source capture"
    row["record_sha256"] = _digest(_encode(row["paper"]))
    labels["annotations"][0]["record_sha256"] = row["record_sha256"]
    labels["packet_sha256"] = _digest(_encode(packet))
    with pytest.raises(ValueError, match="differs from captured source"):
        evaluate(packet, labels, directory)


def test_duplicate_versioned_arxiv_identity_is_not_two_candidates(tmp_path):
    packet, labels, directory = fixture(tmp_path)
    row = packet["rows"][1]
    row["paper"]["arxiv_id"] = packet["rows"][0]["paper"]["arxiv_id"] + "v2"
    row["record_sha256"] = _digest(_encode(row["paper"]))
    labels["packet_sha256"] = _digest(_encode(packet))
    with pytest.raises(ValueError, match="Repeated exact paper identity"):
        evaluate(packet, labels, directory)


def test_actual_frozen_fixture_has_complete_hash_verified_review_inventory():
    directory = Path(__file__).parent / "fixtures/relevance"
    report = evaluate_relevance(
        (directory / "candidates.json").read_bytes(),
        (directory / "annotations.json").read_bytes(),
        RelevancePolicy.load("config/overrides.yaml"),
        source_directory=directory / "sources",
    )
    assert report["sample_count"] == 100 and report["required_phenomena_covered"]
    assert report["source_captures_verified"] == 3
    assert report["source_quality"] == {
        "legacy_seed_description": 18,
        "official_arxiv_metadata": 82,
    }
    assert report["reviewer"]["kind"] == "agent"
    assert not report["reviewer"]["independent_of_policy_author"]
    assert not report["population_accuracy_claim"]
    assert sum(sum(row.values()) for row in report["confusion"].values()) == 100


def supplemental_fixture(tmp_path):
    packet, labels, directory = fixture(tmp_path)
    body = "Retained official primary text with the reviewed method dependency."
    capture = {
        "reviewed_paper_id": packet["rows"][0]["paper"]["id"],
        "source_url": "https://arxiv.org/html/2401.00000v1",
        "observed_at": "2024-01-01T12:00:00Z",
        "evidence_kind": "official_primary_full_method",
        "source_body_sha256": _digest(body.encode()),
        "source_body_utf8": body,
    }
    prior_payload = _encode(labels)
    prior_digest = _digest(prior_payload)
    (directory / f"{prior_digest}.annotations.json").write_bytes(prior_payload)
    labels["supersedes_annotations_sha256"] = prior_digest
    labels["annotations"][0]["evidence_basis"] = "supplemental_primary_source"
    return packet, labels, directory, capture


def save_supplemental(labels, directory, capture):
    payload = _encode(capture)
    digest = _digest(payload)
    (directory / f"{digest}.json").write_bytes(payload)
    labels["annotations"][0]["supplemental_source_sha256"] = [digest]


def test_supplemental_review_verifies_capture_without_changing_metric_arithmetic(tmp_path):
    packet, labels, directory, capture = supplemental_fixture(tmp_path)
    save_supplemental(labels, directory, capture)
    report = evaluate(packet, labels, directory)
    assert report["supplemental_source_captures_verified"] == 1
    assert report["supplemental_reviewed_samples"] == 1
    assert report["supersedes_annotations_sha256"] == labels["supersedes_annotations_sha256"]
    assert report["include_precision"] == 0.5


@pytest.mark.parametrize(
    "failure",
    [
        "wrong_identity",
        "future",
        "naive",
        "body_tamper",
        "outer_tamper",
        "no_capture",
        "no_prior",
        "duplicate",
        "wrong_basis",
        "bad_url",
    ],
)
def test_supplemental_review_rejects_unbound_or_invalid_evidence(tmp_path, failure):
    packet, labels, directory, capture = supplemental_fixture(tmp_path)
    if failure == "wrong_identity":
        capture["reviewed_paper_id"] = "another-paper"
    elif failure == "future":
        capture["observed_at"] = "2024-01-03T00:00:00Z"
    elif failure == "naive":
        capture["observed_at"] = "2024-01-01T12:00:00"
    elif failure == "body_tamper":
        capture["source_body_utf8"] += " altered"
    elif failure == "bad_url":
        capture["source_url"] = "https://user:password@arxiv.org/html/2401.00000"
    save_supplemental(labels, directory, capture)
    annotation = labels["annotations"][0]
    if failure == "outer_tamper":
        (directory / f"{annotation['supplemental_source_sha256'][0]}.json").write_bytes(b"{}")
    elif failure == "no_capture":
        annotation["supplemental_source_sha256"] = []
    elif failure == "no_prior":
        labels.pop("supersedes_annotations_sha256")
    elif failure == "duplicate":
        annotation["supplemental_source_sha256"] *= 2
    elif failure == "wrong_basis":
        annotation["evidence_basis"] = "title_and_abstract"
    with pytest.raises(ValueError):
        evaluate(packet, labels, directory)


def test_original_limited_evidence_labels_remain_visible_with_current_policy():
    root = Path(__file__).resolve().parents[1]
    directory = root / "tests/fixtures/relevance"
    report = evaluate_relevance(
        (directory / "candidates.json").read_bytes(),
        (directory / "annotations.json").read_bytes(),
        RelevancePolicy.load(root / "config/overrides.yaml"),
        source_directory=directory / "sources",
    )
    assert report["include_precision"] == 49 / 52
    assert report["include_recall"] == 49 / 50
    assert not report["precision_recall_thresholds_met"]
    assert report["supplemental_reviewed_samples"] == 0
    assert {
        r["sample_id"]
        for r in report["rows"]
        if r["gold"] == "review" and r["predicted"] == "include"
    } == {"R094", "R095", "R096"}


def test_versioned_foundation_labels_preserve_candidate_and_unreviewed_annotations():
    import json

    root = Path(__file__).resolve().parents[1]
    directory = root / "tests/fixtures/relevance"
    prior = (directory / "annotations.json").read_bytes()
    current = json.loads((directory / "annotations-full-method-20261112.json").read_bytes())
    assert current["supersedes_annotations_sha256"] == _digest(prior)
    assert current["independent_of_policy_author"] is False
    before = json.loads(prior)
    changed = []
    for a, b in zip(before["annotations"], current["annotations"], strict=True):
        if a != b:
            changed.append(a["sample_id"])
            assert a["outcome"] == "review" and b["outcome"] == "include"
            assert a["record_sha256"] == b["record_sha256"]
            assert b["evidence_basis"] == "supplemental_primary_source"
    assert changed == ["R094", "R095", "R096"]


@pytest.mark.parametrize(
    "failure",
    [
        "prior_tamper",
        "different_packet",
        "future_prior",
        "missing_prior_row",
        "duplicate_prior_row",
        "changed_without_evidence",
        "composition_change",
    ],
)
def test_supplemental_review_rejects_broken_prior_annotation_chain(tmp_path, failure):
    import json

    packet, labels, directory, capture = supplemental_fixture(tmp_path)
    save_supplemental(labels, directory, capture)
    prior_path = directory / f"{labels['supersedes_annotations_sha256']}.annotations.json"
    if failure == "prior_tamper":
        prior_path.write_bytes(b"{}")
    elif failure in {
        "different_packet",
        "future_prior",
        "missing_prior_row",
        "duplicate_prior_row",
    }:
        previous = json.loads(prior_path.read_bytes())
        if failure == "different_packet":
            previous["packet_sha256"] = "f" * 64
        elif failure == "future_prior":
            previous["reviewed_at"] = "2024-01-03T00:00:00Z"
        elif failure == "duplicate_prior_row":
            previous["annotations"].append(previous["annotations"][0])
        else:
            previous["annotations"].pop()
        payload = _encode(previous)
        digest = _digest(payload)
        (directory / f"{digest}.annotations.json").write_bytes(payload)
        labels["supersedes_annotations_sha256"] = digest
    elif failure == "changed_without_evidence":
        labels["annotations"][1]["outcome"] = "exclude"
    else:
        labels["annotations"][0]["phenomena"].append("invented_stratum")
    with pytest.raises(ValueError):
        evaluate(packet, labels, directory)
