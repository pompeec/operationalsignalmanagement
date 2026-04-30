"""Data models for signal/noise classification."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Classification(str, Enum):
    SIGNAL = "signal"
    NOISE = "noise"


class SignalCategory(str, Enum):
    BLOCKER = "blocker"
    RISK = "risk"
    DECISION_NEEDED = "decision_needed"
    ESCALATION = "escalation"
    DEPENDENCY_ISSUE = "dependency_issue"
    SCOPE_CHANGE = "scope_change"
    MILESTONE_CONCERN = "milestone_concern"
    RESOURCE_ISSUE = "resource_issue"


class NoiseCategory(str, Enum):
    ROUTINE_UPDATE = "routine_update"
    ADMINISTRATIVE = "administrative"
    DUPLICATE_INFO = "duplicate_info"
    LOW_PRIORITY = "low_priority"
    INFORMATIONAL = "informational"


SIGNAL_CATEGORY_LABELS: dict[SignalCategory, str] = {
    SignalCategory.BLOCKER: "Blocker",
    SignalCategory.RISK: "Risk",
    SignalCategory.DECISION_NEEDED: "Decision Needed",
    SignalCategory.ESCALATION: "Escalation",
    SignalCategory.DEPENDENCY_ISSUE: "Dependency Issue",
    SignalCategory.SCOPE_CHANGE: "Scope Change",
    SignalCategory.MILESTONE_CONCERN: "Milestone Concern",
    SignalCategory.RESOURCE_ISSUE: "Resource Issue",
}

NOISE_CATEGORY_LABELS: dict[NoiseCategory, str] = {
    NoiseCategory.ROUTINE_UPDATE: "Routine Update",
    NoiseCategory.ADMINISTRATIVE: "Administrative",
    NoiseCategory.DUPLICATE_INFO: "Duplicate Info",
    NoiseCategory.LOW_PRIORITY: "Low Priority",
    NoiseCategory.INFORMATIONAL: "Informational",
}


class InputItem(BaseModel):
    """A raw item to be analyzed."""

    id: str
    text: str
    source: Optional[str] = None
    author: Optional[str] = None
    timestamp: Optional[str] = None
    context: Optional[str] = None


class AnalyzedItem(BaseModel):
    """An item after signal/noise classification."""

    id: str
    original_text: str
    source: Optional[str] = None
    author: Optional[str] = None

    classification: Classification
    signal_category: Optional[SignalCategory] = None
    noise_category: Optional[NoiseCategory] = None

    priority: int = Field(ge=1, le=10, description="1 = lowest, 10 = most critical")
    confidence: float = Field(ge=0.0, le=1.0)

    summary: str
    recommended_action: Optional[str] = None
    tags: list[str] = []

    analyzed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def is_signal(self) -> bool:
        return self.classification == Classification.SIGNAL

    @property
    def category_label(self) -> str:
        if self.signal_category:
            return SIGNAL_CATEGORY_LABELS.get(self.signal_category, self.signal_category.value)
        if self.noise_category:
            return NOISE_CATEGORY_LABELS.get(self.noise_category, self.noise_category.value)
        return "Unknown"


class AnalysisReport(BaseModel):
    """Full analysis report for a batch of items."""

    analyzed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_items: int
    signals: list[AnalyzedItem]
    noise: list[AnalyzedItem]
    executive_summary: str
    top_actions: list[str]

    @property
    def critical_signals(self) -> list[AnalyzedItem]:
        return sorted(
            [s for s in self.signals if s.priority >= 8],
            key=lambda x: x.priority,
            reverse=True,
        )

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def noise_count(self) -> int:
        return len(self.noise)

    @property
    def signal_ratio(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.signal_count / self.total_items
