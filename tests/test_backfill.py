"""Historical discovery recovery, source reconciliation, and half-open boundaries."""

import json
import re
from datetime import UTC, datetime, timedelta

import pytest

from src.backfill import HistoricalCrawler, HistoricalSpec
from src.extractors.arxiv import ArxivIntegrityError, ArxivPage
from src.schema import PaperRecord

START = datetime(2024, 1, 1, tzinfo=UTC)


def spec(**kwargs):
    return HistoricalSpec(
        query='all:"Gaussian Splatting"',
        comparator_query='ti:"Gaussian Splatting"',
        policy_digest="a" * 64,
        since=START,
        until=START + timedelta(days=1),
        page_size=60,
        **kwargs,
    )


class FixtureSource:
    def __init__(self, entries=None):
        self.entries = (
            entries
            if entries is not None
            else [(index, START + timedelta(minutes=index)) for index in range(150)]
        )
        self.calls = []
        self.fault = None

    def fetch_page(self, *, query, start, page_size, sort_by, sort_order, max_attempts):
        assert (sort_by, sort_order) == ("submittedDate", "ascending")
        assert max_attempts >= 1
        bounds = re.findall(r"submittedDate:\[(\d+) TO (\d+)\]", query)
        if bounds:
            lower, upper = bounds[-1]
            lower = datetime.strptime(lower, "%Y%m%d%H%M").replace(tzinfo=UTC)
            upper = datetime.strptime(upper, "%Y%m%d%H%M").replace(tzinfo=UTC) + timedelta(
                minutes=1
            )
        else:
            lower, upper = datetime(1990, 1, 1, tzinfo=UTC), datetime(2100, 1, 1, tzinfo=UTC)
        selected = sorted(
            (entry for entry in self.entries if lower <= entry[1] < upper),
            key=lambda entry: (entry[1], entry[0]),
        )
        self.calls.append((start, query))
        batch = selected[start : start + page_size]
        total = len(selected)
        if start == 60 and self.fault == "repeat":
            batch = selected[:page_size]
        if start == 60 and self.fault == "short":
            batch = batch[:-1]
        if start == 60 and self.fault == "total":
            total += 1
        records = tuple(
            PaperRecord(
                id=f"2401.{index:05d}",
                arxiv_id=f"2401.{index:05d}",
                title=f"Gaussian Splatting Fixture {index}",
                published_date=stamp.date().isoformat(),
                published_date_precision="day",
                updated_date=stamp.date().isoformat(),
            )
            for index, stamp in batch
        )
        published = {record.id: stamp for record, (_, stamp) in zip(records, batch, strict=True)}
        return ArxivPage(records, total, start, published, dict(published))


def test_more_than_sixty_replays_and_resumes_without_loss(tmp_path):
    source = FixtureSource()
    first = HistoricalCrawler(spec(), tmp_path, source)
    assert first.run(max_requests=1)["status"] == "running"
    assert next(iter(first.state.slices.values())).offset == 60
    resumed = HistoricalCrawler(spec(), tmp_path, source)
    report = resumed.run(max_requests=3)
    assert report["status"] == "complete"
    assert report["unique_in_interval"] == 150
    assert [start for start, _ in source.calls] == [0, 0, 60, 120]
    assert len({record.id for record in resumed.records()}) == 150
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in tmp_path.rglob("*.json")
    }
    assert resumed.run(max_requests=1)["invocation_requests"] == 0
    assert before == {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in tmp_path.rglob("*.json")
    }


@pytest.mark.parametrize("fault", ["repeat", "short", "total"])
def test_invalid_next_page_does_not_advance_cursor(tmp_path, fault):
    source = FixtureSource()
    source.fault = fault
    crawler = HistoricalCrawler(spec(), tmp_path, source)
    with pytest.raises(ArxivIntegrityError):
        crawler.run(max_requests=10)
    interval = next(iter(crawler.state.slices.values()))
    assert interval.offset == 60
    assert len(interval.pages) == 1
    assert crawler.state.status == "failed"
    source.fault = None
    resumed = HistoricalCrawler(spec(), tmp_path, source)
    assert resumed.run(max_requests=10)["unique_in_interval"] == 150


def test_changed_policy_cannot_reuse_checkpoint(tmp_path):
    source = FixtureSource()
    HistoricalCrawler(spec(), tmp_path, source).run(max_requests=1)
    changed = spec().model_copy(update={"policy_digest": "b" * 64})
    with pytest.raises(ValueError, match="changed"):
        HistoricalCrawler(changed, tmp_path, source).run()
    assert len(source.calls) == 1


def test_overflow_subdivides_and_parent_counts_reconcile(tmp_path):
    source = FixtureSource(
        [(index, START + timedelta(hours=hour)) for index, hour in enumerate([1, 3, 7, 13, 17, 21])]
    )
    bounds = spec().model_copy(update={"page_size": 2, "max_slice_results": 3})
    crawler = HistoricalCrawler(bounds, tmp_path, source)
    report = crawler.run(max_requests=20)
    assert report["status"] == "complete"
    assert report["unique_in_interval"] == 6
    assert len(crawler.state.slices) == 3
    parent = crawler.state.slices[crawler.state.roots[0]]
    assert parent.probe is not None
    assert parent.status == "complete"


def test_inclusive_source_bounds_are_half_open_in_results(tmp_path):
    end = START + timedelta(days=1)
    source = FixtureSource([(0, START), (1, end - timedelta(seconds=1)), (2, end)])
    crawler = HistoricalCrawler(spec(), tmp_path, source)
    assert crawler.run()["unique_in_interval"] == 2
    assert next(iter(crawler.state.slices.values())).expected_total == 3
    assert [record.id for record in crawler.records()] == ["2401.00000", "2401.00001"]


def test_crash_after_page_persistence_before_cursor_ack_replays(tmp_path, monkeypatch):
    import src.backfill as backfill

    real_write = backfill._atomic_write
    interrupted = False

    def crash(path, payload):
        nonlocal interrupted
        if path.name == "checkpoint.json" and not interrupted:
            state = json.loads(payload)
            if any(interval["offset"] for interval in state["slices"].values()):
                interrupted = True
                raise KeyboardInterrupt("simulated process interruption")
        real_write(path, payload)

    monkeypatch.setattr(backfill, "_atomic_write", crash)
    source = FixtureSource()
    with pytest.raises(KeyboardInterrupt):
        HistoricalCrawler(spec(), tmp_path, source).run()
    assert list((tmp_path / "pages").rglob("*.json"))
    saved = json.loads((tmp_path / "checkpoint.json").read_bytes())
    assert all(interval["offset"] == 0 for interval in saved["slices"].values())
    monkeypatch.setattr(backfill, "_atomic_write", real_write)
    resumed = HistoricalCrawler(spec(), tmp_path, source)
    report = resumed.run()
    assert report["unique_in_interval"] == 150
    assert report["interrupted_attempt_upper_bound"] > 0


def test_corrupt_cache_or_forged_empty_completion_fails_closed(tmp_path):
    source = FixtureSource()
    crawler = HistoricalCrawler(spec(), tmp_path, source)
    crawler.run(max_requests=1)
    page = next((tmp_path / "pages").rglob("*.json"))
    original = page.read_bytes()
    page.write_bytes(b"{}")
    with pytest.raises(ValueError, match="checksum"):
        HistoricalCrawler(spec(), tmp_path, source).run()
    page.write_bytes(original)
    checkpoint = tmp_path / "checkpoint.json"
    state = json.loads(checkpoint.read_bytes())
    state["roots"] = []
    state["status"] = "complete"
    checkpoint.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ArxivIntegrityError, match="root inventory"):
        HistoricalCrawler(spec(), tmp_path, source).run()
