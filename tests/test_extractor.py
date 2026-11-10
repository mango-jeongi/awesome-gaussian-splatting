"""Unit tests for mocked arXiv Atom/XML feed parsing (zero external network calls)."""

from src.extractors.arxiv import ArxivExtractor

SAMPLE_ARXIV_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2308.04079v2</id>
    <updated>2023-08-09T12:00:00Z</updated>
    <published>2023-08-08T17:59:00Z</published>
    <title>3D Gaussian Splatting for Real-Time Radiance Field Rendering</title>
    <summary>We introduce three key elements that allow us to achieve state-of-the-art visual quality while maintaining competitive training times and real-time rendering.</summary>
    <author><name>Bernhard Kerbl</name></author>
    <author><name>Georgios Kopanas</name></author>
    <arxiv:comment>SIGGRAPH 2023. Project page: https://repo-sam.github.io/gsplat/ Code: https://github.com/graphdeco-inria/gaussian-splatting</arxiv:comment>
    <arxiv:primary_category term="cs.GR"/>
  </entry>
</feed>
"""


def test_parse_atom_xml() -> None:
    records = ArxivExtractor.parse_atom_xml(SAMPLE_ARXIV_ATOM_XML)
    assert len(records) == 1
    r = records[0]
    assert r.arxiv_id == "2308.04079"
    assert r.published_date == "2023-08-08"
    assert r.updated_date == "2023-08-09"
    assert r.authors == ["Bernhard Kerbl", "Georgios Kopanas"]
    assert r.primary_arxiv_category == "cs.GR"
    assert "SIGGRAPH 2023" in (r.comment or "")


def test_arxiv_dates_have_evidence_and_no_fallback():
    import pytest

    record = ArxivExtractor.parse_atom_xml(SAMPLE_ARXIV_ATOM_XML)[0]
    assert record.published_date_precision == "day"
    assert record.date_placement == "observed"
    assert record.arxiv_doi == "10.48550/arxiv.2308.04079"
    assert record.metadata_evidence["published_date"][0].value == record.published_date
    missing = SAMPLE_ARXIV_ATOM_XML.replace("<published>2023-08-08T17:59:00Z</published>", "")
    with pytest.raises(ValueError, match="lacks original"):
        ArxivExtractor.parse_atom_xml(missing)
    malformed = SAMPLE_ARXIV_ATOM_XML.replace("2023-08-08T17:59:00Z", "not-a-date")
    with pytest.raises(ValueError):
        ArxivExtractor.parse_atom_xml(malformed)
    error = SAMPLE_ARXIV_ATOM_XML.replace(
        "http://arxiv.org/abs/2308.04079v2", "http://arxiv.org/api/errors#bad_query"
    )
    with pytest.raises(ValueError, match="API error"):
        ArxivExtractor.parse_atom_xml(error)
