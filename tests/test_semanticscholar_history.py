import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import ValidationError

from src.cli import main
from src.extractors.semanticscholar import SemanticScholarClient, refresh_semanticscholar
from src.momentum import citation_velocity
from src.observations import SignalStore
from src.openalex_cache import CitationSample
from src.schema import PaperDatabase, PaperRecord
from src.semanticscholar_history import SemanticScholarHistory, SemanticScholarSample, history_path

NOW = datetime(2026, 11, 9, tzinfo=UTC)
IDENTITY = "a" * 40


def sample(stamp=NOW, count=0, paper_id="p", provider_id=IDENTITY):
    return SemanticScholarSample(
        paper_id=paper_id,
        provider_id=provider_id,
        observed_at=stamp,
        citation_count=count,
        influential_citation_count=0,
    )


def paper():
    return PaperRecord(id="p", arxiv_id="2308.04079", title="Original 3DGS paper")


def payload(count=0, identity=IDENTITY):
    return [
        {
            "paperId": identity,
            "title": "Original 3DGS paper",
            "externalIds": {"ArXiv": "2308.04079"},
            "citationCount": count,
            "influentialCitationCount": 0,
            "referenceCount": 0,
            "references": [],
        }
    ]


def api(body):
    return SemanticScholarClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body))
    )


def test_genuine_zero_counts_first_utc_date_and_retention(tmp_path):
    path = tmp_path / "s2.json"
    with api(payload()) as client:
        assert refresh_semanticscholar([paper()], path, client, now=NOW)["ok"] == 1
    hpath = history_path(path)
    first = hpath.read_bytes()
    with api(payload(9)) as client:
        # Force a genuine re-fetch in the same UTC day, preserving its first count.
        path.unlink()
        refresh_semanticscholar([paper()], path, client, now=NOW + timedelta(hours=1))
    assert hpath.read_bytes() == first
    assert SemanticScholarHistory.load(hpath).samples[0].citation_count == 0
    assert SignalStore.load(path, "semanticscholar").observations["p"].values["citation_count"] == 9
    # Calendar-month subtraction clamps a month-end cutoff correctly.
    history = SemanticScholarHistory(
        samples=[
            sample(datetime(2023, 2, 27, tzinfo=UTC)),
            sample(datetime(2023, 2, 28, tzinfo=UTC)),
        ]
    )
    history.record(sample(datetime(2024, 3, 31, tzinfo=UTC), 4))
    assert [s.observed_at.date().isoformat() for s in history.samples] == [
        "2023-02-28",
        "2024-03-31",
    ]


def test_history_before_cache_crash_replays_without_duplicate_or_lost_sample(tmp_path, monkeypatch):
    path = tmp_path / "s2.json"
    save = SignalStore.save

    def crash(self, target):
        assert history_path(path).exists()
        raise OSError("simulated cache publication failure")

    monkeypatch.setattr(SignalStore, "save", crash)
    with api(payload(3)) as client, pytest.raises(OSError, match="simulated"):
        refresh_semanticscholar([paper()], path, client, now=NOW)
    assert not path.exists()
    assert len(SemanticScholarHistory.load(history_path(path)).samples) == 1
    monkeypatch.setattr(SignalStore, "save", save)
    with api(payload(4)) as client:
        assert (
            refresh_semanticscholar([paper()], path, client, now=NOW + timedelta(minutes=1))["ok"]
            == 1
        )
    history = SemanticScholarHistory.load(history_path(path))
    assert len(history.samples) == 1 and history.samples[0].citation_count == 3
    assert SignalStore.load(path, "semanticscholar").observations["p"].values["citation_count"] == 4


def test_failures_misses_and_remap_never_add_samples(tmp_path):
    path = tmp_path / "s2.json"
    with api(payload(8)) as client:
        refresh_semanticscholar([paper()], path, client, now=NOW)
    before = history_path(path).read_bytes()
    later = NOW + timedelta(days=8)
    with api(payload(40, "b" * 40)) as client:
        assert refresh_semanticscholar([paper()], path, client, now=later)["ambiguous"] == 1
    assert history_path(path).read_bytes() == before
    with api([None]) as client:
        assert (
            refresh_semanticscholar([paper()], path, client, now=later + timedelta(days=8))[
                "not_found"
            ]
            == 1
        )
    with SemanticScholarClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(403))
    ) as client:
        assert (
            refresh_semanticscholar([paper()], path, client, now=later + timedelta(days=16))[
                "error"
            ]
            == 1
        )
    assert history_path(path).read_bytes() == before


def test_history_identity_also_fences_cache_loss_and_case_is_normalized(tmp_path):
    path = tmp_path / "s2.json"
    with api(payload(8, IDENTITY.upper())) as client:
        refresh_semanticscholar([paper()], path, client, now=NOW)
    assert SemanticScholarHistory.load(history_path(path)).samples[0].provider_id == IDENTITY
    path.unlink()
    with api(payload(9, "b" * 40)) as client:
        assert (
            refresh_semanticscholar([paper()], path, client, now=NOW + timedelta(days=8))[
                "ambiguous"
            ]
            == 1
        )
    assert len(SemanticScholarHistory.load(history_path(path)).samples) == 1


def test_cache_only_does_not_fabricate_history_from_a_known_cache_timestamp(tmp_path):
    path = tmp_path / "s2.json"
    store = SignalStore(provider="semanticscholar")
    store.apply("p", status="ok", now=NOW, provider_id=IDENTITY, values={"citation_count": 7})
    store.save(path)
    with SemanticScholarClient(max_requests=0) as client:
        refresh_semanticscholar([paper()], path, client, now=NOW, cache_only=True)
    assert not history_path(path).exists()


@pytest.mark.parametrize(
    "change",
    [
        {"citation_count": True},
        {"citation_count": -1},
        {"observed_at": NOW.replace(tzinfo=None)},
        {"provider_id": "https://openalex.org/W1"},
    ],
)
def test_invalid_history_sample_rejected(change):
    raw = sample().model_dump()
    raw.update(change)
    with pytest.raises(ValidationError):
        SemanticScholarSample.model_validate(raw)


def test_duplicate_dates_out_of_order_and_remap_rejected():
    with pytest.raises(ValidationError, match="Duplicate daily"):
        SemanticScholarHistory(samples=[sample(), sample(NOW + timedelta(hours=1))])
    history = SemanticScholarHistory(samples=[sample()])
    with pytest.raises(ValueError, match="Out-of-order"):
        history.record(sample(NOW - timedelta(days=1)))
    with pytest.raises(ValueError, match="remap"):
        history.record(sample(NOW + timedelta(days=1), provider_id="b" * 40))


def test_s2_velocity_actual_fractional_interval_correction_and_provider_separation():
    samples = [sample(NOW - timedelta(days=30.5), 50), sample(NOW, 40)]
    result = citation_velocity(
        samples,
        "p",
        now=NOW,
        ttl=timedelta(days=7),
        provider="semanticscholar",
        provider_id=IDENTITY.upper(),
    )
    assert result.provider == "semanticscholar" and result.status == "ok"
    assert result.elapsed_days == 30.5 and result.raw_velocity == pytest.approx(-10 / 30.5)
    assert result.positive_velocity == 0 and result.provider_correction
    with pytest.raises(ValueError, match="selected provider"):
        citation_velocity(samples, "p", now=NOW, ttl=timedelta(days=7))
    oa = CitationSample(
        paper_id="p", provider_id="https://openalex.org/W1", observed_at=NOW, citation_count=10
    )
    with pytest.raises(ValueError, match="selected provider"):
        citation_velocity([oa], "p", now=NOW, ttl=timedelta(days=7), provider="semanticscholar")


def test_cli_selects_s2_history_and_labels_unavailable_correctly(tmp_path, capsys):
    data, cache, output = tmp_path / "papers.json", tmp_path / "s2.json", tmp_path / "report.json"
    PaperDatabase(papers=[paper()]).save(data)
    history = SemanticScholarHistory(samples=[sample(datetime.now(UTC), 0)])
    history.save(history_path(cache))
    assert (
        main(
            [
                "--data",
                str(data),
                "momentum",
                "--provider",
                "semanticscholar",
                "--cache",
                str(cache),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    report = json.loads(output.read_bytes())
    assert report["provider"] == "semanticscholar" and report["summary"] == {"single_snapshot": 1}
    assert report["papers"][0]["raw_velocity"] is None
    assert json.loads(capsys.readouterr().out)["provider"] == "semanticscholar"
