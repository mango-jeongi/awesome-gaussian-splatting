from pathlib import Path

import pytest

from src.schema import PaperDatabase
from src.storage import load_store, write_store


def sample():
    return PaperDatabase.model_validate(
        {
            "total_count": 2,
            "papers": [
                {
                    "id": "legacy/id",
                    "title": "First paper",
                    "published_date": "2024-01-02",
                    "citation_count": 0,
                },
                {
                    "id": "doi:10.1/test",
                    "title": "Second paper",
                    "published_date": "2024-02-03",
                    "db_references": ["legacy/id"],
                },
            ],
        }
    )


def test_roundtrip_and_noop(tmp_path):
    db = sample()
    path = tmp_path / "manifest.json"
    manifest = write_store(db, path)
    assert load_store(path).model_dump() == db.model_dump()
    assert manifest["legacy_signal_freshness"] == "unknown"
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.rglob("*.json")}
    write_store(db, path)
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.rglob("*.json")}


def test_missing_and_corrupt_shard(tmp_path):
    path = tmp_path / "manifest.json"
    manifest = write_store(sample(), path)
    shard = tmp_path / manifest["shards"][0]["path"]
    original = shard.read_bytes()
    shard.write_bytes(b"[]")
    with pytest.raises(ValueError, match="checksum"):
        load_store(path)
    shard.write_bytes(original)
    shard.unlink()
    with pytest.raises(FileNotFoundError):
        load_store(path)


def test_duplicate_ids_rejected(tmp_path):
    db = sample()
    db.papers[1].id = db.papers[0].id
    with pytest.raises(ValueError, match="Duplicate"):
        write_store(db, tmp_path / "manifest.json")


def test_interrupted_commit_keeps_previous_snapshot(tmp_path, monkeypatch):
    import src.storage as storage

    path = tmp_path / "manifest.json"
    previous = sample()
    write_store(previous, path)
    changed = sample()
    changed.papers[0].published_date = "2025-03-02"
    changed.papers[0].year = 2025
    changed.papers[0].month = 3
    real_write = storage._atomic_write

    def interrupt(target, payload):
        if target == path:
            raise OSError("simulated interruption")
        real_write(target, payload)

    monkeypatch.setattr(storage, "_atomic_write", interrupt)
    with pytest.raises(OSError):
        write_store(changed, path)
    assert load_store(path).model_dump() == previous.model_dump()


def test_real_corpus_parity(tmp_path):
    source = Path(__file__).resolve().parents[1] / "data" / "papers.json"
    db = PaperDatabase.load(source)
    path = tmp_path / "manifest.json"
    write_store(db, path)
    assert load_store(path).model_dump() == db.model_dump()


def test_cli_migration_preview_and_validation(tmp_path, capsys):
    from src.cli import main

    source = Path(__file__).resolve().parents[1] / "data" / "papers.json"
    manifest = tmp_path / "manifest.json"
    assert main(["--data", str(source), "migrate", "--dry-run", "--manifest", str(manifest)]) == 0
    assert not manifest.exists()
    assert '"parity": "exact"' in capsys.readouterr().out
    assert main(["--data", str(source), "migrate", "--manifest", str(manifest)]) == 0
    assert main(["validate", "--manifest", str(manifest)]) == 0


def test_validate_missing_database_fails(tmp_path):
    from src.cli import main

    with pytest.raises(FileNotFoundError):
        main(["--data", str(tmp_path / "missing.json"), "validate"])


def test_signals_are_separate_and_signal_change_keeps_shards(tmp_path):
    import json
    from datetime import UTC, datetime

    db = sample()
    path = tmp_path / "manifest.json"
    first = write_store(db, path)
    shard_bytes = {
        shard["path"]: (tmp_path / shard["path"]).read_bytes() for shard in first["shards"]
    }
    for payload in shard_bytes.values():
        assert "citation_count" not in json.loads(payload)[0]
    loaded = load_store(path)
    observation = loaded._signal_stores["openalex"].observations[db.papers[0].id]
    assert observation.status == "unknown"
    assert observation.fetched_at is None
    assert observation.values["citation_count"] is None
    loaded._signal_stores["openalex"].apply(
        db.papers[0].id,
        status="ok",
        now=datetime(2026, 11, 8, tzinfo=UTC),
        provider_id="W1",
        values={"citation_count": 0, "referenced_works": []},
    )
    loaded.papers[0].citation_count = 0
    loaded.papers[0].openalex_id = "W1"
    second = write_store(loaded, path)
    assert first["shards"] == second["shards"]
    assert first["signals"] != second["signals"]
    assert load_store(path)._signal_stores["openalex"].observations[db.papers[0].id].status == "ok"
    assert shard_bytes == {
        shard["path"]: (tmp_path / shard["path"]).read_bytes() for shard in second["shards"]
    }


def test_database_adapter_and_builder_use_manifest(tmp_path):
    from src.builder import build_artifacts

    db = sample()
    path = tmp_path / "data" / "manifest.json"
    db.save(path)
    assert PaperDatabase.load(path).model_dump() == db.model_dump()
    docs = tmp_path / "docs" / "papers.json"
    build_artifacts(
        path,
        Path(__file__).resolve().parents[1] / "config" / "taxonomy.yaml",
        tmp_path / "README.md",
        docs,
    )
    assert PaperDatabase.load(docs).model_dump() == db.model_dump()
    with pytest.raises(FileNotFoundError):
        PaperDatabase.load(tmp_path / "missing.json")


@pytest.mark.parametrize("filename", ["papers.json", "v2/manifest.json"])
def test_stale_writer_cannot_overwrite_newer_database(tmp_path, filename):
    from src.schema import PaperRecord
    from src.storage import ConcurrentWriteError

    path = tmp_path / filename
    original = sample()
    original.save(path)
    first = PaperDatabase.load(path)
    stale = PaperDatabase.load(path)
    first.upsert([PaperRecord(id="first-new", title="First independently added paper")])
    first.save(path)
    current = path.read_bytes()
    stale.upsert([PaperRecord(id="stale-new", title="Stale independently added paper")])
    with pytest.raises(ConcurrentWriteError, match="changed since load"):
        stale.save(path)
    assert path.read_bytes() == current
    assert PaperDatabase.load(path).get("first-new") is not None
    assert PaperDatabase.load(path).get("stale-new") is None


def test_migration_rerun_preserves_observations_and_refuses_newer_target(tmp_path):
    from datetime import UTC, datetime

    from src.cli import main
    from src.schema import PaperRecord

    source = tmp_path / "legacy.json"
    target = tmp_path / "manifest.json"
    sample().save(source)
    args = ["--data", str(source), "migrate", "--manifest", str(target)]
    assert main(args) == 0
    active = PaperDatabase.load(target)
    active._signal_stores["openalex"].apply(
        active.papers[0].id,
        status="ok",
        provider_id="W1",
        values={"citation_count": 0},
        now=datetime(2026, 11, 8, tzinfo=UTC),
    )
    active.save(target)
    before = target.read_bytes()
    assert main(args) == 0
    assert target.read_bytes() == before
    assert (
        PaperDatabase.load(target)
        ._signal_stores["openalex"]
        .observations[active.papers[0].id]
        .status
        == "ok"
    )
    active.upsert([PaperRecord(id="newer", title="A newer canonical addition")])
    active.save(target)
    before = target.read_bytes()
    with pytest.raises(ValueError, match="differs from source"):
        main(args)
    assert target.read_bytes() == before
    with pytest.raises(ValueError, match="separate manifest"):
        main(["--data", str(source), "migrate", "--manifest", str(source)])


def test_invalid_mutation_cannot_publish(tmp_path):
    path = tmp_path / "papers.json"
    db = sample()
    db.save(path)
    before = path.read_bytes()
    db.papers[0].published_date = "2024-02-30"
    with pytest.raises(ValueError):
        db.save(path)
    assert path.read_bytes() == before


def test_manifest_advance_during_staging_is_not_lost(tmp_path, monkeypatch):
    import src.storage as storage

    path = tmp_path / "manifest.json"
    write_store(sample(), path)
    candidate = sample()
    candidate.papers[0].title = "Stale staged title"
    newer = sample()
    newer.papers[0].title = "Concurrent accepted title"
    real_write = storage._atomic_write
    advanced = False

    def publish_then_advance(target, payload):
        nonlocal advanced
        real_write(target, payload)
        if not advanced and target != path:
            advanced = True
            write_store(newer, path)

    monkeypatch.setattr(storage, "_atomic_write", publish_then_advance)
    with pytest.raises(storage.ConcurrentWriteError, match="during staging"):
        write_store(candidate, path)
    assert load_store(path).papers[0].title == "Concurrent accepted title"
