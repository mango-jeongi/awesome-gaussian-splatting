"""Genuine dated Semantic Scholar counts, separate from latest-value caches."""

from calendar import monthrange
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.storage import _atomic_write, _encode


class SemanticScholarSample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper_id: str = Field(min_length=1)
    provider_id: str = Field(pattern=r"^[a-fA-F0-9]{40}$")
    observed_at: datetime
    citation_count: int = Field(ge=0, strict=True)
    influential_citation_count: int | None = Field(default=None, ge=0, strict=True)

    @field_validator("provider_id")
    @classmethod
    def normalize_identity(cls, value):
        return value.lower()

    @field_validator("observed_at")
    @classmethod
    def aware_time(cls, value):
        if value.utcoffset() is None:
            raise ValueError("History samples require aware observation time")
        return value.astimezone(UTC)


class SemanticScholarHistory(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0.0"] = "1.0.0"
    provider: Literal["semanticscholar"] = "semanticscholar"
    samples: list[SemanticScholarSample] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_dates(self):
        keys = [(s.paper_id, s.observed_at.date()) for s in self.samples]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate daily Semantic Scholar samples")
        return self

    @classmethod
    def load(cls, path: Path):
        return cls.model_validate_json(path.read_bytes()) if path.exists() else cls()

    def save(self, path: Path):
        payload = _encode(self.model_dump(mode="json"))
        if not path.exists() or path.read_bytes() != payload:
            _atomic_write(path, payload)

    def provider_id_for(self, paper_id):
        relevant = [s for s in self.samples if s.paper_id == paper_id]
        return max(relevant, key=lambda s: s.observed_at).provider_id if relevant else None

    def record(self, sample: SemanticScholarSample):
        now = sample.observed_at
        if any(s.observed_at > now for s in self.samples):
            raise ValueError("Out-of-order history observation")
        identity = self.provider_id_for(sample.paper_id)
        if identity and identity != sample.provider_id:
            raise ValueError("History identity remap requires reviewed migration")
        month_index = now.year * 12 + now.month - 1 - 13
        year, month = divmod(month_index, 12)
        cutoff = now.replace(
            year=year, month=month + 1, day=min(now.day, monthrange(year, month + 1)[1])
        )
        self.samples = [s for s in self.samples if s.observed_at >= cutoff]
        if not any(
            s.paper_id == sample.paper_id and s.observed_at.date() == now.date()
            for s in self.samples
        ):
            self.samples.append(sample)
        self.samples.sort(key=lambda s: (s.paper_id, s.observed_at))


def history_path(cache_path: Path) -> Path:
    return cache_path.with_name(cache_path.stem + "-history.json")
