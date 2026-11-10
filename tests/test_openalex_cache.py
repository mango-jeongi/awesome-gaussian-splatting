from datetime import UTC, datetime, timedelta

import httpx

from src.extractors.openalex import OpenAlexClient
from src.openalex_cache import OpenAlexCache, refresh_openalex
from src.schema import PaperDatabase

NOW = datetime(2026, 11, 9, tzinfo=UTC)


def paper():
    return next(
        p for p in PaperDatabase.load("data/papers.json").papers if p.id == "paper:2023-70a2202d04"
    )


def response(p, count=0, refs=None, provider_id=None):
    return {
        "meta": {"count": 1},
        "results": [
            {
                "id": provider_id or p.openalex_id,
                "doi": p.doi,
                "cited_by_count": count,
                "referenced_works": refs or [],
                "title": p.title,
            }
        ],
    }


def test_refresh_cache_only_ttl_and_real_history(tmp_path):
    p = paper()
    path = tmp_path / "cache.json"
    with OpenAlexClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response(p)))
    ) as client:
        assert refresh_openalex([p], path, client, cache_only=True, now=NOW)["requests"] == 0
        assert not path.exists()
        assert refresh_openalex([p], path, client, now=NOW)["ok"] == 1
        before = path.read_bytes(), path.stat().st_mtime_ns
        assert refresh_openalex([p], path, client, now=NOW + timedelta(days=1))["attempted"] == 0
        assert before == (path.read_bytes(), path.stat().st_mtime_ns)
    cache = OpenAlexCache.load(path)
    assert len(cache.history) == 1
    assert cache.history[0].observed_at == NOW
    assert cache.history[0].citation_count == 0
    assert cache.signals.observations[p.id].values["referenced_works"] == []


def test_stale_error_and_identity_remap_preserve_success(tmp_path):
    p, path = paper(), tmp_path / "cache.json"
    with OpenAlexClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=response(p, 12, ["https://openalex.org/W1"]))
        )
    ) as client:
        refresh_openalex([p], path, client, now=NOW)
    with OpenAlexClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(403, text="PRIVATE"))
    ) as client:
        assert refresh_openalex([p], path, client, now=NOW + timedelta(days=31))["error"] == 1
        assert client.requests == 1
    cache = OpenAlexCache.load(path)
    previous = cache.signals.observations[p.id]
    assert previous.fetched_at == NOW
    assert previous.values["citation_count"] == 12
    assert len(cache.history) == 1
    with OpenAlexClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json=response(p, 999, provider_id="https://openalex.org/W999")
            )
        )
    ) as client:
        assert refresh_openalex([p], path, client, now=NOW + timedelta(days=32))["ambiguous"] == 1
    assert OpenAlexCache.load(path).signals.observations[p.id].provider_id == p.openalex_id


def test_missing_unidentified_and_budget_accounting(tmp_path):
    p, path = paper(), tmp_path / "cache.json"
    other = p.model_copy(
        update={
            "id": "manual:unidentified",
            "doi": None,
            "arxiv_id": None,
            "arxiv_doi": None,
            "openalex_id": None,
        }
    )
    with OpenAlexClient(
        max_requests=0, transport=httpx.MockTransport(lambda request: None)
    ) as client:
        result = refresh_openalex([p, other], path, client, now=NOW)
        assert result["attempted"] == 1 and result["ambiguous"] == 1 and result["deferred"] == 1
    with OpenAlexClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"meta": {"count": 0}, "results": []})
        )
    ) as client:
        result = refresh_openalex([p], path, client, now=NOW)
        assert result["not_found"] == 1
    cache = OpenAlexCache.load(path)
    assert not cache.history
    assert cache.signals.observations[p.id].fetched_at is None


def test_daily_dedup_and_later_snapshot(tmp_path):
    p, path = paper(), tmp_path / "cache.json"
    with OpenAlexClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response(p, 10)))
    ) as client:
        refresh_openalex([p], path, client, now=NOW)
    cache = OpenAlexCache.load(path)
    cached_work = cache.works[p.openalex_id]
    cache.record(p.id, cached_work, NOW + timedelta(hours=1))
    assert len(cache.history) == 1
    cache.record(p.id, cached_work, NOW + timedelta(days=8))
    assert len(cache.history) == 2


def test_conflicting_arxiv_provider_merge_requires_review(tmp_path):
    p = paper().model_copy(update={"arxiv_id": "2308.04079", "openalex_id": None})
    raw = response(p, provider_id="https://openalex.org/W123")["results"][0]
    raw["doi"] = "https://doi.org/10.48550/arxiv.2401.00001"
    raw["locations"] = [{"landing_page_url": "https://doi.org/10.48550/arxiv.2308.04079"}]
    path = tmp_path / "cache.json"
    with OpenAlexClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"meta": {"count": 1}, "results": [raw]})
        )
    ) as client:
        report = refresh_openalex([p], path, client, now=NOW)
    assert report["ambiguous"] == 1
    assert not OpenAlexCache.load(path).history
