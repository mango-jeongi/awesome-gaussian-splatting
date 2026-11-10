"""Bind HF application to the exact prepared proposal and canonical snapshot."""

import hashlib
from datetime import datetime

from src.storage import _encode


def content_digest(db):
    return hashlib.sha256(_encode(db.model_dump(mode="json"))).hexdigest()


def apply_proposal(db, candidate, report, approved):
    for key in ("provider", "policy_digest", "source_candidates_sha256", "source_days"):
        if report.get(key) != approved.get(key) or key not in approved:
            raise ValueError("HF source/policy proposal changed; prepare and review again")
    current = content_digest(db)
    if current == approved["result_content_sha256"]:
        return db, False
    if current != approved["source_content_sha256"]:
        raise ValueError("HF canonical snapshot is stale")
    stamp = approved["result_last_updated"]
    if datetime.fromisoformat(stamp.replace("Z", "+00:00")).utcoffset() is None:
        raise ValueError("HF proposal result timestamp requires timezone")
    prepared = candidate.model_copy(deep=True)
    prepared.last_updated = stamp
    if content_digest(prepared) != approved["result_content_sha256"]:
        raise ValueError("HF proposed result changed; prepare and review again")
    return prepared, current != approved["result_content_sha256"]
