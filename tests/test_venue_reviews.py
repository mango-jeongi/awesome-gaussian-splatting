"""Source-bound manual title variants retain all other CVF identity checks."""

import hashlib
import json
from datetime import UTC, datetime

import httpx
import pytest

from src.venue_reviews import TitleReview, apply_title_review
from tests.test_venue_capture import LISTING, PAPER, run

APPROVED = "Gaussian Splatting & Revised Methods"


def failed_capture(root, body=None):
    raw = (
        body
        or PAPER.replace(
            "Gaussian Splatting &amp; Methods", "Gaussian Splatting &amp; Revised Methods"
        )
    ).encode()
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=raw))
    ) as client:
        report = run(root, client, max_requests=1)
    assert report["failed_records"] == 1
    state = json.loads((root / "state.json").read_bytes())
    url = next(iter(state["failures"]))
    return TitleReview(
        source_url=url,
        listing_sha256=hashlib.sha256(LISTING.encode()).hexdigest(),
        response_sha256=hashlib.sha256(raw).hexdigest(),
        listing_title="Gaussian Splatting & Methods",
        approved_title=APPROVED,
        reason="Fixture-only inspected title correction",
        evidence=[
            {"source": "fixture-primary-review", "value": "Same authors, edition and source PDF"}
        ],
        reviewed_by="fixture reviewer",
        reviewed_at=datetime.now(UTC),
    )


def test_reviewed_title_capture_replays_offline_without_rewriting_listing(tmp_path):
    review = failed_capture(tmp_path)
    result = apply_title_review(tmp_path, review)
    assert result["status"] == "applied" and result["network_requests"] == 0
    assert result["publication"]["match_method"].startswith("reviewed_title_variant")
    state = (tmp_path / "state.json").read_bytes()
    assert apply_title_review(tmp_path, review)["status"] == "no_op"
    assert (tmp_path / "state.json").read_bytes() == state
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("Unexpected network"))
    ) as client:
        replay = run(tmp_path, client, max_requests=0)
    assert replay["selected_metadata_complete"] and replay["verified_records"] == 1
    assert replay["reviewed_title_variant_records"] == 1
    assert replay["records"][0]["publication"]["title"] == APPROVED
    assert (tmp_path / f"listing.{review.listing_sha256}.html").read_bytes() == LISTING.encode()


@pytest.mark.parametrize(
    "field,value",
    [
        ("listing_sha256", "0" * 64),
        ("response_sha256", "0" * 64),
        ("approved_title", "Unrelated wrong title"),
    ],
)
def test_review_cannot_use_changed_sources_or_unmatched_title(tmp_path, field, value):
    review = failed_capture(tmp_path)
    before = (tmp_path / "state.json").read_bytes()
    with pytest.raises(ValueError):
        apply_title_review(tmp_path, review.model_copy(update={field: value}))
    assert (tmp_path / "state.json").read_bytes() == before
    assert not (tmp_path / "responses").exists()


@pytest.mark.parametrize(
    "replace", [("Example, Alice", "Different, Author"), ('content="2025"', 'content="2024"')]
)
def test_title_review_cannot_bypass_author_or_year_failure(tmp_path, replace):
    body = PAPER.replace(
        "Gaussian Splatting &amp; Methods", "Gaussian Splatting &amp; Revised Methods"
    ).replace(*replace)
    review = failed_capture(tmp_path, body)
    before = (tmp_path / "state.json").read_bytes()
    with pytest.raises(ValueError):
        apply_title_review(tmp_path, review)
    assert (tmp_path / "state.json").read_bytes() == before


def test_tampered_stored_review_fails_before_network(tmp_path):
    review = failed_capture(tmp_path)
    apply_title_review(tmp_path, review)
    path = tmp_path / "state.json"
    state = json.loads(path.read_bytes())
    state["captures"][review.source_url]["title_review"]["response_sha256"] = "0" * 64
    path.write_text(json.dumps(state), encoding="utf-8")
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("Unexpected network"))
    ) as client:
        with pytest.raises(ValueError, match="evidence differs"):
            run(tmp_path, client, max_requests=0)
