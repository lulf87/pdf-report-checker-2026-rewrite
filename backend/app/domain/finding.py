from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.domain.common import Confidence, Evidence, Location, SourceType


class FindingSeverity(StrEnum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


Severity = FindingSeverity


class DiffFragmentKind(StrEnum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"


class DiffFragment(BaseModel):
    kind: DiffFragmentKind
    text: str
    source: str | None = None


class MissingEvidence(BaseModel):
    label: str
    reason: str
    expected_source: SourceType | None = None
    location: Location | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    id: str
    task_id: str
    check_id: str
    severity: FindingSeverity
    code: str
    message: str
    location: Location | None = None
    expected: Any | None = None
    actual: Any | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    missing_evidence: list[MissingEvidence] = Field(default_factory=list)
    diff_fragments: list[DiffFragment] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_trace_for_actionable_finding(self) -> "Finding":
        if self.severity in {FindingSeverity.ERROR, FindingSeverity.WARN}:
            if not self.evidence and not self.missing_evidence:
                raise ValueError("error and warn findings must include evidence or missing_evidence")
        return self


__all__ = [
    "Confidence",
    "DiffFragment",
    "DiffFragmentKind",
    "Finding",
    "FindingSeverity",
    "MissingEvidence",
    "Severity",
]
