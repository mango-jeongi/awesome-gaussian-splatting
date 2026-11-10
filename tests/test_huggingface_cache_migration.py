from datetime import UTC, datetime, timedelta

import httpx

from src.extractors.huggingface_client import HFPapersClient
from src.huggingface_cache import refresh_huggingface
from src.observations import SignalStore
from src.schema import PaperRecord


def test_fresh_old_contract_refreshes_and_error_keeps_contract(tmp_path):
    path = tmp_path / "hf.json"
    now = datetime(2026, 11, 9, tzinfo=UTC)
    store = SignalStore(provider="huggingface")
    store.apply("p", status="ok", now=now, provider_id="2308.04079", values={"upvotes": 0})
    store.save(path)
    paper = PaperRecord(id="p", arxiv_id="2308.04079", title="Fixture")
    payload = {
        "id": "2308.04079",
        "title": "Fixture",
        "linkedSpaces": [{"id": "owner/evidence"}],
        "numTotalSpaces": 2,
    }
    with HFPapersClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        assert refresh_huggingface([paper], path, client, now=now + timedelta(hours=1))["ok"] == 1
    observation = SignalStore.load(path, "huggingface").observations["p"]
    assert observation.response_schema_version == "hf-paper-v2"
    assert observation.values["linked_spaces_complete"] is False
    store = SignalStore.load(path, "huggingface")
    store.apply("p", status="error", now=now + timedelta(hours=2))
    assert store.observations["p"].response_schema_version == "hf-paper-v2"
