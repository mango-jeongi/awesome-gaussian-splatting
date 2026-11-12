import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.observations import SignalStore
from src.public import DETAIL_LIMIT, build_public
from src.public_huggingface import public_huggingface
from src.schema import PaperDatabase, PaperRecord

NOW = datetime(2026, 11, 12, tzinfo=UTC)


def fixture(tmp_path, values=None):
    paper = PaperRecord(
        id="2307.10206",
        arxiv_id="2307.10206",
        title="Method",
        abstract="Author abstract",
        code_url="https://github.com/official/reviewed",
    )
    db = PaperDatabase(papers=[paper], total_count=1)
    store = SignalStore(provider="huggingface")
    store.apply(
        paper.id,
        status="ok",
        now=NOW,
        provider_id=paper.arxiv_id,
        values=values
        or {
            "upvotes": 0,
            "stars": 0,
            "private": "omit me",
            "provider_ai_summary": {
                "provider": "huggingface",
                "text": "Provider text <script>unsafe()</script>",
            },
            "repository_evidence": {
                "url": "https://github.com/provider/repo",
                "ownership": "official",
            },
            "linked_spaces": [],
            "linked_spaces_total": 0,
            "linked_spaces_complete": True,
        },
    )
    store.save(tmp_path / "huggingface.json")
    return db, store


def test_whitelisted_provider_zero_and_attribution_preserve_bibliography(tmp_path):
    db, _ = fixture(tmp_path)
    before = db.model_dump(mode="json")
    row = public_huggingface(db, tmp_path)[db.papers[0].id]
    assert row["upvotes"] == row["stars"] == 0
    assert row["provider_ai_summary"]["provider"] == "huggingface"
    assert row["provider_ai_summary"]["source_url"] == row["source_url"]
    assert row["repository_evidence"]["ownership"] == "unverified"
    assert row["linked_spaces"] == [] and row["linked_spaces_complete"]
    assert "private" not in row
    assert db.model_dump(mode="json") == before


@pytest.mark.parametrize("status", ["unknown", "not_found", "ambiguous"])
def test_no_match_or_uncertain_identity_never_publishes_retained_values(tmp_path, status):
    db, store = fixture(tmp_path)
    if status == "unknown":
        # Unknown is a legacy-import state, never a live attempt result.
        previous = store.observations[db.papers[0].id]
        store.observations[db.papers[0].id] = previous.model_copy(update={"status": "unknown"})
    else:
        store.apply(db.papers[0].id, status=status, now=NOW + timedelta(hours=1))
    store.save(tmp_path / "huggingface.json")
    row = public_huggingface(db, tmp_path)[db.papers[0].id]
    assert row["status"] == status
    assert row["upvotes"] is None and row["provider_ai_summary"] is None


def test_failure_retains_successful_values_and_original_observation_time(tmp_path):
    db, store = fixture(tmp_path)
    store.apply(db.papers[0].id, status="error", now=NOW + timedelta(hours=1))
    store.save(tmp_path / "huggingface.json")
    row = public_huggingface(db, tmp_path)[db.papers[0].id]
    assert row["status"] == "error" and row["upvotes"] == 0
    assert row["fetched_at"] == NOW.isoformat()
    assert row["last_attempt_at"] == (NOW + timedelta(hours=1)).isoformat()


def test_conflicting_hf_identity_fails_publication(tmp_path):
    db, store = fixture(tmp_path)
    store.observations[db.papers[0].id].provider_id = "2307.99999"
    store.save(tmp_path / "huggingface.json")
    with pytest.raises(ValueError, match="identity mismatch"):
        public_huggingface(db, tmp_path)


def test_uncached_and_inactive_ids_are_not_turned_into_misses(tmp_path):
    db, store = fixture(tmp_path)
    store.apply("inactive", status="ok", now=NOW, provider_id="2307.11111", values={"upvotes": 9})
    store.save(tmp_path / "huggingface.json")
    db.papers.append(PaperRecord(id="unobserved", title="No lookup"))
    assert set(public_huggingface(db, tmp_path)) == {"2307.10206"}


def test_invalid_links_and_unattributed_summary_are_not_published(tmp_path):
    db, _ = fixture(
        tmp_path,
        {
            "upvotes": None,
            "stars": None,
            "repository_evidence": {"url": "https://github.com.attacker.test/repo"},
            "project_page_evidence": "javascript:alert(1)",
            "provider_summary": {"provider": "another", "text": "Not HF text"},
        },
    )
    row = public_huggingface(db, tmp_path)[db.papers[0].id]
    assert all(
        row[key] is None
        for key in [
            "upvotes",
            "stars",
            "repository_evidence",
            "project_page_evidence",
            "provider_summary",
        ]
    )


def test_spaces_use_validated_ids_without_guessing_official_ownership(tmp_path):
    db, store = fixture(
        tmp_path,
        {
            "linked_spaces": [{"id": "owner/demo", "url": "javascript:evil()"}],
            "linked_spaces_total": 2,
            "linked_spaces_complete": False,
        },
    )
    row = public_huggingface(db, tmp_path)[db.papers[0].id]
    assert row["linked_spaces"] == [
        {"id": "owner/demo", "url": "https://huggingface.co/spaces/owner/demo"}
    ]
    assert row["linked_spaces_complete"] is False
    store.observations[db.papers[0].id].values["linked_spaces"] = [{"id": "owner/.."}]
    store.save(tmp_path / "huggingface.json")
    with pytest.raises(ValueError):
        public_huggingface(db, tmp_path)


def test_community_text_is_lazy_bounded_deterministic_and_index_neutral(tmp_path):
    papers = [
        PaperRecord(
            id=f"2501.{i:05}", arxiv_id=f"2501.{i:05}", title="Method", published_date="2025-01-01"
        )
        for i in range(200)
    ]
    db = PaperDatabase(papers=papers, total_count=200)
    plain = build_public(db, tmp_path / "plain")
    community = {
        p.id: {
            "status": "ok",
            "provider_summary": {"provider": "huggingface", "text": "long provider text " * 600},
        }
        for p in papers
    }
    manifest = build_public(db, tmp_path / "community", community=community)
    assert manifest["search"] == plain["search"]
    index = json.loads((tmp_path / "community" / manifest["index"]["path"]).read_bytes())
    original_index = json.loads((tmp_path / "plain" / plain["index"]["path"]).read_bytes())
    assert index["fields"] == original_index["fields"]
    assert "huggingface" not in index["fields"]
    assert "long provider text" not in json.dumps(index)
    assert manifest["index"]["bytes"] / len(papers) <= 750
    assert all(d["bytes"] <= DETAIL_LIMIT for d in manifest["details"])
    assert len(manifest["details"]) > 1
    details = {}
    for item in manifest["details"]:
        details.update(json.loads((tmp_path / "community" / item["path"]).read_bytes()))
    assert details[papers[0].id]["huggingface"] == community[papers[0].id]
    assert build_public(db, tmp_path / "community", community=community) == manifest
    assert "huggingface" not in db.papers[0].model_dump()


def test_frontend_freshness_validates_future_stamps_and_recent_daily_ttl():
    script = Path(__file__).resolve().parents[1] / "docs/assets/huggingface-view.js"
    code = """const h=require(process.argv[1]);const now=Date.parse('2026-11-12T00:00:00Z');
    const old={status:'ok',fetched_at:'2026-11-10T00:00:00Z'};
    console.log(JSON.stringify([h.state(null,now),h.state(old,now),h.state({...old,submitted_on_daily_at:'2026-11-09T00:00:00Z'},now),h.state({...old,fetched_at:'2026-11-13T00:00:00Z'},now),h.safeLink('javascript:alert(1)'),h.safeLink('https://user:password@example.com')]));"""
    result = json.loads(subprocess.check_output(["node", "-e", code, str(script)], text=True))
    assert result[0]["status"] == "unobserved" and not result[0]["available"]
    assert result[1]["available"] and not result[1]["stale"]
    assert result[2]["stale"] and not result[3]["available"]
    assert result[4:] == [None, None]


@pytest.mark.parametrize("bad", [True, -1])
def test_corrupt_numeric_cache_fails_instead_of_publishing_false_counts(tmp_path, bad):
    db, _ = fixture(tmp_path)
    path = tmp_path / "huggingface.json"
    raw = json.loads(path.read_bytes())
    raw["observations"][db.papers[0].id]["values"]["upvotes"] = bad
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid nonnegative integer signal"):
        public_huggingface(db, tmp_path)
