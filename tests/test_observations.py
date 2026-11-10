from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.observations import Observation, SignalStore

NOW = datetime(2026, 11, 8, tzinfo=UTC)


def test_valid_zero_and_empty_references_survive_error(tmp_path):
    store = SignalStore(provider="openalex")
    store.apply(
        "paper",
        status="ok",
        now=NOW,
        provider_id="W1",
        values={"citation_count": 5, "referenced_works": ["W2"]},
    )
    fresh = store.apply(
        "paper",
        status="ok",
        now=NOW + timedelta(hours=1),
        provider_id="W1",
        values={"citation_count": 0, "referenced_works": []},
    )
    failed = store.apply(
        "paper", status="rate_limited", now=NOW + timedelta(hours=2), retry_after=timedelta(hours=1)
    )
    assert failed.values == {"citation_count": 0, "referenced_works": []}
    assert failed.fetched_at == fresh.fetched_at
    assert not failed.due(NOW + timedelta(hours=2, minutes=59), timedelta(days=1))
    assert failed.due(NOW + timedelta(hours=3), timedelta(days=1))
    path = tmp_path / "signals.json"
    store.save(path)
    assert SignalStore.load(path, "openalex") == store
    before = path.stat().st_mtime_ns
    store.save(path)
    assert path.stat().st_mtime_ns == before


def test_unknown_zero_and_confirmed_miss_are_distinct():
    legacy = Observation(provider="openalex", values={"citation_count": 0})
    assert legacy.stale(NOW, timedelta(days=1))
    store = SignalStore(provider="huggingface")
    miss = store.apply("paper", status="not_found", now=NOW)
    assert not miss.due(NOW + timedelta(days=6), timedelta(days=7))
    assert miss.due(NOW + timedelta(days=7), timedelta(days=7))
    assert miss.values == {}


def test_ttl_boundary_and_errors_do_not_advance_success():
    store = SignalStore(provider="semanticscholar")
    store.apply("paper", status="ok", now=NOW, provider_id="abc", values={"citation_count": 3})
    assert not store.observations["paper"].due(NOW + timedelta(hours=23), timedelta(days=1))
    assert store.observations["paper"].due(NOW + timedelta(days=1), timedelta(days=1))
    for status in ("error", "ambiguous", "not_found"):
        observed = store.apply("paper", status=status, now=NOW + timedelta(days=2))
        assert observed.fetched_at == NOW
        assert observed.values["citation_count"] == 3


def test_validation_and_remapping_requirements():
    store = SignalStore(provider="openalex")
    with pytest.raises(ValueError, match="Success"):
        store.apply("paper", status="ok", now=NOW, values={})
    with pytest.raises(ValidationError):
        store.apply("paper", status="ok", now=NOW, provider_id="W1", values={"citation_count": -1})
    store.apply("paper", status="ok", now=NOW, provider_id="W1", values={})
    with pytest.raises(ValueError, match="remapping"):
        store.apply("paper", status="ok", now=NOW, provider_id="W2", values={})
    with pytest.raises(ValueError, match="Out-of-order"):
        store.apply("paper", status="error", now=NOW - timedelta(seconds=1))
    with pytest.raises(ValidationError, match="timezone"):
        Observation(provider="openalex", status="error", last_attempt_at=datetime(2026, 11, 8))
    with pytest.raises(ValidationError, match="Mixed providers"):
        SignalStore(provider="openalex", observations={"p": Observation(provider="huggingface")})
