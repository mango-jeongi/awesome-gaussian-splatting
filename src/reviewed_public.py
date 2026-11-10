"""Accepted source-table evidence for lazy public details; no figure redistribution."""

from src.workers.review import ReviewedExtractionStore


def reviewed_cells(db, reviewed):
    store = ReviewedExtractionStore.model_validate(reviewed.model_dump())
    active = {paper.id: paper for paper in db.papers}
    grouped = {}
    for key, item in sorted(store.records.items()):
        if (
            item.paper_id not in active
            or item.original.kind != "numeric_cell"
            or item.decision.disposition != "accepted"
        ):
            continue
        decision = item.decision
        paper = active[item.paper_id]
        url = next(
            (
                value
                for value in (item.source_url, paper.pdf_url, paper.paper_url)
                if value and value.startswith(("https://", "http://"))
            ),
            None,
        )
        grouped.setdefault(item.paper_id, []).append(
            {
                "evidence_id": key,
                "dataset": decision.dataset,
                "split": decision.split,
                "method": decision.row_label,
                "metric": decision.metric,
                "unit": decision.unit,
                "value": decision.accepted_value,
                "parsed_value": item.original.raw_value,
                "page": item.original.page,
                "bbox": item.original.bbox,
                "source_url": url,
                "pdf_sha256": item.pdf_sha256,
                "reviewed_by": decision.reviewed_by,
                "reviewed_at": decision.reviewed_at.isoformat(),
            }
        )
    return grouped
