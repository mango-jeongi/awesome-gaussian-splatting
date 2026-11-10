"""Strict page integrity and persisted successful/error request pacing."""

from datetime import UTC, datetime, timedelta
from xml.sax.saxutils import escape

import httpx
import pytest

from src.extractors.arxiv import ArxivExtractor, ArxivIntegrityError
from src.extractors.arxiv_gate import ArxivRateDeferred, ArxivRateGate


def atom_page(indices, *, total, start=0, declared_size=None):
    entries = []
    for index in indices:
        timestamp = (datetime(2024, 1, 1, tzinfo=UTC) + timedelta(minutes=index)).isoformat()
        entries.append(
            f"<entry><id>https://arxiv.org/abs/2401.{index:05d}v2</id><title>Gaussian Splatting Fixture {index}</title><summary>{escape('We introduce a Gaussian splatting renderer.')}</summary><published>{timestamp}</published><updated>{timestamp}</updated><author><name>Fixture Author</name></author></entry>"
        )
    size = len(indices) if declared_size is None else declared_size
    return (
        f'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"><opensearch:totalResults>{total}</opensearch:totalResults><opensearch:startIndex>{start}</opensearch:startIndex><opensearch:itemsPerPage>{size}</opensearch:itemsPerPage>'
        + "".join(entries)
        + "</feed>"
    )


class FakeClock:
    def __init__(self):
        self.value = 100.0
        self.sleeps = []

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds


def test_successful_pages_share_persisted_spacing_and_full_timestamps(tmp_path):
    clock = FakeClock()
    starts = []

    def respond(request):
        starts.append(clock.now())
        offset = int(request.url.params["start"])
        return httpx.Response(200, text=atom_page([offset], total=2, start=offset))

    transport = httpx.MockTransport(respond)
    path = tmp_path / "gate.json"
    first = ArxivExtractor(
        gate=ArxivRateGate(path, clock=clock.now, sleep=clock.sleep), transport=transport
    )
    second = ArxivExtractor(
        gate=ArxivRateGate(path, clock=clock.now, sleep=clock.sleep), transport=transport
    )
    page = first.fetch_page(page_size=1, start=0)
    second.fetch_page(page_size=1, start=1)
    assert starts[1] - starts[0] >= 3
    assert page.published_at["2401.00000"] == datetime(2024, 1, 1, tzinfo=UTC)
    assert page.records[0].arxiv_id == "2401.00000"
    assert page.total == 2


def test_retry_attempts_also_respect_gate(tmp_path):
    clock = FakeClock()
    starts = []

    def respond(request):
        starts.append(clock.now())
        return (
            httpx.Response(503)
            if len(starts) < 3
            else httpx.Response(200, text=atom_page([0], total=1))
        )

    extractor = ArxivExtractor(
        gate=ArxivRateGate(tmp_path / "gate.json", clock=clock.now, sleep=clock.sleep),
        transport=httpx.MockTransport(respond),
    )
    assert extractor.fetch_page(page_size=1).attempts == 3
    assert starts == [100.0, 103.0, 109.0]


def test_long_retry_deadline_survives_new_client(tmp_path):
    clock = FakeClock()
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "120"})

    path = tmp_path / "gate.json"
    gate = ArxivRateGate(path, clock=clock.now, sleep=clock.sleep)
    extractor = ArxivExtractor(gate=gate, transport=httpx.MockTransport(respond))
    with pytest.raises(ArxivRateDeferred):
        extractor.fetch_page(page_size=1)
    restarted = ArxivRateGate(path, clock=clock.now, sleep=clock.sleep)
    with pytest.raises(ArxivRateDeferred):
        with restarted.connection():
            pytest.fail("Deferred request must not execute")
    assert len(calls) == 1
    clock.value += 120
    with restarted.connection():
        pass


@pytest.mark.parametrize(
    "xml,start,size",
    [
        (atom_page([0], total=3), 0, 2),
        (atom_page([0], total=1, start=1), 0, 1),
        (atom_page([0, 0], total=2), 0, 2),
        (
            atom_page([0], total=1).replace(
                "<opensearch:totalResults>1</opensearch:totalResults>", ""
            ),
            0,
            1,
        ),
    ],
)
def test_invalid_pages_cannot_claim_complete(xml, start, size):
    with pytest.raises(ArxivIntegrityError):
        ArxivExtractor.parse_page(xml, requested_start=start, page_size=size)


def test_corrupt_rate_state_fails_closed(tmp_path):
    path = tmp_path / "gate.json"
    path.write_text('{"last_finished_at":"not-a-time"}', encoding="utf-8")
    with pytest.raises(ValueError, match="timestamp"):
        with ArxivRateGate(path).connection():
            pytest.fail("Corrupt rate state must not dispatch")
    with pytest.raises(ValueError, match="three seconds"):
        ArxivRateGate(path, interval=0)


def test_redirect_is_not_followed_without_pacing(tmp_path):
    clock = FakeClock()
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location": "https://export.arxiv.org/api/elsewhere"})

    extractor = ArxivExtractor(
        gate=ArxivRateGate(tmp_path / "gate.json", clock=clock.now, sleep=clock.sleep),
        transport=httpx.MockTransport(respond),
    )
    with pytest.raises(RuntimeError, match="302"):
        extractor.fetch_page(page_size=1)
    assert len(calls) == 1


def test_gate_excludes_a_second_active_connection(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    clock = FakeClock()
    first = ArxivRateGate(tmp_path / "gate.json", clock=clock.now, sleep=clock.sleep)
    second = ArxivRateGate(
        tmp_path / "gate.json", clock=clock.now, sleep=clock.sleep, lock_timeout=0.15
    )

    def competing_connection():
        with second.connection():
            return "unexpected connection"

    with first.connection(), ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(competing_connection)
        with pytest.raises(TimeoutError, match="Another arXiv API request"):
            future.result(timeout=2)
    with second.connection():
        pass


def test_exact_id_lookup_uses_id_list_without_topic_filter(tmp_path):
    captured = []

    def respond(request):
        captured.append(dict(request.url.params))
        return httpx.Response(200, text=atom_page([1, 2], total=2))

    extractor = ArxivExtractor(
        gate=ArxivRateGate(tmp_path / "lookup-gate.json"), transport=httpx.MockTransport(respond)
    )
    records = extractor.fetch_ids(["2401.00001v2", "https://arxiv.org/abs/2401.00002"])
    assert set(records) == {"2401.00001", "2401.00002"}
    assert captured[0]["id_list"] == "2401.00001,2401.00002" and "search_query" not in captured[0]


def test_identifier_lookup_rejects_unrelated_or_missing_source_ids(tmp_path):
    extractor = ArxivExtractor(
        gate=ArxivRateGate(tmp_path / "mismatch-gate.json"),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=atom_page([3], total=1))
        ),
    )
    with pytest.raises(ArxivIntegrityError):
        extractor.fetch_ids(["2401.00001"])
    with pytest.raises(ValueError):
        extractor.fetch_ids(["not-an-id"])
    with pytest.raises(ValueError):
        extractor.fetch_ids([])
