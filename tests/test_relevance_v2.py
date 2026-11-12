"""Representation safety boundaries, curated scope and source-disjoint evidence."""

import json
from pathlib import Path

import pytest

from src.identity import paper_keys
from src.relevance import RelevancePolicy
from src.relevance_benchmark import evaluate_relevance
from src.schema import PaperRecord


@pytest.mark.parametrize(
    "title,abstract,outcome",
    [
        (
            "A CT scene reconstruction study",
            "Reconstructs images using 3D Gaussian smoothing.",
            "exclude",
        ),
        (
            "Radiative reconstruction in astronomy",
            "We fit 3D Gaussian density profiles to thermal images.",
            "exclude",
        ),
        (
            "A neural object classifier",
            "Our object volumes combine 3D Gaussians emitting feature vectors and use inverse rendering for classification.",
            "review",
        ),
        (
            "Performance capture",
            "A collection of 3D Gaussian functions aligns mesh silhouettes to image contours.",
            "review",
        ),
        (
            "Gaussian Shell Models for Human Generation",
            "We sample 3D Gaussians on body shells and differentiably render them.",
            "include",
        ),
        (
            "Gaussian Motion Reconstruction",
            "Each 3D Gaussian encodes a lifetime and velocity for a dynamic scene.",
            "include",
        ),
        (
            "Segment Any 3D Gaussians",
            "We segment targets represented by 3D Gaussian Splatting.",
            "include",
        ),
        (
            "Laboratory robot learning",
            "Digital twins are constructed with 3D Gaussian splatting and physics simulation.",
            "include",
        ),
        (
            "Scene restoration",
            "We restore a 3D Gaussian space from low-light multiview images.",
            "include",
        ),
        (
            "Scene reconstruction",
            "A statistical 3D Gaussian mixture model and Gaussian processes estimate scene structure.",
            "review",
        ),
        (
            "Beta Splatting for Online Scenes",
            "Our beta kernels replace the Gaussian Splatting baseline.",
            "review",
        ),
        (
            "Hexagonal Primitives for Rendering",
            "Our surfels are compared to 2DGS in novel view synthesis.",
            "review",
        ),
        (
            "Gaussian Splatting with Triangle Meshes",
            "A hybrid Gaussian and mesh renderer.",
            "include",
        ),
        ("Algebraic 3D Graphic Statics", "3DGS describes equilibrium force diagrams.", "exclude"),
    ],
)
def test_general_representation_and_application_boundaries(title, abstract, outcome):
    record = PaperRecord(title=title, abstract=abstract)
    assert RelevancePolicy().decide(record).outcome == outcome


def test_foundations_require_exact_reviewed_identity_and_keep_source_evidence():
    directory = Path(__file__).resolve().parents[1]
    policy = RelevancePolicy.load(directory / "config/overrides.yaml")
    for identifier in ("2003.08934", "2103.13415", "2201.05989"):
        paper = PaperRecord(
            id="https://arxiv.org/abs/" + identifier + "v2",
            arxiv_id=identifier + "v2",
            title="Verified foundation",
        )
        decision = policy.decide(paper)
        assert decision.outcome == "include" and decision.override
    unknown = PaperRecord(arxiv_id="2501.00001", title="Another neural radiance field method")
    assert not policy.decide(unknown).override
    for override in policy.config.relevance:
        assert override.reviewed_at.utcoffset() is not None
        if not set(override.identifiers) & {"2003.08934", "2103.13415", "2201.05989"}:
            continue
        assert override.evidence[0].source_url.startswith("https://arxiv.org/abs/")
        assert override.evidence[0].value["source_capture_sha256"]


def test_source_disjoint_packets_with_explicit_scope_review_version_meet_thresholds():
    root = Path(__file__).resolve().parents[1]
    policy = RelevancePolicy.load(root / "config/overrides.yaml")
    inventories = []
    for name in ("relevance", "relevance-challenge"):
        directory = root / "tests/fixtures" / name
        packet_payload = (directory / "candidates.json").read_bytes()
        report = evaluate_relevance(
            packet_payload,
            (
                directory
                / (
                    "annotations-full-method-20261112.json"
                    if name == "relevance"
                    else "annotations.json"
                )
            ).read_bytes(),
            policy,
            source_directory=directory / "sources",
        )
        assert report["sample_count"] == 100
        assert report["include_precision"] >= 0.95
        assert report["include_recall"] >= 0.95
        assert report["precision_recall_thresholds_met"]
        assert not report["population_accuracy_claim"]
        keys = set()
        for row in json.loads(packet_payload)["rows"]:
            keys.update(paper_keys(PaperRecord.model_validate(row["paper"])))
        inventories.append(keys)
    assert not inventories[0].intersection(inventories[1])


def test_reviewed_cvpr_applications_require_exact_identity_and_captured_evidence():
    root = Path(__file__).resolve().parents[1]
    policy = RelevancePolicy.load(root / "config/overrides.yaml")
    for identifier in ("2503.18421", "2502.14454"):
        record = PaperRecord(arxiv_id=identifier, title="Source-reviewed application")
        decision = policy.decide(record)
        assert decision.outcome == "include" and decision.override
        override = next(x for x in policy.config.relevance if identifier in x.identifiers)
        evidence = override.evidence[0]
        assert evidence.reviewed_by and evidence.reviewed_at >= evidence.observed_at
        assert len(evidence.value["official_capture_sha256"]) == 64
        assert evidence.source_url.startswith(
            ("https://openaccess.thecvf.com/", "https://arxiv.org/html/")
        )
    assert not policy.decide(PaperRecord(title="DeepDeblurRF-G 4DGC")).override
