"""Claude API-powered signal/noise analyzer with prompt caching and structured tool use."""

from __future__ import annotations

import json
import uuid
from typing import Any

import anthropic

from .models import (
    AnalysisReport,
    AnalyzedItem,
    Classification,
    InputItem,
    NoiseCategory,
    SignalCategory,
)

MODEL = "claude-sonnet-4-6"

# System prompt cached at the API level for cost efficiency across batch calls
_SYSTEM_PROMPT = """You are an expert program manager and operational intelligence analyst embedded in a fast-moving engineering organization. Your sole job is to distinguish **signal** from **noise** in the stream of updates, messages, tickets, and status reports that program managers (PgMs) and product managers (PMs) receive every day.

## Definitions

### SIGNAL — requires attention, decision, or action
| Category | Examples |
|---|---|
| `blocker` | CI is broken and blocking the release train; an engineer is waiting on a legal review |
| `risk` | A key engineer is on PTO during crunch week; third-party API rate limits may be hit |
| `decision_needed` | Two teams disagree on the API contract; feature flag strategy unresolved |
| `escalation` | Customer escalating SLA breach; executive asking for status on incident |
| `dependency_issue` | Upstream team slipped; shared library not ready for integration |
| `scope_change` | Engineering added a new sub-system without PM sign-off; requirements quietly changed |
| `milestone_concern` | Sprint velocity suggests milestone is at risk; QA backlog growing |
| `resource_issue` | Team 20% under capacity for Q3; budget approval still pending |

### NOISE — does not require immediate attention
| Category | Examples |
|---|---|
| `routine_update` | Weekly status "everything on track", daily standup with no impediments |
| `administrative` | Meeting rescheduled, calendar invite, room booking |
| `duplicate_info` | Same incident already captured in the tracker |
| `low_priority` | Minor technical debt note, cosmetic UI feedback for a future sprint |
| `informational` | FYI announcement, release note for an unrelated service |

## Priority Scale (1–10)
- **9–10** Critical: Active blockers or escalations threatening the current sprint or release
- **7–8** High: Risks or decisions that could become blockers within days
- **5–6** Medium: Issues requiring a response this week
- **3–4** Low: Items to monitor or schedule for the next planning cycle
- **1–2** Very Low: Noise with negligible PM impact

## Your Output
Always call the `classify_item` tool with structured output. Be concise and specific. Recommended actions must be actionable (verb + object + timeframe).
"""

# Tool definition for structured classification output
_CLASSIFY_TOOL: dict[str, Any] = {
    "name": "classify_item",
    "description": "Classify one program-management item as signal or noise and return structured metadata.",
    "input_schema": {
        "type": "object",
        "properties": {
            "classification": {
                "type": "string",
                "enum": ["signal", "noise"],
            },
            "signal_category": {
                "type": "string",
                "enum": [
                    "blocker",
                    "risk",
                    "decision_needed",
                    "escalation",
                    "dependency_issue",
                    "scope_change",
                    "milestone_concern",
                    "resource_issue",
                ],
                "description": "Required when classification is 'signal'.",
            },
            "noise_category": {
                "type": "string",
                "enum": [
                    "routine_update",
                    "administrative",
                    "duplicate_info",
                    "low_priority",
                    "informational",
                ],
                "description": "Required when classification is 'noise'.",
            },
            "priority": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "How confident you are in the classification (0–1).",
            },
            "summary": {
                "type": "string",
                "description": "One crisp sentence describing this item.",
            },
            "recommended_action": {
                "type": "string",
                "description": "Specific, time-bound action for the PM (signals only).",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Relevant labels, e.g. 'engineering', 'customer', 'deadline', 'Q3'.",
            },
        },
        "required": ["classification", "priority", "confidence", "summary", "tags"],
    },
}

# Digest synthesis tool
_DIGEST_TOOL: dict[str, Any] = {
    "name": "build_digest",
    "description": "Synthesize a PM executive digest from a list of pre-classified items.",
    "input_schema": {
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": "3–5 sentence executive summary of what the PM needs to know right now.",
            },
            "top_actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of the 3–5 most important actions for the PM to take today.",
            },
        },
        "required": ["executive_summary", "top_actions"],
    },
}


class SignalAnalyzer:
    """Analyzes program-management items using Claude with prompt caching and tool use."""

    def __init__(self, api_key: str | None = None) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    def analyze_item(self, item: InputItem) -> AnalyzedItem:
        """Classify a single item as signal or noise."""
        user_content = self._build_user_message(item)

        response = self._client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[_CLASSIFY_TOOL],
            tool_choice={"type": "tool", "name": "classify_item"},
            messages=[{"role": "user", "content": user_content}],
        )

        tool_input = self._extract_tool_input(response)
        return self._build_analyzed_item(item, tool_input)

    def analyze_batch(self, items: list[InputItem]) -> AnalysisReport:
        """Classify a batch of items and produce a full analysis report."""
        analyzed: list[AnalyzedItem] = []
        for item in items:
            analyzed.append(self.analyze_item(item))

        signals = sorted(
            [a for a in analyzed if a.is_signal],
            key=lambda x: x.priority,
            reverse=True,
        )
        noise = [a for a in analyzed if not a.is_signal]

        executive_summary, top_actions = self._build_digest(signals)

        return AnalysisReport(
            total_items=len(analyzed),
            signals=signals,
            noise=noise,
            executive_summary=executive_summary,
            top_actions=top_actions,
        )

    def analyze_text(self, text: str, source: str | None = None) -> AnalyzedItem:
        """Convenience wrapper to analyze a raw string."""
        item = InputItem(id=str(uuid.uuid4())[:8], text=text, source=source)
        return self.analyze_item(item)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_user_message(self, item: InputItem) -> str:
        parts = [f"**Item ID:** {item.id}"]
        if item.source:
            parts.append(f"**Source:** {item.source}")
        if item.author:
            parts.append(f"**Author:** {item.author}")
        if item.timestamp:
            parts.append(f"**Timestamp:** {item.timestamp}")
        if item.context:
            parts.append(f"**Context:** {item.context}")
        parts.append(f"\n**Content:**\n{item.text}")
        return "\n".join(parts)

    def _extract_tool_input(self, response: anthropic.types.Message) -> dict[str, Any]:
        for block in response.content:
            if block.type == "tool_use":
                return block.input  # type: ignore[return-value]
        raise ValueError("No tool_use block in response")

    def _build_analyzed_item(self, item: InputItem, tool_input: dict[str, Any]) -> AnalyzedItem:
        classification = Classification(tool_input["classification"])
        signal_cat_raw = tool_input.get("signal_category")
        noise_cat_raw = tool_input.get("noise_category")

        return AnalyzedItem(
            id=item.id,
            original_text=item.text,
            source=item.source,
            author=item.author,
            classification=classification,
            signal_category=SignalCategory(signal_cat_raw) if signal_cat_raw else None,
            noise_category=NoiseCategory(noise_cat_raw) if noise_cat_raw else None,
            priority=int(tool_input["priority"]),
            confidence=float(tool_input["confidence"]),
            summary=tool_input["summary"],
            recommended_action=tool_input.get("recommended_action"),
            tags=tool_input.get("tags", []),
        )

    def _build_digest(self, signals: list[AnalyzedItem]) -> tuple[str, list[str]]:
        """Ask Claude to synthesize an executive digest from the classified signals."""
        if not signals:
            return (
                "No signals detected. All items reviewed are noise — no immediate action required.",
                [],
            )

        signal_summaries = "\n".join(
            f"- [P{s.priority}] [{s.category_label}] {s.summary}"
            + (f" → {s.recommended_action}" if s.recommended_action else "")
            for s in signals
        )

        response = self._client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[_DIGEST_TOOL],
            tool_choice={"type": "tool", "name": "build_digest"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Based on the following classified signals, write an executive digest "
                        "for the program manager:\n\n"
                        + signal_summaries
                    ),
                }
            ],
        )

        tool_input = self._extract_tool_input(response)
        return tool_input["executive_summary"], tool_input.get("top_actions", [])
