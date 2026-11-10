"""Strict, immutable snapshot storage; the manifest is the atomic commit point."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from src.file_lock import exclusive_file
from src.identity import IdentityIndex
from src.schema import PaperDatabase, PaperRecord


class ConcurrentWriteError(RuntimeError):
    """A writer's input changed before publication; its staged files remain inactive."""


def _encode(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".staging-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _inventory(db: PaperDatabase) -> None:
    ids = [paper.id for paper in db.papers]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate canonical paper IDs")
    for paper in db.papers:
        original = paper.model_dump()
        if PaperRecord.model_validate(original).model_dump() != original:
            raise ValueError(f"Record requires normalization before publication: {paper.id}")
    IdentityIndex(db.papers, db.aliases)
    from src.curation import validate_archive

    validate_archive(db)
    if db.total_count != len(ids):
        raise ValueError("Database count mismatch")


SIGNAL_FIELDS = (
    "citation_count",
    "influential_citation_count",
    "openalex_id",
    "referenced_works",
    "db_citation_count",
    "db_citations",
    "db_references",
)


def _read_component(manifest: Path, component: dict):
    relative = Path(component["path"])
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != component["path"]:
        raise ValueError("Unsafe component path")
    target = (manifest.parent / relative).resolve()
    if not target.is_relative_to(manifest.parent.resolve()):
        raise ValueError("Component escapes store")
    payload = target.read_bytes()
    if _digest(payload) != component["sha256"]:
        raise ValueError("Component checksum mismatch")
    return json.loads(payload)


def _publish_component(root: Path, prefix: str, value: object) -> dict:
    payload = _encode(value)
    digest = _digest(payload)
    relative = f"{prefix}.{digest}.json"
    path = root / relative
    if not path.exists() or path.read_bytes() != payload:
        _atomic_write(path, payload)
    return {"path": relative, "sha256": digest}


def load_store(manifest_path: str | Path) -> PaperDatabase:
    """Fail closed on missing, corrupted, or inconsistent snapshot components."""
    path = Path(manifest_path)
    manifest_bytes = path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest["schema_version"] != "2.0.0":
        raise ValueError("Unsupported storage schema")
    records = []
    seen_months = set()
    for shard in manifest["shards"]:
        papers = _read_component(path, shard)
        if len(papers) != shard["count"]:
            raise ValueError("Shard count mismatch")
        month = shard["month"]
        if month in seen_months:
            raise ValueError("Duplicate shard month")
        seen_months.add(month)
        if any(paper["published_date"][:7] != month for paper in papers):
            raise ValueError("Paper in incorrect month shard")
        records.extend(papers)
    from src.observations import SignalStore

    aliases = _read_component(path, manifest["aliases"])
    signals = _read_component(path, manifest["signals"]["openalex"])
    signal_store = SignalStore.model_validate(signals["store"])
    if signal_store.provider != "openalex":
        raise ValueError("Incorrect snapshot signal provider")
    if set(signals["compatibility"]) != {paper["id"] for paper in records}:
        raise ValueError("Signal compatibility inventory mismatch")
    if set(signal_store.observations) != set(signals["compatibility"]):
        raise ValueError("Observation inventory mismatch")
    for paper in records:
        compatibility = signals["compatibility"][paper["id"]]
        if set(compatibility) != set(SIGNAL_FIELDS):
            raise ValueError("Incomplete signal compatibility fields")
        if any(field in paper for field in SIGNAL_FIELDS):
            raise ValueError("Dynamic signals present in canonical shard")
        paper.update(compatibility)
    by_id = {paper["id"]: paper for paper in records}
    order = manifest["record_order"]
    if len(by_id) != len(records) or len(order) != len(set(order)) or set(order) != set(by_id):
        raise ValueError("Invalid record inventory")
    db = PaperDatabase.model_validate(
        {
            "schema_version": manifest["record_schema_version"],
            "last_updated": manifest["last_updated"],
            "total_count": manifest["total_count"],
            "papers": [by_id[paper_id] for paper_id in order],
            "aliases": aliases["record_aliases"],
            "archive": _read_component(path, manifest["archive"])["entries"],
        }
    )
    _inventory(db)
    if IdentityIndex(db.papers, db.aliases).aliases != aliases["aliases"]:
        raise ValueError("Alias index mismatch")
    db._signal_stores["openalex"] = signal_store
    if _digest(_encode(db.model_dump(mode="json"))) != manifest["content_sha256"]:
        raise ValueError("Snapshot content mismatch")
    db._loaded_path = path.resolve()
    db._loaded_sha256 = _digest(manifest_bytes)
    return db


def write_store(
    db: PaperDatabase, manifest_path: str | Path, *, expected_sha256: str | None = None
) -> dict:
    """Publish immutable shards before switching the manifest; retain prior generations.

    This compatibility stage preserves all legacy fields, including signals with
    unknown observation times. It does not activate v2 for existing writers.
    """
    from src.observations import Observation, SignalStore

    _inventory(db)
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    initial = _digest(path.read_bytes()) if path.exists() else None
    if expected_sha256 is None and db._loaded_path == path.resolve():
        expected_sha256 = db._loaded_sha256
    if expected_sha256 is not None and expected_sha256 != initial:
        raise ConcurrentWriteError("Database changed since load; reload and retry")
    groups: dict[str, list[dict]] = {}
    compatibility = {}
    signal_store = db._signal_stores.get("openalex", SignalStore(provider="openalex")).model_copy(
        deep=True
    )
    active_ids = {paper.id for paper in db.papers}
    if set(signal_store.observations) - active_ids:
        raise ValueError("Orphaned observations require explicit archival")
    for paper in db.papers:
        raw = paper.model_dump(mode="json")
        compatibility[paper.id] = {field: raw.pop(field) for field in SIGNAL_FIELDS}
        groups.setdefault(paper.published_date[:7], []).append(raw)
        if paper.id not in signal_store.observations:
            signal_store.observations[paper.id] = Observation(
                provider="openalex",
                provider_id=paper.openalex_id,
                values={
                    "citation_count": paper.citation_count if paper.citation_count else None,
                    "referenced_works": paper.referenced_works,
                },
            )
    alias_component = _publish_component(
        path.parent,
        "aliases",
        {
            "schema_version": "1.0.0",
            "record_aliases": db.aliases,
            "aliases": IdentityIndex(db.papers, db.aliases).aliases,
        },
    )
    signal_component = _publish_component(
        path.parent,
        "signals/openalex",
        {
            "store": signal_store.model_dump(mode="json"),
            "compatibility": compatibility,
        },
    )
    shards = []
    for month, papers in sorted(groups.items()):
        payload = _encode(sorted(papers, key=lambda paper: paper["id"]))
        digest = _digest(payload)
        relative = f"papers/{month}.{digest}.json"
        target = path.parent / relative
        if not target.exists() or target.read_bytes() != payload:
            _atomic_write(target, payload)
        shards.append({"month": month, "path": relative, "sha256": digest, "count": len(papers)})
    from src.curation import ArchiveLedger

    archive_component = _publish_component(
        path.parent, "archive/papers", ArchiveLedger(entries=db.archive).model_dump(mode="json")
    )
    manifest = {
        "schema_version": "2.0.0",
        "record_schema_version": db.schema_version,
        "last_updated": db.last_updated,
        "total_count": db.total_count,
        "record_order": [paper.id for paper in db.papers],
        "aliases": alias_component,
        "archive": archive_component,
        "signals": {"openalex": signal_component},
        "content_sha256": _digest(_encode(db.model_dump(mode="json"))),
        "legacy_signal_freshness": "unknown",
        "shards": shards,
    }
    # Validate the full candidate before changing the active manifest.
    fd, candidate = tempfile.mkstemp(dir=path.parent, prefix=".candidate-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(_encode(manifest))
        projected = load_store(candidate)
        if projected.model_dump() != db.model_dump():
            raise ValueError("Migration parity failure")
        payload = _encode(manifest)
        with exclusive_file(str(path) + ".writer.lock"):
            actual = _digest(path.read_bytes()) if path.exists() else None
            if actual != initial:
                raise ConcurrentWriteError("Manifest changed during staging; reload and retry")
            if not path.exists() or path.read_bytes() != payload:
                _atomic_write(path, payload)
        db._loaded_path = path.resolve()
        db._loaded_sha256 = _digest(payload)
    finally:
        Path(candidate).unlink(missing_ok=True)
    return manifest
