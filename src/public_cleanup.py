"""Bounded cleanup of unreferenced public artifacts, retaining verified generations."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from src.file_lock import exclusive_file
from src.releases import MAX_BYTES, MAX_FILES, check_public, descriptors, safe_name, sha
from src.storage import _atomic_write, _encode

# Cleanup may inspect an oversized historical cache without relaxing release limits.
MAX_CLEANUP_BYTES = 500_000_000

OWNED = re.compile(
    r"(?:index|search|aliases|archive|signals|trending|"
    r"details/[0-9]{4}-(?:0[1-9]|1[0-2])(?:-[01])*|"
    r"graph/(?:index|overview|adjacency(?:-[01])*))\.([a-f0-9]{64})\.json"
)


def _link(path):
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def _root(root):
    root = Path(root)
    if _link(root):
        raise ValueError("Public artifact root cannot be a link")
    root = root.resolve(strict=True)
    if not root.is_dir() or root.parent == root or _link(root / "public.run.lock"):
        raise ValueError("Invalid public artifact root or writer lock")
    return root


def _target(root, name):
    path = root / safe_name(name)
    if not path.resolve().is_relative_to(root):
        raise ValueError("Artifact escapes the intended root")
    for parent in [path, *path.parents]:
        if _link(parent):
            raise ValueError("Public artifact paths cannot contain links")
        if parent == root:
            break
    return path


def _limits(files, size, max_scan_bytes=None):
    scan_limit = MAX_BYTES if max_scan_bytes is None else max_scan_bytes
    if type(files) is not int or not 1 <= files <= MAX_FILES:
        raise ValueError("Invalid cleanup file budget")
    if type(scan_limit) is not int or not 1 <= scan_limit <= MAX_CLEANUP_BYTES:
        raise ValueError("Invalid cleanup scan byte budget")
    if type(size) is not int or not 1 <= size <= scan_limit:
        raise ValueError("Invalid cleanup byte budget")
    return scan_limit


def _walk(root):
    result, entries = [], 0

    def fail(error):
        raise error

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        entries += len(dirs) + len(files)
        if entries > MAX_FILES:
            raise ValueError("Public artifact inventory exceeds entry budget")
        for name in dirs + files:
            if _link(Path(directory) / name):
                raise ValueError("Public artifact tree cannot contain links")
        for name in files:
            if name.endswith((".run.lock", ".writer.lock")) or name.startswith(".staging-"):
                continue
            result.append((Path(directory) / name).relative_to(root).as_posix())
    return sorted(result)


def _plan(root, retain, max_delete_files, max_delete_bytes, max_scan_bytes=None):
    scan_limit = _limits(max_delete_files, max_delete_bytes, max_scan_bytes)
    if not 1 <= len(retain) <= 5:
        raise ValueError("Retain one to five explicitly selected previous manifests")
    inventory = _walk(root)
    files, protected, identities = {}, {}, []
    for path in [root / "manifest.json", *map(Path, retain)]:
        if _link(path) or path.stat().st_size > 2_000_000:
            raise ValueError("Invalid or oversized retained manifest")
        path = path.resolve(strict=True)
        if path != root / "manifest.json" and path.is_relative_to(root):
            raise ValueError("Store retained manifest snapshots outside the public artifact root")
        raw = path.read_bytes()
        manifest = json.loads(raw)
        required = {
            "schema_version",
            "build_digest",
            "source_sha256",
            "index",
            "search",
            "aliases",
            "archive",
            "details",
            "graph",
            "total_count",
            "total_edges",
        }
        if manifest.get("schema_version") != "1.0.0" or not required <= manifest.keys():
            raise ValueError("Incomplete or unsupported public manifest")
        graph = manifest["graph"]
        if (
            not isinstance(graph, dict)
            or not {"index", "overview", "buckets", "coverage"} <= graph.keys()
        ):
            raise ValueError("Incomplete public graph manifest")
        if not isinstance(manifest["details"], list) or not isinstance(graph["buckets"], list):
            raise ValueError("Invalid retained artifact inventory")
        pointers = [manifest[k] for k in ("index", "search", "aliases", "archive")]
        pointers += [graph["index"], graph["overview"], *manifest["details"], *graph["buckets"]]
        pointers += [manifest[k] for k in ("signals", "trending") if k in manifest]
        if any(
            not isinstance(x, dict) or not {"path", "sha256", "bytes"} <= x.keys() for x in pointers
        ):
            raise ValueError("Incomplete retained artifact descriptor")
        items = list(descriptors(manifest))
        if len(items) > MAX_FILES:
            raise ValueError("Too many retained artifact descriptors")
        for item in items:
            name = safe_name(item["path"])
            owned = OWNED.fullmatch(name)
            if not owned or owned[1] != item["sha256"]:
                raise ValueError("Retained manifest contains an unexpected artifact name")
            target = _target(root, name)
            if type(item.get("bytes")) is not int or target.stat().st_size != item["bytes"]:
                raise ValueError("Retained artifact size mismatch")
            if name not in protected:
                protected[name] = {"sha256": item["sha256"], "bytes": item["bytes"]}
                if sum(x["bytes"] for x in protected.values()) > MAX_BYTES:
                    raise ValueError("Retained artifact bytes exceed budget")
                files["data/" + name] = target.read_bytes()
        check_public({**files, "data/manifest.json": raw, "index.html": b""})
        catalog = json.loads(files["data/" + manifest["index"]["path"]])
        adjacency = json.loads(files["data/" + graph["index"]["path"]])
        if not set(catalog["detail_paths"]) <= {x["path"] for x in manifest["details"]}:
            raise ValueError("Catalog references an undeclared detail artifact")
        if not set(adjacency["pointers"].values()) <= {x["path"] for x in graph["buckets"]}:
            raise ValueError("Graph references an undeclared adjacency artifact")
        identities.append(
            {"path": path.as_posix(), "sha256": sha(raw), "build_digest": manifest["build_digest"]}
        )
    digests = [x["build_digest"] for x in identities]
    if len(set(digests)) != len(digests):
        raise ValueError("Retained generations must be distinct from each other and current")
    candidates, unknown, scanned_bytes = [], [], sum(x["bytes"] for x in protected.values())
    for name in inventory:
        if name == "manifest.json" or name in protected:
            continue
        owned = OWNED.fullmatch(name)
        if not owned:
            unknown.append(name)
            continue
        target = _target(root, name)
        size = target.stat().st_size
        scanned_bytes += size
        if scanned_bytes > scan_limit:
            raise ValueError("Public immutable artifact bytes exceed scan budget")
        if sha(target.read_bytes()) != owned[1]:
            raise ValueError("Corrupt immutable artifact; cleanup refused before deletion")
        candidates.append({"path": name, "sha256": owned[1], "bytes": size})
    if len(candidates) > max_delete_files or sum(x["bytes"] for x in candidates) > max_delete_bytes:
        raise ValueError("Cleanup exceeds deletion budget; no files removed")
    plan = {
        "schema_version": "1.0.0",
        "root": root.as_posix(),
        "current_manifest": identities[0],
        "retained_manifests": identities[1:],
        "protected": dict(sorted(protected.items())),
        "max_delete_files": max_delete_files,
        "max_delete_bytes": max_delete_bytes,
        "unknown_files_preserved": unknown,
        "delete": candidates,
    }
    if max_scan_bytes is not None:
        plan["max_scan_bytes"] = max_scan_bytes
    return {**plan, "plan_id": sha(_encode(plan))}


def plan_cleanup(
    root, retain, *, max_delete_files=500, max_delete_bytes=100_000_000, max_scan_bytes=None
):
    root = _root(root)
    with exclusive_file(root / "public.run.lock", resource="public artifact writer"):
        return _plan(root, retain, max_delete_files, max_delete_bytes, max_scan_bytes)


def apply_cleanup(root, approved):
    root = _root(root)
    if (
        root.as_posix() != approved["root"]
        or sha(_encode({k: v for k, v in approved.items() if k != "plan_id"}))
        != approved["plan_id"]
    ):
        raise ValueError("Cleanup plan root or identity mismatch")
    _limits(
        approved["max_delete_files"], approved["max_delete_bytes"], approved.get("max_scan_bytes")
    )
    if len(approved["delete"]) > approved["max_delete_files"]:
        raise ValueError("Invalid approved deletion inventory")
    allowed = {x["path"]: x for x in approved["delete"]}
    if len(allowed) != len(approved["delete"]):
        raise ValueError("Duplicate approved deletion path")
    with exclusive_file(root / "public.run.lock", resource="public artifact writer"):
        fresh = _plan(
            root,
            [x["path"] for x in approved["retained_manifests"]],
            approved["max_delete_files"],
            approved["max_delete_bytes"],
            approved.get("max_scan_bytes"),
        )
        for key in fresh.keys() - {"delete", "plan_id"}:
            if fresh[key] != approved[key]:
                raise ValueError("Cleanup inputs changed; prepare a new plan")
        if any(allowed.get(x["path"]) != x for x in fresh["delete"]):
            raise ValueError("Unapproved artifact inventory change; no files removed")
        removed = []
        for item in fresh["delete"]:
            # Only individually verified regular files are removed, never directories.
            for manifest in [fresh["current_manifest"], *fresh["retained_manifests"]]:
                if sha(Path(manifest["path"]).read_bytes()) != manifest["sha256"]:
                    raise ValueError("Manifest changed during cleanup; stopped")
            path = _target(root, item["path"])
            if not path.is_file() or sha(path.read_bytes()) != item["sha256"]:
                raise ValueError("Candidate changed during cleanup; stopped")
            path.unlink()
            removed.append(item)
        return {
            "status": "applied" if removed else "no_op",
            "plan_id": approved["plan_id"],
            "root": root.as_posix(),
            "deleted": removed,
            "deleted_bytes": sum(x["bytes"] for x in removed),
            "already_absent_files": len(allowed) - len(fresh["delete"]),
            "retained_builds": [
                x["build_digest"] for x in [fresh["current_manifest"], *fresh["retained_manifests"]]
            ],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preview = commands.add_parser("plan")
    preview.add_argument("--root", type=Path, required=True)
    preview.add_argument("--retain", type=Path, action="append", required=True)
    preview.add_argument("--output", type=Path, required=True)
    preview.add_argument("--max-delete-files", type=int, default=500)
    preview.add_argument("--max-delete-bytes", type=int, default=100_000_000)
    preview.add_argument(
        "--max-scan-bytes",
        type=int,
        help="Explicit historical-cache scan bound, at most 500 MB; release limits stay unchanged",
    )
    apply = commands.add_parser("apply")
    apply.add_argument("--root", type=Path, required=True)
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    destination = args.output if args.command == "plan" else args.receipt
    root = args.root.resolve(strict=True)
    if destination.resolve().is_relative_to(root):
        raise ValueError("Store cleanup plans/receipts outside public artifacts")
    if args.command == "plan":
        if any(destination.resolve() == path.resolve() for path in args.retain):
            raise ValueError("Cleanup output cannot overwrite a retained manifest")
        result = plan_cleanup(
            args.root,
            args.retain,
            max_delete_files=args.max_delete_files,
            max_delete_bytes=args.max_delete_bytes,
            max_scan_bytes=args.max_scan_bytes,
        )
    else:
        if args.plan.stat().st_size > 2_000_000:
            raise ValueError("Oversized cleanup plan")
        approved = json.loads(args.plan.read_bytes())
        inputs = [args.plan, *[Path(x["path"]) for x in approved["retained_manifests"]]]
        if any(destination.resolve() == path.resolve() for path in inputs):
            raise ValueError("Cleanup receipt cannot overwrite its plan or retained manifests")
        result = apply_cleanup(args.root, approved)
    _atomic_write(destination, _encode(result))
    print(
        json.dumps(
            {
                "status": result.get("status", "planned"),
                "plan_id": result["plan_id"],
                "files": len(result.get("deleted", result.get("delete", []))),
                "bytes": result.get(
                    "deleted_bytes", sum(x["bytes"] for x in result.get("delete", []))
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
