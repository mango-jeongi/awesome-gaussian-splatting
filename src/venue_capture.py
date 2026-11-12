"""Paced resumable official-CVF metadata capture bound to a frozen listing/policy."""

import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from src.extractors.cvf import parse_listing, parse_publication, publication_candidate
from src.extractors.openalex import OpenAlexClient
from src.file_lock import exclusive_file
from src.schema import PaperRecord
from src.storage import _atomic_write, _encode


def capture_cvf(
    listing_bytes,
    root: Path,
    *,
    venue,
    year,
    track,
    policy,
    max_requests=10,
    max_seconds=120,
    all_metadata=False,
    client=None,
    clock=time.monotonic,
    sleep=time.sleep,
):
    if not 0 <= max_requests <= 500 or not 0 < max_seconds <= 1800:
        raise ValueError("Invalid CVF capture budgets")
    root = Path(root)
    digest = hashlib.sha256(listing_bytes).hexdigest()
    listing = parse_listing(listing_bytes.decode("utf-8"), venue=venue, year=year, track=track)
    dispositions = []
    for row in listing:
        decision = policy.decide(
            PaperRecord(
                id=row.source_url,
                title=row.title,
                authors=row.authors,
                published_date=f"{year}-01-01",
                published_date_precision="year",
                date_placement="year_start",
                source="cvf",
            )
        )
        dispositions.append(
            {
                "listing": row.model_dump(mode="json"),
                "title_outcome": decision.outcome,
                "title_reason": decision.reason,
            }
        )
    selected = {
        row.source_url: row
        for row, item in zip(listing, dispositions, strict=True)
        if all_metadata or item["title_outcome"] in ("include", "review")
    }
    expected = {
        "schema_version": 1,
        "listing_sha256": digest,
        "policy_digest": policy.digest,
        "venue": venue,
        "year": year,
        "track": track,
    }
    if all_metadata:
        expected["selection_mode"] = "all_metadata"
    state_path = root / "state.json"
    started = clock()
    requests = 0
    owns = client is None
    client = client or httpx.Client(timeout=20, follow_redirects=False)
    try:
        with exclusive_file(root / "capture.run.lock", resource="CVF metadata capture"):
            inventory_path = root / "inventory.json"
            legacy_inventory = (
                json.loads(inventory_path.read_bytes())
                if not state_path.exists() and inventory_path.exists()
                else None
            )
            initial = {**expected, "captures": {}, "failures": {}}
            if legacy_inventory is not None:
                initial = {
                    key: legacy_inventory[key]
                    for key in (
                        "schema_version",
                        "listing_sha256",
                        "policy_digest",
                        "venue",
                        "year",
                        "track",
                    )
                }
                if "selection_mode" in legacy_inventory:
                    initial["selection_mode"] = legacy_inventory["selection_mode"]
                initial.update(captures={}, failures={})
            state = json.loads(state_path.read_bytes()) if state_path.exists() else initial
            selection_mode = "all_metadata" if all_metadata else "title_priority"
            if state.get("selection_mode", "title_priority") != selection_mode:
                raise ValueError("Frozen CVF selection mode changed; use a separate epoch")
            if any(state.get(key) != value for key, value in expected.items()):
                raise ValueError("Frozen CVF listing/policy/edition changed")
            if set(state["captures"]) - set(selected) or set(state["failures"]) - set(selected):
                raise ValueError("CVF state contains unexpected paper URLs")
            for failure in state["failures"].values():
                retry_at = datetime.fromisoformat(failure["retry_at"])
                if retry_at.utcoffset() is None:
                    raise ValueError("CVF retry deadline requires timezone")
            verified = {}
            for url, capture in state["captures"].items():
                sha = capture["sha256"]
                import re

                if not re.fullmatch(r"[a-f0-9]{64}", sha):
                    raise ValueError("Invalid CVF capture digest")
                raw = (root / "responses" / f"{sha}.html").read_bytes()
                if hashlib.sha256(raw).hexdigest() != sha:
                    raise ValueError("CVF capture hash mismatch")
                stamp = datetime.fromisoformat(capture["observed_at"])
                if stamp.utcoffset() is None or stamp > datetime.now(UTC):
                    raise ValueError("Invalid CVF capture time")
                from src.venue_reviews import parse_reviewed_capture

                verified[url] = parse_reviewed_capture(raw, selected[url], capture, digest)
            listing_path = root / f"listing.{digest}.html"
            if (
                listing_path.exists()
                and hashlib.sha256(listing_path.read_bytes()).hexdigest() != digest
            ):
                raise ValueError("Frozen CVF listing hash mismatch")
            _atomic_write(listing_path, listing_bytes)
            if not state_path.exists():
                _atomic_write(state_path, _encode(state))
            _atomic_write(
                root / "inventory.json",
                _encode({**expected, "title_screening_only": True, "records": dispositions}),
            )
            next_request = clock()
            for url, row in selected.items():
                if url in verified:
                    continue
                previous = state["failures"].get(url)
                if previous and datetime.fromisoformat(previous["retry_at"]) > datetime.now(UTC):
                    continue
                wait = max(0, next_request - clock())
                if requests >= max_requests or clock() - started + wait >= max_seconds:
                    break
                if wait:
                    sleep(wait)
                requests += 1
                now = datetime.now(UTC)
                retry = 3600
                stop = False
                raw = None
                response_status = None
                try:
                    with client.stream("GET", url, follow_redirects=False) as response:
                        response_status = response.status_code
                        if response.status_code != 200:
                            if response.status_code in (429, 503):
                                retry = max(retry, OpenAlexClient._retry_delay(response, 60))
                                stop = True
                            raise ValueError(f"http_{response.status_code}")
                        content = bytearray()
                        for chunk in response.iter_bytes():
                            content.extend(chunk)
                            if len(content) > 2_000_000 or clock() - started >= max_seconds:
                                raise ValueError("response_budget")
                    raw = bytes(content)
                    publication = parse_publication(raw.decode("utf-8"), row)
                    sha = hashlib.sha256(raw).hexdigest()
                    _atomic_write(root / "responses" / f"{sha}.html", raw)
                    state["captures"][url] = {"sha256": sha, "observed_at": now.isoformat()}
                    state["failures"].pop(url, None)
                    verified[url] = publication
                except (httpx.HTTPError, ValueError, UnicodeError) as failure:
                    reason = (
                        "transport"
                        if isinstance(failure, httpx.HTTPError)
                        else "metadata_or_response_invalid"
                    )
                    failure_record = {
                        "reason": reason,
                        "retry_at": (now + timedelta(seconds=retry)).isoformat(),
                        "response_http_status": response_status,
                        "attempted_at": now.isoformat(),
                    }
                    if raw is not None:
                        # Preserve complete bounded public responses for diagnosis;
                        # invalid metadata is never registered as a verified capture.
                        diagnostic_sha = hashlib.sha256(raw).hexdigest()
                        diagnostic = f"diagnostics/{diagnostic_sha}.html"
                        _atomic_write(root / diagnostic, raw)
                        failure_record.update(
                            response_sha256=diagnostic_sha,
                            response_bytes=len(raw),
                            response_path=diagnostic,
                        )
                    state["failures"][url] = failure_record
                _atomic_write(state_path, _encode(state))
                next_request = clock() + 1
                if stop:
                    break
            records = []
            for url, publication in verified.items():
                observed = datetime.fromisoformat(state["captures"][url]["observed_at"])
                decision = policy.decide(publication_candidate(publication, observed_at=observed))
                records.append(
                    {
                        "publication": publication.model_dump(mode="json"),
                        "capture": state["captures"][url],
                        "metadata_outcome": decision.outcome,
                        "metadata_reason": decision.reason,
                    }
                )
            report = {
                **expected,
                "listing_records": len(listing),
                "title_dispositions": {
                    outcome: sum(r["title_outcome"] == outcome for r in dispositions)
                    for outcome in ("include", "review", "exclude")
                },
                "selected_records": len(selected),
                "verified_records": len(verified),
                "reviewed_title_variant_records": sum(
                    "title_review" in state["captures"][url] for url in verified
                ),
                "reviewed_author_variant_records": sum(
                    "author_review" in state["captures"][url] for url in verified
                ),
                "reviewed_source_url_records": sum(
                    "url_review" in state["captures"][url] for url in verified
                ),
                "pending_records": len(selected) - len(verified),
                "failed_records": len(state["failures"]),
                "invocation_requests": requests,
                "selected_metadata_complete": len(verified) == len(selected),
                "venue_inventory_reconciled": False,
                "corpus_modified": False,
                "records": records,
            }
            _atomic_write(root / "latest-report.json", _encode(report))
            return report
    finally:
        if owns:
            client.close()
