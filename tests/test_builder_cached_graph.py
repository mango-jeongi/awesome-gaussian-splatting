"""Public builds consume cached lineage offline and fail before output on conflicts."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from src.builder import build_artifacts
from src.extractors.openalex import OpenAlexWork
from src.identity import IdentityConflict
from src.openalex_cache import OpenAlexCache
from src.schema import PaperDatabase, PaperRecord
from src.storage import write_store

NOW = datetime(2026, 11, 11, tzinfo=UTC)
TAXONOMY = Path(__file__).resolve().parents[1] / "config/taxonomy.yaml"


def prohibit_network(*args, **kwargs):
    raise AssertionError("An offline build must not create an HTTP client")


def inputs(tmp_path, papers):
    data = tmp_path / "data/papers.json"
    data.parent.mkdir()
    PaperDatabase(papers=papers, total_count=len(papers)).save(data)
    return data, data.parent / "signals/openalex-cache.json"


@pytest.mark.parametrize("storage", ["v1", "v2"])
def test_build_uses_cached_edges_empty_success_and_retained_failure_without_source_write(
    tmp_path, monkeypatch, storage
):
    first = PaperRecord(
        id="stable/first",
        title="First Gaussian method",
        citation_count=99,
        openalex_id="https://openalex.org/W1",
        referenced_works=["https://openalex.org/W2"],
        db_references=["stable/second"],
    )
    second = PaperRecord(id="stable/second", title="Second Gaussian method")
    legacy_only = PaperRecord(
        id="stable/third", title="Legacy unobserved source", db_references=[first.id]
    )
    data, cache_path = inputs(tmp_path, [first, second, legacy_only])
    if storage == "v2":
        manifest = data.parent / "manifest.json"
        write_store(PaperDatabase.load(data), manifest)
        data = manifest
    cache = OpenAlexCache()
    cache.record(
        first.id,
        OpenAlexWork(id="https://openalex.org/W1", cited_by_count=0, referenced_works=[]),
        NOW,
    )
    cache.signals.apply(first.id, status="error", now=NOW + timedelta(hours=1))
    cache.record(
        second.id,
        OpenAlexWork(
            id="https://openalex.org/W2",
            cited_by_count=7,
            referenced_works=["https://openalex.org/W1", "https://openalex.org/W999"],
        ),
        NOW,
    )
    cache_path.parent.mkdir(exist_ok=True)
    cache.save(cache_path)
    original, cache_bytes = data.read_bytes(), cache_path.read_bytes()
    source_files = {p: p.read_bytes() for p in data.parent.rglob("*") if p.is_file()}
    monkeypatch.setattr(httpx, "Client", prohibit_network)
    readme, legacy = tmp_path / "README.md", tmp_path / "docs/papers.json"
    build_artifacts(data, TAXONOMY, readme, legacy)
    published = PaperDatabase.load(legacy)
    assert published.get(first.id).citation_count == 0
    assert published.get(first.id).db_references == []
    assert published.get(second.id).db_references == [first.id]
    assert published.get(first.id).db_citations == [second.id, legacy_only.id]
    assert published.get(legacy_only.id).db_references == [first.id]
    manifest = json.loads((legacy.parent / "data/manifest.json").read_bytes())
    assert manifest["graph"]["coverage"]["edges"] == 2
    assert manifest["graph"]["coverage"]["unmatched_source_references"] == 1
    signals = json.loads((legacy.parent / "data" / manifest["signals"]["path"]).read_bytes())
    assert signals["papers"][first.id]["openalex"]["status"] == "error"
    assert signals["papers"][first.id]["openalex"]["citation_count"] == 0
    assert data.read_bytes() == original
    assert cache_path.read_bytes() == cache_bytes
    assert source_files == {p: p.read_bytes() for p in data.parent.rglob("*") if p.is_file()}
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    build_artifacts(data, TAXONOMY, readme, legacy)
    assert before == {
        p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }


def test_cache_identity_collision_fails_before_any_public_output(tmp_path, monkeypatch):
    first = PaperRecord(id="new/preprint", title="First source title")
    seed = PaperRecord(id="old/seed", title="Registered source title", doi="10.1000/shared")
    data, cache_path = inputs(tmp_path, [first, seed])
    cache = OpenAlexCache()
    cache.record(
        first.id,
        OpenAlexWork(
            id="https://openalex.org/W1",
            doi="10.1000/shared",
            cited_by_count=1,
            referenced_works=[],
        ),
        NOW,
    )
    cache_path.parent.mkdir(exist_ok=True)
    cache.save(cache_path)
    readme, legacy = tmp_path / "README.md", tmp_path / "docs/papers.json"
    legacy.parent.mkdir()
    readme.write_bytes(b"prior readme")
    legacy.write_bytes(b"prior legacy projection")
    manifest = legacy.parent / "data/manifest.json"
    manifest.parent.mkdir()
    manifest.write_bytes(b"prior manifest")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    monkeypatch.setattr(httpx, "Client", prohibit_network)
    with pytest.raises(IdentityConflict, match="Alias collision"):
        build_artifacts(data, TAXONOMY, readme, legacy)
    assert before == {
        p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }
