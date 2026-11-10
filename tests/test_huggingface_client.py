import httpx
import pytest

from src.extractors.huggingface_client import HFFailure, HFPapersClient


def test_miss_failure_and_identity_are_distinct():
    for status, expected in [(404, None), (429, "rate_limited"), (403, "authentication")]:
        with HFPapersClient(
            max_requests=1,
            transport=httpx.MockTransport(lambda request, status=status: httpx.Response(status)),
        ) as client:
            if expected:
                with pytest.raises(HFFailure, match=expected):
                    client.paper("2308.04079")
            else:
                assert client.paper("2308.04079") is None
            assert client.requests == 1
    with HFPapersClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"id": "2308.040790", "title": "Mismatch"})
        )
    ) as client:
        with pytest.raises(HFFailure):
            client.paper("2308.04079")


def test_daily_and_budget():
    with HFPapersClient(
        max_requests=1,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json=[{"paper": {"id": "2308.04079", "title": "Fixture", "upvotes": 0}}]
            )
        ),
    ) as client:
        assert client.daily(limit=1)[0].paper.upvotes == 0
        with pytest.raises(HFFailure, match="run_budget"):
            client.daily(limit=1)
