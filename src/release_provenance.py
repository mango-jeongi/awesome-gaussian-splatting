"""Verify a retained Pages archive before unpacking any of its contents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from src.releases import MAX_BYTES, REVISION

WEEKLY_WORKFLOW = ".github/workflows/weekly-release.yml"
MAIN_REF = "refs/heads/main"
SHA256 = r"[a-f0-9]{64}"
# The last observed production main snapshot before the attestation rollout.
LEGACY_MAIN_SNAPSHOT = "271a0972c38a9075fe4966849ede21f6c192d9e6"
MAX_METADATA_BYTES = 2_000_000


def _read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError("Invalid or oversized release provenance metadata")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("Release provenance metadata must be an object")
    return value


def _git_revision(value) -> str:
    if not isinstance(value, str) or not re.fullmatch(REVISION, value):
        raise ValueError("Invalid release source revision")
    return value


def _source_revision(source_run: dict, repository: str) -> str:
    head_repo = source_run.get("head_repository")
    if (
        not isinstance(head_repo, dict)
        or head_repo.get("full_name") != repository
        or source_run.get("path") != WEEKLY_WORKFLOW
        or source_run.get("head_branch") != "main"
        or source_run.get("event") not in ("schedule", "workflow_dispatch")
        or source_run.get("status") != "completed"
    ):
        raise ValueError("Expected a completed weekly release attempt from this repository's main")
    return _git_revision(source_run.get("head_sha"))


def _assert_ancestor(ancestor: str, descendant: str, root: Path) -> None:
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=root,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        raise ValueError("Release revision is outside the trusted main history") from error


def _archive_digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES + 10_000_000:
        raise ValueError("Invalid or oversized retained release archive")
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def verify_retained_provenance(
    artifact_dir: Path,
    source_run: dict,
    repository: str,
    expected_release_id: str,
    *,
    root: Path,
    legacy_archive_sha256: str = "",
) -> str:
    """Return the verified source revision to compare with the restored manifest."""
    run_revision = _source_revision(source_run, repository)
    _assert_ancestor(run_revision, "HEAD", root)

    receipt = _read_json(artifact_dir / "receipt.json")
    if (
        not re.fullmatch(SHA256, expected_release_id)
        or receipt.get("release_id") != expected_release_id
    ):
        raise ValueError("Retained receipt differs from the expected release ID")
    release_revision = _git_revision(receipt.get("source_revision"))
    archive = artifact_dir / "release.tar"
    digest = _archive_digest(archive)
    if receipt.get("archive_sha256") != digest:
        raise ValueError("Retained archive bytes differ from the candidate receipt")

    if legacy_archive_sha256:
        if not re.fullmatch(SHA256, legacy_archive_sha256) or digest != legacy_archive_sha256:
            raise ValueError("Retained archive differs from the independently trusted SHA-256")
        # Old publishing jobs could commit generated files after workflow start.
        _assert_ancestor(LEGACY_MAIN_SNAPSHOT, "HEAD", root)
        _assert_ancestor(run_revision, release_revision, root)
        _assert_ancestor(release_revision, LEGACY_MAIN_SNAPSHOT, root)
    else:
        if release_revision != run_revision:
            raise ValueError("Release revision differs from the selected workflow attempt")
        subprocess.run(
            [
                "gh",
                "attestation",
                "verify",
                str(archive.resolve()),
                "--repo",
                repository,
                "--signer-workflow",
                f"{repository}/{WEEKLY_WORKFLOW}",
                "--source-ref",
                MAIN_REF,
                "--source-digest",
                run_revision,
                "--deny-self-hosted-runners",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            timeout=120,
        )
    return release_revision


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--legacy-archive-sha256", default="")
    args = parser.parse_args()
    try:
        revision = verify_retained_provenance(
            args.artifact_dir,
            _read_json(args.source_run),
            args.repository,
            args.release_id,
            root=Path(__file__).resolve().parents[1],
            legacy_archive_sha256=args.legacy_archive_sha256,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    print(revision)


if __name__ == "__main__":
    main()
