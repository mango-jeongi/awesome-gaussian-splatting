"""Versioned, digest-bound envelopes for machine-readable run evidence."""

from hashlib import sha256
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from src.public import compact

Sha256 = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
EvidenceId = Annotated[str, StringConstraints(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")]
EvidenceKey = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
Job = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")]
TerminalStatus = Literal["succeeded", "failed"]


class RunReceipt(BaseModel):
    """Content identity for a terminal job's inputs, outputs and outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int = Field(ge=1, le=1)
    run_id: Sha256
    job: Job
    inputs: dict[EvidenceKey, EvidenceId] = Field(min_length=1)
    outputs: dict[EvidenceKey, EvidenceId] = Field(min_length=1)
    status: TerminalStatus

    @model_validator(mode="after")
    def check_run_id(self):
        body = self.model_dump(mode="json", exclude={"run_id"})
        if self.run_id != sha256(compact(body)).hexdigest():
            raise ValueError("Run receipt identity does not match its fields")
        return self


def run_receipt(
    job: str,
    *,
    inputs: dict[str, str],
    outputs: dict[str, str],
    status: TerminalStatus = "succeeded",
) -> dict:
    """Create a validated envelope from public digests or source commit IDs."""

    body = {"schema_version": 1, "job": job, "inputs": inputs, "outputs": outputs, "status": status}
    return RunReceipt(run_id=sha256(compact(body)).hexdigest(), **body).model_dump(mode="json")
