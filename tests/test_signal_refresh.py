from datetime import UTC, datetime, timedelta

import httpx
import pytest

from src import signal_refresh
from src.extractors.huggingface_client import HFPapersClient
from src.extractors.openalex import OpenAlexClient
from src.huggingface_cache import refresh_huggingface
from src.observations import SignalStore
from src.openalex_cache import OpenAlexCache, refresh_openalex
from src.schema import PaperRecord

NOW = datetime(2026, 11, 9, tzinfo=UTC)


def paper(identifier="2308.04079"):
    return PaperRecord(
        id=identifier,
        arxiv_id=identifier,
        title="Gaussian Splatting fixture",
        published_date="2023-08-08",
    )


@pytest.mark.parametrize("provider", ["openalex", "semanticscholar", "huggingface"])
def test_cache_only_and_zero_budget_leave_unattempted_queue_durable(tmp_path, provider):
    cache = tmp_path / "cache.json"
    report = signal_refresh.refresh_signals(
        [paper()],
        provider,
        cache,
        max_requests=0,
        cache_only=True,
        require_key=True,
        now=NOW,
    )
    assert report["status"] == "cache_only" and report["requests"] == 0
    assert report["remaining_due"] == 1 and not cache.exists()
    report = signal_refresh.refresh_signals(
        [paper()],
        provider,
        cache,
        max_requests=0,
        now=NOW,
    )
    assert report["status"] == "deferred" and report["requests"] == 0
    assert report["attempted"] == 0 and report["remaining_due"] == 1
    assert not cache.exists()


@pytest.mark.parametrize(
    "provider,client_name",
    [
        ("openalex", "OpenAlexClient"),
        ("semanticscholar", "SemanticScholarClient"),
    ],
)
def test_scheduled_missing_key_is_explicit_and_never_constructs_client(
    tmp_path, monkeypatch, provider, client_name
):
    def forbidden(**kwargs):
        pytest.fail("Missing-key scheduled pass must not create a client")

    monkeypatch.setattr(signal_refresh, client_name, forbidden)
    report = signal_refresh.refresh_signals(
        [paper()], provider, tmp_path / "cache.json", require_key=True
    )
    assert report["status"] == "skipped" and report["reason"] == "missing_credential"
    assert report["requests"] == 0


def test_sampling_old_success_weekly_preserves_default_ttl_and_real_history(tmp_path):
    p, cache = paper(), tmp_path / "cache.json"
    raw = {
        "meta": {"count": 1},
        "results": [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.48550/arxiv.2308.04079",
                "cited_by_count": 4,
                "referenced_works": [],
                "title": p.title,
            }
        ],
    }
    with OpenAlexClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=raw))
    ) as client:
        assert refresh_openalex([p], cache, client, now=NOW)["ok"] == 1
        later = NOW + timedelta(days=7)
        assert refresh_openalex([p], cache, client, now=later)["attempted"] == 0
        assert refresh_openalex([p], cache, client, now=later, sample_history=True)["ok"] == 1
    history = OpenAlexCache.load(cache).history
    assert [s.observed_at for s in history] == [NOW, later]
    assert [s.citation_count for s in history] == [4, 4]


def test_recent_sampling_daily_and_retry_clock_remains_separate(tmp_path):
    p = paper().model_copy(update={"published_date": "2026-11-01"})
    cache = tmp_path / "cache.json"
    data = OpenAlexCache()
    data.signals.apply(
        p.id,
        status="ok",
        now=NOW - timedelta(days=2),
        provider_id="https://openalex.org/W1",
        values={"citation_count": 9},
    )
    data.save(cache)
    with OpenAlexClient(max_requests=0) as client:
        assert refresh_openalex([p], cache, client, now=NOW, cache_only=True)["due"] == 0
        assert (
            refresh_openalex([p], cache, client, now=NOW, cache_only=True, sample_history=True)[
                "due"
            ]
            == 1
        )
    data.signals.apply(p.id, status="error", now=NOW, retry_after=timedelta(hours=2))
    data.save(cache)
    before = cache.read_bytes()
    with OpenAlexClient(max_requests=0) as client:
        assert (
            refresh_openalex([p], cache, client, now=NOW + timedelta(hours=1), sample_history=True)[
                "attempted"
            ]
            == 0
        )
    assert cache.read_bytes() == before


def test_bounded_hf_queue_prioritizes_unattempted_then_oldest_and_replays(tmp_path):
    known, new = paper(), paper("2401.00001")
    path = tmp_path / "hf.json"
    store = SignalStore(provider="huggingface")
    store.apply(
        known.id,
        status="ok",
        now=NOW - timedelta(days=2),
        provider_id=known.arxiv_id,
        values={"submitted_on_daily_at": (NOW - timedelta(days=3)).isoformat()},
        response_schema_version="hf-paper-v2",
    )
    store.save(path)
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(404)

    with HFPapersClient(transport=httpx.MockTransport(handler)) as client:
        assert refresh_huggingface([known, new], path, client, limit=1, now=NOW)["attempted"] == 1
    assert seen == ["/api/papers/2401.00001"]
    with HFPapersClient(transport=httpx.MockTransport(handler)) as client:
        assert refresh_huggingface([known, new], path, client, limit=1, now=NOW)["attempted"] == 1
        assert refresh_huggingface([known, new], path, client, limit=1, now=NOW)["attempted"] == 0
    assert seen == ["/api/papers/2401.00001", "/api/papers/2308.04079"]


def test_provider_failure_reports_degraded_without_erasing_success_or_exposing_body(
    tmp_path, monkeypatch
):
    path = tmp_path / "oa.json"
    p = paper()
    cache = OpenAlexCache()
    cache.signals.apply(
        p.id,
        status="ok",
        now=NOW - timedelta(days=31),
        provider_id="https://openalex.org/W1",
        values={"citation_count": 42},
    )
    cache.save(path)
    monkeypatch.setattr(
        signal_refresh,
        "OpenAlexClient",
        lambda **kwargs: OpenAlexClient(
            **kwargs,
            transport=httpx.MockTransport(
                lambda r: httpx.Response(403, text="private credential value")
            ),
        ),
    )
    report = signal_refresh.refresh_signals(
        [p], "openalex", path, require_key=True, api_key="private key", now=NOW
    )
    assert report["status"] == "degraded" and report["error"] == 1
    assert "private" not in str(report)
    saved = OpenAlexCache.load(path).signals.observations[p.id]
    assert saved.values["citation_count"] == 42 and saved.fetched_at == NOW - timedelta(days=31)


@pytest.mark.parametrize(
    "filename", ["daily-feed.yml", "midweek-sync.yml", "weekly-release.yml", "daily-signals.yml"]
)
def test_scheduled_writers_keep_signal_checkpoint_health_and_serialization(filename):
    from pathlib import Path

    import yaml

    path = Path(__file__).resolve().parents[1] / ".github/workflows" / filename
    workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert workflow["concurrency"] == {"group": "repository-writer", "cancel-in-progress": "false"}
    job = next(iter(workflow["jobs"].values()))
    refresh = next(step for step in job["steps"] if "refresh-signals" in step.get("run", ""))
    script = refresh["run"]
    assert (
        script.index("git fetch") < script.index("refresh-signals") < script.index("src.cli build")
    )
    assert "--max-requests 5 --max-seconds 90 --limit 100" in script
    assert "--due --require-key" in script and '--summary-file "$GITHUB_STEP_SUMMARY"' in script
    assert "for provider in openalex semanticscholar huggingface" in script
    assert "if (( signal_status != 0 ))" in script
    assert "secrets.OPENALEX_API_KEY" in refresh["env"]["OPENALEX_API_KEY"]
    assert "secrets.SEMANTIC_SCHOLAR_API_KEY" in refresh["env"]["SEMANTIC_SCHOLAR_API_KEY"]
    commit = next(step["run"] for step in job["steps"] if "git add --all" in step.get("run", ""))
    assert "data/signals" in commit and "reports/runs" in commit
    if filename == "daily-signals.yml":
        assert workflow["on"]["schedule"][0]["cron"] == "0 4 * * *"
