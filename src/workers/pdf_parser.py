"""Conservative ruled-table/image candidates; run only inside the bounded child process."""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from src.workers.queue import ExtractedCandidate, ExtractionJob, ExtractionResult


def extractor_version():
    return f"pdfplumber-{version('pdfplumber')}-lines-v1"


def extract(job: ExtractionJob, path: Path) -> ExtractionResult:
    import pdfplumber

    if job.extractor_version != extractor_version():
        raise ValueError("Extractor version differs from job contract")
    with path.open("rb") as stream:
        payload = stream.read(job.limits.max_bytes + 1)
    if len(payload) > job.limits.max_bytes:
        raise OverflowError("size_limit")
    if hashlib.sha256(payload).hexdigest() != job.pdf_sha256 or not payload.startswith(b"%PDF-"):
        raise ValueError("invalid_pdf")
    candidates = []
    warnings = [
        "Unreviewed candidates; dataset/split/metric/unit context requires source review.",
        "Ruled tables and embedded images only; borderless tables and vector figures may be missed.",
    ]
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        count = len(pdf.pages)
        if not count:
            raise ValueError("invalid_pdf")
        if count > job.limits.max_pages:
            raise OverflowError("page_limit")
        for page in pdf.pages:
            for table in page.find_tables():
                rows = table.extract()
                heading = " | ".join(str(value or "") for value in rows[0])[:1000] if rows else None
                for row_index, row in enumerate(rows):
                    for column_index, text in enumerate(row):
                        if not text or not re.search(r"\d", text):
                            continue
                        bbox = table.rows[row_index].cells[column_index]
                        if bbox is None:
                            continue
                        candidates.append(
                            ExtractedCandidate(
                                kind="numeric_cell",
                                page=page.page_number,
                                bbox=bbox,
                                table_heading=heading,
                                row_label=str(row[0] or "")[:500],
                                column_label=str(rows[0][column_index] or "")[:500],
                                raw_value=str(text)[:1000],
                                confidence=0.5,
                            )
                        )
                        if len(candidates) >= 5000:
                            raise OverflowError("candidate_limit")
            for image in page.images:
                bbox = (image["x0"], image["top"], image["x1"], image["bottom"])
                if min(bbox) < 0 or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
                    continue
                candidates.append(
                    ExtractedCandidate(
                        kind="figure", page=page.page_number, bbox=bbox, confidence=0.25
                    )
                )
                if len(candidates) >= 5000:
                    raise OverflowError("candidate_limit")
            page.close()
    return ExtractionResult(
        job_key=job.key,
        paper_id=job.paper_id,
        pdf_sha256=job.pdf_sha256,
        extractor_version=job.extractor_version,
        completed_at=datetime.now(UTC),
        page_count=count,
        candidates=candidates,
        warnings=warnings,
    )


def main():
    job = ExtractionJob.model_validate_json(sys.stdin.buffer.read(100000))
    try:
        result = extract(job, Path(sys.argv[1]))
    except OverflowError as error:
        return {"size_limit": 3, "page_limit": 4}.get(str(error), 5)
    except (ValueError, OSError):
        return 2
    except Exception:
        return 5
    sys.stdout.write(json.dumps(result.model_dump(mode="json"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
