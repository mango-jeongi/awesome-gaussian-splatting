from types import SimpleNamespace as NS

import pytest

from src.workers.evaluation import CONTEXT_FIELDS, evaluate
from src.workers.queue import ExtractedCandidate


def reference():
    decision = NS(
        disposition="accepted",
        accepted_value="32.15",
        reviewed_by="fixture reviewer",
        row_label="Model A",
        column_label="PSNR",
        metric="PSNR",
        unit="dB",
        dataset="Scene",
        split="test",
    )
    return NS(
        paper_id="p",
        pdf_sha256="a" * 64,
        original=NS(kind="numeric_cell", page=1, bbox=(0, 0, 100, 20)),
        decision=decision,
    )


def candidate(**updates):
    return ExtractedCandidate(
        kind="numeric_cell",
        page=1,
        bbox=(20, 2, 40, 15),
        raw_value=updates.pop("raw_value", "32.15"),
        confidence=0.25,
        **updates,
    )


def result(candidates, **updates):
    return NS(
        paper_id="p",
        pdf_sha256="a" * 64,
        extractor_version="fixture-v1",
        candidates=candidates,
        **updates,
    )


def score(candidates):
    return evaluate(NS(records={"reference": reference()}), [result(candidates)], ["p"])


def test_value_and_context_are_scored_independently():
    payload = score([candidate(unit="dB", metric="SSIM")])
    item = payload["evaluations"][0]
    assert item["matched_cells"] == item["exact_value_cells"] == 1
    assert item["context_counts"]["unit"]["exact"] == 1
    assert item["context_counts"]["metric"]["different"] == 1
    assert item["context_counts"]["dataset"]["missing"] == 1
    assert payload["population_precision"] is None


def test_outside_subset_predictions_are_unverified_not_false_positives():
    outside = candidate().model_copy(update={"bbox": (200, 2, 220, 15)})
    item = score([outside])["evaluations"][0]
    assert item["matched_cells"] == 0
    assert item["exact_value_fraction_of_matches"] is None
    assert item["candidates_outside_accepted_reference_subset_not_scored"] == 1


def test_duplicate_predictions_refuse_cell_instead_of_choosing_a_favorable_order():
    for candidates in (
        [candidate(), candidate(raw_value="99")],
        [candidate(raw_value="99"), candidate()],
    ):
        item = score(candidates)["evaluations"][0]
        assert item["matched_cells"] == 0
        assert item["duplicate_coordinate_cells_refused"] == 1


def test_unknown_pdf_or_duplicate_source_result_refused():
    source = result([])
    source.pdf_sha256 = "b" * 64
    with pytest.raises(ValueError, match="scope"):
        evaluate(NS(records={"reference": reference()}), [source], ["p"])
    with pytest.raises(ValueError, match="Duplicate result"):
        evaluate(NS(records={"reference": reference()}), [result([]), result([])], ["p"])


def test_wrong_value_does_not_get_credit_from_correct_unit():
    item = score([candidate(raw_value="32.16", unit="dB")])["evaluations"][0]
    assert item["matched_cells"] == 1 and item["exact_value_cells"] == 0
    assert item["context_counts"]["unit"]["exact"] == 1
    assert all(
        sum(states.values()) == 1
        for field, states in item["context_counts"].items()
        if field in CONTEXT_FIELDS
    )


def test_unit_case_is_significant_for_scale_prefixes():
    ref = reference()
    ref.decision.unit = "mW"
    item = evaluate(NS(records={"reference": ref}), [result([candidate(unit="MW")])], ["p"])[
        "evaluations"
    ][0]
    assert item["context_counts"]["unit"]["different"] == 1
    assert item["context_counts"]["unit"]["exact"] == 0
