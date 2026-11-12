"""Hash-bound CVF title, author or source-URL adjudication; default metadata matching stays strict."""

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

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


class URLReview(CaptureReview):
    """An inspected alternate HTTP-200 page for a frozen listing URL returning 404."""

    listing_title: str = Field(min_length=3)
    listing_authors: list[str] = Field(min_length=1, max_length=200)
    approved_source_url: str
    original_failure_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    observed_at: datetime
    response_bytes: int = Field(ge=1, le=2_000_000, strict=True)
    response_http_status: Literal[200]

    @model_validator(mode="after")
    def bounded_official_alternate(self):
        original, alternate = urlparse(self.source_url), urlparse(self.approved_source_url)
        for url in (original, alternate):
            if (
                url.scheme != "https"
                or url.netloc != "openaccess.thecvf.com"
                or url.query
                or url.fragment
                or not re.fullmatch(
                    r"/content/(?:CVPR|ICCV)\d{4}W?/html/[A-Za-z0-9_-]+\.html", url.path
                )
            ):
                raise ValueError("URL review requires a plain official CVF paper-page URL")
        if (
            original.path.rsplit("/", 1)[0] != alternate.path.rsplit("/", 1)[0]
            or self.source_url == self.approved_source_url
        ):
            raise ValueError("URL review requires a distinct URL in the same edition/track")
        if (
            self.observed_at.utcoffset() is None
            or self.observed_at > self.reviewed_at
            or self.reviewed_at > datetime.now(UTC)
            or any(not name.strip() for name in self.listing_authors)
        ):
            raise ValueError("URL review requires valid source/review times and authors")
        return self


def _parse_url_review(raw, listing, capture, listing_sha256):
    if any(key in capture for key in ("title_review", "author_review")):
        raise ValueError("Combined metadata reviews require a separate review contract")
    review = URLReview.model_validate(capture["url_review"])
    if (
        review.listing_sha256 != listing_sha256
        or review.source_url != listing.source_url
        or review.listing_title != listing.title
        or review.listing_authors != listing.authors
        or review.response_sha256 != capture["sha256"]
        or hashlib.sha256(raw).hexdigest() != review.response_sha256
        or len(raw) != review.response_bytes
        or datetime.fromisoformat(capture["observed_at"]) != review.observed_at
        or capture.get("original_failure", {}).get("response_http_status") != 404
        or hashlib.sha256(_encode(capture.get("original_failure"))).hexdigest()
        != review.original_failure_sha256
    ):
        raise ValueError("Reviewed CVF URL evidence differs from its frozen source")
    publication = parse_publication(
        raw.decode("utf-8"), listing.model_copy(update={"source_url": review.approved_source_url})
    )
    return publication.model_copy(
        update={"match_method": "reviewed_source_url_exact_title_authors_edition_pdf"}
    )


def apply_url_review(root, review):
    """Promote a bounded retained alternate response offline; never retry the old URL."""
    review = URLReview.model_validate(review.model_dump(mode="json"))
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
        listing = next((row for row in rows if row.source_url == review.source_url), None)
        if listing is None:
            raise ValueError("Review does not identify the original listing row")
        if any(row.source_url == review.approved_source_url for row in rows) or any(
            url != review.source_url
            and capture.get("url_review", {}).get("approved_source_url")
            == review.approved_source_url
            for url, capture in state["captures"].items()
        ):
            raise ValueError("Alternate URL already belongs to another listing/capture row")
        existing = state["captures"].get(review.source_url)
        if existing:
            if existing.get("url_review") != review.model_dump(mode="json"):
                raise ValueError(
                    "Changing an existing URL adjudication requires a new review epoch"
                )
            raw = (root / "responses" / f"{review.response_sha256}.html").read_bytes()
            _parse_url_review(raw, listing, existing, review.listing_sha256)
            return {"status": "no_op", "source_url": review.source_url, "network_requests": 0}
        failure = state["failures"].get(review.source_url, {})
        if failure.get("response_http_status") != 404:
            raise ValueError("URL review requires a recorded HTTP-404 listing URL")
        path = root / "diagnostics" / f"{review.response_sha256}.html"
        if path.stat().st_size > 2_000_000:
            raise ValueError("Oversized alternate response")
        raw = path.read_bytes()
        capture = {
            "sha256": review.response_sha256,
            "observed_at": review.observed_at.isoformat(),
            "original_failure": failure,
            "url_review": review.model_dump(mode="json"),
        }
        publication = _parse_url_review(raw, listing, capture, review.listing_sha256)
        _atomic_write(root / "responses" / f"{review.response_sha256}.html", raw)
        state["captures"][review.source_url] = capture
        state["failures"].pop(review.source_url)
        _atomic_write(state_path, _encode(state))
        return {
            "status": "applied",
            "source_url": review.source_url,
            "approved_source_url": review.approved_source_url,
            "network_requests": 0,
            "publication": publication.model_dump(mode="json"),
            "original_failure_preserved": True,
        }


def parse_reviewed_capture(raw, listing, capture, listing_sha256):
    kinds = [key for key in ("title_review", "author_review", "url_review") if key in capture]
    if not kinds:
        return parse_publication(raw.decode("utf-8"), listing)
    if len(kinds) != 1:
        raise ValueError("Combined metadata reviews require a separate review contract")
    key = kinds[0]
    if key == "url_review":
        return _parse_url_review(raw, listing, capture, listing_sha256)
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
    parser.add_argument("--field", choices=["title", "authors", "url"], default="title")
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
    model, apply = {
        "title": (TitleReview, apply_title_review),
        "authors": (AuthorReview, apply_author_review),
        "url": (URLReview, apply_url_review),
    }[args.field]
    result = apply(args.cache, model.model_validate_json(args.review.read_bytes()))
    _atomic_write(args.receipt, _encode(result))
    print(json.dumps({k: v for k, v in result.items() if k != "publication"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
