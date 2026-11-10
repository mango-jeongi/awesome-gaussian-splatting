import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.observations import SignalStore
from src.openalex_cache import OpenAlexCache
from src.public import build_public
from src.public_signals import public_signals
from src.schema import PaperDatabase, PaperRecord

NOW = datetime(2026, 11, 9, tzinfo=UTC)


def test_public_counts_preserve_zero_source_labels_and_omit_private_response_fields(tmp_path):
    db = PaperDatabase(papers=[PaperRecord(id="p", title="Paper")])
    oa = OpenAlexCache()
    oa.signals.apply(
        "p",
        status="ok",
        now=NOW,
        provider_id="https://openalex.org/W1",
        values={"citation_count": 0, "private": "secret"},
    )
    oa.save(tmp_path / "openalex-cache.json")
    s2 = SignalStore(provider="semanticscholar")
    s2.apply(
        "p",
        status="ok",
        now=NOW,
        provider_id="a" * 40,
        values={"citation_count": 7, "influential_citation_count": 0},
    )
    s2.apply("archived", status="ok", now=NOW, provider_id="b" * 40, values={"citation_count": 900})
    s2.save(tmp_path / "semanticscholar.json")
    signals = public_signals(db, tmp_path)
    assert signals["papers"]["p"]["openalex"]["citation_count"] == 0
    assert signals["papers"]["p"]["semanticscholar"]["citation_count"] == 7
    assert signals["papers"]["p"]["semanticscholar"]["influential_citation_count"] == 0
    assert "archived" not in signals["papers"] and "secret" not in json.dumps(signals)
    manifest = build_public(db, tmp_path / "public", signals=signals)
    raw = (tmp_path / "public" / manifest["signals"]["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["signals"]["sha256"]
    index = json.loads((tmp_path / "public" / manifest["index"]["path"]).read_bytes())
    row = dict(zip(index["fields"], index["papers"][0], strict=True))
    assert row["citation_count"] == 0 and row["citation_status"] == "ok"
    assert row["citation_fetched_at"] == NOW.isoformat()
    assert build_public(db, tmp_path / "public", signals=signals) == manifest


def test_missing_and_ambiguous_are_unavailable_errors_retain_dated_success(tmp_path):
    db = PaperDatabase(
        papers=[PaperRecord(id="p", title="Paper"), PaperRecord(id="missing", title="Missing")]
    )
    store = SignalStore(provider="semanticscholar")
    store.apply("p", status="ok", now=NOW, provider_id="a" * 40, values={"citation_count": 4})
    store.apply("p", status="error", now=NOW + timedelta(hours=1))
    db._signal_stores["semanticscholar"] = store
    signals = public_signals(db, tmp_path)
    assert signals["papers"]["p"]["semanticscholar"]["citation_count"] == 4
    assert signals["papers"]["p"]["semanticscholar"]["status"] == "error"
    assert signals["papers"]["missing"]["semanticscholar"]["citation_count"] is None
    store.apply("p", status="ambiguous", now=NOW + timedelta(hours=2))
    assert public_signals(db, tmp_path)["papers"]["p"]["semanticscholar"]["citation_count"] is None


def test_browser_count_selection_freshness_and_zero_sort_are_source_separated():
    asset = Path(__file__).resolve().parents[1] / "docs/assets/provider-signals.js"
    script = r"""
const api=require(process.argv[1]);
const assert=require('assert/strict');
const paper={id:'p',published_date:'2026-11-01',citation_count:99,citation_status:'unknown'};
const payload={papers:{p:{openalex:{citation_count:0,status:'ok',fetched_at:'2026-11-09T00:00:00Z'},semanticscholar:{citation_count:7,influential_citation_count:0,status:'ok',fetched_at:'2026-11-01T00:00:00Z'}}}};
const now=Date.parse('2026-11-09T01:00:00Z');
const oa=api.signal(paper,'openalex',payload,now), s2=api.signal(paper,'semanticscholar',payload,now);
assert.equal(oa.count,0);assert.equal(oa.label,'OpenAlex');assert.equal(oa.stale,false);
assert.equal(s2.count,7);assert.equal(s2.influential,0);assert.equal(s2.stale,true);
assert.equal(api.signal(paper,'semanticscholar',null,now).count,null);
assert.equal(api.compare(oa,s2)<0,true);
assert.equal(api.compare(oa,{count:null,stale:false})<0,true);
assert.equal(api.signal({...paper,id:'toString'},'semanticscholar',payload,now).count,null);
"""
    subprocess.run(["node", "-e", script, str(asset)], check=True, capture_output=True, text=True)


def test_five_thousand_complete_provider_rows_fit_lazy_artifact_budget(tmp_path):
    db = PaperDatabase(papers=[PaperRecord(id=f"paper-{i}", title="Fixture") for i in range(5000)])
    for provider in ("openalex", "semanticscholar"):
        store = SignalStore(provider=provider)
        for paper in db.papers:
            store.apply(
                paper.id,
                status="ok",
                now=NOW,
                provider_id="https://openalex.org/W1" if provider == "openalex" else "a" * 40,
                values={"citation_count": 100000, "influential_citation_count": 100},
            )
        db._signal_stores[provider] = store
    signals = public_signals(db, tmp_path)
    assert len(signals["papers"]) == 5000
    from src.public import compact

    assert len(compact(signals)) < 4_000_000
