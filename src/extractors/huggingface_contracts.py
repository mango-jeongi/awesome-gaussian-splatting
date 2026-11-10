"""HF Daily Papers contract derived from a dated live response, not guessed links."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.identity import normalize_arxiv


class HFAuthor(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    name: str | None = None


class HFSpace(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    id: str = Field(pattern=r"^[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+$")

    @field_validator("id")
    @classmethod
    def valid_space(cls, value):
        if value.rsplit("/", 1)[-1] in (".", ".."):
            raise ValueError("Invalid linked Space identifier")
        return value


class HFPaper(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    id: str
    title: str
    summary: str | None = None
    ai_summary: str | None = None
    authors: list[HFAuthor] = Field(default_factory=list)
    linkedSpaces: list[HFSpace] | None = None
    numTotalSpaces: int | None = Field(default=None, ge=0)
    githubRepo: str | None = None
    githubStars: int | None = Field(default=None, ge=0)
    upvotes: int | None = Field(default=None, ge=0)
    projectPage: str | None = None
    publishedAt: str | None = None
    submittedOnDailyAt: str | None = None

    @field_validator("id")
    @classmethod
    def canonical_id(cls, value):
        import re

        normalized = normalize_arxiv(value)
        if not normalized or not re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})", normalized):
            raise ValueError("HF paper identity is not an arXiv identifier")
        return normalized

    @field_validator("publishedAt", "submittedOnDailyAt")
    @classmethod
    def valid_timestamp(cls, value):
        if (
            value is not None
            and datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is None
        ):
            raise ValueError("HF timestamp requires timezone")
        return value


class HFDailyEntry(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    paper: HFPaper
    publishedAt: str | None = None


def parse_daily(payload):
    if not isinstance(payload, list):
        raise ValueError("Expected HF daily list")
    records = [HFDailyEntry.model_validate(item) for item in payload]
    ids = [item.paper.id for item in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Repeated HF paper identity")
    return records
