"""Frozen HF discovery windows that survive budget stops and UTC-day changes."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.extractors.huggingface_contracts import parse_daily
from src.file_lock import exclusive_file
from src.huggingface_discovery import discover_daily
from src.storage import _atomic_write, _encode


class HFWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    run_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    since: date
    until: date
    lookback: int = Field(ge=1, le=15)
    limit: int = Field(ge=1, le=100)
    phase: Literal["pending", "sampled"] = "pending"
    responses: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_window(self):
        if not 0 <= (self.until - self.since).days < 2 * self.lookback:
            raise ValueError("Invalid frozen HF window")
        for day, digest in self.responses.items():
            import re

            if (
                not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)
                or not self.since <= date.fromisoformat(day) <= self.until
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
            ):
                raise ValueError("Invalid frozen HF response reference")
        if self.phase == "sampled" and len(self.responses) != (self.until - self.since).days + 1:
            raise ValueError("Sampled HF window must account for every requested date")
        return self


def frozen_response(root: Path, day: str, digest: str, limit: int):
    import re

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Invalid HF response locator")
    raw = (root / "responses" / f"{day}.{digest}.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Frozen HF response hash mismatch")
    payload = json.loads(raw)
    if payload.get("contract_version") != 2 or payload["day"] != day or payload["limit"] != limit:
        raise ValueError("Frozen HF response contract mismatch")
    return payload


def discover_scheduled(client, root: Path, *, until: date, lookback=7, limit=100, now=None):
    now = now or datetime.now(UTC)
    if (
        now.utcoffset() is None
        or until > now.date()
        or not 1 <= lookback <= 15
        or not 1 <= limit <= 100
    ):
        raise ValueError("Invalid scheduled HF discovery bounds")
    root = Path(root)
    active = root / "scheduled-active.json"
    with exclusive_file(root / "scheduled.run.lock", resource="Scheduled HF discovery"):
        state = HFWindow.model_validate_json(active.read_bytes()) if active.exists() else None
        if state and (state.lookback != lookback or state.limit != limit):
            raise ValueError("Frozen HF discovery configuration changed")
        if state and until < state.until:
            raise ValueError("Scheduled HF discovery cannot regress")
        if state is None or state.phase == "sampled":
            if state:
                _atomic_write(
                    root / "scheduled-runs" / f"{state.run_id}.json",
                    _encode(state.model_dump(mode="json")),
                )
                lower = state.until - timedelta(days=lookback - 1)
                upper = min(until, state.until + timedelta(days=lookback))
            else:
                upper = until
                lower = upper - timedelta(days=lookback - 1)
            state = HFWindow(
                run_id=uuid4().hex, since=lower, until=upper, lookback=lookback, limit=limit
            )
            _atomic_write(active, _encode(state.model_dump(mode="json")))
        # Validate every retained pointer before admitting any further request.
        for day, digest in state.responses.items():
            payload = frozen_response(root, day, digest, limit)
            observed = datetime.fromisoformat(payload["fetched_at"])
            if observed.utcoffset() is None or observed > now:
                raise ValueError("Invalid frozen HF observation time")
            parse_daily(payload["entries"])
        found = {}
        days = []
        failure = None
        for offset in range((state.until - state.since).days + 1):
            day = (state.until - timedelta(days=offset)).isoformat()
            digest = state.responses.get(day)
            resumed = bool(digest)
            if digest:
                payload = frozen_response(root, day, digest, limit)
            else:
                _, single = discover_daily(
                    client, root, until=date.fromisoformat(day), lookback=1, limit=limit, now=now
                )
                status = single["days"][0]["status"]
                if status not in ("fetched", "possibly_truncated"):
                    failure = {"day": day, "status": status}
                    break
                raw = (root / f"{day}-{limit}.json").read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                _atomic_write(root / "responses" / f"{day}.{digest}.json", raw)
                payload = frozen_response(root, day, digest, limit)
                state.responses[day] = digest
                _atomic_write(active, _encode(state.model_dump(mode="json")))
            observed = datetime.fromisoformat(payload["fetched_at"])
            if observed.utcoffset() is None or observed > now:
                raise ValueError("Invalid frozen HF observation time")
            entries = parse_daily(payload["entries"])
            for entry in entries:
                found.setdefault(entry.paper.id, entry)
            days.append(
                {
                    "day": day,
                    "status": "possibly_truncated" if len(entries) >= limit else "fetched",
                    "count": len(entries),
                    "response_sha256": digest,
                    "resumed_frozen": resumed,
                }
            )
        sampled = failure is None
        if sampled:
            state.phase = "sampled"
            _atomic_write(active, _encode(state.model_dump(mode="json")))
        return list(found.values()), {
            "run_id": state.run_id,
            "phase": state.phase,
            "since": state.since.isoformat(),
            "until": state.until.isoformat(),
            "requested_days": (state.until - state.since).days + 1,
            "days": days,
            "failure": failure,
            "unique_candidates": len(found),
            "discovery_limit": limit,
            "sampled": sampled,
            "complete": sampled and all(day["status"] == "fetched" for day in days),
            "requests": client.requests,
            "corpus_modified": False,
        }
