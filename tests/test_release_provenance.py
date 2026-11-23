import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from src import release_provenance as provenance

REPOSITORY = "mango-jeongi/awesome-gaussian-splatting"
RELEASE_ID = "d" * 64
RUN_SHA = "a" * 40


@pytest.fixture
def retained(tmp_path):
    archive = tmp_path / "release.tar"
    raw = b"immutable candidate bytes"
    archive.write_bytes(raw)
    receipt = {
        "release_id": RELEASE_ID,
        "source_revision": RUN_SHA,
        "archive_sha256": hashlib.sha256(raw).hexdigest(),
    }
    (tmp_path / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    run = {
        "path": ".github/workflows/weekly-release.yml",
        "head_branch": "main",
        "head_repository": {"full_name": REPOSITORY},
        "head_sha": RUN_SHA,
        "event": "schedule",
        "status": "completed",
        # Completed archives are recoverable even when deployment failed.
        "conclusion": "failure",
    }
    return archive, receipt, run


def test_attestation_is_bound_to_main_workflow_run_and_exact_archive(retained, monkeypatch):
    archive, _, run = retained
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: calls.append(command))
    assert (
        provenance.verify_retained_provenance(
            archive.parent, run, REPOSITORY, RELEASE_ID, root=archive.parent
        )
        == RUN_SHA
    )
    assert calls == [
        ["git", "merge-base", "--is-ancestor", RUN_SHA, "HEAD"],
        [
            "gh",
            "attestation",
            "verify",
            str(archive.resolve()),
            "--repo",
            REPOSITORY,
            "--signer-workflow",
            f"{REPOSITORY}/.github/workflows/weekly-release.yml",
            "--source-ref",
            "refs/heads/main",
            "--source-digest",
            RUN_SHA,
            "--deny-self-hosted-runners",
        ],
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("head_branch", "branch"),
        ("head_repository", {"full_name": "other/project"}),
        ("path", ".github/workflows/other.yml"),
        ("event", "pull_request"),
        ("status", "in_progress"),
    ],
)
def test_wrong_run_is_refused_before_git_or_attestation(retained, monkeypatch, field, value):
    archive, _, run = retained
    run[field] = value
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("unexpected process"))
    with pytest.raises(ValueError, match="completed weekly release attempt"):
        provenance.verify_retained_provenance(
            archive.parent, run, REPOSITORY, RELEASE_ID, root=archive.parent
        )


def test_tampered_archive_never_reaches_signature_verification(retained, monkeypatch):
    archive, _, run = retained
    archive.write_bytes(b"modified bytes")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: calls.append(command))
    with pytest.raises(ValueError, match="archive bytes differ"):
        provenance.verify_retained_provenance(
            archive.parent, run, REPOSITORY, RELEASE_ID, root=archive.parent
        )
    assert [call[0] for call in calls] == ["git"]


def test_failed_signature_does_not_fall_back_to_legacy(retained, monkeypatch):
    archive, _, run = retained
    calls = []

    def fail_attestation(command, **_kwargs):
        calls.append(command[0])
        if command[0] == "gh":
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(subprocess, "run", fail_attestation)
    with pytest.raises(subprocess.CalledProcessError):
        provenance.verify_retained_provenance(
            archive.parent, run, REPOSITORY, RELEASE_ID, root=archive.parent
        )
    assert calls == ["git", "gh"]


def test_legacy_digest_is_independent_and_revision_is_fenced(retained, monkeypatch):
    archive, receipt, run = retained
    candidate_sha = "b" * 40
    receipt["source_revision"] = candidate_sha
    (archive.parent / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: calls.append(command))
    assert (
        provenance.verify_retained_provenance(
            archive.parent,
            run,
            REPOSITORY,
            RELEASE_ID,
            root=archive.parent,
            legacy_archive_sha256=receipt["archive_sha256"],
        )
        == candidate_sha
    )
    expected_legacy_anchor = "271a0972c38a9075fe4966849ede21f6c192d9e6"
    assert [call[3:] for call in calls] == [
        [RUN_SHA, "HEAD"],
        [expected_legacy_anchor, "HEAD"],
        [RUN_SHA, candidate_sha],
        [candidate_sha, expected_legacy_anchor],
    ]
    with pytest.raises(ValueError, match="independently trusted SHA-256"):
        provenance.verify_retained_provenance(
            archive.parent,
            run,
            REPOSITORY,
            RELEASE_ID,
            root=archive.parent,
            legacy_archive_sha256="c" * 64,
        )

    def refuse_post_cutover_revision(command, **_kwargs):
        if command[3:] == [candidate_sha, expected_legacy_anchor]:
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(subprocess, "run", refuse_post_cutover_revision)
    with pytest.raises(ValueError, match="outside the trusted main history"):
        provenance.verify_retained_provenance(
            archive.parent,
            run,
            REPOSITORY,
            RELEASE_ID,
            root=archive.parent,
            legacy_archive_sha256=receipt["archive_sha256"],
        )


def test_workflows_gate_publication_and_rollback_on_provenance():
    workflows = Path(__file__).resolve().parents[1] / ".github/workflows"
    weekly = yaml.safe_load((workflows / "weekly-release.yml").read_text(encoding="utf-8"))
    build = weekly["jobs"]["release-and-build"]["steps"]
    signing = next(i for i, step in enumerate(build) if step.get("id") == "archive-attestation")
    verification = next(
        i for i, step in enumerate(build) if "gh attestation verify" in step.get("run", "")
    )
    publish = next(i for i, step in enumerate(build) if "gh release create" in step.get("run", ""))
    upload = next(
        i for i, step in enumerate(build) if "upload-pages-artifact" in step.get("uses", "")
    )
    assert signing < verification < publish < upload
    assert build[signing]["with"]["subject-path"].endswith("/papers-release/release.tar")
    assert "src.releases restore" in build[verification]["run"]
    assert build[upload]["with"]["path"].endswith("/attested-site")

    redeploy = yaml.safe_load((workflows / "redeploy-pages.yml").read_text(encoding="utf-8"))
    restore = next(
        step["run"]
        for step in redeploy["jobs"]["redeploy"]["steps"]
        if step.get("id") == "restored"
    )
    assert restore.index("src.release_provenance") < restore.index("src.releases restore")
