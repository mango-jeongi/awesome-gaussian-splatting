from datetime import UTC, datetime
from types import SimpleNamespace

from src.reviewed_public import reviewed_cells
from src.schema import PaperRecord
from src.workers.queue import ExtractedCandidate
from src.workers.review import CandidateDecision, ReviewedCandidate, ReviewedExtractionStore


def test_public_projection_only_accepted_active_numeric_evidence():
    paper = PaperRecord(id="p", title="Fixture method", pdf_url="https://example.org/p.pdf")
    store = ReviewedExtractionStore()
    for index, (paper_id, kind, disposition) in enumerate(
        [
            ("p", "numeric_cell", "accepted"),
            ("p", "numeric_cell", "rejected"),
            ("inactive", "numeric_cell", "accepted"),
            ("p", "figure", "accepted"),
        ]
    ):
        decision = CandidateDecision(
            candidate_index=index,
            disposition=disposition,
            reason="Fixture checked",
            source_checked=True,
            reviewed_by="fixture reviewer",
            reviewed_at=datetime(2026, 11, 9, tzinfo=UTC),
            dataset="Dataset",
            split="test",
            metric="PSNR",
            unit="dB",
            row_label="<script>method</script>",
            column_label="PSNR",
            accepted_value="31.40",
            caption="Fixture caption",
            reuse_basis="Original fixture",
        )
        original = ExtractedCandidate(
            kind=kind,
            page=2,
            bbox=(1, 2, 3, 4),
            raw_value="31.4" if kind == "numeric_cell" else None,
            confidence=0.5,
        )
        store.records[f"job:{index}"] = ReviewedCandidate(
            paper_id=paper_id,
            job_key="job",
            pdf_sha256="a" * 64,
            result_sha256="b" * 64,
            source_url="file:///private/source.pdf",
            original=original,
            decision=decision,
        )
    projection = reviewed_cells(SimpleNamespace(papers=[paper]), store)
    assert list(projection) == ["p"] and len(projection["p"]) == 1
    cell = projection["p"][0]
    assert cell["value"] == "31.40" and cell["parsed_value"] == "31.4"
    assert cell["method"] == "<script>method</script>"
    assert cell["source_url"] == "https://example.org/p.pdf" and cell["page"] == 2
    assert "private" not in str(projection)
