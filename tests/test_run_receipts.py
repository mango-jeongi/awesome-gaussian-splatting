import json
import sys

import pytest
from pydantic import ValidationError

from src import releases
from src.run_receipts import RunReceipt, run_receipt


def test_run_receipt_rejects_tampered_or_sensitive_fields():
    saved = run_receipt(
        "test.job", inputs={"revision": "a" * 40}, outputs={"archive_sha256": "b" * 64}
    )
    assert RunReceipt.model_validate(saved).status == "succeeded"
    with pytest.raises(ValidationError, match="identity does not match"):
        RunReceipt.model_validate({**saved, "status": "failed"})
    with pytest.raises(ValidationError):
        RunReceipt.model_validate({**saved, "schema_version": 2})
    with pytest.raises(ValidationError):
        RunReceipt.model_validate({**saved, "schema_version": True})
    with pytest.raises(ValidationError):
        run_receipt(
            "test.job",
            inputs={"source": "https://fixture.example/?token=private"},
            outputs=saved["outputs"],
        )


def test_verify_failure_records_terminal_status_without_raw_invalid_request(tmp_path, monkeypatch):
    output = tmp_path / "verify.json"
    invalid_release_id = "untrusted-release-argument"
    base_url = "https://fixture.example/?token=sample-private-value"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "releases",
            "verify-url",
            "--base-url",
            base_url,
            "--expected-release-id",
            invalid_release_id,
            "--report",
            str(output),
        ],
    )
    with pytest.raises(SystemExit, match="1"):
        releases.main()
    raw = output.read_text()
    report = json.loads(raw)
    assert report["status"] == "verification_failed"
    assert report["release_id"] is None
    assert invalid_release_id not in raw and "sample-private-value" not in raw
    run = RunReceipt.model_validate(report.pop("run_receipt"))
    assert run.job == "release.verify-url" and run.status == "failed"
    assert run.outputs["verification_sha256"] == releases.sha(releases.compact(report))


def test_restore_receipt_stays_outside_verified_site(tmp_path, monkeypatch):
    # Release archive verification has its own fixtures. Here test CLI sidecar isolation.
    release_id = "a" * 64
    verified_files = {"index.html": b"<html>fixture</html>"}
    manifest = {
        "release_id": release_id,
        "source_revision": "b" * 40,
        "files": releases.inventory(verified_files),
    }
    monkeypatch.setattr(
        releases, "load_archive", lambda archive, expected: (verified_files, manifest)
    )
    output = tmp_path / "site"
    args = [
        "releases",
        "restore",
        "--archive",
        str(tmp_path / "release.tar"),
        "--expected-release-id",
        release_id,
        "--output",
        str(output),
        "--report",
    ]
    monkeypatch.setattr(sys, "argv", args + [str(output / "restore.json")])
    with pytest.raises(SystemExit, match="2"):
        releases.main()
    assert not output.exists()
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("existing file")
    monkeypatch.setattr(sys, "argv", args + [str(blocked_parent / "restore.json")])
    with pytest.raises(OSError):
        releases.main()
    assert not output.exists()
    report = tmp_path / "restore.json"
    monkeypatch.setattr(sys, "argv", args + [str(report)])
    releases.main()
    assert releases.read_site(output) == verified_files
    run = RunReceipt.model_validate(json.loads(report.read_bytes())["run_receipt"])
    assert run.job == "release.restore" and run.status == "succeeded"
    assert run.inputs == {"release_id": release_id}
    assert run.outputs == {
        "site_inventory_sha256": releases.sha(releases.compact(manifest["files"]))
    }
