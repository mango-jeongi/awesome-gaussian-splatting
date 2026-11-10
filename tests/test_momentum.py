from datetime import UTC, datetime, timedelta

import pytest

from src.momentum import citation_velocity
from src.openalex_cache import CitationSample

NOW = datetime(2026, 11, 9, tzinfo=UTC)


def sample(days, count, identity="https://openalex.org/W1", paper="p"):
    return CitationSample(
        paper_id=paper,
        provider_id=identity,
        observed_at=NOW - timedelta(days=days),
        citation_count=count,
    )


def calculate(samples, **kwargs):
    return citation_velocity(samples, "p", now=NOW, ttl=timedelta(days=7), **kwargs)


def test_nearest_thirty_day_actual_fractional_window():
    result = calculate([sample(44, 1), sample(31.5, 10), sample(28, 20), sample(0, 83)])
    assert result.status == "ok"
    assert result.elapsed_days == 31.5
    assert result.raw_delta == 73
    assert result.raw_velocity == pytest.approx(73 / 31.5)
    assert result.baseline_at == NOW - timedelta(days=31.5)


@pytest.mark.parametrize("days,eligible", [(6.999, False), (7, True), (45, True), (45.001, False)])
def test_window_boundaries(days, eligible):
    result = calculate([sample(days, 1), sample(0, 2)])
    assert (result.status == "ok") == eligible


def test_zero_and_provider_correction():
    result = calculate([sample(30, 100), sample(0, 70)])
    assert result.raw_delta == -30 and result.raw_velocity == -1
    assert result.provider_correction and result.positive_velocity == 0
    zero = calculate([sample(30, 0), sample(0, 0)])
    assert zero.status == "ok" and zero.positive_velocity == 0


def test_unavailable_is_never_zero():
    assert calculate([]).status == "no_observations"
    single = calculate([sample(0, 100)])
    assert single.status == "single_snapshot" and single.raw_velocity is None
    stale = calculate([sample(37, 1), sample(7, 2)])
    assert stale.status == "stale" and stale.raw_velocity is None
    assert calculate([sample(0, 1, paper="another")]).status == "no_observations"


def test_remap_cannot_splice_old_segments():
    series = [sample(40, 1), sample(20, 100, "https://openalex.org/W2"), sample(0, 3)]
    assert calculate(series).status == "identity_changed"
    assert calculate([sample(30, 1), sample(0, 2)], provider_id="W2").status == "identity_changed"
    resumed = calculate(series + [sample(8, 2)])
    assert resumed.status == "ok" and resumed.elapsed_days == 8


def test_tie_is_deterministic_and_invalid_time_rejected():
    assert calculate([sample(31, 1), sample(29, 1), sample(0, 2)]).elapsed_days == 29
    with pytest.raises(ValueError):
        calculate([sample(-1, 1)])
    with pytest.raises(ValueError):
        calculate([sample(0, 1), sample(0, 2)])
