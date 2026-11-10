import pytest

from src.huggingface_import import apply_proposal, content_digest
from src.schema import PaperDatabase, PaperRecord


def fixture():
    db = PaperDatabase(papers=[PaperRecord(id="p", title="Fixture method")], total_count=1)
    candidate = db.model_copy(deep=True)
    candidate.papers[0].title = "Updated fixture method"
    candidate.last_updated = "2026-11-09T00:00:00Z"
    approved = {
        "provider": "huggingface",
        "policy_digest": "policy",
        "source_candidates_sha256": "source",
        "source_days": ["2026-11-09"],
        "source_content_sha256": content_digest(db),
        "result_content_sha256": content_digest(candidate),
        "result_last_updated": candidate.last_updated,
    }
    return db, candidate, approved


def test_exact_application_and_idempotent_replay():
    db, candidate, approved = fixture()
    prepared, changed = apply_proposal(db, candidate, approved, approved)
    assert changed and prepared.papers[0].title == "Updated fixture method"
    assert db.papers[0].title == "Fixture method"
    assert apply_proposal(prepared, candidate, approved, approved)[1] is False


@pytest.mark.parametrize("change", ["source", "policy", "corpus", "result"])
def test_changed_proposal_fails_closed(change):
    db, candidate, approved = fixture()
    report = dict(approved)
    if change == "source":
        report["source_candidates_sha256"] = "changed"
    elif change == "policy":
        report["policy_digest"] = "changed"
    elif change == "corpus":
        db.papers[0].title = "Concurrent update"
    else:
        candidate.papers[0].title = "Unexpected proposal"
    with pytest.raises(ValueError):
        apply_proposal(db, candidate, report, approved)
