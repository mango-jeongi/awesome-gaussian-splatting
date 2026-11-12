"""Coverage uses actual observations and fails closed on inconsistent snapshots."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import yaml

from src.cli import main
from src.coverage import SnapshotInputs, coverage_snapshot, write_coverage_report
from src.observations import SignalStore
from src.openalex_cache import CitationSample, OpenAlexCache
from src.schema import PaperDatabase, PaperRecord
from src.storage import _encode, write_store

NOW = datetime(2026, 11, 11, 12, tzinfo=UTC)


def fixture(root):
    (root / "data").mkdir(parents=True)
    db = PaperDatabase(
        papers=[
            PaperRecord(
                id="a",
                title="First Gaussian Splatting method",
                authors=["Alice One"],
                published_date="2026-10-01",
                db_references=["b"],
            ),
            PaperRecord(
                id="b",
                title="Second Gaussian Splatting method",
                authors=["Bob Two"],
                published_date="2026-10-02",
                db_references=["a"],
            ),
        ],
        total_count=2,
        last_updated="2026-11-10T00:00:00Z",
    )
    db.save(root / "data/papers.json")
    return db


def inputs_bytes(root):
    return {
        p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file()
    }


def test_provider_separation_zero_stale_retained_values_and_no_network(tmp_path, monkeypatch):
    fixture(tmp_path)
    signals = tmp_path / "data/signals"
    signals.mkdir()
    oa = OpenAlexCache()
    oa.signals.apply(
        "a",
        status="ok",
        provider_id="https://openalex.org/W1",
        now=NOW - timedelta(days=1),
        values={"citation_count": 0, "referenced_works": []},
    )
    oa.signals.apply(
        "outside-active",
        status="ok",
        provider_id="https://openalex.org/W99",
        now=NOW - timedelta(days=1),
        values={"citation_count": 99},
    )
    oa.history = [
        CitationSample(
            paper_id="a",
            provider_id="https://openalex.org/W1",
            observed_at=NOW - timedelta(days=days),
            citation_count=count,
        )
        for days, count in [(10, 3), (1, 0)]
    ]
    oa.save(signals / "openalex-cache.json")
    hf = SignalStore(provider="huggingface")
    hf.apply(
        "a",
        status="ok",
        provider_id="a",
        now=NOW - timedelta(days=10),
        values={"upvotes": 0, "submitted_on_daily_at": (NOW - timedelta(days=11)).isoformat()},
    )
    hf.apply("a", status="error", now=NOW - timedelta(hours=1))
    hf.save(signals / "huggingface.json")
    s2 = SignalStore(provider="semanticscholar")
    s2.apply("a", status="rate_limited", now=NOW - timedelta(hours=1))
    s2.save(signals / "semanticscholar.json")
    before = inputs_bytes(tmp_path)
    monkeypatch.setattr(
        httpx.Client, "send", lambda *args, **kwargs: pytest.fail("Unexpected HTTP")
    )
    result = coverage_snapshot(tmp_path, now=NOW)
    assert inputs_bytes(tmp_path) == before
    assert coverage_snapshot(tmp_path, now=NOW) == result
    actual = result["providers"]
    assert actual["openalex"]["verified_observed_zero_citations"] == 1
    assert actual["openalex"]["unobserved"] == 1
    assert actual["openalex"]["outside_active_cache_entries"] == 1
    assert actual["openalex"]["velocity_statuses"] == {"no_observations": 1, "ok": 1}
    assert actual["huggingface"]["latest_attempt_statuses"] == {"error": 1}
    assert actual["huggingface"]["stale_successful_values"] == 1
    assert actual["semanticscholar"]["verified_observed_zero_citations"] == 0
    assert actual["semanticscholar"]["velocity_statuses"] == {"no_observations": 2}
    assert result["graph"]["edges"] == 1  # Observed empty refs clear a; legacy b -> a survives.
    assert result["graph"]["provenance_statuses"] == {"observed": 1, "legacy_unverified": 1}


@pytest.mark.parametrize("appearance", [False, True])
def test_changed_or_new_optional_input_refuses_cli_report(tmp_path, monkeypatch, appearance):
    fixture(tmp_path)
    original = SnapshotInputs.finish

    def changed(self):
        if appearance:
            (tmp_path / "data/signals").mkdir()
            (tmp_path / "data/signals/huggingface.json").write_text("{}")
        else:
            with (tmp_path / "data/papers.json").open("ab") as stream:
                stream.write(b" ")
        return original(self)

    monkeypatch.setattr(SnapshotInputs, "finish", changed)
    output = tmp_path / "reports/new.json"
    with pytest.raises(ValueError, match="changed|appeared"):
        main(
            [
                "coverage",
                "--root",
                str(tmp_path),
                "--as-of",
                NOW.isoformat(),
                "--output",
                str(output),
            ]
        )
    assert not output.exists()


@pytest.mark.parametrize("bad", ["../outside.json", "/absolute.json"])
def test_source_paths_cannot_escape_root(tmp_path, bad):
    fixture(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/sources.yaml").write_text(
        yaml.safe_dump(
            {
                "editions": [
                    {
                        "venue": "CVPR",
                        "year": 2025,
                        "track": "main",
                        "status": "partial",
                        "coverage": "partial",
                        "evidence": [{"evidence_file": bad}],
                    }
                ]
            }
        )
    )
    with pytest.raises(ValueError):
        coverage_snapshot(tmp_path, now=NOW)


def test_stale_seed_and_extraction_bindings_are_visible(tmp_path):
    fixture(tmp_path)
    (tmp_path / "data/reviews").mkdir()
    (tmp_path / "data/reviews/seed-reconciliation.json").write_bytes(
        _encode(
            {
                "baseline_records": 1,
                "source_content_sha256": "0" * 64,
                "summary": {"retained": 1},
                "rows": [
                    {
                        "old_id": "old",
                        "canonical_id": "a",
                        "disposition": "retained",
                        "reviewed": True,
                        "reviewed_canonical_record_sha256": "0" * 64,
                    }
                ],
            }
        )
    )
    (tmp_path / "data/extraction").mkdir()
    (tmp_path / "data/extraction/coverage.json").write_bytes(
        _encode(
            {
                "schema_version": "1.0.0",
                "source_content_sha256": "0" * 64,
                "extractor_version": "fixture",
                "records": {"a": {"state": "processed", "source_task_id": None}},
                "source_tasks": {},
                "summary": {"processed": 1},
            }
        )
    )
    result = coverage_snapshot(tmp_path, now=NOW)
    assert not result["seed"]["canonical_binding_current"]
    assert result["seed"]["stale_retained_record_bindings"] == ["old"]
    assert not result["extraction"]["canonical_binding_current"]
    assert result["extraction"]["unobserved_active"] == 1
    assert result["extraction"]["accepted_numeric_cells"] == 0


def test_v2_components_verified_without_creating_observed_zeros(tmp_path):
    db = fixture(tmp_path)
    v1 = coverage_snapshot(tmp_path, now=NOW)
    path = tmp_path / "data/manifest.json"
    manifest = write_store(db, path)
    before = inputs_bytes(tmp_path)
    v2 = coverage_snapshot(tmp_path, data_path=path, now=NOW)
    assert v1["canonical"] == v2["canonical"]
    assert v1["graph"] == v2["graph"]
    assert v2["providers"]["openalex"]["verified_observed_zero_citations"] == 0
    assert v2["providers"]["openalex"]["fresh_successful_values"] == 0
    assert v2["providers"]["openalex"]["latest_attempt_statuses"] == {"unknown": 2}
    assert inputs_bytes(tmp_path) == before
    shard = path.parent / manifest["shards"][0]["path"]
    shard.write_bytes(shard.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum"):
        coverage_snapshot(tmp_path, data_path=path, now=NOW)


def test_historical_pages_and_exact_application_inventory_verified(tmp_path):
    from src.backfill import HistoricalCrawler
    from tests.test_backfill import FixtureSource, spec

    fixture(tmp_path)
    directory = tmp_path / "data/history"
    crawler = HistoricalCrawler(spec(), directory, FixtureSource(entries=[]))
    assert crawler.run(max_requests=2)["status"] == "complete"
    (tmp_path / "config").mkdir()
    (tmp_path / "config/sources.yaml").write_text(
        yaml.safe_dump(
            {
                "editions": [],
                "historical_runs": [
                    {
                        "checkpoint": "data/history/checkpoint.json",
                        "application_report": "data/history/application.json",
                    }
                ],
            }
        )
    )
    application = directory / "application.json"
    application.write_bytes(
        _encode(
            {"unique_candidates": 0, "dispositions": [], "outcomes": {}, "policy_digest": "a" * 64}
        )
    )
    before = inputs_bytes(tmp_path)
    result = coverage_snapshot(tmp_path, now=datetime.now(UTC) + timedelta(seconds=1))
    assert result["historical_discovery"][0]["status"] == "complete"
    assert result["historical_discovery"][0]["cached_pages_verified"]
    assert inputs_bytes(tmp_path) == before
    checkpoint = json.loads((directory / "checkpoint.json").read_bytes())
    page = next(iter(checkpoint["slices"].values()))["pages"][0]["path"]
    (directory / page).write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        coverage_snapshot(tmp_path, now=datetime.now(UTC) + timedelta(seconds=1))


def test_mixed_provider_cache_and_existing_output_refused(tmp_path):
    fixture(tmp_path)
    result = coverage_snapshot(tmp_path, now=NOW)
    with pytest.raises(ValueError):
        write_coverage_report(tmp_path, tmp_path / "data/new.json", result)
    output = tmp_path / "reports/new.json"
    write_coverage_report(tmp_path, output, result)
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        write_coverage_report(tmp_path, output, result)
    assert output.read_bytes() == before
    (tmp_path / "data/signals").mkdir()
    SignalStore(provider="huggingface").save(tmp_path / "data/signals/semanticscholar.json")
    with pytest.raises(ValueError, match="provider mismatch"):
        coverage_snapshot(tmp_path, now=NOW)
