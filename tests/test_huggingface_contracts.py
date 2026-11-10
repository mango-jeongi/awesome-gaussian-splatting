import pytest

from src.extractors.huggingface_contracts import parse_daily


def test_nested_optional_zero_and_summary_attribution():
    entries = parse_daily(
        [
            {
                "paper": {
                    "id": "2308.04079v2",
                    "title": "Fixture",
                    "summary": "Provider text",
                    "upvotes": 0,
                }
            }
        ]
    )
    paper = entries[0].paper
    assert paper.id == "2308.04079" and paper.upvotes == 0
    assert paper.githubStars is None and paper.githubRepo is None
    assert paper.summary == "Provider text" and not hasattr(paper, "abstract")


@pytest.mark.parametrize(
    "payload",
    [
        [{"title": "Missing paper"}],
        [{"paper": {"id": "bad", "title": "Fixture"}}],
        [{"paper": {"id": "2308.04079", "title": "Fixture", "upvotes": True}}],
    ],
)
def test_invalid_contracts_fail_closed(payload):
    with pytest.raises(ValueError):
        parse_daily(payload)


def test_author_order_linked_spaces_and_ai_text_are_evidence():
    from src.extractors.huggingface import candidate_record

    entries = parse_daily(
        [
            {
                "paper": {
                    "id": "2308.04079",
                    "title": "Fixture method",
                    "publishedAt": "2023-08-08T00:00:00Z",
                    "authors": [{"name": "First Author"}, {"name": "Second Author"}],
                    "ai_summary": "Provider AI text",
                    "linkedSpaces": [{"id": "owner/linked-space"}],
                    "numTotalSpaces": 2,
                }
            }
        ]
    )
    record = candidate_record(entries[0])
    assert record.authors == ["First Author", "Second Author"] and record.abstract == ""
    assert entries[0].paper.linkedSpaces[0].id == "owner/linked-space"
    assert entries[0].paper.numTotalSpaces == 2


def test_candidate_retains_actual_source_observation_time():
    from datetime import UTC, datetime

    from src.extractors.huggingface import candidate_record

    entry = parse_daily(
        [
            {
                "paper": {
                    "id": "2308.04079",
                    "title": "Fixture method",
                    "publishedAt": "2023-08-08T00:00:00Z",
                }
            }
        ]
    )[0]
    observed = datetime(2026, 11, 9, tzinfo=UTC)
    record = candidate_record(entry, observed_at=observed)
    assert record.metadata_evidence["published_date"][0].observed_at == observed
    assert record.published_date == "2023-08-08"
