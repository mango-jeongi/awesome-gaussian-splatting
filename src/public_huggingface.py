"""Whitelist HF community observations into lazy details without changing bibliography."""

from pathlib import Path
from urllib.parse import urlsplit

from src.extractors.huggingface_contracts import HFSpace
from src.identity import normalize_arxiv
from src.observations import SignalStore


def safe_url(value, host=None):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return None
    try:
        url = urlsplit(value)
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            return None
        if host and url.hostname.casefold() != host:
            return None
        return value
    except ValueError:
        return None


def count(value):
    return value if type(value) is int and value >= 0 else None


def public_huggingface(db, source: Path):
    store = SignalStore.load(source / "huggingface.json", "huggingface")
    rows = {}
    for paper in db.papers:
        observation = store.observations.get(paper.id)
        if observation is None:
            continue
        usable = observation.fetched_at and observation.status not in {
            "unknown",
            "ambiguous",
            "not_found",
        }
        values = observation.values if usable else {}
        if usable and (
            not paper.arxiv_id
            or normalize_arxiv(observation.provider_id) != normalize_arxiv(paper.arxiv_id)
        ):
            raise ValueError("Public HF observation identity mismatch")
        source_url = (
            "https://huggingface.co/papers/" + normalize_arxiv(paper.arxiv_id)
            if paper.arxiv_id
            else None
        )
        result = {
            "status": observation.status,
            "fetched_at": observation.fetched_at.isoformat() if observation.fetched_at else None,
            "last_attempt_at": observation.last_attempt_at.isoformat()
            if observation.last_attempt_at
            else None,
            "source_url": source_url,
            "upvotes": count(values.get("upvotes")),
            "stars": count(values.get("stars")),
            "submitted_on_daily_at": values.get("submitted_on_daily_at"),
        }
        for field in ("provider_summary", "provider_ai_summary"):
            summary = values.get(field)
            result[field] = (
                {"text": summary["text"], "provider": "huggingface", "source_url": source_url}
                if isinstance(summary, dict)
                and summary.get("provider") == "huggingface"
                and isinstance(summary.get("text"), str)
                else None
            )
        repository = values.get("repository_evidence")
        result["repository_evidence"] = (
            {"url": url, "ownership": "unverified"}
            if isinstance(repository, dict)
            and (url := safe_url(repository.get("url"), "github.com"))
            else None
        )
        result["project_page_evidence"] = safe_url(values.get("project_page_evidence"))
        result["linked_spaces"] = None
        if isinstance(values.get("linked_spaces"), list):
            spaces = []
            for item in values["linked_spaces"]:
                space = HFSpace.model_validate({"id": item.get("id")})
                spaces.append({"id": space.id, "url": "https://huggingface.co/spaces/" + space.id})
            result["linked_spaces"] = spaces
        result["linked_spaces_total"] = count(values.get("linked_spaces_total"))
        result["linked_spaces_complete"] = (
            values.get("linked_spaces_complete")
            if type(values.get("linked_spaces_complete")) is bool
            else None
        )
        rows[paper.id] = result
    return rows
