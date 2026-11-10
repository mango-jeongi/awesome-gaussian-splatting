"""Daily update coverage, publication fencing, and moving-source recovery."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.daily import DailySession
from src.extractors.arxiv import ArxivIntegrityError, ArxivPage
from src.relevance import RelevancePolicy
from src.schema import PaperDatabase, PaperRecord

NOW = datetime(2024, 2, 1, tzinfo=UTC)
TAXONOMY = Path(__file__).resolve().parents[1] / "config/taxonomy.yaml"


class Source:
    def __init__(self, count=150):
        self.records = [
            PaperRecord(
                id=f"2401.{i:05}",
                arxiv_id=f"2401.{i:05}",
                title=f"Gaussian Splatting for scene reconstruction {i}",
                authors=["A. Author"],
                abstract="We reconstruct 3D scenes with Gaussian splatting.",
                published_date="2020-01-01",
                source="arxiv",
            )
            for i in range(count)
        ]
        self.times = {p.id: NOW - timedelta(minutes=i + 1) for i, p in enumerate(self.records)}
        self.calls = []

    def fetch_page(self, **kwargs):
        assert kwargs["sort_by"] == "lastUpdatedDate"
        assert kwargs["sort_order"] == "descending"
        assert kwargs["max_attempts"] == 1
        self.calls.append(kwargs)
        start = kwargs["start"]
        records = self.records[start : start + kwargs["page_size"]]
        return ArxivPage(
            tuple(records),
            len(self.records),
            start,
            {p.id: datetime(2020, 1, 1, tzinfo=UTC) for p in records},
            {p.id: self.times[p.id] for p in records},
        )


def setup(tmp_path, count=150):
    path = tmp_path / "papers.json"
    PaperDatabase().save(path)
    source = Source(count)
    session = DailySession(tmp_path / "daily", path, TAXONOMY, RelevancePolicy(), source)
    return path, source, session


def run(session, **kwargs):
    return session.run(
        query="all:gaussian", since=NOW - timedelta(days=1), until=NOW, page_size=60, **kwargs
    )


def test_more_than_sixty_old_revisions_resume_and_publish(tmp_path):
    path, source, session = setup(tmp_path)
    original = path.read_bytes()
    assert not run(session, max_requests=2)["source_complete"]
    assert path.read_bytes() == original
    assert not (session.directory / "watermark.json").exists()
    preview = run(session, max_requests=4, dry_run=True)
    assert preview["source_complete"] and preview["verified_pages"] == 3
    assert path.read_bytes() == original
    assert len(source.calls) == 6
    result = run(session, max_requests=1)
    assert result["watermark_advanced"] and result["invocation_requests"] == 0
    assert PaperDatabase.load(path).total_count == 150
    assert all(p.published_date == "2020-01-01" for p in PaperDatabase.load(path).papers)
    # A missed month uses the previous watermark, never now-minus-seven-days.
    later = session.run(
        query="all:gaussian", until=NOW + timedelta(days=30), page_size=60, max_requests=1
    )
    assert datetime.fromisoformat(later["since"]) == NOW - timedelta(days=7)


def test_moving_page_fails_closed_and_restart_keeps_evidence(tmp_path):
    path, source, session = setup(tmp_path, 3)
    original = path.read_bytes()
    run(session, max_requests=1)
    source.records[0] = source.records[0].model_copy(update={"title": "Changed title"})
    with pytest.raises(ArxivIntegrityError, match="changed during replay"):
        run(session, max_requests=1)
    assert path.read_bytes() == original
    assert not (session.directory / "watermark.json").exists()
    result = run(session, max_requests=2, restart=True)
    assert result["watermark_advanced"]
    assert len(list((session.directory / "runs").glob("*.json"))) == 1


def test_short_page_and_duplicate_fail_without_write(tmp_path):
    path, source, session = setup(tmp_path)
    run(session, max_requests=1)
    source.records[60] = source.records[0]
    with pytest.raises(ArxivIntegrityError, match="repeated"):
        run(session, max_requests=1)
    assert PaperDatabase.load(path).total_count == 0


def test_first_scan_explicit_boundary_empty_source_and_tamper(tmp_path):
    _, source, session = setup(tmp_path, 0)
    with pytest.raises(ValueError, match="explicit --since"):
        session.run(query="all:gaussian")
    run(session, max_requests=1)
    page = next((session.directory / "pages").glob("*.json"))
    original = page.read_bytes()
    page.write_bytes(b"{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        run(session, max_requests=1)
    page.write_bytes(original)
    assert run(session, max_requests=1)["watermark_advanced"]
    assert len(source.calls) == 2


def test_stop_at_overlap_boundary_and_do_not_import_future_updates(tmp_path):
    path, source, session = setup(tmp_path, 150)
    source.times[source.records[0].id] = NOW + timedelta(minutes=1)
    result = session.run(
        query="all:gaussian",
        since=NOW - timedelta(minutes=65),
        until=NOW,
        page_size=60,
        max_requests=4,
    )
    assert result["watermark_advanced"] and result["pages"] == 2
    assert PaperDatabase.load(path).total_count == 64


def test_failed_publication_leaves_watermark_unchanged(tmp_path, monkeypatch):
    _, _, session = setup(tmp_path, 2)

    def fail(*args, **kwargs):
        raise RuntimeError("simulated canonical write failure")

    monkeypatch.setattr(PaperDatabase, "save", fail)
    with pytest.raises(RuntimeError, match="simulated"):
        run(session, max_requests=2)
    assert not (session.directory / "watermark.json").exists()


def test_no_regressing_or_future_cutoff(tmp_path):
    _, _, session = setup(tmp_path, 0)
    run(session, max_requests=2)
    with pytest.raises(ValueError, match="advance"):
        session.run(query="all:gaussian", until=NOW - timedelta(days=1), page_size=60)
    with pytest.raises(ValueError, match="at or before now"):
        session.run(query="all:gaussian", until=datetime.now(UTC) + timedelta(days=1), page_size=60)


def test_source_failure_is_charged_and_retry_uses_same_cursor(tmp_path, monkeypatch):
    import json

    from src.extractors.arxiv import ArxivRequestFailure

    _, source, session = setup(tmp_path, 2)
    fetch = source.fetch_page

    def fail(**kwargs):
        raise ArxivRequestFailure("sanitized provider failure", attempts=1)

    monkeypatch.setattr(source, "fetch_page", fail)
    with pytest.raises(ArxivRequestFailure):
        run(session, max_requests=1)
    state = json.loads((session.directory / "active.json").read_bytes())
    assert state["requests"] == 1 and not state["pages"]
    monkeypatch.setattr(source, "fetch_page", fetch)
    result = run(session, max_requests=2)
    assert result["total_requests"] == 3 and result["watermark_advanced"]


def test_crash_after_canonical_commit_replays_without_duplicate(tmp_path, monkeypatch):
    import src.daily as daily

    path, _, session = setup(tmp_path, 2)
    write = daily._atomic_write

    def interrupt(target, payload):
        if Path(target).name == "watermark.json":
            raise RuntimeError("crash after canonical commit")
        write(target, payload)

    monkeypatch.setattr(daily, "_atomic_write", interrupt)
    with pytest.raises(RuntimeError, match="after canonical"):
        run(session, max_requests=2)
    assert PaperDatabase.load(path).total_count == 2
    committed = path.read_bytes()
    assert not (session.directory / "watermark.json").exists()
    monkeypatch.setattr(daily, "_atomic_write", write)
    result = run(session, max_requests=1)
    assert result["watermark_advanced"] and not result["corpus_written"]
    assert result["invocation_requests"] == 0 and path.read_bytes() == committed


def test_daily_cli_dry_run_and_frozen_request(tmp_path, monkeypatch, capsys):
    import json

    import src.cli as cli

    path, source, session = setup(tmp_path, 3)
    monkeypatch.setattr(cli, "ArxivExtractor", lambda: source)
    args = [
        "--data",
        str(path),
        "daily",
        "--state-dir",
        str(session.directory),
        "--query",
        "all:gaussian",
        "--since",
        "2024-01-31",
        "--until",
        "2024-02-01",
        "--page-size",
        "60",
        "--max-requests",
        "2",
        "--dry-run",
    ]
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["source_complete"]
    assert PaperDatabase.load(path).total_count == 0
    with pytest.raises(ValueError, match="Frozen daily request changed"):
        session.run(query="different query", page_size=60)


def test_source_drift_automatically_restarts_next_scheduled_pass(tmp_path):
    import json

    path, source, session = setup(tmp_path, 3)
    run(session, max_requests=1)
    source.records[0] = source.records[0].model_copy(
        update={"abstract": "Updated Gaussian splatting reconstruction abstract."}
    )
    with pytest.raises(ArxivIntegrityError):
        run(session, max_requests=1)
    assert json.loads((session.directory / "active.json").read_bytes())["phase"] == "unstable"
    # A normal scheduled invocation supplies neither the initial --since nor
    # --restart. It must recover its initial boundary from the failed run.
    result = session.run(query="all:gaussian", until=NOW, page_size=60, max_requests=2)
    assert result["watermark_advanced"] and PaperDatabase.load(path).total_count == 3
    assert len(list((session.directory / "runs").glob("*.json"))) == 1


def test_short_page_cannot_acknowledge_a_cursor(tmp_path, monkeypatch):
    import json
    from dataclasses import replace

    _, source, session = setup(tmp_path)
    fetch = source.fetch_page

    def short(**kwargs):
        page = fetch(**kwargs)
        records = page.records[:-1]
        return replace(
            page, records=records, updated_at={p.id: page.updated_at[p.id] for p in records}
        )

    monkeypatch.setattr(source, "fetch_page", short)
    with pytest.raises(ArxivIntegrityError, match="offset/count"):
        run(session, max_requests=1)
    state = json.loads((session.directory / "active.json").read_bytes())
    assert not state["pages"] and state["phase"] == "unstable"


def test_weekly_reconciliation_recovers_delayed_indexing_with_independent_state(tmp_path):
    path, source, daily = setup(tmp_path, 2)
    # The source indexes one record late, retaining its older update timestamp.
    old_id = source.records[1].id
    source.times[old_id] = NOW - timedelta(days=20)
    recent = daily.run(
        query="all:gaussian",
        since=NOW - timedelta(days=7),
        until=NOW,
        page_size=60,
        max_requests=2,
    )
    assert recent["watermark_advanced"]
    assert PaperDatabase.load(path).total_count == 1
    daily_watermark = (daily.directory / "watermark.json").read_bytes()
    weekly = DailySession(tmp_path / "weekly", path, TAXONOMY, RelevancePolicy(), source)
    pending = weekly.run(
        query="all:gaussian",
        since=NOW - timedelta(days=30),
        until=NOW,
        page_size=60,
        overlap_days=30,
        max_requests=1,
    )
    assert not pending["source_complete"]
    assert not (weekly.directory / "watermark.json").exists()
    assert PaperDatabase.load(path).total_count == 1
    complete = weekly.run(
        query="all:gaussian",
        page_size=60,
        overlap_days=30,
        max_requests=1,
    )
    assert complete["watermark_advanced"]
    assert PaperDatabase.load(path).total_count == 2
    assert (daily.directory / "watermark.json").read_bytes() == daily_watermark
    # A missed weekly run also resumes from its old watermark, not now-minus-30.
    replay = weekly.run(
        query="all:gaussian",
        until=NOW + timedelta(days=45),
        page_size=60,
        overlap_days=30,
        max_requests=2,
    )
    assert datetime.fromisoformat(replay["since"]) == NOW - timedelta(days=30)
    assert replay["watermark_advanced"]
    assert PaperDatabase.load(path).total_count == 2
    assert (daily.directory / "watermark.json").read_bytes() == daily_watermark
