from datetime import UTC, datetime, timedelta

import httpx

from src.extractors.huggingface_client import HFPapersClient
from src.huggingface_cache import refresh_huggingface
from src.observations import SignalStore
from src.schema import PaperRecord


def test_hf_success_failure_preservation_and_cache_only(tmp_path):
    paper = PaperRecord(
        id="p",
        arxiv_id="2308.04079",
        title="Fixture",
        abstract="Author abstract",
        code_url="https://official.example/code",
    )
    path = tmp_path / "hf.json"
    now = datetime(2026, 11, 9, tzinfo=UTC)
    payload = {
        "id": "2308.04079",
        "title": "Fixture",
        "upvotes": 0,
        "summary": "HF summary",
        "githubRepo": "https://unverified.example/repo",
    }
    with HFPapersClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        assert refresh_huggingface([paper], path, client, now=now)["ok"] == 1
    before = SignalStore.load(path, "huggingface").observations["p"]
    assert before.values["upvotes"] == 0 and "stars" not in before.values
    assert before.values["repository_evidence"]["ownership"] == "unverified"
    assert paper.abstract == "Author abstract" and paper.code_url == "https://official.example/code"
    with HFPapersClient(
        max_requests=1, transport=httpx.MockTransport(lambda request: httpx.Response(500))
    ) as client:
        assert refresh_huggingface([paper], path, client, now=now + timedelta(days=8))["error"] == 1
    after = SignalStore.load(path, "huggingface").observations["p"]
    assert after.values == before.values and after.fetched_at == before.fetched_at
    raw = path.read_bytes()
    with HFPapersClient(max_requests=0) as client:
        assert refresh_huggingface([paper], path, client, cache_only=True)["requests"] == 0
    assert path.read_bytes() == raw
