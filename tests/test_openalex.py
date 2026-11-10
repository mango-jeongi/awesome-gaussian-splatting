import httpx
import pytest

from src.extractors.openalex import OpenAlexClient, OpenAlexFailure


class Clock:
    def __init__(self):
        self.value = 0

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


def work(doi="10.1234/exact", count=0):
    return {
        "id": "https://openalex.org/W123",
        "doi": "https://doi.org/" + doi,
        "title": "A paper",
        "cited_by_count": count,
        "referenced_works": [],
    }


def client(handler, **kwargs):
    clock = Clock()
    result = OpenAlexClient(
        transport=httpx.MockTransport(handler),
        clock=clock.now,
        sleep=clock.sleep,
        jitter=lambda: 0,
        **kwargs,
    )
    return result, clock


def test_exact_zero_empty_and_header_credentials():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer private-secret"
        assert "private-secret" not in str(request.url)
        assert request.url.params["filter"] == "doi:10.1234/exact"
        return httpx.Response(
            200, json={"meta": {"count": 1, "cost_usd": 0.001}, "results": [work()]}
        )

    api, _ = client(handler, api_key="private-secret")
    with api:
        result = api.by_dois(["HTTPS://DOI.ORG/10.1234/EXACT"])
        assert result["10.1234/exact"][0].cited_by_count == 0
        assert result["10.1234/exact"][0].referenced_works == []
        assert api.requests == 1 and api.cost_usd == 0.001


@pytest.mark.parametrize("status", [401, 403])
def test_auth_is_latched_and_sanitized(status):
    api, _ = client(lambda request: httpx.Response(status, text="private-secret"))
    with api:
        for _ in range(2):
            with pytest.raises(OpenAlexFailure, match="authentication") as error:
                api.by_dois(["10.1234/exact"])
            assert "private-secret" not in str(error.value)
        assert api.requests == 1


def test_no_substring_identity_or_partial_pagination():
    for payload in [
        {"meta": {"count": 1}, "results": [work("10.1234/exact-suffix")]},
        {"meta": {"count": 2}, "results": [work()]},
        {"meta": {"count": 1}, "results": [work(count=True)]},
    ]:
        api, _ = client(lambda request, payload=payload: httpx.Response(200, json=payload))
        with api, pytest.raises(OpenAlexFailure):
            api.by_dois(["10.1234/exact"])


def test_retry_after_and_request_ceiling():
    replies = [
        httpx.Response(429, headers={"Retry-After": "4"}),
        httpx.Response(200, json={"meta": {"count": 0}, "results": []}),
    ]
    api, clock = client(lambda request: replies.pop(0), max_requests=2)
    with api:
        assert api.by_dois(["10.1234/exact"]) == {"10.1234/exact": []}
        assert clock.value == 4
        with pytest.raises(OpenAlexFailure, match="run_budget"):
            api.by_dois(["10.1234/exact"])
        assert api.requests == 2


def test_budget_exhaustion_preserves_current_success_and_stops_next():
    api, _ = client(
        lambda request: httpx.Response(
            200,
            headers={"X-RateLimit-Remaining": "0"},
            json={"meta": {"count": 1}, "results": [work()]},
        )
    )
    with api:
        assert api.by_dois(["10.1234/exact"])["10.1234/exact"]
        with pytest.raises(OpenAlexFailure, match="account_budget"):
            api.by_dois(["10.1234/exact"])
        assert api.requests == 1


def test_long_retry_defers_and_transport_errors_never_leak_urls():
    api, _ = client(lambda request: httpx.Response(429, headers={"Retry-After": "3600"}))
    with api, pytest.raises(OpenAlexFailure) as error:
        api.by_dois(["10.1234/exact"])
    assert error.value.retry_after == 3600
    assert api.requests == 1

    def bad(request):
        raise httpx.ConnectError("secret raw request", request=request)

    api, clock = client(bad)
    with api, pytest.raises(OpenAlexFailure, match="transport") as error:
        api.by_dois(["10.1234/exact"])
    assert "secret" not in str(error.value)
    assert api.requests == 3 and clock.value >= 3


def test_empty_dois_and_batch_limits_do_not_request():
    api, _ = client(lambda request: pytest.fail("Unexpected network request"))
    with api:
        assert api.by_dois([]) == {}
        with pytest.raises(ValueError):
            api.by_dois([f"10.1234/{i}" for i in range(41)])
        assert api.requests == 0


def test_publication_work_matches_evidenced_location_alias():
    raw = work("10.1234/publication")
    raw["locations"] = [{"landing_page_url": "https://doi.org/10.48550/arxiv.2308.04079"}]
    api, _ = client(
        lambda request: httpx.Response(200, json={"meta": {"count": 1}, "results": [raw]})
    )
    with api:
        result = api.by_dois(["10.48550/arxiv.2308.04079"])
        assert result["10.48550/arxiv.2308.04079"][0].doi == "https://doi.org/10.1234/publication"
