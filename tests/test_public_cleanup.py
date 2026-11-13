"""Retention cleanup protects manifests, refuses stale inputs, and resumes safely."""

from pathlib import Path

import pytest

import src.file_lock as locks
import src.public_cleanup as cleanup
from src.public import build_public
from src.public_cleanup import apply_cleanup, plan_cleanup
from src.schema import PaperDatabase, PaperRecord


def database(version):
    return PaperDatabase(
        papers=[
            PaperRecord(id="paper", title="Method version " + version, published_date="2024-01-01")
        ],
        total_count=1,
        last_updated="2026-11-11T00:00:00Z",
    )


def generations(tmp_path):
    root = tmp_path / "public"
    prior = tmp_path / "previous.json"
    for version in ["A", "B", "C"]:
        build_public(database(version), root)
        if version == "B":
            prior.write_bytes((root / "manifest.json").read_bytes())
    (root / "user-note.json").write_text('"keep this"')
    return root, prior


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*.json")}


def test_cleanup_preserves_current_previous_unknown_and_replays(tmp_path):
    root, prior = generations(tmp_path)
    before = snapshot(root)
    plan = plan_cleanup(root, [prior])
    assert len(plan["delete"]) > 1
    assert plan["unknown_files_preserved"] == ["user-note.json"]
    receipt = apply_cleanup(root, plan)
    assert len(receipt["deleted"]) == len(plan["delete"])
    assert receipt["deleted_bytes"] == sum(x["bytes"] for x in plan["delete"])
    for name in ["manifest.json", "user-note.json", *plan["protected"]]:
        assert (root / name).read_bytes() == before[name]
    assert plan_cleanup(root, [prior])["delete"] == []
    replay = apply_cleanup(root, plan)
    assert replay["status"] == "no_op"
    assert replay["already_absent_files"] == len(plan["delete"])


def test_changed_manifest_refuses_before_deletion(tmp_path):
    root, prior = generations(tmp_path)
    plan = plan_cleanup(root, [prior])
    build_public(database("D"), root)
    before = snapshot(root)
    with pytest.raises(ValueError, match="inputs changed"):
        apply_cleanup(root, plan)
    assert snapshot(root) == before


def test_corrupt_candidate_refuses_all_deletion(tmp_path):
    root, prior = generations(tmp_path)
    plan = plan_cleanup(root, [prior])
    (root / plan["delete"][1]["path"]).write_bytes(b"corrupted")
    before = snapshot(root)
    with pytest.raises(ValueError, match="Corrupt immutable"):
        apply_cleanup(root, plan)
    assert snapshot(root) == before


def test_missing_retained_artifact_and_limits_refuse_before_deletion(tmp_path):
    root, prior = generations(tmp_path)
    before = snapshot(root)
    with pytest.raises(ValueError, match="deletion budget"):
        plan_cleanup(root, [prior], max_delete_files=1)
    assert snapshot(root) == before
    with pytest.raises(ValueError, match="distinct"):
        plan_cleanup(root, [root / "manifest.json"])
    plan = plan_cleanup(root, [prior])
    missing = next(iter(plan["protected"]))
    (root / missing).unlink()
    after_missing = snapshot(root)
    with pytest.raises(FileNotFoundError):
        apply_cleanup(root, plan)
    assert snapshot(root) == after_missing


def test_interrupted_removal_keeps_generations_and_resumes_same_plan(tmp_path, monkeypatch):
    root, prior = generations(tmp_path)
    plan = plan_cleanup(root, [prior])
    protected = {name: (root / name).read_bytes() for name in plan["protected"]}
    original = Path.unlink
    calls = 0

    def interrupted(path, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected interruption")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", interrupted)
        with pytest.raises(OSError, match="injected interruption"):
            apply_cleanup(root, plan)
    assert protected == {name: (root / name).read_bytes() for name in protected}
    result = apply_cleanup(root, plan)
    assert result["already_absent_files"] == 1
    assert len(result["deleted"]) == len(plan["delete"]) - 1


def test_build_and_cleanup_share_actual_filesystem_lock(tmp_path, monkeypatch):
    root, prior = generations(tmp_path)
    plan = plan_cleanup(root, [prior])
    before = snapshot(root)
    actual = locks.exclusive_file

    def bounded(path, **kwargs):
        return actual(path, timeout=0.05, **kwargs)

    with actual(root / "public.run.lock"):
        monkeypatch.setattr(locks, "exclusive_file", bounded)
        monkeypatch.setattr(cleanup, "exclusive_file", bounded)
        with pytest.raises(TimeoutError):
            build_public(database("D"), root)
        with pytest.raises(TimeoutError):
            apply_cleanup(root, plan)
    assert snapshot(root) == before


def test_symlink_tree_is_refused_without_touching_target(tmp_path):
    root, prior = generations(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"outside")
    try:
        (root / "linked.json").symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation unavailable on this host")
    with pytest.raises(ValueError, match="links"):
        plan_cleanup(root, [prior])
    assert outside.read_bytes() == b"outside"


def test_forged_retained_path_and_tampered_plan_do_not_remove_files(tmp_path):
    import json

    from src.public import compact
    from src.releases import sha

    root, prior = generations(tmp_path)
    plan = plan_cleanup(root, [prior])
    before = snapshot(root)
    tampered = {**plan, "root": str(tmp_path / "elsewhere")}
    with pytest.raises(ValueError, match="root or identity"):
        apply_cleanup(root, tampered)
    bad = json.loads(prior.read_bytes())
    bad["index"]["path"] = "../outside.json"
    bad["build_digest"] = sha(compact({k: v for k, v in bad.items() if k != "build_digest"}))
    forged = tmp_path / "forged.json"
    forged.write_bytes(compact(bad))
    with pytest.raises(ValueError, match="Unsafe release path|unexpected artifact name"):
        plan_cleanup(root, [forged])
    assert snapshot(root) == before


def test_cli_outputs_cannot_overwrite_retention_inputs(tmp_path, monkeypatch):
    import sys

    from src.public_cleanup import main
    from src.storage import _encode

    root, prior = generations(tmp_path)
    before = snapshot(root)
    prior_bytes = prior.read_bytes()
    monkeypatch.setattr(
        sys,
        "argv",
        ["cleanup", "plan", "--root", str(root), "--retain", str(prior), "--output", str(prior)],
    )
    with pytest.raises(ValueError, match="overwrite"):
        main()
    assert prior.read_bytes() == prior_bytes
    plan = tmp_path / "plan.json"
    plan.write_bytes(_encode(plan_cleanup(root, [prior])))
    plan_bytes = plan.read_bytes()
    monkeypatch.setattr(
        sys,
        "argv",
        ["cleanup", "apply", "--root", str(root), "--plan", str(plan), "--receipt", str(plan)],
    )
    with pytest.raises(ValueError, match="overwrite"):
        main()
    assert plan.read_bytes() == plan_bytes
    assert snapshot(root) == before


@pytest.mark.parametrize("field", ["details", "buckets"])
def test_transitive_artifact_pointers_cannot_be_omitted_from_retention(tmp_path, field):
    import json

    from src.public import compact
    from src.releases import sha

    root, prior = generations(tmp_path)
    forged = json.loads(prior.read_bytes())
    if field == "details":
        forged["details"] = []
    else:
        forged["graph"]["buckets"] = []
    forged["build_digest"] = sha(compact({k: v for k, v in forged.items() if k != "build_digest"}))
    prior.write_bytes(compact(forged))
    before = snapshot(root)
    with pytest.raises(ValueError, match="undeclared"):
        plan_cleanup(root, [prior])
    assert snapshot(root) == before


def test_explicit_oversized_history_budget_preserves_release_limit_and_replay(
    tmp_path, monkeypatch
):
    from src.public import _artifact

    root, prior = generations(tmp_path)
    for version in range(3):
        _artifact(root, "signals", {"stale": str(version) * 10_000})
    initial = plan_cleanup(root, [prior])
    protected_bytes = sum(item["bytes"] for item in initial["protected"].values())
    obsolete_bytes = sum(item["bytes"] for item in initial["delete"])
    scanned_bytes = protected_bytes + obsolete_bytes
    monkeypatch.setattr(cleanup, "MAX_BYTES", protected_bytes + 100)
    before = snapshot(root)
    with pytest.raises(ValueError, match="scan budget"):
        plan_cleanup(root, [prior], max_delete_bytes=protected_bytes)
    assert snapshot(root) == before
    plan = plan_cleanup(
        root, [prior], max_scan_bytes=scanned_bytes, max_delete_bytes=obsolete_bytes
    )
    assert plan["max_scan_bytes"] == scanned_bytes
    assert obsolete_bytes > cleanup.MAX_BYTES
    receipt = apply_cleanup(root, plan)
    assert receipt["deleted_bytes"] == obsolete_bytes
    for name in ["manifest.json", "user-note.json", *plan["protected"]]:
        assert (root / name).read_bytes() == before[name]
    assert apply_cleanup(root, plan)["status"] == "no_op"
    assert cleanup.MAX_BYTES == protected_bytes + 100


@pytest.mark.parametrize("scan_limit", [True, 0, 500_000_001])
def test_invalid_extended_scan_bound_refuses_without_deletion(tmp_path, scan_limit):
    root, prior = generations(tmp_path)
    before = snapshot(root)
    with pytest.raises(ValueError, match="scan byte budget"):
        plan_cleanup(root, [prior], max_scan_bytes=scan_limit)
    assert snapshot(root) == before
