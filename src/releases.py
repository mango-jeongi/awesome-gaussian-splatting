"""Immutable Pages candidates: exact site bytes, input fingerprints and safe restoration."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit

import httpx

from src.public import compact
from src.schema import PaperDatabase

MAX_BYTES = 200_000_000
MAX_FILES = 5000
REVISION = r"(?:[a-f0-9]{40}|[a-f0-9]{64})"
WEEK_TAG = r"v[0-9]{4}\.W(?:0[1-9]|[1-4][0-9]|5[0-3])"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if (
        not name
        or not path.parts
        or path.is_absolute()
        or str(path) != name
        or ".." in path.parts
        or "\\" in name
        or ":" in name
        or any(ord(c) < 32 for c in name)
    ):
        raise ValueError("Unsafe release path")
    return name


def descriptors(value):
    if isinstance(value, dict):
        if {"path", "sha256"} <= value.keys():
            yield value
        for item in value.values():
            yield from descriptors(item)
    elif isinstance(value, list):
        for item in value:
            yield from descriptors(item)


def check_public(files):
    manifest = json.loads(files["data/manifest.json"])
    base = {k: v for k, v in manifest.items() if k != "build_digest"}
    if sha(compact(base)) != manifest["build_digest"]:
        raise ValueError("Invalid public build digest")
    for item in descriptors(manifest):
        name = "data/" + safe_name(item["path"])
        if name not in files or sha(files[name]) != item["sha256"]:
            raise ValueError("Missing or corrupt public artifact")
        if "bytes" in item and len(files[name]) != item["bytes"]:
            raise ValueError("Public artifact size mismatch")
    if "index.html" not in files:
        raise ValueError("Release requires the portal entry point")
    return manifest


def inventory(files):
    return {
        safe_name(name): {"sha256": sha(raw), "bytes": len(raw)}
        for name, raw in sorted(files.items())
    }


def site_paths(site):
    for path in sorted(site.rglob("*")):
        if path.name.endswith((".writer.lock", ".run.lock")) or path.name.startswith(
            (".staging-", ".candidate-")
        ):
            continue
        yield path


def read_site(site):
    result = {}
    for path in site_paths(site):
        if path.is_symlink():
            raise ValueError("Release sites cannot contain symlinks")
        if path.is_file():
            name = path.relative_to(site).as_posix()
            if name == "release.json":
                raise ValueError("Site already contains release metadata")
            if (
                len(result) >= MAX_FILES - 1
                or path.stat().st_size + sum(map(len, result.values())) > MAX_BYTES
            ):
                raise ValueError("Release size budget exceeded")
            result[safe_name(name)] = path.read_bytes()
    if len(result) > MAX_FILES or sum(map(len, result.values())) > MAX_BYTES:
        raise ValueError("Release size budget exceeded")
    return result


def input_identity(root, data):
    db = PaperDatabase.load(data)
    paths = {data.resolve()}
    metadata = json.loads(data.read_bytes())
    if metadata["schema_version"] == "2.0.0":
        for item in descriptors(metadata):
            path = (data.parent / safe_name(item["path"])).resolve()
            if data.parent.resolve() not in path.parents:
                raise ValueError("Source component escapes store")
            paths.add(path)
    paths.update((data.parent / "signals").rglob("*.json"))
    reviewed = data.parent / "extraction/reviewed.json"
    if reviewed.exists():
        paths.add(reviewed)
    for pattern in ("src/**/*.py", "config/*.yaml", "config/*.css", ".github/workflows/*.yml"):
        paths.update(root.glob(pattern))
    for name in (
        "pyproject.toml",
        "uv.lock",
        "package.json",
        "package-lock.json",
        "tailwind.config.cjs",
    ):
        if (root / name).exists():
            paths.add(root / name)
    inputs = {}
    for path in sorted(paths):
        if path.is_symlink():
            raise ValueError("Release inputs cannot be symlinks")
        path = path.resolve()
        if path.is_symlink() or root.resolve() not in path.parents:
            raise ValueError("Release input must remain inside the repository")
        inputs[path.relative_to(root.resolve()).as_posix()] = sha(path.read_bytes())
    return {
        "inputs": inputs,
        "input_digest": sha(compact(inputs)),
        "data_model_sha256": sha(compact(db.model_dump(mode="json"))),
    }


def verify_files(files, expected_id=None):
    if len(files) > MAX_FILES or sum(map(len, files.values())) > MAX_BYTES:
        raise ValueError("Release payload budget exceeded")
    release = json.loads(files["release.json"])
    if not re.fullmatch(REVISION, release.get("source_revision", "")):
        raise ValueError("Invalid release source revision")
    if release.get("release_tag") is not None and not re.fullmatch(
        WEEK_TAG, release["release_tag"]
    ):
        raise ValueError("Invalid release tag")
    body = {k: v for k, v in release.items() if k != "release_id"}
    if release.get("schema_version") != 1 or sha(compact(body)) != release["release_id"]:
        raise ValueError("Invalid release identity")
    if expected_id is not None and expected_id != release["release_id"]:
        raise ValueError("Release differs from expected candidate")
    actual = inventory({k: v for k, v in files.items() if k != "release.json"})
    if release["files"] != actual:
        raise ValueError("Release file inventory differs")
    if sha(compact(release["inputs"])) != release["input_digest"]:
        raise ValueError("Release input digest differs")
    manifest = check_public(files)
    if (
        manifest["build_digest"] != release["public_build_digest"]
        or manifest["source_sha256"] != release["data_model_sha256"]
    ):
        raise ValueError("Release public/source binding differs")
    return release


def archive_bytes(files):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, raw in sorted(files.items()):
            info = tarfile.TarInfo(safe_name(name))
            info.size, info.mode, info.mtime = len(raw), 0o644, 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(raw))
    return buffer.getvalue()


def load_archive(path, expected_id):
    if path.stat().st_size > MAX_BYTES + 10_000_000:
        raise ValueError("Oversized release archive")
    files, size = {}, 0
    with tarfile.open(path, "r:") as archive:
        for member in archive:
            name = safe_name(member.name)
            if not member.isfile() or name in files or member.size < 0:
                raise ValueError("Unsafe or duplicate archive member")
            size += member.size
            if size > MAX_BYTES or len(files) >= MAX_FILES:
                raise ValueError("Release archive budget exceeded")
            files[name] = archive.extractfile(member).read()
    return files, verify_files(files, expected_id)


def write_new(files, destination):
    destination.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        target = destination / safe_name(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)


def check_projection(root, data, files):
    from src.builder import build_artifacts

    with tempfile.TemporaryDirectory(prefix="papers-release-verify-") as folder:
        stage = Path(folder)
        build_artifacts(
            data, root / "config/taxonomy.yaml", stage / "README.md", stage / "site/papers.json"
        )
        expected = read_site(stage / "site")
        for name, raw in expected.items():
            if files.get(name) != raw:
                raise ValueError("Site projection differs from current build inputs")


def pack(root, data, site, output, revision, release_tag=None):
    root, data, site, output = [Path(p).resolve() for p in (root, data, site, output)]
    if output == site or site in output.parents or output.exists():
        raise ValueError("Use a new output directory outside the site")
    if not re.fullmatch(REVISION, revision):
        raise ValueError("Release requires a full source commit")
    if release_tag is not None and not re.fullmatch(WEEK_TAG, release_tag):
        raise ValueError("Invalid release tag")
    before = input_identity(root, data)
    files = read_site(site)
    manifest = check_public(files)
    check_projection(root, data, files)
    if manifest["source_sha256"] != before["data_model_sha256"]:
        raise ValueError("Portal was built from a different canonical model")
    release = {
        "schema_version": 1,
        "source_revision": revision,
        "release_tag": release_tag,
        **before,
        "public_build_digest": manifest["build_digest"],
        "files": inventory(files),
    }
    release["release_id"] = sha(compact(release))
    files["release.json"] = compact(release)
    if sum(map(len, files.values())) > MAX_BYTES:
        raise ValueError("Release metadata exceeds size budget")
    verify_files(files, release["release_id"])
    archive = archive_bytes(files)
    if input_identity(root, data) != before:
        raise ValueError("Release inputs changed during packaging")
    output.mkdir(parents=True, exist_ok=False)
    write_new(files, output / "site")
    (output / "release.tar").write_bytes(archive)
    receipt = {
        "release_id": release["release_id"],
        "source_revision": revision,
        "archive_sha256": sha(archive),
        "archive_bytes": len(archive),
        "site_files": len(files),
        "input_digest": release["input_digest"],
        "public_build_digest": manifest["build_digest"],
    }
    (output / "receipt.json").write_bytes(compact(receipt))
    return receipt


def verify_url(base_url, expected_id, *, client=None, max_seconds=300, clock=time.monotonic):
    url = urlsplit(base_url)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError("Use an HTTPS deployment base without credentials, query or fragment")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_id) or not 0 < max_seconds <= 900:
        raise ValueError("Invalid deployment verification identity/budget")
    started, received, requests = clock(), 0, 0
    owned = client is None
    client = client or httpx.Client(timeout=20, follow_redirects=False)

    def fetch(name, limit):
        nonlocal received, requests
        if clock() - started >= max_seconds or requests >= MAX_FILES + 1:
            raise ValueError("Deployment verification budget exceeded")
        requests += 1
        with client.stream(
            "GET",
            base_url.rstrip("/") + "/" + quote(safe_name(name), safe="/"),
            headers={"Cache-Control": "no-cache"},
            follow_redirects=False,
        ) as response:
            if response.status_code != 200:
                raise ValueError("Deployment file unavailable")
            raw = bytearray()
            for chunk in response.iter_bytes():
                raw.extend(chunk)
                received += len(chunk)
                if (
                    len(raw) > limit
                    or received > MAX_BYTES + 2_000_000
                    or clock() - started >= max_seconds
                ):
                    raise ValueError("Deployment verification response budget exceeded")
        return bytes(raw)

    try:
        raw = fetch("release.json", 2_000_000)
        metadata = json.loads(raw)
        body = {k: v for k, v in metadata.items() if k != "release_id"}
        if (
            metadata.get("release_id") != expected_id
            or sha(compact(body)) != expected_id
            or raw != compact(metadata)
        ):
            raise ValueError("Deployed release differs from expected candidate")
        if len(metadata["files"]) >= MAX_FILES:
            raise ValueError("Deployment file count budget exceeded")
        files = {"release.json": raw}
        for name, item in sorted(metadata["files"].items()):
            if type(item["bytes"]) is not int or not 0 <= item["bytes"] <= MAX_BYTES:
                raise ValueError("Invalid deployment file size")
            payload = fetch(name, item["bytes"])
            if len(payload) != item["bytes"] or sha(payload) != item["sha256"]:
                raise ValueError("Deployed file differs from candidate")
            files[name] = payload
        verify_files(files, expected_id)
        # Fence a deployment changing between requests.
        if fetch("release.json", 2_000_000) != raw:
            raise ValueError("Deployment changed during verification")
        return {
            "release_id": expected_id,
            "source_revision": metadata["source_revision"],
            "verified_files": len(files),
            "requests": requests,
            "decoded_bytes": received,
            "seconds": round(clock() - started, 4),
            "static_bytes_verified": True,
            "browser_routes_verified": False,
        }
    finally:
        if owned:
            client.close()


def check_committed_inputs(root, data, site):
    root, site = Path(root).resolve(), Path(site).resolve()
    if root not in site.parents:
        raise ValueError("Candidate site must be inside the committed repository")
    tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0"))
    consumed = set(input_identity(root, data)["inputs"])
    consumed.update(
        path.relative_to(root).as_posix() for path in site_paths(site) if path.is_file()
    )
    if consumed - tracked:
        raise ValueError("Candidate inputs/site contain uncommitted or ignored files")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("pack")
    create.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    create.add_argument("--data", type=Path, default=Path("data/papers.json"))
    create.add_argument("--site", type=Path, default=Path("docs"))
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--release-tag")
    restore = commands.add_parser("restore")
    restore.add_argument("--archive", type=Path, required=True)
    restore.add_argument("--expected-release-id", required=True)
    restore.add_argument("--output", type=Path, required=True)
    deployed = commands.add_parser("verify-url")
    deployed.add_argument("--base-url", required=True)
    deployed.add_argument("--expected-release-id", required=True)
    deployed.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "verify-url":
        report_path = args.report.resolve()
        repo = Path(__file__).resolve().parents[1]
        if (
            report_path.exists()
            or report_path == repo
            or any(
                p == report_path or p in report_path.parents for p in (repo / "data", repo / "docs")
            )
        ):
            parser.error("Use a new verification report outside canonical data and deployed docs")
        failed = False
        try:
            result = verify_url(args.base_url, args.expected_release_id)
            result["status"] = "verified_static_bytes"
        except (ValueError, KeyError, TypeError, httpx.HTTPError) as error:
            failed = True
            result = {
                "status": "verification_failed",
                "release_id": args.expected_release_id,
                "failure_type": type(error).__name__,
                "static_bytes_verified": False,
            }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("xb") as stream:
            stream.write(compact(result))
        print(json.dumps(result))
        if failed:
            raise SystemExit(1)
        return
    repo = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output == repo or any(
        p == output or p in output.parents for p in (repo / "data", repo / "docs")
    ):
        parser.error("Use a new staging output outside canonical data and deployed docs")
    if args.command == "pack":
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=args.root, text=True
        ).strip()
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=args.root):
            parser.error("Commit the exact candidate before packaging; working tree must be clean")
        if args.release_tag:
            tagged = subprocess.check_output(
                ["git", "rev-parse", args.release_tag + "^{commit}"], cwd=args.root, text=True
            ).strip()
            if tagged != revision:
                parser.error("Release tag must point to the exact candidate commit")
        data = args.data if args.data.is_absolute() else args.root / args.data
        site = args.site if args.site.is_absolute() else args.root / args.site
        check_committed_inputs(args.root, data, site)
        result = pack(args.root, data, site, args.output, revision, args.release_tag)
    else:
        files, result = load_archive(args.archive, args.expected_release_id)
        write_new(files, args.output)
    print(json.dumps({key: result[key] for key in ("release_id", "source_revision")}))


if __name__ == "__main__":
    main()
