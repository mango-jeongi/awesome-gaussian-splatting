"""Abstract base extractor interface for modular paper sources."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.schema import PaperRecord


class BaseExtractor(ABC):
    """Contract for all paper metadata ingestion adapters."""

    @abstractmethod
    def fetch_recent(self, max_results: int = 50) -> list[PaperRecord]:
        """Fetch recent papers from the upstream source and return validated PaperRecords."""
        raise NotImplementedError
