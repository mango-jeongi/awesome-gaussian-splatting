"""Tests for Markdown and artifact builder logic."""

from __future__ import annotations

from src.builder import generate_readme, gfm_slug
from src.schema import PaperDatabase, TaxonomyConfig


def test_gfm_slug_exact_github_anchors():
    """Verify that gfm_slug produces exact GFM heading anchors."""
    # Test cases with punctuation, whitespace, and symbols
    assert gfm_slug("Foundations & Acceleration") == "foundations--acceleration"
    assert gfm_slug("Dynamic & 4DGS") == "dynamic--4dgs"
    assert gfm_slug("Active Perception, SLAM & Robotics") == "active-perception-slam--robotics"
    assert gfm_slug("Human Avatars & VR") == "human-avatars--vr"
    assert (
        gfm_slug("Generative Priors & 3D Reconstruction") == "generative-priors--3d-reconstruction"
    )
    assert gfm_slug("Autonomous Driving & Urban Scenes") == "autonomous-driving--urban-scenes"
    assert (
        gfm_slug("Medical, Defense & Multimodal Sensors") == "medical-defense--multimodal-sensors"
    )
    assert gfm_slug("2D Gaussians, Geometry & Compression") == "2d-gaussians-geometry--compression"
    assert gfm_slug("Simple Title") == "simple-title"
    assert (
        gfm_slug("Title with (parentheses) and [brackets]!")
        == "title-with-parentheses-and-brackets"
    )


def test_readme_anchors_match_headings():
    """Verify that every category link in generate_readme matches its corresponding section heading."""
    tax = TaxonomyConfig.from_yaml("config/taxonomy.yaml")
    db = PaperDatabase.load("data/papers.json")
    readme = generate_readme(db, tax)

    for cat in tax.categories:
        expected_anchor = f"#{gfm_slug(cat.name)}"
        expected_heading = f"### {cat.name}"

        # 1. Heading must exist
        assert expected_heading in readme, f"Heading '{expected_heading}' missing in README"
        # 2. Table link must use the exact expected anchor
        assert f"[{cat.name}]({expected_anchor})" in readme, (
            f"Category link for '{cat.name}' does not use anchor '{expected_anchor}'"
        )


def test_no_frontier_superlative():
    """Verify that the 'frontier' superlative has been removed from README generated titles."""
    tax = TaxonomyConfig.from_yaml("config/taxonomy.yaml")
    db = PaperDatabase.load("data/papers.json")
    readme = generate_readme(db, tax)

    # First heading should not contain frontier
    first_line = readme.splitlines()[0]
    assert "frontier" not in first_line.lower()
    assert "Comprehensive Research Database" in first_line
