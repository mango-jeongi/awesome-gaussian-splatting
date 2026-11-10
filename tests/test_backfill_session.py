"""End-to-end bounded backfill, canonical apply, and no-op replay via the CLI."""

import argparse
import json
from datetime import UTC, datetime

import pytest
from test_backfill import FixtureSource

from src.backfill_session import BackfillSession, HistoricalRequest
from src.cli import main, utc_bound
from src.relevance import RelevancePolicy
from src.schema import PaperDatabase


def test_backfill_cli_earliest_budget_resume_apply_and_noop(tmp_path, monkeypatch, capsys):
    import src.cli as cli

    source = FixtureSource()
    monkeypatch.setattr(cli, "ArxivExtractor", lambda: source)
    path = tmp_path / "papers.json"
    PaperDatabase().save(path)
    original = path.read_bytes()
    directory = tmp_path / "run"
    args = [
        "--data",
        str(path),
        "backfill",
        "--until",
        "2024-01-02",
        "--run-dir",
        str(directory),
        "--page-size",
        "60",
        "--resume",
    ]
    assert main([*args, "--max-requests", "1"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert not first["source_complete"]
    assert path.read_bytes() == original
    assert len(source.calls) == 1
    assert main([*args, "--max-requests", "2"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert not second["source_complete"]
    assert path.read_bytes() == original
    assert main([*args, "--max-requests", "3"]) == 0
    third = json.loads(capsys.readouterr().out)
    assert third["source_complete"] and third["corpus_written"]
    assert third["inserted_canonical_records"] == 150
    assert third["total_invocation_requests"] <= 3
    assert PaperDatabase.load(path).total_count == 150
    imported = path.read_bytes()
    calls = len(source.calls)
    assert main([*args, "--max-requests", "1"]) == 0
    replay = json.loads(capsys.readouterr().out)
    assert replay["source_complete"] and not replay["corpus_written"]
    assert replay["total_invocation_requests"] == 0
    assert path.read_bytes() == imported
    assert len(source.calls) == calls


def test_dry_run_keeps_corpus_and_rejects_changed_frozen_request(tmp_path, monkeypatch, capsys):
    import src.cli as cli

    source = FixtureSource()
    monkeypatch.setattr(cli, "ArxivExtractor", lambda: source)
    path = tmp_path / "manifest.json"
    PaperDatabase().save(path)
    before = path.read_bytes()
    args = [
        "--data",
        str(path),
        "backfill",
        "--since",
        "2024-01-01",
        "--until",
        "2024-01-02",
        "--run-dir",
        str(tmp_path / "run"),
        "--page-size",
        "60",
    ]
    assert main([*args, "--dry-run", "--max-requests", "5"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["source_complete"] and not report["corpus_written"]
    assert report["outcomes"]["include"] == 150
    assert path.read_bytes() == before
    with pytest.raises(ValueError, match="exists"):
        main([*args, "--dry-run"])
    changed = [*args]
    changed[changed.index("2024-01-02")] = "2024-01-03"
    with pytest.raises(ValueError, match="changed"):
        main([*changed, "--resume", "--dry-run"])
    assert path.read_bytes() == before


def test_invalid_time_and_budget_do_not_fetch(tmp_path):
    with pytest.raises(argparse.ArgumentTypeError):
        utc_bound("2024-01-01T12:00:00")
    assert utc_bound("2024-01-01") == datetime(2024, 1, 1, tzinfo=UTC)
    policy = RelevancePolicy()
    request = HistoricalRequest(
        query='all:"Gaussian Splatting"',
        comparator_query='ti:"Gaussian Splatting"',
        policy_digest=policy.digest,
        since=datetime(2024, 1, 1, tzinfo=UTC),
        until=datetime(2024, 1, 2, tzinfo=UTC),
    )
    source = FixtureSource()
    session = BackfillSession(
        request,
        tmp_path / "run",
        source,
        policy,
        tmp_path / "missing.json",
        tmp_path / "taxonomy.yaml",
    )
    with pytest.raises(ValueError, match="positive"):
        session.run(max_requests=0)
    assert not source.calls
