"""Stage checksum-pinned llama.cpp/CUDA archives and Qwen GGUFs; no service changes."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path
from urllib.parse import urlsplit


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def validate_pins(pins):
    items = [*pins["assets"], *pins["model_files"]]
    if not pins["assets"] or not pins["model_files"]:
        raise ValueError("Runtime and model pins are both required")
    if len({item["name"] for item in items}) != len(items):
        raise ValueError("Artifact names must be unique")
    for item in items:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", item["name"]):
            raise ValueError("Unsafe artifact name")
        if not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]):
            raise ValueError("Invalid artifact checksum")
        if type(item["bytes"]) is not int or not 1 <= item["bytes"] <= 6_000_000_000:
            raise ValueError("Invalid artifact size")
        if item["kind"] == "runtime":
            prefix = f"https://github.com/ggml-org/llama.cpp/releases/download/{pins['release']}/"
        elif item["kind"] == "model":
            prefix = f"https://huggingface.co/{pins['model_repository']}/resolve/{pins['model_revision']}/"
        else:
            raise ValueError("Invalid artifact kind")
        if item["url"] != prefix + item["name"]:
            raise ValueError("Artifact URL differs from immutable pin")
    if sum(item["bytes"] for item in items) > 8_000_000_000:
        raise ValueError("Aggregate download budget exceeded")
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    pins = json.loads(args.pins.read_text(encoding="utf-8-sig"))
    items = validate_pins(pins)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "preview_no_network",
                    "files": len(items),
                    "download_bytes": sum(item["bytes"] for item in items),
                    "root": str(args.root.resolve()),
                    "services_modified": False,
                }
            )
        )
        return
    root = args.root.resolve()
    if root == Path(root.anchor) or root == Path.home():
        parser.error("Use a dedicated staging directory")
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < 15_000_000_000:
        parser.error("Staging requires at least 15 GB free")
    for item in items:
        name = item["name"]
        if Path(name).name != name or name in (".", ".."):
            raise ValueError("Unsafe artifact name")
        if urlsplit(item["url"]).scheme != "https" or urlsplit(item["url"]).hostname not in (
            "github.com",
            "huggingface.co",
        ):
            raise ValueError("Unexpected artifact origin")
        target = root / name
        if not target.exists():
            part = root / (name + ".part")
            subprocess.run(
                [
                    "curl",
                    "--fail",
                    "--location",
                    "--silent",
                    "--show-error",
                    "--continue-at",
                    "-",
                    "--retry",
                    "2",
                    "--connect-timeout",
                    "20",
                    "--max-time",
                    "1800",
                    "--limit-rate",
                    "25M",
                    "--output",
                    str(part),
                    item["url"],
                ],
                check=True,
                timeout=5500,
            )
            if part.stat().st_size != item["bytes"] or digest(part) != item["sha256"]:
                raise ValueError("Downloaded artifact checksum mismatch")
            part.rename(target)
        elif target.stat().st_size != item["bytes"] or digest(target) != item["sha256"]:
            raise ValueError("Existing artifact checksum mismatch")
        print("verified " + name, flush=True)
        if item["kind"] == "runtime":
            destination = root / name.removesuffix(".tar.gz")
            destination.mkdir(exist_ok=True)
            with tarfile.open(target) as archive:
                archive.extractall(destination, filter="data")
            print("extracted " + name, flush=True)
    receipt = {
        "status": "staged_verified",
        "pins": pins,
        "services_modified": False,
        "model_inference_verified": False,
    }
    (root / "staging-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("staging complete", flush=True)


if __name__ == "__main__":
    main()
