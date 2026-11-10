"""Public payload, parity, and deterministic generation acceptance tests."""

import json
from pathlib import Path

from src.public import DETAIL_LIMIT, build_public
from src.schema import PaperDatabase


def fixture_5000():
    source = PaperDatabase.load(Path(__file__).resolve().parents[1] / "data" / "papers.json")
    papers = []
    for position in range(5000):
        original = source.papers[position % len(source.papers)]
        identifier = f"2501.{position:05d}"
        papers.append(
            original.model_copy(
                update={
                    "id": identifier,
                    "arxiv_id": identifier,
                    "doi": None,
                    "arxiv_doi": None,
                    "metadata_evidence": {},
                    "openalex_id": None,
                    "paper_url": f"https://arxiv.org/abs/{identifier}",
                    "pdf_url": f"https://arxiv.org/pdf/{identifier}.pdf",
                    "referenced_works": [],
                    "db_references": [f"2501.{position - 1:05d}"] if position else [],
                    "db_citations": [f"2501.{position + 1:05d}"] if position < 4999 else [],
                    "db_citation_count": int(position < 4999),
                }
            )
        )
    return PaperDatabase(papers=papers, total_count=5000, last_updated="2026-11-08T00:00:00Z")


def test_5000_payload_and_lazy_search_parity(tmp_path):
    db = fixture_5000()
    manifest = build_public(db, tmp_path)
    assert manifest["index"]["bytes"] <= 4_000_000
    assert manifest["index"]["bytes"] / 5000 <= 750
    assert all(artifact["bytes"] <= DETAIL_LIMIT for artifact in manifest["details"])
    index = json.loads((tmp_path / manifest["index"]["path"]).read_bytes())
    search = json.loads((tmp_path / manifest["search"]["path"]).read_bytes())
    assert "abstract" not in index["fields"]
    assert "authors" not in index["fields"]
    assert len(index["papers"]) == len(search) == 5000
    pointer_position = index["fields"].index("detail_path")
    id_position = index["fields"].index("id")
    for row in index["papers"]:
        path = index["detail_paths"][row[pointer_position]]
        assert row[id_position] in json.loads((tmp_path / path).read_bytes())
    records = {}
    for artifact in manifest["details"]:
        records.update(json.loads((tmp_path / artifact["path"]).read_bytes()))
    for paper in db.papers:
        assert records[paper.id]["abstract"] == paper.abstract
        assert records[paper.id]["authors"] == paper.authors
        assert paper.abstract.lower() in search[paper.id]
        assert records[paper.id]["citation_status"] == "unknown"
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in tmp_path.rglob("*.json")
    }
    assert build_public(db, tmp_path) == manifest
    assert before == {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in tmp_path.rglob("*.json")
    }


def test_successful_zero_stays_available_after_refresh_error(tmp_path):
    from datetime import UTC, datetime, timedelta

    from src.observations import SignalStore
    from src.schema import PaperRecord

    paper = PaperRecord(title="Observed zero citation method", citation_count=7)
    db = PaperDatabase(papers=[paper], total_count=1)
    signals = SignalStore(provider="openalex")
    now = datetime(2026, 11, 8, tzinfo=UTC)
    signals.apply(paper.id, status="ok", provider_id="W1", values={"citation_count": 0}, now=now)
    signals.apply(paper.id, status="error", now=now + timedelta(hours=1))
    db._signal_stores["openalex"] = signals
    manifest = build_public(db, tmp_path)
    index = json.loads((tmp_path / manifest["index"]["path"]).read_bytes())
    assert index["papers"][0][index["fields"].index("citation_count")] == 0
    assert index["papers"][0][index["fields"].index("citation_status")] == "error"


def test_public_dates_keep_precision_and_archive_is_separate(tmp_path):
    from datetime import UTC, datetime

    from src.contracts import FieldEvidence
    from src.curation import archive_paper
    from src.schema import PaperRecord

    records = [
        PaperRecord(
            id="day",
            title="Precisely dated method",
            published_date="2024-07-15",
            published_date_precision="day",
        ),
        PaperRecord(
            id="month",
            title="Month dated method",
            published_date="2024-07-01",
            published_date_precision="month",
        ),
        PaperRecord(
            id="year",
            title="Year dated method",
            published_date="2024-01-01",
            published_date_precision="year",
        ),
        PaperRecord(id="legacy", title="Unknown precision method", published_date="2024-09-21"),
    ]
    db = PaperDatabase(papers=records, total_count=4)
    archive_paper(
        db,
        "legacy",
        disposition="excluded",
        reason="Fixture-only reviewed archive",
        evidence=[FieldEvidence(source="fixture", value="reviewed evidence")],
        reviewed_by="fixture reviewer",
        reviewed_at=datetime(2026, 11, 8, tzinfo=UTC),
    )
    manifest = build_public(db, tmp_path)
    index = json.loads((tmp_path / manifest["index"]["path"]).read_bytes())
    rows = {row[0]: dict(zip(index["fields"], row, strict=True)) for row in index["papers"]}
    for row in rows.values():
        row["published_date_precision"] = index["date_precisions"][row["published_date_precision"]]
    assert rows["day"]["published_date_precision"] == "day"
    assert rows["month"]["published_date_precision"] == "month"
    assert rows["year"]["published_date_precision"] == "year"
    assert "legacy" not in rows
    archive = json.loads((tmp_path / manifest["archive"]["path"]).read_bytes())
    assert archive["papers"]["legacy"]["disposition"] == "excluded"
    assert archive["aliases"]["legacy"] == "legacy"
    assert (
        "paper" not in archive["papers"]["legacy"]
    )  # Full archival records stay in canonical storage.


def test_legacy_public_export_does_not_embed_full_archive(tmp_path):
    from datetime import UTC, datetime

    from src.builder import build_artifacts
    from src.contracts import FieldEvidence
    from src.curation import archive_paper
    from src.schema import PaperRecord

    db = PaperDatabase(
        papers=[
            PaperRecord(id="removed", title="Excluded fixture"),
            PaperRecord(id="active", title="Active fixture"),
        ],
        total_count=2,
    )
    archive_paper(
        db,
        "removed",
        disposition="excluded",
        reason="Fixture-only exclusion",
        evidence=[FieldEvidence(source="fixture", value="evidence")],
        reviewed_by="fixture reviewer",
        reviewed_at=datetime(2026, 11, 8, tzinfo=UTC),
    )
    source = tmp_path / "canonical" / "manifest.json"
    db.save(source)
    destination = tmp_path / "docs" / "papers.json"
    build_artifacts(
        source,
        Path(__file__).resolve().parents[1] / "config" / "taxonomy.yaml",
        tmp_path / "README.md",
        destination,
    )
    exported = PaperDatabase.load(destination)
    assert exported.archive == {}
    assert [paper.id for paper in exported.papers] == ["active"]
    assert "removed" in PaperDatabase.load(source).archive
    manifest = json.loads((tmp_path / "docs" / "data" / "manifest.json").read_bytes())
    tombstones = json.loads((tmp_path / "docs" / "data" / manifest["archive"]["path"]).read_bytes())
    assert tombstones["papers"]["removed"]["disposition"] == "excluded"
