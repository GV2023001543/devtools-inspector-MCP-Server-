from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Category = Literal["console", "runtime", "network", "performance", "security", "accessibility"]
Severity = Literal["error", "warning", "info"]
Confidence = Literal["confirmed", "correlated", "potential", "suspicion"]
Verification = Literal["unverified", "passed", "failed", "not_applicable"]


class SourceLocation(BaseModel):
    url: str
    line: int | None = None
    column: int | None = None
    function: str | None = None


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    category: Category
    severity: Severity
    confidence: Confidence
    title: str
    explanation: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    url: str | None = None
    target_id: str | None = None
    source_location: SourceLocation | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    verification: Verification = "unverified"


def build_issue(
    *,
    category: Category,
    severity: Severity,
    confidence: Confidence,
    title: str,
    explanation: str,
    url: str | None = None,
    target_id: str | None = None,
    source_location: SourceLocation | None = None,
    evidence: dict[str, Any] | None = None,
) -> Issue:
    dedupe_key = "\0".join((category, title, url or "", target_id or ""))
    issue_id = sha256(dedupe_key.encode("utf-8", errors="replace")).hexdigest()[:16]
    return Issue(
        issue_id=issue_id,
        category=category,
        severity=severity,
        confidence=confidence,
        title=title[:240],
        explanation=explanation[:2000],
        url=url,
        target_id=target_id,
        source_location=source_location,
        evidence=evidence or {},
    )