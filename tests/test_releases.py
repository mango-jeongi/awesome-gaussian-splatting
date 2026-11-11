import json
import tarfile
from pathlib import Path

import pytest

from src.builder import build_artifacts
from src.releases import archive_bytes, load_archive, pack, safe_name, write_new
from src.schema import PaperDatabase, PaperRecord


def fixture(root):
    (root / "src").mkdir(parents=True)
    (root / "src/code.py").write_text("version = 1\n")
    (root / "data").mkdir()
    db = PaperDatabase(
        papers=[
            PaperRecord(id="paper", title="Gaussian splatting fixture", published_date="2024-01-01")
        ],
        total_count=1,
        last_updated="2024-01-01T00:00:00Z",
    )
    db.save(root / "data/papers.json")
    (root / "docs").mkdir()
    (root / "docs/index.html").write_text("<html>Version A</html>")
    (root / "config").mkdir()
    (root / "config/taxonomy.yaml").write_bytes(
        (Path(__file__).resolve().parents[1] / "config/taxonomy.yaml").read_bytes()
    )
    build_artifacts(
        root / "data/papers.json",
        root / "config/taxonomy.yaml",
        root / "README.md",
        root / "docs/papers.json",
    )
    return db


def create(root, output):
    return pack(root, root / "data/papers.json", root / "docs", output, "a" * 40)


def test_candidate_is_deterministic_and_rollback_uses_exact_archive(tmp_path):
    root = tmp_path / "repo"
    fixture(root)
    first, replay, later = [tmp_path / name for name in ("a", "replay", "b")]
    a = create(root, first)
    assert create(root, replay) == a
    assert (first / "release.tar").read_bytes() == (replay / "release.tar").read_bytes()
    (root / "docs/index.html").write_text("<html>Version B</html>")
    b = create(root, later)
    assert b["release_id"] != a["release_id"]
    files, metadata = load_archive(first / "release.tar", a["release_id"])
    restore = tmp_path / "rollback"
    write_new(files, restore)
    assert (restore / "index.html").read_text() == "<html>Version A</html>"
    assert metadata["source_revision"] == "a" * 40
    assert not any(name.endswith(".writer.lock") for name in files)
    assert metadata["public_build_digest"] == b["public_build_digest"]
    with pytest.raises(FileExistsError):
        write_new(files, restore)


def test_code_change_changes_release_id_even_with_identical_site(tmp_path):
    root = tmp_path / "repo"
    fixture(root)
    a = create(root, tmp_path / "a")
    (root / "src/code.py").write_text("version = 2\n")
    b = create(root, tmp_path / "b")
    assert a["release_id"] != b["release_id"]
    assert a["public_build_digest"] == b["public_build_digest"]


def test_missing_public_artifact_or_stale_source_refused(tmp_path):
    root = tmp_path / "repo"
    db = fixture(root)
    manifest = json.loads((root / "docs/data/manifest.json").read_bytes())
    shard = root / "docs/data" / manifest["index"]["path"]
    raw = shard.read_bytes()
    shard.unlink()
    with pytest.raises(ValueError, match="Missing or corrupt"):
        create(root, tmp_path / "a")
    shard.write_bytes(raw)
    db.papers[0].title = "Changed canonical source"
    db.save(root / "data/papers.json")
    with pytest.raises(ValueError, match="current build inputs|different canonical"):
        create(root, tmp_path / "b")


def test_archive_tampering_extra_files_and_wrong_expected_id_refused(tmp_path):
    root = tmp_path / "repo"
    fixture(root)
    a = create(root, tmp_path / "a")
    with pytest.raises(ValueError, match="expected candidate"):
        load_archive(tmp_path / "a/release.tar", "b" * 64)
    files, _ = load_archive(tmp_path / "a/release.tar", a["release_id"])
    files["index.html"] += b"tampered"
    bad = tmp_path / "bad.tar"
    bad.write_bytes(archive_bytes(files))
    with pytest.raises(ValueError, match="inventory"):
        load_archive(bad, a["release_id"])


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/drive", "a\\b", ".", "a/./b"])
def test_unsafe_paths_are_rejected(name):
    with pytest.raises(ValueError):
        safe_name(name)


def test_symlink_member_refused_before_restoration(tmp_path):
    archive = tmp_path / "link.tar"
    with tarfile.open(archive, "w") as stream:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        stream.addfile(info)
    with pytest.raises(ValueError, match="Unsafe"):
        load_archive(archive, "a" * 64)


def test_deployed_site_bytes_are_bound_to_expected_candidate(tmp_path):
    import httpx

    from src.releases import verify_url

    root = tmp_path / "repo"
    fixture(root)
    receipt = create(root, tmp_path / "a")
    site = tmp_path / "a/site"

    def respond(request):
        assert request.url.path.startswith("/project/")
        relative = request.url.path.removeprefix("/project/")
        return httpx.Response(200, content=(site / relative).read_bytes())

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        report = verify_url(
            "https://fixture.example/project/", receipt["release_id"], client=client
        )
    assert report["static_bytes_verified"] is True
    assert report["browser_routes_verified"] is False
    (site / "index.html").write_text("tampered")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ValueError, match="differs from candidate"):
            verify_url("https://fixture.example/project/", receipt["release_id"], client=client)


def test_changed_provider_cache_requires_rebuilding_site(tmp_path):
    from datetime import UTC, datetime

    from src.observations import Observation, SignalStore

    root = tmp_path / "repo"
    fixture(root)
    now = datetime.now(UTC)
    signals = root / "data/signals"
    signals.mkdir()
    store = SignalStore(
        provider="semanticscholar",
        observations={
            "paper": Observation(
                provider="semanticscholar",
                provider_id="fixture",
                status="ok",
                fetched_at=now,
                last_attempt_at=now,
                values={"citation_count": 7},
            )
        },
    )
    store.save(signals / "semanticscholar.json")
    with pytest.raises(ValueError, match="current build inputs"):
        create(root, tmp_path / "candidate")


def test_monthly_store_inputs_remain_bound_to_same_public_model(tmp_path):
    from src.storage import write_store

    root = tmp_path / "repo"
    db = fixture(root)
    manifest = root / "data-v2/manifest.json"
    write_store(db, manifest)
    receipt = pack(root, manifest, root / "docs", tmp_path / "candidate", "a" * 40)
    files, release = load_archive(tmp_path / "candidate/release.tar", receipt["release_id"])
    assert "data-v2/manifest.json" in release["inputs"]
    assert release["data_model_sha256"] == json.loads(files["data/manifest.json"])["source_sha256"]


def test_release_workflows_preserve_candidate_and_verification_order():
    import yaml

    workflows = Path(__file__).resolve().parents[1] / ".github/workflows"
    weekly = yaml.load(
        (workflows / "weekly-release.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    stage = weekly["jobs"]["release-and-build"]
    deploy = weekly["jobs"]["deploy-pages"]
    producer = next(s for s in stage["steps"] if s.get("id") == "candidate")
    assert "src.releases pack" in producer["run"]
    assert '"pages_artifact_name=' in producer["run"]
    upload = next(s for s in stage["steps"] if "upload-pages-artifact" in s.get("uses", ""))
    assert upload["with"]["path"].endswith("papers-release/site")
    verify_index = next(
        i for i, s in enumerate(deploy["steps"]) if "src.releases verify-url" in s.get("run", "")
    )
    publish_index = next(
        i for i, s in enumerate(deploy["steps"]) if "gh release edit" in s.get("run", "")
    )
    assert verify_index < publish_index
    assert (
        next(s for s in deploy["steps"] if "checkout@" in s.get("uses", ""))["with"]["ref"]
        == "${{ needs.release-and-build.outputs.source_revision }}"
    )
    retry = yaml.load(
        (workflows / "redeploy-pages.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    runs = "\n".join(s.get("run", "") for s in retry["jobs"]["redeploy"]["steps"])
    assert "src.releases restore" in runs and "src.releases verify-url" in runs
    assert "src.cli build" not in runs and "git merge" not in runs
    assert retry["concurrency"]["group"] == "repository-writer"


def test_ignored_site_files_cannot_enter_committed_candidate(tmp_path):
    import subprocess

    from src.releases import check_committed_inputs

    root = tmp_path / "repo"
    fixture(root)
    (root / ".gitignore").write_text(".env\n*.writer.lock\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    check_committed_inputs(root, root / "data/papers.json", root / "docs")
    (root / "docs/.env").write_text("fixture-only-ignored-file")
    with pytest.raises(ValueError, match="ignored files"):
        check_committed_inputs(root, root / "data/papers.json", root / "docs")


def test_network_fence_metadata_does_not_reduce_the_site_payload_budget(tmp_path, monkeypatch):
    import httpx

    import src.releases as releases

    root = tmp_path / "repo"
    fixture(root)
    receipt = create(root, tmp_path / "candidate")
    files, _ = load_archive(tmp_path / "candidate/release.tar", receipt["release_id"])
    payload_bytes = sum(map(len, files.values()))
    monkeypatch.setattr(releases, "MAX_BYTES", payload_bytes)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, content=files[req.url.path.removeprefix("/project/")])
        )
    ) as client:
        report = releases.verify_url(
            "https://fixture.example/project/", receipt["release_id"], client=client
        )
    assert report["decoded_bytes"] == payload_bytes + len(files["release.json"])
