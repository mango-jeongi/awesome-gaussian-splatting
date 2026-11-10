"""Bounded, replayable HF daily discovery. Canonical import is a separate review step."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from src.extractors.huggingface_client import HFFailure
from src.extractors.huggingface_contracts import parse_daily
from src.file_lock import exclusive_file
from src.storage import _atomic_write, _encode


def discover_daily(client, root: Path, *, until: date, lookback=7, limit=100, now=None):
    if not 1 <= lookback <= 31 or not 1 <= limit <= 100:
        raise ValueError("HF discovery requires1..31 days and1..100 entries/day")
    now = now or datetime.now(UTC)
    if now.utcoffset() is None or until > now.date():
        raise ValueError("Discovery requires aware time and no future dates")
    root = Path(root)
    found = {}
    days = []
    with exclusive_file(root / "discovery.run.lock", resource="HF discovery"):
        for offset in range(lookback):
            day = until - timedelta(days=offset)
            pointer = root / f"{day.isoformat()}-{limit}.json"
            payload = json.loads(pointer.read_bytes()) if pointer.exists() else None
            cached = False
            if payload:
                if payload["day"] != day.isoformat() or payload["limit"] != limit:
                    raise ValueError("Discovery cache contract mismatch")
                parsed = datetime.fromisoformat(payload["fetched_at"])
                if parsed.utcoffset() is None or parsed > now:
                    raise ValueError("Invalid discovery cache time")
                cached = payload.get("contract_version") == 2 and now - parsed < timedelta(days=1)
            if not cached:
                try:
                    entries = client.daily(day=day, limit=limit)
                except HFFailure as failure:
                    days.append({"day": day.isoformat(), "status": failure.reason})
                    break
                payload = {
                    "contract_version": 2,
                    "day": day.isoformat(),
                    "limit": limit,
                    "fetched_at": now.isoformat(),
                    "entries": [entry.model_dump(mode="json") for entry in entries],
                }
                encoded = _encode(payload)
                digest = hashlib.sha256(encoded).hexdigest()
                _atomic_write(root / "responses" / f"{day.isoformat()}.{digest}.json", encoded)
                _atomic_write(pointer, encoded)
            entries = parse_daily(payload["entries"])
            for entry in entries:
                found.setdefault(entry.paper.id, entry)
            days.append(
                {
                    "day": day.isoformat(),
                    "status": "possibly_truncated" if len(entries) >= limit else "fetched",
                    "count": len(entries),
                    "cache_reused": cached,
                }
            )
    return list(found.values()), {
        "requested_days": lookback,
        "days": days,
        "unique_candidates": len(found),
        "complete": len(days) == lookback and all(day["status"] == "fetched" for day in days),
    }
