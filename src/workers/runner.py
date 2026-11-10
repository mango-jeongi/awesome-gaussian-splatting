"""One bounded pass; PDF inputs and temporary parser output stay on configured local storage."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from src.storage import _atomic_write
from src.workers.queue import ExtractionLimits, ExtractionQueue, ExtractionResult


def local_cache(path: Path) -> Path:
    path = Path(path).resolve()
    if os.name == "nt" and (str(path).startswith("\\\\") or path.drive.upper() == "G:"):
        raise ValueError("PDF cache must use configured local SSD storage, outside Google Drive")
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_pdf(path: Path, cache: Path, limits: ExtractionLimits) -> str:
    cache = local_cache(cache)
    with Path(path).open("rb") as stream:
        payload = stream.read(limits.max_bytes + 1)
    if len(payload) > limits.max_bytes or not payload.startswith(b"%PDF-"):
        raise ValueError("PDF is invalid or exceeds configured size limit")
    digest = hashlib.sha256(payload).hexdigest()
    destination = cache / f"{digest}.pdf"
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise ValueError("Corrupt PDF cache")
    else:
        _atomic_write(destination, payload)
    return digest


def worker_pass(
    queue: ExtractionQueue, cache: Path, *, max_jobs: int = 1, llama_config: Path | None = None
) -> dict:
    if not 1 <= max_jobs <= 100:
        raise ValueError("Pass requires a job budget between1 and100")
    if llama_config is not None:
        from src.workers.llama_parser import LlamaConfig

        llama_config = Path(llama_config).resolve()
        LlamaConfig.model_validate_json(llama_config.read_bytes())
    cache = local_cache(cache)
    report = {"claimed": 0, "review-required": 0, "failed": 0}
    # Never retry a failed job twice in the same bounded pass.
    seen = set()
    for _ in range(max_jobs):
        job = queue.claim(exclude_keys=seen)
        if job is None:
            break
        seen.add(job.key)
        report["claimed"] += 1
        source = cache / f"{job.pdf_sha256}.pdf"
        if not source.is_file():
            queue.fail(job.key, job.lease_token, "pdf_unavailable")
            report["failed"] += 1
            continue
        command = [sys.executable, "-m", "src.workers.pdf_parser", str(source)]
        if llama_config is not None:
            command = [
                sys.executable,
                "-m",
                "src.workers.llama_parser",
                str(source),
                str(llama_config),
            ]
        with tempfile.TemporaryFile(dir=cache) as output:
            try:
                process = subprocess.run(
                    command,
                    input=job.model_dump_json().encode(),
                    stdout=output,
                    stderr=subprocess.DEVNULL,
                    timeout=job.limits.timeout_seconds,
                    check=False,
                    cwd=Path(__file__).resolve().parents[2],
                )
            except subprocess.TimeoutExpired:
                queue.fail(job.key, job.lease_token, "timeout")
                report["failed"] += 1
                continue
            if process.returncode:
                code = {2: "invalid_pdf", 3: "size_limit", 4: "page_limit"}.get(
                    process.returncode, "parser_error"
                )
                queue.fail(job.key, job.lease_token, code)
                report["failed"] += 1
                continue
            output.seek(0)
            try:
                payload = output.read(5_000_001)
                if len(payload) > 5_000_000:
                    raise ValueError("Oversized parser result")
                result = ExtractionResult.model_validate_json(payload)
                queue.finish(job.key, job.lease_token, result)
            except ValueError:
                queue.fail(job.key, job.lease_token, "parser_error")
                report["failed"] += 1
                continue
            report["review-required"] += 1
    return report
