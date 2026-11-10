"""Identity evidence, conflict handling, and stable alias regression tests."""

import pytest

from src.identity import (
    IdentityConflict,
    IdentityIndex,
    identifier_key,
    normalize_arxiv,
    normalize_doi,
)
from src.schema import PaperDatabase, PaperRecord
from src.storage import load_store, write_store


def record(**kwargs):
    return PaperRecord(
        title="A Gaussian Splatting Method", authors=["Jane Researcher"], year=2024, **kwargs
    )


def test_identifier_forms():
    assert normalize_doi("https://dx.doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalize_arxiv("https://arxiv.org/pdf/hep-th/9901001v3.pdf") == "hep-th/9901001"
    assert identifier_key("https://arxiv.org/abs/2401.12345v2") == "arxiv:2401.12345"
    assert identifier_key("https://openalex.org/W123/") == "openalex:W123"
    assert identifier_key("OPENALEX:w123") == "openalex:W123"


def test_stable_id_and_alias_survive_roundtrip(tmp_path):
    db = PaperDatabase()
    db.upsert([record(id="curated:stable")])
    db.upsert([record(arxiv_id="2401.12345", doi="https://doi.org/10.1000/ABC")])
    assert db.total_count == 1
    assert db.papers[0].id == "curated:stable"
    assert db.get("2401.12345v3").id == "curated:stable"
    assert db.get("10.1000/abc").id == "curated:stable"
    path = tmp_path / "manifest.json"
    write_store(db, path)
    restored = load_store(path)
    assert restored.aliases == db.aliases
    assert restored.get("https://arxiv.org/abs/2401.12345").id == "curated:stable"


def test_title_without_author_agreement_requires_review():
    db = PaperDatabase()
    db.upsert([record(id="original")])
    before = db.model_dump()
    other = PaperRecord(
        id="different", title=db.papers[0].title, authors=["Other Person"], year=2024
    )
    with pytest.raises(IdentityConflict, match="review"):
        db.upsert([other])
    assert db.model_dump() == before


def test_conflicting_identifiers_do_not_merge():
    db = PaperDatabase()
    db.upsert([record(arxiv_id="2401.12345", doi="10.1000/one")])
    before = db.model_dump()
    with pytest.raises(IdentityConflict, match="Contradictory"):
        db.upsert([record(arxiv_id="2401.12345", doi="10.1000/two")])
    assert db.model_dump() == before


def test_cross_record_identifier_conflict_and_batch_atomicity():
    first = record(arxiv_id="2401.12345")
    second = PaperRecord(title="Another unrelated method", doi="10.1000/two")
    db = PaperDatabase(papers=[first, second], total_count=2)
    before = db.model_dump()
    with pytest.raises(IdentityConflict, match="multiple"):
        db.upsert(
            [
                PaperRecord(title="Unrelated addition"),
                record(arxiv_id=first.arxiv_id, doi=second.doi),
            ]
        )
    assert db.model_dump() == before


def test_alias_collision_and_missing_target():
    first = record(id="one")
    second = PaperRecord(id="two", title="Second unrelated paper")
    with pytest.raises(IdentityConflict, match="collision"):
        IdentityIndex([first, second], {"one": "two"})
    with pytest.raises(IdentityConflict, match="missing"):
        IdentityIndex([first], {"old": "missing"})


def test_reingestion_preserves_observations_and_timestamp():
    original = record(arxiv_id="2401.12345", citation_count=17, referenced_works=["W123"])
    db = PaperDatabase()
    db.upsert([original])
    before = db.model_dump()
    db.upsert([record(arxiv_id="2401.12345")])
    assert db.model_dump() == before


def test_empty_snapshot(tmp_path):
    db = PaperDatabase()
    path = tmp_path / "nested" / "manifest.json"
    write_store(db, path)
    assert load_store(path).model_dump() == db.model_dump()


def test_abbreviated_seed_authors_do_not_agree_through_et_al():
    db = PaperDatabase()
    original = PaperRecord(
        id="seed:zhou", title="Same normalized title", authors=["Zhou et al."], year=2025
    )
    db.upsert([original])
    before = db.model_dump()
    with pytest.raises(IdentityConflict, match="review"):
        db.upsert(
            [PaperRecord(id="seed:li", title=original.title, authors=["Li et al."], year=2025)]
        )
    assert db.model_dump() == before


def test_abbreviated_author_matches_real_family_name_and_preserves_seed_id():
    db = PaperDatabase()
    db.upsert(
        [PaperRecord(id="seed:zhou", title="A source title", authors=["Zhou et al."], year=2025)]
    )
    db.upsert(
        [
            PaperRecord(
                arxiv_id="2501.12345",
                title="A source title",
                authors=["Jane Zhou", "Other Writer"],
                year=2025,
            )
        ]
    )
    assert db.total_count == 1 and db.get("2501.12345").id == "seed:zhou"


@pytest.mark.parametrize(
    "authors,expected",
    [
        (["Zhou et al."], {"zhou"}),
        (["Zhou ET. AL."], {"zhou"}),
        (["Smith, Jane", "J. Doe"], {"smith", "doe"}),
        (["Unknown", "Anonymous", "et al."], set()),
        (["José García", "García et al."], {"garcia"}),
        (
            ["ATLAS Collaboration", "Other Collaboration"],
            {"atlas collaboration", "other collaboration"},
        ),
    ],
)
def test_author_surname_evidence(authors, expected):
    from src.identity import author_surnames

    assert author_surnames(authors) == expected
