import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.observations import SignalStore
from src.openalex_cache import CitationSample, OpenAlexCache
from src.public import build_public, compact
from src.public_trending import public_trending
from src.ranking import RankingConfig, rank_trending
from src.schema import PaperDatabase, PaperRecord
from src.semanticscholar_history import SemanticScholarHistory, SemanticScholarSample

NOW = datetime(2026, 11, 9, tzinfo=UTC)


def paper(key="p"):
    return PaperRecord(
        id=key,
        title="Paper",
        published_date="2026-10-10",
        published_date_precision="day",
        date_placement="observed",
    )


def sources(path, papers):
    oa = OpenAlexCache()
    hf = SignalStore(provider="huggingface")
    s2 = SignalStore(provider="semanticscholar")
    history = SemanticScholarHistory()
    for p in papers:
        oa.signals.apply(
            p.id,
            status="ok",
            now=NOW,
            provider_id="https://openalex.org/W1",
            values={"citation_count": 130},
        )
        s2.apply(p.id, status="ok", now=NOW, provider_id="a" * 40, values={"citation_count": 1007})
        hf.apply(p.id, status="ok", now=NOW, provider_id="2601.00001", values={"upvotes": 0})
        for days, count in [(30, 100), (0, 130)]:
            oa.history.append(
                CitationSample(
                    paper_id=p.id,
                    provider_id="https://openalex.org/W1",
                    observed_at=NOW - timedelta(days=days),
                    citation_count=count,
                )
            )
        for days, count in [(30, 1000), (0, 1007)]:
            history.samples.append(
                SemanticScholarSample(
                    paper_id=p.id,
                    provider_id="a" * 40,
                    observed_at=NOW - timedelta(days=days),
                    citation_count=count,
                )
            )
    oa.save(path / "openalex-cache.json")
    s2.save(path / "semanticscholar.json")
    hf.save(path / "huggingface.json")
    history.save(path / "semanticscholar-history.json")
    return oa, hf, s2, history


def test_public_complete_scores_source_separation_formula_and_noop(tmp_path):
    db = PaperDatabase(papers=[paper()], last_updated=NOW.isoformat())
    sources(tmp_path, db.papers)
    snapshot = public_trending(db, tmp_path, RankingConfig())
    oa = snapshot["providers"]["openalex"]["papers"]["p"]
    s2 = snapshot["providers"]["semanticscholar"]["papers"]["p"]
    assert oa["coverage"] == s2["coverage"] == "complete"
    assert oa["score"] == pytest.approx(25) and s2["score"] == pytest.approx(25)
    assert oa["velocity"][snapshot["velocity_fields"].index("raw_velocity")] == 1
    assert s2["velocity"][snapshot["velocity_fields"].index("raw_velocity")] == pytest.approx(
        7 / 30
    )
    assert snapshot == public_trending(db, tmp_path, RankingConfig())
    manifest = build_public(db, tmp_path / "public", trending=snapshot)
    assert json.loads((tmp_path / "public" / manifest["trending"]["path"]).read_bytes()) == snapshot


def test_partial_zero_upvotes_renormalize_and_earliest_stale_component_expires_pool(tmp_path):
    db = PaperDatabase(papers=[paper()], last_updated=NOW.isoformat())
    hf = SignalStore(provider="huggingface")
    stamp = NOW - timedelta(days=6.9)
    hf.apply("p", status="ok", now=stamp, provider_id="2601.00001", values={"upvotes": 0})
    hf.save(tmp_path / "huggingface.json")
    snapshot = public_trending(db, tmp_path, RankingConfig())
    row = snapshot["providers"]["openalex"]["papers"]["p"]
    assert row["coverage"] == "partial" and row["weights_used"] == {"upvotes": 1}
    assert (
        row["velocity"][snapshot["velocity_fields"].index("status")] == "no_observations"
        and row["score"] == 25
    )
    assert datetime.fromisoformat(snapshot["valid_until"]) == stamp + timedelta(days=7)


def test_no_signals_never_becomes_zero_score(tmp_path):
    db = PaperDatabase(papers=[paper()], last_updated=NOW.isoformat())
    snapshot = public_trending(db, tmp_path, RankingConfig())
    for provider in snapshot["providers"].values():
        row = provider["papers"]["p"]
        assert row["coverage"] == "unavailable" and row["score"] is None


def test_velocity_history_is_indexed_once_per_paper(tmp_path, monkeypatch):
    import src.ranking as ranking

    papers = [paper(str(i)) for i in range(5)]
    oa, hf, _, _ = sources(tmp_path, papers)
    calculate = ranking.citation_velocity
    seen = []

    def capture(samples, key, **kwargs):
        seen.append((key, len(samples)))
        return calculate(samples, key, **kwargs)

    monkeypatch.setattr(ranking, "citation_velocity", capture)
    rank_trending(papers, oa, hf, now=NOW, config=RankingConfig())
    assert seen == [(str(i), 2) for i in range(5)]


def test_five_thousand_two_provider_complete_scores_fit_budget(tmp_path):
    papers = [paper(f"paper:2026-{i:010d}") for i in range(5000)]
    db = PaperDatabase(papers=papers, last_updated=NOW.isoformat())
    sources(tmp_path, papers)
    snapshot = public_trending(db, tmp_path, RankingConfig())
    assert len(compact(snapshot)) <= 4_000_000


def test_browser_expiry_provider_choice_zero_and_coverage_order():
    asset = Path(__file__).resolve().parents[1] / "docs/assets/trending-view.js"
    code = r"""
const assert=require('assert/strict'),api=require(process.argv[1]);
const p={as_of:'2026-11-09T00:00:00Z',valid_until:'2026-11-10T00:00:00Z',providers:{openalex:{papers:{p:{coverage:'complete',score:0}}},semanticscholar:{papers:{p:{coverage:'partial',score:90}}}}};
const now=Date.parse('2026-11-09T12:00:00Z');
assert.equal(api.row(p,'p','openalex',now).score,0);
assert.equal(api.row(p,'p','semanticscholar',now).score,90);
assert.ok(api.compare(api.row(p,'p','openalex',now),api.row(p,'p','semanticscholar',now))<0);
assert.equal(api.row(p,'p','openalex',Date.parse(p.valid_until)).reason,'snapshot_expired');
assert.equal(api.row(p,'p','openalex',Date.parse(p.as_of)-1).reason,'future_snapshot');
assert.equal(api.row(p,'toString','openalex',now).score,null);
"""
    subprocess.run(["node", "-e", code, str(asset)], check=True, capture_output=True, text=True)
