import httpx
import pytest

from src.extractors.dblp import DBLPClient, DBLPFailure, parse_page


def page(total, first, count):
    return {
        "result": {
            "hits": {
                "@total": str(total),
                "@sent": str(count),
                "@first": str(first),
                "hit": [
                    {"info": {"key": f"conf/fixture/{i}", "title": "Fixture paper"}}
                    for i in range(first, first + count)
                ],
            }
        }
    }


def test_more_than_1000_total_results_are_paged_without_loss():
    offsets = []

    def respond(request):
        first = int(request.url.params["f"])
        offsets.append(first)
        return httpx.Response(200, json=page(1001, first, min(600, 1001 - first)))

    with DBLPClient(
        max_requests=2, transport=httpx.MockTransport(respond), sleep=lambda seconds: None
    ) as client:
        rows = client.search("venue:fixture: year:2023:", page_size=600)
    assert offsets == [0, 600]
    assert len(rows) == len({r["key"] for r in rows}) == 1001


def test_budget_exhaustion_never_returns_partial_inventory():
    with DBLPClient(
        max_requests=1,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=page(1001, 0, 600))),
    ) as client:
        with pytest.raises(DBLPFailure, match="request budget"):
            client.search("fixture", page_size=600)


def test_oversized_response_refused_before_json_parse():
    with DBLPClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * 100))
    ) as client:
        with pytest.raises(DBLPFailure, match="byte budget"):
            client.search("fixture", max_response_bytes=10)


def test_oversized_page_refused_even_when_total_is_consistent():
    with DBLPClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=page(2, 0, 2)))
    ) as client:
        with pytest.raises(DBLPFailure, match="page size"):
            client.search("fixture", page_size=1)


def test_deadline_includes_required_pacing_and_blocks_next_request():
    calls = []
    with DBLPClient(
        clock=lambda: 0,
        sleep=lambda seconds: calls.append("sleep"),
        transport=httpx.MockTransport(
            lambda request: calls.append("request") or httpx.Response(200, json=page(2, 0, 1))
        ),
    ) as client:
        with pytest.raises(DBLPFailure, match="time budget"):
            client.search("fixture", page_size=1, max_seconds=0.5)
    assert calls == ["request"]


def test_unhashable_work_key_is_a_contract_failure():
    payload = page(1, 0, 1)
    payload["result"]["hits"]["hit"][0]["info"]["key"] = ["not-a-string"]
    with pytest.raises(DBLPFailure, match="contract"):
        parse_page(payload, 0)
