"""Initial database seeding utility combining local NPS Papers metadata and arXiv backfill."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.enricher import MultiProviderEnricher
from src.extractors.arxiv import ArxivExtractor
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

        year_str = str(item.get("year") or "2024")
        month_str = str(item.get("month") or "01")
        year = int(year_str) if year_str.isdigit() else 2024
        month = int(month_str) if month_str.isdigit() and 1 <= int(month_str) <= 12 else 1

        # Determine source (arXiv vs non-arXiv schema-on-read test)
        arxiv_match = ARXIV_FILENAME_RE.search(f"{item.get('file', '')} {abstract}")
        arxiv_id = arxiv_match.group(1) if arxiv_match else None
        source = "arxiv" if arxiv_id else "manual"

        subcat = item.get("subcategory")
        initial_cats = [subcat] if subcat else []

        rec = PaperRecord(
            arxiv_id=arxiv_id,
            source=source,
            title=title,
            authors=item.get("authors") or ["Unknown"],
            published_date=f"{year:04d}-{month:02d}-01",
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
    db = PaperDatabase.load(data_path)
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
