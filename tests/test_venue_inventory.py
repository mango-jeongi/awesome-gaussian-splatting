import pytest

from src.venue_inventory import reconcile_inventory


def html(title="Scene 360°", authors="Alice One ⋅ Bob Two"):
    return (
        f'<table class="elc-table"><tr><td><strong>{title}</strong>'
        f"<i>{authors}</i></td></tr></table>"
    ).encode()


def reconcile(raw, rows):
    return reconcile_inventory(
        raw, rows, source_url="https://example.org/accepted", listing_sha256="a" * 64
    )


def test_unicode_authors_are_split_and_typography_needs_full_sequence():
    result = reconcile(html(), [{"title": "Scene 360deg", "authors": ["Alice One", "Bob Two"]}])
    assert len(result["typography_pairs"]) == 1
    assert result["typography_pairs"][0]["accepted"]["authors"] == ["Alice One", "Bob Two"]
    assert not result["accepted_only"] and not result["cvf_only"]
    assert result["canonical_identity_modified"] is False
    assert result["inventory_reconciled"] is False


def test_typography_with_different_authors_remains_unresolved():
    result = reconcile(html(), [{"title": "Scene 360deg", "authors": ["Alice One", "Other Two"]}])
    assert not result["typography_pairs"]
    assert len(result["ambiguous_pairs"]) == 1
    assert len(result["accepted_only"]) == len(result["cvf_only"]) == 1


def test_exact_title_author_quality_differences_are_not_hidden():
    result = reconcile(
        html("Example paper", "Alice One · Bob Two"),
        [{"title": "Example paper", "authors": ["Alice One", "Bo Two"]}],
    )
    assert result["normalized_title_matches"] == 1
    assert len(result["exact_title_author_differences"]) == 1
    assert result["exact_title_author_differences"][0]["accepted"]["authors"] == [
        "Alice One",
        "Bob Two",
    ]


def test_missing_source_or_title_collision_fails_closed():
    with pytest.raises(ValueError, match="rows"):
        reconcile(b"<html>No accepted table</html>", [{"title": "A paper", "authors": []}])
    with pytest.raises(ValueError, match="collision"):
        reconcile(
            html("A paper"),
            [{"title": "A paper", "authors": []}, {"title": "A paper", "authors": []}],
        )


def test_missing_counterparts_are_reported_without_assuming_withdrawals():
    result = reconcile(
        html("Accepted-only paper"), [{"title": "Proceedings-only paper", "authors": []}]
    )
    assert len(result["accepted_only"]) == len(result["cvf_only"]) == 1
    assert not result["typography_pairs"]
