import httpx
import pytest

from src.extractors.semanticscholar import (
    SemanticScholarClient,
    SemanticScholarFailure,
    refresh_semanticscholar,
)
from src.observations import SignalStore
from src.schema import PaperRecord


def payload(arxiv="2308.04079"):
    return {
        "paperId": "a" * 40,
        "title": "Original 3DGS paper",
        "externalIds": {"ArXiv": arxiv},
        "citationCount": 0,
        "influentialCitationCount": 0,
        "referenceCount": 0,
        "references": [],
    }


def test_zero_exact_identity_cache_and_separate_provider(tmp_path):
    p = PaperRecord(id="2308.04079", arxiv_id="2308.04079", title="Original 3DGS paper")

    def handler(request):
        assert request.headers["x-api-key"] == "private"
        assert "private" not in str(request.url)
        return httpx.Response(200, json=[payload()])

    path = tmp_path / "s2.json"
    with SemanticScholarClient(api_key="private", transport=httpx.MockTransport(handler)) as client:
        assert refresh_semanticscholar([p], path, client)["ok"] == 1
    store = SignalStore.load(path, "semanticscholar")
    obs = store.observations[p.id]
    assert obs.values["citation_count"] == 0 and obs.values["influential_citation_count"] == 0
    assert obs.values["references"] == [] and obs.values["references_complete"]
    with pytest.raises(ValueError):
        SignalStore.load(path, "openalex")
    before = path.read_bytes()
    with SemanticScholarClient(max_requests=0) as client:
        assert refresh_semanticscholar([p], path, client, cache_only=True)["requests"] == 0
    assert path.read_bytes() == before


def test_mismatch_never_assigns_counts(tmp_path):
    p = PaperRecord(id="2308.04079", arxiv_id="2308.04079", title="Original 3DGS paper")
    path = tmp_path / "s2.json"
    with SemanticScholarClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=[payload("2308.040790")])
        )
    ) as client:
        assert refresh_semanticscholar([p], path, client)["ambiguous"] == 1
    assert not SignalStore.load(path, "semanticscholar").observations[p.id].values


def test_pacing_and_auth_latch_and_shape():
    times = [0.0]
    seen = []

    def handler(request):
        seen.append(times[0])
        return httpx.Response(200, json=[None])

    with SemanticScholarClient(
        clock=lambda: times[0],
        sleep=lambda delay: times.__setitem__(0, times[0] + delay),
        transport=httpx.MockTransport(handler),
    ) as client:
        client.batch(["DOI:10.1234/a"])
        client.batch(["DOI:10.1234/b"])
    assert seen == [0, 1]
    with SemanticScholarClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(403, text="private"))
    ) as client:
        for _ in range(2):
            with pytest.raises(SemanticScholarFailure, match="authentication") as error:
                client.batch(["DOI:10.1234/a"])
            assert "private" not in str(error.value)
        assert client.requests == 1
    with SemanticScholarClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
    ) as client:
        with pytest.raises(SemanticScholarFailure, match="invalid_response"):
            client.batch(["DOI:10.1234/a"])


def test_long_rate_limit_defers():
    with SemanticScholarClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, headers={"Retry-After": "3600"})
        )
    ) as client:
        with pytest.raises(SemanticScholarFailure, match="retry_deadline") as error:
            client.batch(["DOI:10.1234/a"])
        assert error.value.retry_after == pytest.approx(3600, abs=0.01)
        assert client.requests == 1
