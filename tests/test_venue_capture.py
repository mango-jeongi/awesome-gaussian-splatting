import json

import httpx
import pytest

from src.extractors.cvf import parse_listing, parse_publication, publication_candidate
from src.relevance import RelevancePolicy
from src.venue_capture import capture_cvf

LISTING = '<dt class="ptitle"><a href="/content/CVPR2025/html/Example_Method_paper.html">Gaussian Splatting &amp; Methods</a></dt><dd><input name="query_author" value="Alice Example"></dd>'
PAPER = '<meta name="citation_title" content="Gaussian Splatting &amp; Methods"><meta name="citation_author" content="Example, Alice"><meta name="citation_publication_date" content="2025"><meta name="citation_conference_title" content="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition"><meta name="citation_pdf_url" content="https://openaccess.thecvf.com/content/CVPR2025/papers/Example_Method_paper.pdf"><div id="abstract">We reconstruct <i>3D scenes</i> using Gaussian splatting.</div>'


def run(root, client, **kwargs):
    return capture_cvf(
        LISTING.encode(),
        root,
        venue="CVPR",
        year=2025,
        track="main",
        policy=RelevancePolicy(),
        client=client,
        **kwargs,
    )


def test_resume_replay_and_official_abstract_evidence(tmp_path):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=PAPER))
    ) as client:
        pending = run(tmp_path, client, max_requests=0)
        assert pending["pending_records"] == 1 and not pending["corpus_modified"]
        complete = run(tmp_path, client, max_requests=1)
        assert complete["verified_records"] == 1 and complete["selected_metadata_complete"]
        assert not complete["venue_inventory_reconciled"]
        replay = run(tmp_path, client, max_requests=0)
        assert replay["invocation_requests"] == 0 and replay["records"] == complete["records"]
    row = complete["records"][0]
    assert row["publication"]["abstract"] == "We reconstruct 3D scenes using Gaussian splatting."
    listing = parse_listing(LISTING, venue="CVPR", year=2025)[0]
    from datetime import datetime

    candidate = publication_candidate(
        parse_publication(PAPER, listing),
        observed_at=datetime.fromisoformat(row["capture"]["observed_at"]),
    )
    assert candidate.metadata_evidence["abstract"][0].source == "cvf_official_proceedings"
    assert candidate.published_date_precision == "year"


def test_tampered_capture_and_changed_listing_fail_before_network(tmp_path):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=PAPER))
    ) as client:
        report = run(tmp_path, client)
    sha = report["records"][0]["capture"]["sha256"]
    (tmp_path / "responses" / f"{sha}.html").write_text("changed", encoding="utf-8")
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("Unexpected network"))
    ) as client:
        with pytest.raises(ValueError, match="hash mismatch"):
            run(tmp_path, client)
        with pytest.raises(ValueError, match="listing/policy"):
            capture_cvf(
                (LISTING + " ").encode(),
                tmp_path,
                venue="CVPR",
                year=2025,
                track="main",
                policy=RelevancePolicy(),
                client=client,
            )


def test_rate_limit_persists_retry_and_skips_until_due(tmp_path):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(429, headers={"Retry-After": "7200"})
        )
    ) as client:
        report = run(tmp_path, client)
        assert report["failed_records"] == 1 and report["invocation_requests"] == 1
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("Unexpected retry"))
    ) as client:
        assert run(tmp_path, client)["invocation_requests"] == 0
    state = json.loads((tmp_path / "state.json").read_bytes())
    assert len(state["failures"]) == 1


@pytest.mark.parametrize(
    "fragment",
    ['<div id="abstract">unfinished', '<div id="abstract">A</div><div id="abstract">B</div>'],
)
def test_ambiguous_or_incomplete_author_abstract_is_rejected(fragment):
    listing = parse_listing(LISTING, venue="CVPR", year=2025)[0]
    metadata = PAPER.split('<div id="abstract">')[0]
    with pytest.raises(ValueError):
        parse_publication(metadata + fragment, listing)


def test_missing_abstract_is_not_fabricated():
    listing = parse_listing(LISTING, venue="CVPR", year=2025)[0]
    assert parse_publication(PAPER.split('<div id="abstract">')[0], listing).abstract is None


def test_pacing_between_successful_metadata_requests(tmp_path):
    now = [0.0]
    seen = []

    def handler(request):
        seen.append(now[0])
        body = (
            PAPER.replace("Example_Method", "Second_Method")
            if "Second_Method" in request.url.path
            else PAPER
        )
        return httpx.Response(200, text=body)

    listing = LISTING + LISTING.replace("Example_Method", "Second_Method")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = capture_cvf(
            listing.encode(),
            tmp_path,
            venue="CVPR",
            year=2025,
            track="main",
            policy=RelevancePolicy(),
            client=client,
            clock=lambda: now[0],
            sleep=lambda seconds: now.__setitem__(0, now[0] + seconds),
        )
    assert report["verified_records"] == 2 and seen == [0.0, 1.0]


def test_cli_zero_budget_writes_replayable_report_without_network(tmp_path, capsys):
    from src.cli import main

    listing = tmp_path / "listing.html"
    listing.write_text(LISTING, encoding="utf-8")
    report = tmp_path / "report.json"
    assert (
        main(
            [
                "discover-cvf",
                "--listing",
                str(listing),
                "--venue",
                "CVPR",
                "--year",
                "2025",
                "--cache",
                str(tmp_path / "capture"),
                "--max-requests",
                "0",
                "--report",
                str(report),
            ]
        )
        == 0
    )
    saved = json.loads(report.read_bytes())
    assert saved["pending_records"] == 1 and saved["invocation_requests"] == 0
    assert json.loads(capsys.readouterr().out)["corpus_modified"] is False


def test_all_metadata_can_review_gaussian_methods_with_opaque_titles(tmp_path):
    listing = LISTING.replace("Gaussian Splatting &amp; Methods", "Opaque Method")
    paper = PAPER.replace("Gaussian Splatting &amp; Methods", "Opaque Method")
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=paper))
    ) as client:
        before = capture_cvf(
            listing.encode(),
            tmp_path / "title",
            venue="CVPR",
            year=2025,
            track="main",
            policy=RelevancePolicy(),
            max_requests=0,
            client=client,
        )
        assert before["selected_records"] == 0
        after = capture_cvf(
            listing.encode(),
            tmp_path / "all",
            venue="CVPR",
            year=2025,
            track="main",
            policy=RelevancePolicy(),
            max_requests=1,
            all_metadata=True,
            client=client,
        )
    assert after["selection_mode"] == "all_metadata"
    assert after["selected_records"] == after["verified_records"] == 1
    assert after["records"][0]["metadata_outcome"] == "include"
    inventory = json.loads((tmp_path / "all/inventory.json").read_bytes())
    assert inventory["title_screening_only"] is True
    assert inventory["records"][0]["title_outcome"] == "exclude"


@pytest.mark.parametrize("first_mode", [False, True])
def test_selection_mode_cannot_change_in_an_existing_epoch(tmp_path, first_mode):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("Unexpected traffic"))
    ) as client:
        run(tmp_path, client, max_requests=0, all_metadata=first_mode)
        with pytest.raises(ValueError, match="selection mode|listing/policy"):
            run(tmp_path, client, max_requests=0, all_metadata=not first_mode)


def test_legacy_zero_request_inventory_still_fences_selection_mode(tmp_path):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("Unexpected traffic"))
    ) as client:
        run(tmp_path, client, max_requests=0)
        (tmp_path / "state.json").unlink()
        with pytest.raises(ValueError, match="selection mode"):
            run(tmp_path, client, max_requests=0, all_metadata=True)


@pytest.mark.parametrize("oversized", [False, True])
def test_invalid_response_diagnostics_are_bounded_and_not_verified(tmp_path, oversized):
    import hashlib

    raw = b"x" * 2_000_001 if oversized else b"<html>Missing citation metadata</html>"
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=raw))
    ) as client:
        report = run(tmp_path, client, max_requests=1)
    assert report["verified_records"] == 0 and report["failed_records"] == 1
    state = json.loads((tmp_path / "state.json").read_bytes())
    failure = next(iter(state["failures"].values()))
    assert failure["response_http_status"] == 200
    if oversized:
        assert "response_path" not in failure
        assert not (tmp_path / "diagnostics").exists()
    else:
        assert failure["response_bytes"] == len(raw)
        assert failure["response_sha256"] == hashlib.sha256(raw).hexdigest()
        assert (tmp_path / failure["response_path"]).read_bytes() == raw
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("Retry deadline bypassed"))
    ) as client:
        replay = run(tmp_path, client, max_requests=1)
    assert replay["invocation_requests"] == 0 and replay["verified_records"] == 0
