"""Bounded preparation for manually dispatched, already reviewed worker imports."""

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from src.schema import PaperDatabase
from src.workers.queue import ExtractionResult
from src.workers.review import ExtractionReview

ALLOWED_HOSTS = {"arxiv.org", "export.arxiv.org", "openaccess.thecvf.com"}
MAX_PDF_BYTES = 50_000_000


def public_pdf_url(value):
    url = urlsplit(value)
    if (
        url.scheme != "https"
        or url.hostname not in ALLOWED_HOSTS
        or url.port not in (None, 443)
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError("Reviewed import requires an approved canonical public PDF URL")
    return value


def download_reviewed_pdf(
    url,
    destination: Path,
    expected_sha256: str,
    *,
    client=None,
    max_bytes=MAX_PDF_BYTES,
    max_seconds=120,
    clock=time.monotonic,
):
    public_pdf_url(url)
    if (
        not re.fullmatch(r"[a-f0-9]{64}", expected_sha256)
        or not 1 <= max_bytes <= MAX_PDF_BYTES
        or not 0 < max_seconds <= 300
    ):
        raise ValueError("Invalid reviewed PDF download limits")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".partial")
    started = clock()
    owns = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(20, connect=10), follow_redirects=False)
    try:
        for redirects in range(4):
            if clock() - started >= max_seconds:
                raise ValueError("Reviewed PDF download time budget exceeded")
            public_pdf_url(url)
            with client.stream("GET", url, follow_redirects=False) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    if redirects == 3 or not response.headers.get("Location"):
                        raise ValueError("Reviewed PDF redirect limit exceeded")
                    url = public_pdf_url(urljoin(url, response.headers["Location"]))
                    continue
                if response.status_code != 200:
                    raise ValueError("Reviewed PDF source request failed")
                length = response.headers.get("Content-Length")
                if length is not None and not 0 <= int(length) <= max_bytes:
                    raise ValueError("Reviewed PDF exceeds size budget")
                size = 0
                digest = hashlib.sha256()
                prefix = bytearray()
                with partial.open("wb") as output:
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > max_bytes or clock() - started >= max_seconds:
                            raise ValueError("Reviewed PDF download budget exceeded")
                        if len(prefix) < 5:
                            prefix.extend(chunk[: 5 - len(prefix)])
                        output.write(chunk)
                        digest.update(chunk)
                if bytes(prefix) != b"%PDF-" or digest.hexdigest() != expected_sha256:
                    raise ValueError("Reviewed PDF content/digest mismatch")
                os.replace(partial, destination)
                return {"pdf_sha256": digest.hexdigest(), "bytes": size, "requests": redirects + 1}
        raise ValueError("Reviewed PDF download incomplete")
    except httpx.HTTPError:
        raise ValueError("Reviewed PDF transport failed") from None
    finally:
        partial.unlink(missing_ok=True)
        if owns:
            client.close()


def prepare_reviewed_import(data: Path, key: str, output: Path, *, client=None):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", key):
        raise ValueError("Invalid reviewed import key")
    inputs = (data.parent / "extraction/review-inputs").resolve()
    if not inputs.is_relative_to(data.parent.resolve()):
        raise ValueError("Reviewed inputs escape canonical data directory")
    paths = {name: (inputs / f"{key}.{name}.json").resolve() for name in ("review", "result")}
    for path in paths.values():
        if not path.is_relative_to(inputs) or path.stat().st_size > 5_000_000:
            raise ValueError("Invalid reviewed input path/size")
    raw = paths["result"].read_bytes()
    result = ExtractionResult.model_validate_json(raw)
    review = ExtractionReview.model_validate_json(paths["review"].read_bytes())
    if hashlib.sha256(raw).hexdigest() != review.expected_result_sha256:
        raise ValueError("Reviewed result bytes changed")
    db = PaperDatabase.load(data)
    paper = next((p for p in db.papers if p.id == result.paper_id), None)
    if paper is None or not paper.pdf_url:
        raise ValueError("Reviewed paper needs an active canonical PDF URL")
    if review.source_url not in (paper.pdf_url, paper.paper_url):
        raise ValueError("Reviewed source URL does not match canonical source")
    report = download_reviewed_pdf(paper.pdf_url, output, result.pdf_sha256, client=client)
    return {
        **report,
        "paper_id": paper.id,
        "result_sha256": review.expected_result_sha256,
        "canonical_modified": False,
        "reviewed_ledger_modified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(prepare_reviewed_import(args.data, args.key, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
