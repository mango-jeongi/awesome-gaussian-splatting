"""Offline topic-policy regression cases, not a population accuracy estimate."""

from datetime import UTC, datetime

import pytest

from src.contracts import FieldEvidence
from src.relevance import OverrideConfig, RelevanceOverride, RelevancePolicy
from src.schema import PaperRecord


@pytest.mark.parametrize(
    "title,abstract,outcome",
    [
        ("3D Gaussian Splatting for radiance fields", "", "include"),
        ("Gaussian Splatting for medical ultrasound", "", "include"),
        ("Gaussian Splatting for SAR reconstruction", "", "include"),
        ("Thermal Gaussian Splatting", "", "include"),
        ("2D Gaussian splats for surfaces", "", "include"),
        ("GaussianSplatting acceleration", "", "include"),
        (
            "UltraGauss ultrasound volumes",
            "Reconstructs 3D ultrasound from sparse scans using differentiable Gaussian primitives.",
            "include",
        ),
        (
            "Streaming 3D Gaussians",
            "Streams neural scene rendering with Gaussian primitives.",
            "include",
        ),
        ("3D Gaussian avatars in VR", "Real-time avatar synthesis.", "include"),
        ("Image-GS via 2D Gaussians", "Content-adaptive image compression.", "include"),
        ("UAV reconstruction using Gaussian Splatt...", "A scene capture pipeline.", "review"),
        ("3D Gaussian kernels in ultrasound", "Statistical reconstruction.", "review"),
        ("Gaussian‑Splatting renderer", "", "include"),
        ("4DGS for dynamic scenes", "A radiance field model.", "include"),
        ("3D-GS with differentiable rasterization", "", "include"),
        (
            "A new reconstruction system",
            "We introduce Gaussian splatting for novel view synthesis.",
            "include",
        ),
        ("3DGS in geological survey", "Analysis of geographic survey records.", "review"),
        ("2DGS chemical statistics", "A Gaussian statistical model.", "review"),
        ("NeRF: a neural radiance field foundation", "", "review"),
        ("A scene representation", "We study 3D Gaussians.", "review"),
        ("A brief comparison", "Related work mentions Gaussian splatting.", "review"),
        ("Gaussian processes for ultrasound segmentation", "", "exclude"),
        ("MRI classification with convolutional neural networks", "", "exclude"),
        ("Gaussian mixture inference", "A mathematical density estimation problem.", "exclude"),
        ("Thermal sensor calibration", "Temperature measurement using regression.", "exclude"),
        ("Statistical splattering", "A Gaussian splattering process in chemistry.", "exclude"),
        ("Digital twins for logistics", "A supply chain simulation system.", "exclude"),
        ("Unrelated medical paper", "Reconstruction in ultrasound imaging.", "exclude"),
    ],
)
def test_topic_dispositions(title, abstract, outcome):
    record = PaperRecord(
        title=title, abstract=abstract, primary_category="Medical, Defense & Multimodal Sensors"
    )
    assert RelevancePolicy().decide(record).outcome == outcome


def override(identifier, action):
    return RelevanceOverride(
        identifiers=[identifier],
        action=action,
        reason="Fixture-only reviewed scope",
        evidence=[FieldEvidence(source="fixture-review", value="Explicit foundation evidence")],
        reviewed_by="fixture reviewer",
        reviewed_at=datetime(2026, 11, 8, tzinfo=UTC),
    )


def test_reviewed_foundation_override_and_policy_digest():
    paper = PaperRecord(arxiv_id="2003.08934", title="Neural radiance field foundation")
    baseline = RelevancePolicy()
    policy = RelevancePolicy(
        OverrideConfig(relevance=[override("https://arxiv.org/abs/2003.08934v2", "include")])
    )
    assert baseline.decide(paper).outcome == "review"
    assert policy.decide(paper).outcome == "include"
    assert policy.decide(paper).override
    assert policy.digest != baseline.digest
    assert RelevancePolicy().digest == baseline.digest


def test_conflicting_override_aliases_fail_validation():
    with pytest.raises(ValueError, match="Conflicting"):
        RelevancePolicy(
            OverrideConfig(
                relevance=[
                    override("2401.12345", "include"),
                    override("arxiv:2401.12345", "exclude"),
                ]
            )
        )
    policy = RelevancePolicy(
        OverrideConfig(
            relevance=[override("2401.12345", "include"), override("10.1000/conflict", "exclude")]
        )
    )
    with pytest.raises(ValueError, match="contradictory"):
        policy.decide(
            PaperRecord(
                arxiv_id="2401.12345",
                doi="10.1000/conflict",
                title="A conflicting identity fixture",
            )
        )


def test_official_cvf_comparison_only_abstracts_require_review():
    import json
    from pathlib import Path

    cases = json.loads(
        (Path(__file__).parent / "fixtures/cvf-comparison-regressions.json").read_text(
            encoding="utf-8"
        )
    )["cases"]
    for case in cases:
        paper = PaperRecord(id=case["source_url"], title=case["title"], abstract=case["abstract"])
        assert RelevancePolicy().decide(paper).outcome == case["expected"], case["title"]


def test_source_backed_review_override_holds_otherwise_included_candidate():
    from datetime import UTC, datetime

    from src.contracts import FieldEvidence
    from src.relevance import OverrideConfig, RelevanceOverride

    paper = PaperRecord(arxiv_id="2501.00001", title="Gaussian Splatting comparison")
    assert RelevancePolicy().decide(paper).outcome == "include"
    now = datetime.now(UTC)
    override = RelevanceOverride(
        identifiers=[paper.arxiv_id],
        action="review",
        reason="Author abstract describes an alternative method; exact scope needs review",
        evidence=[FieldEvidence(source="fixture author abstract", value=paper.title)],
        reviewed_by="fixture reviewer",
        reviewed_at=now,
    )
    decision = RelevancePolicy(OverrideConfig(relevance=[override])).decide(paper)
    assert decision.outcome == "review" and decision.override


def test_primary_gaussian_splattings_methods_are_recognized():
    import json
    from pathlib import Path

    cases = json.loads(
        (Path(__file__).parent / "fixtures/gaussian-splattings-regressions.json").read_text(
            encoding="utf-8"
        )
    )["cases"]
    for case in cases:
        paper = PaperRecord(
            arxiv_id=case["source_id"], title=case["title"], abstract=case["abstract"]
        )
        assert RelevancePolicy().decide(paper).outcome == "include", case["source_id"]


@pytest.mark.parametrize(
    "title,abstract",
    [
        ("A brief comparison", "Related work mentions Gaussian Splattings."),
        (
            "A NeRF reconstruction method",
            "Previous Gaussian Splattings approaches render scenes; we use NeRF instead.",
        ),
        ("Scene reconstruction", "We discuss Gaussian splattingsomething for rendering."),
    ],
)
def test_plural_spelling_preserves_scope_and_word_boundaries(title, abstract):
    paper = PaperRecord(id="plural-boundary-fixture", title=title, abstract=abstract)
    assert RelevancePolicy().decide(paper).outcome != "include"
