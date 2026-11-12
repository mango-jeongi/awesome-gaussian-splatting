"""Alternate CVF URLs require exact frozen identity and retained source provenance."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from src.extractors.cvf import parse_listing, parse_publication
from src.storage import _encode
from src.venue_reviews import URLReview, apply_url_review, parse_reviewed_capture
from tests.test_venue_capture import LISTING, PAPER, run

ALTERNATE = "https://openaccess.thecvf.com/content/CVPR2025/html/Fixed_Method_paper.html"


def candidate(root, replacement=None):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(404))) as client:
        run(root, client, max_requests=1)
    state = json.loads((root / "state.json").read_bytes())
    url, failure = next(iter(state["failures"].items()))
    body = PAPER.replace("Example_Method_paper.pdf", "Fixed_Method_paper.pdf")
    if replacement:
        body = body.replace(*replacement)
    raw = body.encode()
    digest = hashlib.sha256(raw).hexdigest()
    (root / "diagnostics").mkdir(exist_ok=True)
    (root / "diagnostics" / f"{digest}.html").write_bytes(raw)
    review = URLReview(
        source_url=url,
        listing_sha256=state["listing_sha256"],
        response_sha256=digest,
        original_failure_sha256=hashlib.sha256(_encode(failure)).hexdigest(),
        listing_title="Gaussian Splatting & Methods",
        listing_authors=["Alice Example"],
        approved_source_url=ALTERNATE,
        observed_at=datetime.now(UTC),
        response_bytes=len(raw),
        response_http_status=200,
        reason="Fixture-only inspected CVF URL correction",
        evidence=[{"source": "fixture-capture", "value": "Complete bounded HTTP-200 response"}],
        reviewed_by="fixture reviewer",
        reviewed_at=datetime.now(UTC),
    )
    return review, raw, failure


def test_url_review_preserves_failure_and_real_alternate_observation(tmp_path):
    review, raw, failure = candidate(tmp_path)
    listing = parse_listing(LISTING, venue="CVPR", year=2025)[0]
    with pytest.raises(ValueError, match="PDF does not match"):
        parse_publication(raw.decode(), listing)
    result = apply_url_review(tmp_path, review)
    assert result["status"] == "applied" and result["network_requests"] == 0
    assert result["publication"]["source_url"] == ALTERNATE
    assert (
        result["publication"]["match_method"]
        == "reviewed_source_url_exact_title_authors_edition_pdf"
    )
    before = (tmp_path / "state.json").read_bytes()
    capture = json.loads(before)["captures"][review.source_url]
    assert capture["original_failure"] == failure
    assert datetime.fromisoformat(capture["observed_at"]) == review.observed_at
    assert not json.loads(before)["failures"]
    assert apply_url_review(tmp_path, review)["status"] == "no_op"
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("Unexpected network"))
    ) as client:
        replay = run(tmp_path, client, max_requests=0)
    assert replay["reviewed_source_url_records"] == 1
    assert replay["selected_metadata_complete"]
    assert replay["records"][0]["publication"]["source_url"] == ALTERNATE
    assert (tmp_path / "state.json").read_bytes() == before
    assert (tmp_path / f"listing.{review.listing_sha256}.html").read_bytes() == LISTING.encode()


@pytest.mark.parametrize(
    "replacement",
    [
        ("Gaussian Splatting &amp; Methods", "Unrelated title"),
        ("Example, Alice", "Someone, Bob"),
        ('content="2025"', 'content="2024"'),
        ("Computer Vision and Pattern Recognition", "International Conference on Computer Vision"),
        ("Fixed_Method_paper.pdf", "Another_Method_paper.pdf"),
        ("/CVPR2025/papers/", "/CVPR2025W/papers/"),
    ],
)
def test_url_review_does_not_relax_any_identity_check(tmp_path, replacement):
    review, _, _ = candidate(tmp_path, replacement)
    before = (tmp_path / "state.json").read_bytes()
    with pytest.raises(ValueError):
        apply_url_review(tmp_path, review)
    assert (tmp_path / "state.json").read_bytes() == before
    assert not (tmp_path / "responses").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("listing_sha256", "0" * 64),
        ("response_sha256", "0" * 64),
        ("original_failure_sha256", "0" * 64),
        ("listing_title", "Different frozen title"),
        ("listing_authors", ["Different Author"]),
        ("response_bytes", 1),
    ],
)
def test_url_review_rejects_changed_bindings(tmp_path, field, value):
    review, _, _ = candidate(tmp_path)
    before = (tmp_path / "state.json").read_bytes()
    with pytest.raises((ValueError, FileNotFoundError)):
        apply_url_review(tmp_path, review.model_copy(update={field: value}))
    assert (tmp_path / "state.json").read_bytes() == before


@pytest.mark.parametrize(
    "value",
    [
        "https://evil.example/content/CVPR2025/html/Fixed_Method_paper.html",
        ALTERNATE.replace("https:", "http:"),
        ALTERNATE.replace("/CVPR2025/", "/CVPR2024/"),
        ALTERNATE.replace("/CVPR2025/", "/CVPR2025W/"),
        ALTERNATE + "?redirect=1",
        ALTERNATE + "#fragment",
        ALTERNATE.replace("openaccess.thecvf.com", "user@openaccess.thecvf.com"),
        ALTERNATE.replace("openaccess.thecvf.com", "openaccess.thecvf.com:443"),
        ALTERNATE.replace("Fixed_Method", "../Fixed_Method"),
        ALTERNATE.replace("Fixed_Method", "%2e%2e/Fixed_Method"),
    ],
)
def test_url_review_rejects_unsafe_or_cross_edition_urls(tmp_path, value):
    review, _, _ = candidate(tmp_path)
    with pytest.raises(ValueError):
        URLReview.model_validate({**review.model_dump(mode="json"), "approved_source_url": value})


def test_url_review_rejects_wrong_status_and_times(tmp_path):
    review, _, _ = candidate(tmp_path)
    for update in [
        {"response_http_status": 302},
        {"observed_at": datetime.now()},
        {"observed_at": datetime.now(UTC) + timedelta(days=1)},
        {"reviewed_at": datetime.now(UTC) + timedelta(days=1)},
        {"approved_source_url": review.source_url},
        {"response_bytes": 2_000_001},
    ]:
        with pytest.raises(ValueError):
            URLReview.model_validate({**review.model_dump(mode="json"), **update})


def test_url_review_replay_rejects_tampering_and_changed_decision(tmp_path):
    review, raw, _ = candidate(tmp_path)
    apply_url_review(tmp_path, review)
    before = (tmp_path / "state.json").read_bytes()
    with pytest.raises(ValueError, match="new review epoch"):
        apply_url_review(tmp_path, review.model_copy(update={"reason": "Changed review"}))
    listing = parse_listing(LISTING, venue="CVPR", year=2025)[0]
    capture = json.loads(before)["captures"][review.source_url]
    capture["original_failure"]["retry_at"] = "2000-01-01T00:00:00+00:00"
    with pytest.raises(ValueError, match="frozen source"):
        parse_reviewed_capture(raw, listing, capture, review.listing_sha256)
    capture["title_review"] = {}
    with pytest.raises(ValueError, match="Combined"):
        parse_reviewed_capture(raw, listing, capture, review.listing_sha256)
    assert (tmp_path / "state.json").read_bytes() == before


def test_url_review_requires_404_and_bounded_body(tmp_path):
    review, _, _ = candidate(tmp_path)
    state = json.loads((tmp_path / "state.json").read_bytes())
    state["failures"][review.source_url]["response_http_status"] = 503
    (tmp_path / "state.json").write_bytes(_encode(state))
    with pytest.raises(ValueError, match="HTTP-404"):
        apply_url_review(tmp_path, review)
    state["failures"][review.source_url]["response_http_status"] = 404
    (tmp_path / "state.json").write_bytes(_encode(state))
    (tmp_path / "diagnostics" / f"{review.response_sha256}.html").write_bytes(b"x" * 2_000_001)
    with pytest.raises(ValueError, match="Oversized"):
        apply_url_review(tmp_path, review)


def test_url_review_cli_applies_offline_and_writes_receipt(tmp_path, monkeypatch):
    from src.venue_reviews import main

    root = tmp_path / "capture"
    review, _, _ = candidate(root)
    review_path = tmp_path / "review.json"
    review_path.write_bytes(_encode(review.model_dump(mode="json")))
    receipt = tmp_path / "receipt.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "venue_reviews",
            "--field",
            "url",
            "--cache",
            str(root),
            "--review",
            str(review_path),
            "--receipt",
            str(receipt),
        ],
    )
    assert main() == 0
    result = json.loads(receipt.read_bytes())
    assert result["network_requests"] == 0
    assert result["approved_source_url"] == ALTERNATE


def test_url_review_rejects_alternate_already_in_frozen_listing(tmp_path):
    review, _, _ = candidate(tmp_path)
    extra = LISTING.replace("Example_Method_paper.html", "Fixed_Method_paper.html").replace(
        "Gaussian Splatting &amp; Methods", "Other Gaussian Splatting Methods"
    )
    raw = (LISTING + extra).encode()
    digest = hashlib.sha256(raw).hexdigest()
    state = json.loads((tmp_path / "state.json").read_bytes())
    state["listing_sha256"] = digest
    before = _encode(state)
    (tmp_path / "state.json").write_bytes(before)
    (tmp_path / f"listing.{digest}.html").write_bytes(raw)
    with pytest.raises(ValueError, match="another listing/capture"):
        apply_url_review(tmp_path, review.model_copy(update={"listing_sha256": digest}))
    assert (tmp_path / "state.json").read_bytes() == before


def test_url_review_rejects_alternate_already_used_by_another_capture(tmp_path):
    review, _, _ = candidate(tmp_path)
    state = json.loads((tmp_path / "state.json").read_bytes())
    state["captures"]["another-frozen-row"] = {"url_review": {"approved_source_url": ALTERNATE}}
    before = _encode(state)
    (tmp_path / "state.json").write_bytes(before)
    with pytest.raises(ValueError, match="another listing/capture"):
        apply_url_review(tmp_path, review)
    assert (tmp_path / "state.json").read_bytes() == before


def test_url_review_replay_rejects_body_or_listing_tampering(tmp_path):
    review, _, _ = candidate(tmp_path)
    apply_url_review(tmp_path, review)
    response = tmp_path / "responses" / f"{review.response_sha256}.html"
    raw = response.read_bytes()
    response.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="frozen source"):
        apply_url_review(tmp_path, review)
    response.write_bytes(raw)
    (tmp_path / f"listing.{review.listing_sha256}.html").write_bytes(LISTING.encode() + b" ")
    with pytest.raises(ValueError, match="listing hash"):
        apply_url_review(tmp_path, review)


def test_url_review_noop_refuses_a_combined_tampered_capture(tmp_path):
    review, _, _ = candidate(tmp_path)
    apply_url_review(tmp_path, review)
    state = json.loads((tmp_path / "state.json").read_bytes())
    state["captures"][review.source_url]["author_review"] = {}
    before = _encode(state)
    (tmp_path / "state.json").write_bytes(before)
    with pytest.raises(ValueError, match="Combined"):
        apply_url_review(tmp_path, review)
    assert (tmp_path / "state.json").read_bytes() == before
