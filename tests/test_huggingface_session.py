import argparse
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from src.cli import prepare_hf_preview
from src.extractors.huggingface_client import HFFailure
from src.extractors.huggingface_contracts import parse_daily
from src.huggingface_session import discover_scheduled
from src.schema import PaperDatabase

NOW = datetime(2026, 11, 9, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1]


class Client:
    def __init__(self, budget=100, full=False):
        self.budget = budget
        self.requests = 0
        self.days = []
        self.full = full

    def daily(self, *, day, limit):
        if self.requests >= self.budget:
            raise HFFailure("run_budget")
        self.requests += 1
        self.days.append(day.isoformat())
        return parse_daily(
            [
                {
                    "paper": {
                        "id": "2308.04079",
                        "title": "3D Gaussian Splatting Fixture",
                        "publishedAt": "2023-08-08T00:00:00Z",
                        "summary": "Provider prose",
                    }
                }
            ]
            if self.full
            else []
        )


def test_pending_window_survives_utc_and_ttl_without_refetching_completed_days(tmp_path):
    first = Client(1)
    _, report = discover_scheduled(first, tmp_path, until=NOW.date(), lookback=2, now=NOW)
    assert report["phase"] == "pending" and first.days == ["2026-11-09"]
    run_id = report["run_id"]
    later = Client(1)
    _, resumed = discover_scheduled(
        later, tmp_path, until=date(2026, 11, 12), lookback=2, now=NOW + timedelta(days=3)
    )
    assert resumed["sampled"] and resumed["complete"] and resumed["run_id"] == run_id
    assert resumed["until"] == "2026-11-09" and later.days == ["2026-11-08"]
    assert resumed["days"][0]["resumed_frozen"]
    assert resumed["days"][0]["response_sha256"] == report["days"][0]["response_sha256"]


def test_outage_catches_up_in_bounded_overlapping_windows_without_date_gap(tmp_path):
    _, initial = discover_scheduled(Client(), tmp_path, until=NOW.date(), lookback=2, now=NOW)
    _, next_window = discover_scheduled(
        Client(), tmp_path, until=date(2026, 11, 15), lookback=2, now=NOW + timedelta(days=6)
    )
    assert next_window["since"] == "2026-11-08" and next_window["until"] == "2026-11-11"
    assert next_window["requested_days"] == 4 and next_window["sampled"]
    seen = {d["day"] for d in initial["days"] + next_window["days"]}
    for _ in range(2):
        _, report = discover_scheduled(
            Client(), tmp_path, until=date(2026, 11, 15), lookback=2, now=NOW + timedelta(days=6)
        )
        seen.update(d["day"] for d in report["days"])
    assert seen == {(date(2026, 11, 8) + timedelta(days=i)).isoformat() for i in range(8)}
    assert len(list((tmp_path / "scheduled-runs").glob("*.json"))) == 3


def test_tampered_frozen_evidence_and_configuration_fail_before_provider_traffic(tmp_path):
    _, report = discover_scheduled(Client(1), tmp_path, until=NOW.date(), lookback=2, now=NOW)
    first = report["days"][0]
    path = tmp_path / "responses" / f"{first['day']}.{first['response_sha256']}.json"
    path.write_bytes(b"{}")
    client = Client()
    with pytest.raises(ValueError, match="hash mismatch"):
        discover_scheduled(client, tmp_path, until=NOW.date(), lookback=2, now=NOW)
    assert client.requests == 0
    with pytest.raises(ValueError, match="configuration changed"):
        discover_scheduled(client, tmp_path, until=NOW.date(), lookback=3, now=NOW)
    assert client.requests == 0


def test_full_page_is_sampled_but_inventory_never_claimed_complete(tmp_path):
    entries, report = discover_scheduled(
        Client(full=True), tmp_path, until=NOW.date(), lookback=1, limit=1, now=NOW
    )
    assert len(entries) == 1 and report["sampled"] and not report["complete"]
    assert report["days"][0]["status"] == "possibly_truncated"
    assert not report["corpus_modified"]


def test_preview_uses_frozen_response_hash_not_mutable_daily_pointer(tmp_path):
    entries, report = discover_scheduled(
        Client(full=True), tmp_path / "cache", until=NOW.date(), lookback=1, now=NOW
    )
    assert entries
    (tmp_path / "cache/latest-report.json").write_text(json.dumps(report), encoding="utf-8")
    # A separate legacy pass can replace a dated pointer; the frozen response is authoritative.
    (tmp_path / "cache/2026-11-09-100.json").write_bytes(b"{}")
    data = tmp_path / "papers.json"
    PaperDatabase().save(data)
    before = data.read_bytes()
    args = argparse.Namespace(
        cache=tmp_path / "cache", data=data, taxonomy=ROOT / "config/taxonomy.yaml"
    )
    _, _, proposal = prepare_hf_preview(args)
    assert proposal["unique_candidates"] == 1 and proposal["discovery_complete"]
    assert data.read_bytes() == before


@pytest.mark.parametrize("filename", ["daily-feed.yml", "daily-signals.yml"])
def test_scheduled_hf_discovery_is_budgeted_persisted_and_preview_only(filename):
    workflow = yaml.load(
        (ROOT / ".github/workflows" / filename).read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    assert workflow["concurrency"] == {"group": "repository-writer", "cancel-in-progress": "false"}
    steps = next(iter(workflow["jobs"].values()))["steps"]
    script = next(s["run"] for s in steps if "discover-huggingface" in s.get("run", ""))
    assert (
        script.index("git fetch")
        < script.index("discover-huggingface")
        < script.index("src.cli build")
    )
    assert "--max-requests 10 --max-seconds 120" in script
    assert "--preview-report reports/runs/hf-import-proposal.json" in script
    assert "apply-huggingface-import" not in script
    commit = next(s["run"] for s in steps if "git add --all" in s.get("run", ""))
    assert "data/ingestion/huggingface" in commit and "reports/runs" in commit
