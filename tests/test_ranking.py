from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.observations import SignalStore
from src.openalex_cache import CitationSample, OpenAlexCache
from src.ranking import RankingConfig, midranks, rank_trending
from src.schema import PaperRecord

NOW = datetime(2026, 11, 9, tzinfo=UTC)


def paper(key, age=30, precision="day"):
    return PaperRecord(
        id=key,
        title="Paper " + key,
        published_date=(NOW - timedelta(days=age)).date().isoformat(),
        published_date_precision=precision,
        date_placement="observed" if precision == "day" else "legacy_unknown",
    )


def add_velocity(cache, key, delta):
    for days, count in [(30, 100), (0, 100 + delta)]:
        cache.history.append(
            CitationSample(
                paper_id=key,
                provider_id="https://openalex.org/W1",
                observed_at=NOW - timedelta(days=days),
                citation_count=count,
            )
        )


def add_hf(hf, key, value, age=0):
    hf.apply(
        key, status="ok", now=NOW - timedelta(days=age), provider_id=key, values={"upvotes": value}
    )


def rank(papers, cache, hf):
    return rank_trending(papers, cache, hf, now=NOW, config=RankingConfig())["papers"]


def test_hand_calculated_ties_and_decay():
    cache, hf = OpenAlexCache(), SignalStore(provider="huggingface")
    papers = [paper(key) for key in ["a", "b", "c"]]
    for key, delta, votes in [("a", 0, 0), ("b", 30, 10), ("c", 30, 20)]:
        add_velocity(cache, key, delta)
        add_hf(hf, key, votes)
    rows = {row["paper_id"]: row for row in rank(papers, cache, hf)}
    assert rows["a"]["score"] == 0
    assert rows["b"]["percentiles"] == {"velocity": 0.75, "upvotes": 0.5}
    assert rows["b"]["score"] == pytest.approx(33.75)
    assert rows["c"]["score"] == pytest.approx(41.25)
    assert all(row["coverage"] == "complete" for row in rows.values())


def test_partial_renormalization_and_complete_order():
    cache, hf = OpenAlexCache(), SignalStore(provider="huggingface")
    add_velocity(cache, "complete", 0)
    add_hf(hf, "complete", 0)
    add_hf(hf, "partial", 10)
    rows = rank([paper("complete"), paper("partial")], cache, hf)
    assert [r["paper_id"] for r in rows] == ["complete", "partial"]
    assert rows[1]["weights_used"] == {"upvotes": 1}
    assert rows[1]["score"] == 50
    assert rows[1]["coverage"] == "partial"
    assert rows[1]["upvotes_observed_at"] == NOW.isoformat()


def test_no_fabricated_dates_or_signals_and_freshness_boundary():
    cache, hf = OpenAlexCache(), SignalStore(provider="huggingface")
    for key in ["unknown", "old", "stale", "future", "edge"]:
        add_hf(hf, key, 100, age=7 if key == "stale" else 0)
    rows = rank(
        [
            paper("unknown", precision="unknown"),
            paper("old", age=91),
            paper("future", age=-1),
            paper("stale"),
            paper("edge", age=90),
        ],
        cache,
        hf,
    )
    byid = {r["paper_id"]: r for r in rows}
    assert byid["edge"]["coverage"] == "partial"
    assert byid["edge"]["score"] == pytest.approx(6.25)
    for key in ["unknown", "old", "future", "stale"]:
        assert byid[key]["score"] is None


def test_midrank_singleton_equal_and_invalid_values():
    assert midranks({"a": 0}) == {"a": 0.5}
    assert midranks({"a": 1, "b": 1}) == {"a": 0.5, "b": 0.5}
    with pytest.raises(ValueError):
        midranks({"a": float("nan")})
    config = RankingConfig.load(Path("config/ranking.yaml"))
    assert config.weights == {"velocity": 0.7, "upvotes": 0.3}
    with pytest.raises(ValueError):
        RankingConfig(weights={"velocity": -1, "upvotes": 2})
