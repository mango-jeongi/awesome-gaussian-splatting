"""Explicit author corrections never relax title, edition, PDF or source checks."""

import hashlib
import json
from datetime import UTC, datetime

import httpx
import pytest

from src.venue_reviews import AuthorReview, apply_author_review
from tests.test_venue_capture import LISTING, PAPER, run


def failed_author_capture(root, replacement=None):
    body = PAPER.replace("Example, Alice", "Correct, Alice")
    if replacement:
        body = body.replace(*replacement)
    raw = body.encode()
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=raw))
    ) as client:
        report = run(root, client, max_requests=1)
    assert report["failed_records"] == 1
    state = json.loads((root / "state.json").read_bytes())
    url = next(iter(state["failures"]))
    return AuthorReview(
        source_url=url,
        listing_sha256=hashlib.sha256(LISTING.encode()).hexdigest(),
        response_sha256=hashlib.sha256(raw).hexdigest(),
        listing_authors=["Alice Example"],
        approved_authors=["Alice Correct"],
        reason="Fixture-only source-inspected author spelling correction",
        evidence=[{"source": "fixture-primary-review", "value": "Corrected author spelling"}],
        reviewed_by="fixture reviewer",
        reviewed_at=datetime.now(UTC),
    )


def test_author_review_replay_preserves_source_and_real_capture_time(tmp_path):
    review = failed_author_capture(tmp_path)
    before = json.loads((tmp_path / "state.json").read_bytes())
    observed = before["failures"][review.source_url]["attempted_at"]
    result = apply_author_review(tmp_path, review)
    assert result["status"] == "applied" and result["network_requests"] == 0
    assert result["publication"]["authors"] == ["Alice Correct"]
    assert (
        result["publication"]["match_method"] == "reviewed_author_variant_exact_title_edition_pdf"
    )
    state = (tmp_path / "state.json").read_bytes()
    assert json.loads(state)["captures"][review.source_url]["observed_at"] == observed
    assert apply_author_review(tmp_path, review)["status"] == "no_op"
    assert (tmp_path / "state.json").read_bytes() == state
    assert (tmp_path / f"listing.{review.listing_sha256}.html").read_bytes() == LISTING.encode()
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("Unexpected network"))
    ) as client:
        replay = run(tmp_path, client, max_requests=0)
    assert replay["selected_metadata_complete"]
    assert replay["reviewed_author_variant_records"] == 1
    assert replay["reviewed_title_variant_records"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("listing_sha256", "0" * 64),
        ("response_sha256", "0" * 64),
        ("listing_authors", ["Different original author"]),
        ("approved_authors", ["Wrong approved author"]),
    ],
)
def test_author_review_refuses_changed_sources_or_unmatched_names(tmp_path, field, value):
    review = failed_author_capture(tmp_path)
    before = (tmp_path / "state.json").read_bytes()
    with pytest.raises(ValueError):
        apply_author_review(tmp_path, review.model_copy(update={field: value}))
    assert (tmp_path / "state.json").read_bytes() == before
    assert not (tmp_path / "responses").exists()


@pytest.mark.parametrize(
    "replacement",
    [
        ("Gaussian Splatting &amp; Methods", "Different paper title"),
        ('content="2025"', 'content="2024"'),
        ("Computer Vision and Pattern Recognition", "International Conference on Computer Vision"),
        ("Example_Method_paper.pdf", "Different_Method_paper.pdf"),
    ],
)
def test_author_review_cannot_bypass_other_metadata_failures(tmp_path, replacement):
    review = failed_author_capture(tmp_path, replacement)
    before = (tmp_path / "state.json").read_bytes()
    with pytest.raises(ValueError):
        apply_author_review(tmp_path, review)
    assert (tmp_path / "state.json").read_bytes() == before


@pytest.mark.parametrize("combined", [False, True])
def test_tampered_or_combined_stored_reviews_fail_before_network(tmp_path, combined):
    review = failed_author_capture(tmp_path)
    apply_author_review(tmp_path, review)
    path = tmp_path / "state.json"
    state = json.loads(path.read_bytes())
    capture = state["captures"][review.source_url]
    if combined:
        capture["title_review"] = {}
    else:
        capture["author_review"]["response_sha256"] = "0" * 64
    path.write_text(json.dumps(state), encoding="utf-8")
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("Unexpected network"))
    ) as client:
        with pytest.raises(ValueError):
            run(tmp_path, client, max_requests=0)
