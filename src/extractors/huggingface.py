"""Placeholder HuggingFace Daily Papers API extractor (Banked for Phase 2)."""

from __future__ import annotations

import os

from src.extractors.base import BaseExtractor
from src.schema import PaperRecord


class HuggingFaceExtractor(BaseExtractor):
    """Phase 2 adapter for https://huggingface.co/api/daily_papers.

    Currently skipped unless ENABLE_HUGGINGFACE=true is set in the environment.
    """

    API_URL = "https://huggingface.co/api/daily_papers"

    def __init__(self, enabled: bool | None = None) -> None:
        if enabled is None:
            enabled = os.getenv("ENABLE_HUGGINGFACE", "false").lower() in ("1", "true", "yes")
        self.enabled = enabled

    def fetch_recent(self, max_results: int = 50) -> list[PaperRecord]:
        if not self.enabled:
            return []
        # Banked Phase 2 implementation stub
        return []
