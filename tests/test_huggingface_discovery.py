from datetime import UTC, date, datetime

import httpx

from src.extractors.huggingface import candidate_record
from src.extractors.huggingface_client import HFPapersClient
from src.huggingface_discovery import discover_daily


def test_bounded_discovery_resume_and_provider_fields_not_canonical(tmp_path):
    payload = [
        {
            "paper": {
                "id": "2308.04079",
                "title": "3D Gaussian Splatting Fixture",
                "publishedAt": "2023-08-08T00:00:00Z",
                "summary": "HF provider prose",
                "githubRepo": "https://unverified.example/repo",
                "upvotes": 0,
            }
        }
    ]
    now = datetime(2026, 11, 9, tzinfo=UTC)
    with HFPapersClient(
        max_requests=1,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
    ) as client:
        entries, report = discover_daily(
            client, tmp_path, until=date(2026, 11, 9), lookback=2, limit=10, now=now
        )
        assert not report["complete"] and report["days"][-1]["status"] == "run_budget"
    record = candidate_record(entries[0])
    assert record.abstract == "" and not record.code_url and record.source == "huggingface"
    with HFPapersClient(
        max_requests=1,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
    ) as client:
        entries, report = discover_daily(
            client, tmp_path, until=date(2026, 11, 9), lookback=2, limit=10, now=now
        )
        assert report["complete"] and client.requests == 1 and len(entries) == 1
    with HFPapersClient(max_requests=0) as client:
        _, report = discover_daily(
            client, tmp_path, until=date(2026, 11, 9), lookback=2, limit=10, now=now
        )
        assert report["complete"] and client.requests == 0


def test_full_page_cannot_claim_complete_inventory(tmp_path):
    with HFPapersClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json=[{"paper": {"id": "2308.04079", "title": "Fixture"}}]
            )
        )
    ) as client:
        _, report = discover_daily(
            client,
            tmp_path,
            until=date(2026, 11, 9),
            lookback=1,
            limit=1,
            now=datetime(2026, 11, 9, tzinfo=UTC),
        )
    assert not report["complete"] and report["days"][0]["status"] == "possibly_truncated"
