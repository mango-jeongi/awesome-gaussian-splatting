"""Rehearse full-corpus storage parity and failures in an isolated directory."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import src.storage as storage
from src.builder import build_artifacts
from src.public_signals import public_signals
from src.public_trending import public_trending
from src.ranking import RankingConfig
from src.schema import PaperDatabase, PaperRecord
from src.storage import _encode


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    stage = args.workdir.resolve()
    source = root / "data/papers.json"
    report_path = (args.report or stage / "rehearsal.json").resolve()
    for candidate in (stage, report_path):
        if candidate == root or any(
            p == candidate or p in candidate.parents for p in (root / "data", root / "docs")
        ):
            parser.error("Use isolated work/report paths outside canonical data and deployed docs")
    data = stage / "data"
    data.mkdir(parents=True, exist_ok=True)
    manifest = data / "manifest.json"

    def digest(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    source_hash = digest(source)
    sidecars = {}
    for path in (root / "data/signals").glob("*.json"):
        target = data / "signals" / path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(path, target)
        sidecars[str(path.relative_to(root))] = digest(path)
    reviewed = root / "data/extraction/reviewed.json"
    (data / "extraction").mkdir(exist_ok=True)
    shutil.copyfile(reviewed, data / "extraction/reviewed.json")
    sidecars[str(reviewed.relative_to(root))] = digest(reviewed)
    legacy = PaperDatabase.load(source)
    snapshot = storage.write_store(legacy, manifest)
    loaded = storage.load_store(manifest)
    assert loaded.model_dump() == legacy.model_dump()
    config = RankingConfig.load(root / "config/ranking.yaml")
    assert public_signals(legacy, root / "data/signals") == public_signals(loaded, data / "signals")
    assert public_trending(legacy, root / "data/signals", config) == public_trending(
        loaded, data / "signals", config
    )

    def inventory():
        return {
            str(p.relative_to(stage)): (digest(p), p.stat().st_mtime_ns)
            for p in data.rglob("*.json")
        }

    before = inventory()
    loaded.save(manifest)
    assert inventory() == before
    for name, path in [("v1", source), ("v2", manifest)]:
        dest = stage / name
        dest.mkdir(exist_ok=True)
        build_artifacts(
            path, root / "config/taxonomy.yaml", dest / "README.md", dest / "papers.json"
        )

    def artifacts(name):
        return {
            str(p.relative_to(stage / name)): digest(p)
            for p in (stage / name).rglob("*")
            if p.is_file() and not p.name.endswith(".lock")
        }

    assert artifacts("v1") == artifacts("v2")
    public_before = artifacts("v2")
    build_artifacts(
        manifest, root / "config/taxonomy.yaml", stage / "v2/README.md", stage / "v2/papers.json"
    )
    assert artifacts("v2") == public_before
    baseline_bytes = manifest.read_bytes()
    first = storage.load_store(manifest)
    stale = storage.load_store(manifest)
    first.upsert(
        [
            PaperRecord(
                id="rehearsal:first",
                title="Gaussian splatting isolated writer fixture",
                published_date="2026-11-10",
            )
        ]
    )
    first.save(manifest)
    advanced = manifest.read_bytes()
    stale.upsert(
        [
            PaperRecord(
                id="rehearsal:stale",
                title="Gaussian splatting stale writer fixture",
                published_date="2026-11-10",
            )
        ]
    )
    try:
        stale.save(manifest)
    except storage.ConcurrentWriteError:
        pass
    else:
        raise AssertionError("Stale writer accepted")
    assert (
        manifest.read_bytes() == advanced
        and storage.load_store(manifest).get("rehearsal:first") is not None
    )
    storage._atomic_write(manifest, baseline_bytes)
    assert storage.load_store(manifest).model_dump() == legacy.model_dump()
    shard = data / snapshot["shards"][0]["path"]
    assert shard.resolve().is_relative_to(stage.resolve())
    raw = shard.read_bytes()
    try:
        storage._atomic_write(shard, b"{}")
        try:
            storage.load_store(manifest)
        except ValueError:
            pass
        else:
            raise AssertionError("Corrupt shard accepted")
        shard.unlink()
        try:
            storage.load_store(manifest)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("Missing shard accepted")
    finally:
        storage._atomic_write(shard, raw)
    interrupted = storage.load_store(manifest)
    interrupted.upsert(
        [
            PaperRecord(
                id="rehearsal:interrupted",
                title="Gaussian splatting interrupted stage fixture",
                published_date="2026-11-10",
            )
        ]
    )
    real_publish = storage._publish_component
    injected = []

    def fail_after_component(component_root, prefix, value):
        result = real_publish(component_root, prefix, value)
        if not injected:
            injected.append("data/" + result["path"])
            raise OSError("Intentional staged-write interruption")
        return result

    storage._publish_component = fail_after_component
    try:
        try:
            interrupted.save(manifest)
        except OSError:
            pass
        else:
            raise AssertionError("Failure injection not exercised")
    finally:
        storage._publish_component = real_publish
    assert (
        injected
        and manifest.read_bytes() == baseline_bytes
        and storage.load_store(manifest).model_dump() == legacy.model_dump()
    )
    assert digest(source) == source_hash
    for name, sha in sidecars.items():
        assert digest(root / name) == sha
    base = json.loads((root / "data/baselines/seed-a235a1e.json").read_bytes())
    old_edges = {(p["id"], t) for p in base["papers"] for t in p.get("db_references", [])}
    edges = {(p.id, t) for p in legacy.papers for t in p.db_references}
    removed = []
    for a, b in sorted(old_edges - edges):
        assert a in legacy.archive and b in legacy.archive
        removed.append(
            {
                "source": a,
                "target": b,
                "disposition": "Both endpoints are explicitly archived; edge retained in baseline/archival evidence",
            }
        )
    report = {
        "source_raw_sha256": source_hash,
        "source_records": legacy.total_count,
        "v2_monthly_shards": len(snapshot["shards"]),
        "v2_content_sha256": snapshot["content_sha256"],
        "all_record_fields_order_aliases_archive_equal": True,
        "typed_provider_sidecars_preserved": sidecars,
        "public_provider_and_trending_payloads_equal": True,
        "public_build_file_count": len(public_before),
        "v1_v2_generated_bytes_equal": True,
        "noop_store_bytes_and_mtimes_equal": True,
        "noop_build_bytes_equal": True,
        "stale_writer_refused": True,
        "accepted_concurrent_update_preserved": True,
        "rollback_restored_exact_model": True,
        "missing_and_corrupt_shards_refused": True,
        "interrupted_stage_preserved_manifest": True,
        "injected_unreferenced_component": injected[0],
        "baseline_edges": len(old_edges),
        "active_edges_preserved": len(old_edges & edges),
        "removed_edges_accounted": removed,
        "new_edges": len(edges - old_edges),
        "canonical_modified": False,
        "writer_defaults_switched": False,
        "remote_writers_verified": False,
        "scope": "Isolated full-corpus rehearsal; canonical activation and remote rollout remain pending.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(_encode(report))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
