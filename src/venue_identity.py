"""Source-bound CVF/arXiv identity and original-date resolution."""

import hashlib
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.contracts import FieldEvidence
from src.extractors.cvf import CVFPublication, publication_candidate
from src.identity import author_surnames, normalize_arxiv, title_key
from src.schema import PaperRecord
from src.storage import _encode


def metadata_digest(record):
    return hashlib.sha256(_encode(record.model_dump(mode="json"))).hexdigest()


class VenueIdentityReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    publication_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    arxiv_record_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def aware_review(self):
        if self.reviewed_at.utcoffset() is None:
            raise ValueError("Venue identity review requires aware time")
        return self


def resolve_publication(
    publication: CVFPublication,
    *,
    cvf_observed_at: datetime,
    arxiv: PaperRecord | None = None,
    arxiv_observed_at: datetime | None = None,
    review: VenueIdentityReview | None = None,
):
    candidate = publication_candidate(publication, observed_at=cvf_observed_at)
    audit = {
        "source_url": publication.source_url,
        "publication_sha256": metadata_digest(publication),
        "arxiv_id": publication.arxiv_id,
        "status": "publication_year_only",
    }
    if not publication.arxiv_id:
        return candidate, audit
    if arxiv is None or normalize_arxiv(arxiv.arxiv_id) != normalize_arxiv(publication.arxiv_id):
        return None, {
            **audit,
            "status": "review",
            "reason": "Exact arXiv identity source missing or contradictory",
        }
    if (
        arxiv_observed_at is None
        or arxiv_observed_at.utcoffset() is None
        or arxiv_observed_at > datetime.now(UTC)
    ):
        raise ValueError("Exact arXiv observation requires valid aware time")
    source_digest = metadata_digest(arxiv)
    title_match = title_key(publication.title) == title_key(arxiv.title)
    author_match = bool(author_surnames(publication.authors) & author_surnames(arxiv.authors))
    audit.update(
        arxiv_record_sha256=source_digest,
        title_exact_normalized=title_match,
        author_surname_agreement=author_match,
    )
    if review is not None:
        if (
            review.publication_sha256 != audit["publication_sha256"]
            or review.arxiv_record_sha256 != source_digest
        ):
            raise ValueError("Venue identity review source snapshots changed")
        if not max(cvf_observed_at, arxiv_observed_at) <= review.reviewed_at <= datetime.now(UTC):
            raise ValueError("Venue identity review time is invalid")
    if not (title_match and author_match) and review is None:
        return None, {
            **audit,
            "status": "review",
            "reason": "Title or author identity needs source-bound review",
        }
    if (
        arxiv.published_date_precision != "day"
        or int(arxiv.published_date[:4]) > publication.venue_year
    ):
        return None, {
            **audit,
            "status": "review",
            "reason": "Original date precision or chronology needs adjudication",
        }
    evidence = {key: list(values) for key, values in candidate.metadata_evidence.items()}
    for field, value in [("arxiv_id", arxiv.arxiv_id), ("published_date", arxiv.published_date)]:
        evidence.setdefault(field, []).append(
            FieldEvidence(
                source="arxiv_exact_lookup",
                source_url=f"https://arxiv.org/abs/{arxiv.arxiv_id}",
                value=value,
                observed_at=arxiv_observed_at,
                reviewed_by=review.reviewed_by if review else None,
                reviewed_at=review.reviewed_at if review else None,
            )
        )
    update = {
        field: getattr(arxiv, field)
        for field in (
            "published_date",
            "published_date_precision",
            "date_placement",
            "year",
            "month",
            "updated_date",
        )
    }
    if arxiv.arxiv_doi:
        update["arxiv_doi"] = arxiv.arxiv_doi
    update["metadata_evidence"] = evidence
    candidate = PaperRecord.model_validate(candidate.model_copy(update=update).model_dump())
    audit.update(
        status="original_date_verified",
        original_date=arxiv.published_date,
        publication_year=publication.venue_year,
        reviewed_identity=review.model_dump(mode="json") if review else None,
    )
    return candidate, audit
