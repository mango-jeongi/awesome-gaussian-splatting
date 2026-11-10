"""HF discovery adapter; provider summaries are not author abstracts."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from src.contracts import FieldEvidence
from src.extractors.base import BaseExtractor
from src.extractors.huggingface_client import HFPapersClient
from src.huggingface_discovery import discover_daily
from src.relevance import RelevancePolicy
from src.schema import PaperRecord
from src.storage import _atomic_write, _encode


def candidate_record(entry, *, observed_at=None):
    paper = entry.paper
    if not paper.publishedAt:
        raise ValueError("HF candidate needs source publication date verification")
    published = datetime.fromisoformat(paper.publishedAt.replace("Z", "+00:00")).date().isoformat()
    return PaperRecord(
        id=paper.id,
        arxiv_id=paper.id,
        source="huggingface",
        title=paper.title,
        authors=[author.name for author in paper.authors if author.name and author.name.strip()]
        or ["Unknown"],
        published_date=published,
        published_date_precision="day",
        date_placement="observed",
        paper_url="https://arxiv.org/abs/" + paper.id,
        pdf_url="https://arxiv.org/pdf/" + paper.id + ".pdf",
        metadata_evidence={
            "published_date": [
                FieldEvidence(
                    source="huggingface",
                    source_url="https://huggingface.co/papers/" + paper.id,
                    value=published,
                    observed_at=observed_at,
                )
            ]
        },
    )


class HuggingFaceExtractor(BaseExtractor):
    def __init__(self, enabled=None, *, cache_dir=None):
        self.enabled = (
            os.getenv("ENABLE_HUGGINGFACE", "false").lower() in ("1", "true", "yes")
            if enabled is None
            else enabled
        )
        self.root = Path(__file__).resolve().parents[2]
        self.cache_dir = Path(cache_dir) if cache_dir else self.root / "data/ingestion/huggingface"

    def fetch_recent(self, max_results=50):
        if not self.enabled:
            return []
        with HFPapersClient(max_requests=7) as client:
            entries, report = discover_daily(
                client, self.cache_dir, until=datetime.now(UTC).date(), limit=max_results
            )
        policy = RelevancePolicy.load(self.root / "config/overrides.yaml")
        included = []
        dispositions = []
        for entry in entries:
            try:
                record = candidate_record(entry)
                decision = policy.decide(record)
                if decision.outcome == "include":
                    included.append(record)
                dispositions.append(
                    {"id": entry.paper.id, "outcome": decision.outcome, "reason": decision.reason}
                )
            except ValueError:
                dispositions.append(
                    {
                        "id": entry.paper.id,
                        "outcome": "review",
                        "reason": "Source publication date requires verification",
                    }
                )
        _atomic_write(
            self.cache_dir / "latest-report.json",
            _encode(
                {
                    **report,
                    "discovery_limit": max_results,
                    "dispositions": dispositions,
                    "policy_digest": policy.digest,
                    "corpus_modified": False,
                }
            ),
        )
        return included
