"""Initial database seeding utility combining local NPS Papers metadata and arXiv backfill."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from src.contracts import FieldEvidence
from src.enricher import MultiProviderEnricher
from src.extractors.arxiv import ArxivExtractor
from src.identity import normalize_arxiv
from src.schema import PaperDatabase, PaperRecord

ARXIV_FILENAME_RE = re.compile(r"\b(\d{4}\.\d{4,5})\b")


def load_local_papers(
    success_json_path: str | Path, enricher: MultiProviderEnricher
) -> list[PaperRecord]:
    """Import 3DGS, NeRF, spatial reconstruction, and medical/defense 3D papers from local success.json."""
    path = Path(success_json_path)
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as f:
        raw_items = json.load(f)

    records: list[PaperRecord] = []
    for item in raw_items:
        cat = item.get("category", "")
        title = item.get("title", "")
        abstract = item.get("abstract", "")
        text_lower = f"{title} {abstract} {cat}".lower()

        # Include all 3D Gaussian Splatting & CV papers, plus relevant 3D/spatial papers across categories
        is_relevant = cat == "3D Gaussian Splatting & Computer Vision" or any(
            kw in text_lower
            for kw in (
                "gaussian splatting",
                "3dgs",
                "4dgs",
                "2dgs",
                "radiance field",
                "nerf",
                "3d ultrasound",
                "3d reconstruction",
                "digital twin",
                "slam",
            )
        )
        if not is_relevant:
            continue

        supplied_date = item.get("published_date")
        if supplied_date:
            parsed_date = date.fromisoformat(str(supplied_date))
            year, month = parsed_date.year, parsed_date.month
            publication_date = parsed_date.isoformat()
            precision = "day"
        else:
            year_str = str(item.get("year") or "")
            if not year_str.isdigit() or not 1990 <= int(year_str) <= 2100:
                raise ValueError(f"Seed requires reviewed publication year: {title}")
            year = int(year_str)
            supplied_month = item.get("month")
            if supplied_month is None or supplied_month == "":
                month, precision = 1, "year"
            else:
                month_str = str(supplied_month)
                if not month_str.isdigit() or not 1 <= int(month_str) <= 12:
                    raise ValueError(f"Seed requires reviewed publication month: {title}")
                month, precision = int(month_str), "month"
            publication_date = f"{year:04d}-{month:02d}-01"
        # Identifier hints from the filename never establish publication day precision.
        arxiv_match = ARXIV_FILENAME_RE.search(str(item.get("file") or ""))
        arxiv_id = (
            normalize_arxiv(str(item["arxiv_id"]))
            if item.get("arxiv_id")
            else (arxiv_match.group(1) if arxiv_match else None)
        )
        source = "manual"  # The local cache is the source; an arXiv ID is identifier evidence.

        subcat = item.get("subcategory")
        initial_cats = [subcat] if subcat else []

        rec = PaperRecord(
            arxiv_id=arxiv_id,
            source=source,
            title=title,
            authors=item.get("authors") or ["Unknown"],
            published_date=publication_date,
            published_date_precision=precision,
            metadata_evidence={
                "published_date": [
                    FieldEvidence(
                        source="local_seed_metadata",
                        source_url=f"local-seed:{path.name}",
                        value=publication_date,
                    )
                ]
            },
            year=year,
            month=month,
            abstract=abstract,
            categories=initial_cats or ["Foundations & Acceleration"],
        )
        records.append(enricher.enrich(rec, use_llm=False))

    return records


def seed_database(
    data_path: str | Path,
    taxonomy_path: str | Path,
    local_success_json: str | Path | None = None,
    fetch_arxiv_count: int = 100,
) -> int:
    """Seed `data/papers.json` from local curated papers and live arXiv backfill."""
    db = PaperDatabase.load(data_path) if Path(data_path).exists() else PaperDatabase()
    enricher = MultiProviderEnricher(taxonomy_path)

    all_records: list[PaperRecord] = []

    if local_success_json and Path(local_success_json).exists():
        local_recs = load_local_papers(local_success_json, enricher)
        all_records.extend(local_recs)

    if fetch_arxiv_count > 0:
        try:
            extractor = ArxivExtractor()
            arxiv_recs = extractor.fetch_recent(max_results=fetch_arxiv_count)
            for r in arxiv_recs:
                all_records.append(enricher.enrich(r, use_llm=False))
        except Exception as exc:
            print(f"[seed] Warning: Live arXiv fetch skipped or failed ({exc}); using local seed.")

    added = db.upsert(all_records)
    db.save(data_path)
    return added
