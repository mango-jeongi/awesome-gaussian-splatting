"""Explicit, hash-bound CVF title adjudication; default metadata matching stays strict."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.contracts import FieldEvidence
from src.extractors.cvf import parse_listing, parse_publication
from src.file_lock import exclusive_file
from src.storage import _atomic_write, _encode


class TitleReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    schema_version: Literal["1.0.0"] = "1.0.0"
    source_url: str
    listing_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    listing_title: str = Field(min_length=3)
    approved_title: str = Field(min_length=3)
    reason: str = Field(min_length=1)
    evidence: list[FieldEvidence] = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime

    @model_validator(mode="after")
    def reviewed(self):
        if self.reviewed_at.utcoffset() is None or self.approved_title == self.listing_title:
            raise ValueError("Title adjudication requires aware review time and an actual variant")
        return self


def parse_reviewed_capture(raw, listing, capture, listing_sha256):
    data = capture.get("title_review")
    if data is None:
        return parse_publication(raw.decode("utf-8"), listing)
    review = TitleReview.model_validate(data)
    observed = datetime.fromisoformat(capture["observed_at"])
    if observed.utcoffset() is None or observed > datetime.now(UTC):
        raise ValueError("Invalid reviewed source observation time")
    if (
        review.listing_sha256 != listing_sha256
        or review.source_url != listing.source_url
        or review.listing_title != listing.title
        or review.response_sha256 != capture["sha256"]
        or hashlib.sha256(raw).hexdigest() != review.response_sha256
    ):
        raise ValueError("Reviewed CVF title evidence differs from its frozen source")
    publication = parse_publication(
        raw.decode("utf-8"), listing.model_copy(update={"title": review.approved_title})
    )
    return publication.model_copy(
        update={"match_method": "reviewed_title_variant_exact_authors_edition_pdf"}
    )


def apply_title_review(root, review):
    root = Path(root)
    with exclusive_file(root / "capture.run.lock", resource="CVF metadata capture"):
        state_path = root / "state.json"
        state = json.loads(state_path.read_bytes())
        if state["listing_sha256"] != review.listing_sha256:
            raise ValueError("Review belongs to a different frozen listing")
        listing_raw = (root / f"listing.{review.listing_sha256}.html").read_bytes()
        if hashlib.sha256(listing_raw).hexdigest() != review.listing_sha256:
            raise ValueError("Frozen listing hash mismatch")
        rows = parse_listing(
            listing_raw.decode("utf-8"),
            venue=state["venue"],
            year=state["year"],
            track=state["track"],
        )
        listing = next((x for x in rows if x.source_url == review.source_url), None)
        if listing is None or listing.title != review.listing_title:
            raise ValueError("Review does not identify the original listing row")
        existing = state["captures"].get(review.source_url)
        if existing:
            if existing.get("title_review") != review.model_dump(mode="json"):
                raise ValueError(
                    "Changing an existing title adjudication requires a new review epoch"
                )
            raw = (root / "responses" / f"{review.response_sha256}.html").read_bytes()
            parse_reviewed_capture(raw, listing, existing, review.listing_sha256)
            return {"status": "no_op", "source_url": review.source_url, "network_requests": 0}
        failure = state["failures"].get(review.source_url, {})
        if (
            failure.get("response_sha256") != review.response_sha256
            or failure.get("response_http_status") != 200
        ):
            raise ValueError("Review must use a retained complete official HTTP-200 response")
        raw = (root / "diagnostics" / f"{review.response_sha256}.html").read_bytes()
        if len(raw) > 2_000_000 or len(raw) != failure["response_bytes"]:
            raise ValueError("Reviewed response exceeds or differs from its bounded capture")
        try:
            parse_publication(raw.decode("utf-8"), listing)
        except ValueError as error:
            if str(error) != "CVF listing/paper title mismatch":
                raise ValueError("Title review cannot bypass another metadata failure") from None
        else:
            raise ValueError("Response already validates without title adjudication")
        capture = {
            "sha256": review.response_sha256,
            "observed_at": failure["attempted_at"],
            "title_review": review.model_dump(mode="json"),
        }
        publication = parse_reviewed_capture(raw, listing, capture, review.listing_sha256)
        _atomic_write(root / "responses" / f"{review.response_sha256}.html", raw)
        state["captures"][review.source_url] = capture
        state["failures"].pop(review.source_url)
        _atomic_write(state_path, _encode(state))
        return {
            "status": "applied",
            "source_url": review.source_url,
            "network_requests": 0,
            "publication": publication.model_dump(mode="json"),
            "response_sha256": review.response_sha256,
            "listing_sha256": review.listing_sha256,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.review.stat().st_size > 200_000:
        raise ValueError("Oversized title review")
    if args.receipt.resolve() == args.review.resolve() or args.receipt.resolve().is_relative_to(
        args.cache.resolve()
    ):
        raise ValueError("Store review receipts outside the capture and review inputs")
    result = apply_title_review(
        args.cache, TitleReview.model_validate_json(args.review.read_bytes())
    )
    _atomic_write(args.receipt, _encode(result))
    print(json.dumps({k: v for k, v in result.items() if k != "publication"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
