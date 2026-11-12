"""Hash-bound CVF title or author adjudication; default metadata matching stays strict."""

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


class CaptureReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    schema_version: Literal["1.0.0"] = "1.0.0"
    source_url: str
    listing_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=1)
    evidence: list[FieldEvidence] = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime

    @model_validator(mode="after")
    def aware_review(self):
        if self.reviewed_at.utcoffset() is None:
            raise ValueError("Metadata adjudication requires aware review time")
        return self


class TitleReview(CaptureReview):
    listing_title: str = Field(min_length=3)
    approved_title: str = Field(min_length=3)

    @model_validator(mode="after")
    def actual_variant(self):
        if self.approved_title == self.listing_title:
            raise ValueError("Title adjudication requires an actual variant")
        return self


class AuthorReview(CaptureReview):
    listing_authors: list[str] = Field(min_length=1, max_length=200)
    approved_authors: list[str] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def actual_variant(self):
        if self.approved_authors == self.listing_authors or any(
            not name.strip() for name in self.listing_authors + self.approved_authors
        ):
            raise ValueError("Author adjudication requires nonempty names and an actual variant")
        return self


def parse_reviewed_capture(raw, listing, capture, listing_sha256):
    kinds = [key for key in ("title_review", "author_review") if key in capture]
    if not kinds:
        return parse_publication(raw.decode("utf-8"), listing)
    if len(kinds) != 1:
        raise ValueError("Combined title and author review requires a separate review contract")
    key = kinds[0]
    title_review = key == "title_review"
    model = TitleReview if title_review else AuthorReview
    review = model.model_validate(capture[key])
    observed = datetime.fromisoformat(capture["observed_at"])
    if observed.utcoffset() is None or observed > datetime.now(UTC):
        raise ValueError("Invalid reviewed source observation time")
    original_matches = (
        review.listing_title == listing.title
        if title_review
        else review.listing_authors == listing.authors
    )
    if (
        review.listing_sha256 != listing_sha256
        or review.source_url != listing.source_url
        or not original_matches
        or review.response_sha256 != capture["sha256"]
        or hashlib.sha256(raw).hexdigest() != review.response_sha256
    ):
        raise ValueError("Reviewed CVF metadata evidence differs from its frozen source")
    update = (
        {"title": review.approved_title} if title_review else {"authors": review.approved_authors}
    )
    publication = parse_publication(raw.decode("utf-8"), listing.model_copy(update=update))
    method = (
        "reviewed_title_variant_exact_authors_edition_pdf"
        if title_review
        else "reviewed_author_variant_exact_title_edition_pdf"
    )
    return publication.model_copy(update={"match_method": method})


def apply_title_review(root, review):
    return _apply_review(root, review, title_review=True)


def apply_author_review(root, review):
    return _apply_review(root, review, title_review=False)


def _apply_review(root, review, *, title_review):
    root = Path(root)
    key = "title_review" if title_review else "author_review"
    failure_reason = (
        "CVF listing/paper title mismatch" if title_review else "CVF author inventory mismatch"
    )
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
        original_matches = listing is not None and (
            listing.title == review.listing_title
            if title_review
            else listing.authors == review.listing_authors
        )
        if not original_matches:
            raise ValueError("Review does not identify the original listing row")
        existing = state["captures"].get(review.source_url)
        if existing:
            if existing.get(key) != review.model_dump(mode="json"):
                raise ValueError(
                    "Changing an existing metadata adjudication requires a new review epoch"
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
            if str(error) != failure_reason:
                raise ValueError("Metadata review cannot bypass another metadata failure") from None
        else:
            raise ValueError("Response already validates without title adjudication")
        capture = {
            "sha256": review.response_sha256,
            "observed_at": failure["attempted_at"],
            key: review.model_dump(mode="json"),
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
    parser.add_argument("--field", choices=["title", "authors"], default="title")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.review.stat().st_size > 200_000:
        raise ValueError("Oversized metadata review")
    if args.receipt.resolve() == args.review.resolve() or args.receipt.resolve().is_relative_to(
        args.cache.resolve()
    ):
        raise ValueError("Store review receipts outside the capture and review inputs")
    model, apply = (
        (TitleReview, apply_title_review)
        if args.field == "title"
        else (AuthorReview, apply_author_review)
    )
    result = apply(args.cache, model.model_validate_json(args.review.read_bytes()))
    _atomic_write(args.receipt, _encode(result))
    print(json.dumps({k: v for k, v in result.items() if k != "publication"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
