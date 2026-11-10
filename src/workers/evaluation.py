"""Score extraction against an explicit reviewed positive subset; no population precision claim."""

import argparse
import hashlib
from pathlib import Path

from src.storage import _encode
from src.workers.queue import ExtractionResult
from src.workers.review import ReviewedExtractionStore

CONTEXT_FIELDS = ("row_label", "column_label", "dataset", "split", "metric", "unit")


def text(value):
    return " ".join((value or "").split())


def inside_fraction(predicted, reference):
    x0, y0, x1, y1 = predicted
    a0, b0, a1, b1 = reference
    overlap = max(0, min(x1, a1) - max(x0, a0)) * max(0, min(y1, b1) - max(y0, b0))
    return overlap / ((x1 - x0) * (y1 - y0))


def evaluate(store, results, paper_ids):
    if not paper_ids or len(paper_ids) != len(set(paper_ids)):
        raise ValueError("Select unique paper IDs for the reviewed evaluation scope")
    references = {
        key: record
        for key, record in store.records.items()
        if record.paper_id in paper_ids
        and record.original.kind == "numeric_cell"
        and record.decision.disposition == "accepted"
    }
    if {record.paper_id for record in references.values()} != set(paper_ids):
        raise ValueError("Every selected paper requires accepted numeric reference cells")
    expected = {}
    for record in references.values():
        expected.setdefault(record.paper_id, set()).add(record.pdf_sha256)
    if any(len(hashes) != 1 for hashes in expected.values()):
        raise ValueError("Multiple reviewed PDF versions require a separate scoped ledger")
    groups = {}
    for result in results:
        if result.paper_id not in expected or result.pdf_sha256 not in expected[result.paper_id]:
            raise ValueError("Prediction is outside the selected paper/PDF scope")
        group = groups.setdefault(result.extractor_version, {})
        if result.paper_id in group:
            raise ValueError("Duplicate result for the same extractor and source paper")
        group[result.paper_id] = result
    if not groups:
        raise ValueError("Supply at least one extraction result")
    summaries = []
    for version, papers in sorted(groups.items()):
        matches, ambiguous, outside, duplicates = {}, 0, 0, 0
        collided = set()
        for result in papers.values():
            for candidate in result.candidates:
                if candidate.kind != "numeric_cell":
                    continue
                targets = [
                    key
                    for key, ref in references.items()
                    if ref.paper_id == result.paper_id
                    and ref.original.page == candidate.page
                    and inside_fraction(candidate.bbox, ref.original.bbox) >= 0.8
                ]
                if len(targets) > 1:
                    ambiguous += 1
                elif not targets:
                    outside += 1
                elif targets[0] in collided:
                    duplicates += 1
                elif targets[0] in matches:
                    duplicates += 1
                    del matches[targets[0]]
                    collided.add(targets[0])
                else:
                    matches[targets[0]] = candidate
        rows = []
        for key, ref in sorted(references.items()):
            candidate = matches.get(key)
            rows.append(
                {
                    "review_key": key,
                    "paper_id": ref.paper_id,
                    "page": ref.original.page,
                    "matched": candidate is not None,
                    "value_exact": text(candidate.raw_value) == text(ref.decision.accepted_value)
                    if candidate
                    else False,
                    "context": {
                        field: (
                            "missing"
                            if not candidate or not text(getattr(candidate, field))
                            else "exact"
                            if text(getattr(candidate, field)) == text(getattr(ref.decision, field))
                            else "different"
                        )
                        for field in CONTEXT_FIELDS
                    },
                }
            )
        matched = len(matches)
        exact = sum(row["value_exact"] for row in rows)
        summaries.append(
            {
                "extractor_version": version,
                "selected_papers": len(paper_ids),
                "papers_with_results": len(papers),
                "reference_cells": len(references),
                "matched_cells": matched,
                "exact_value_cells": exact,
                "reviewed_subset_recall": matched / len(references),
                "exact_value_recall": exact / len(references),
                "exact_value_fraction_of_matches": exact / matched if matched else None,
                "candidates_outside_accepted_reference_subset_not_scored": outside,
                "ambiguous_coordinate_candidates": ambiguous,
                "duplicate_coordinate_candidates": duplicates,
                "duplicate_coordinate_cells_refused": len(collided),
                "context_counts": {
                    field: {
                        state: sum(row["context"][field] == state for row in rows)
                        for state in ("exact", "different", "missing")
                    }
                    for field in CONTEXT_FIELDS
                },
                "rows": rows,
            }
        )
    return {
        "scope": "Explicit accepted numeric-cell subset only; not full table/corpus recall or precision",
        "paper_ids": sorted(paper_ids),
        "population_precision": None,
        "reviewers": sorted({record.decision.reviewed_by for record in references.values()}),
        "matching": "Same paper/PDF/page; at least 80% of predicted box inside reviewed box; ambiguous matches refused",
        "text_comparison": "Whitespace normalization only; case-sensitive; no numeric/unit conversions",
        "limitations": [
            "Review labels are existing source-inspected references, not an independent human benchmark.",
            "Predictions outside the accepted reference subset are not scored or labelled false positives.",
            "Context string differences require inspection; equivalent paraphrases can differ.",
            "No speed, VRAM, model-weight attestation or live model superiority is established.",
        ],
        "evaluations": summaries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed", type=Path, required=True)
    parser.add_argument("--result", type=Path, action="append", required=True)
    parser.add_argument("--paper-id", action="append", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.report.resolve()
    if output.exists() or any(
        p == output or p in output.parents for p in (root / "data", root / "docs")
    ):
        parser.error("Use a new report path outside canonical data and deployed docs")
    raw = args.reviewed.read_bytes()
    results = [p.read_bytes() for p in args.result]
    report = evaluate(
        ReviewedExtractionStore.model_validate_json(raw),
        [ExtractionResult.model_validate_json(value) for value in results],
        args.paper_id,
    )
    report.update(
        reviewed_ledger_sha256=hashlib.sha256(raw).hexdigest(),
        result_sha256=[hashlib.sha256(value).hexdigest() for value in results],
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(_encode(report))
    print(f"[extraction-evaluation] {len(report['evaluations'])} extractor group(s); {output}")


if __name__ == "__main__":
    main()
