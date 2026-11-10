"""Evidence and date-precision contracts for canonical bibliographic metadata."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

DatePrecision = Literal["day", "month", "year", "unknown"]
DatePlacement = Literal["observed", "month_start", "year_start", "legacy_unknown"]


class FieldEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: str = Field(min_length=1)
    source_url: str | None = None
    value: JsonValue
    observed_at: datetime | None = None
    reviewed_by: str | None = Field(default=None, min_length=1)
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_evidence(self):
        for timestamp in (self.observed_at, self.reviewed_at):
            if timestamp is not None and timestamp.utcoffset() is None:
                raise ValueError("Evidence timestamps require a timezone")
        if bool(self.reviewed_by) != (self.reviewed_at is not None):
            raise ValueError("Review evidence requires both reviewer and review time")
        json.dumps(self.value, allow_nan=False)
        return self
