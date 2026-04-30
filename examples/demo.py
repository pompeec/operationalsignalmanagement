"""
Quick demo — run without installing the package.

    python examples/demo.py

Requires ANTHROPIC_API_KEY to be set in the environment or in a .env file.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from signal_detector.analyzer import SignalAnalyzer
from signal_detector.models import InputItem
from signal_detector.reporter import console, print_report

DEMO_ITEMS = [
    InputItem(
        id="d1",
        source="slack",
        text=(
            "Auth service throwing 500s on ~5% of login attempts since 14:00 UTC. "
            "Root cause: Redis connection pool exhaustion. Hotfix in review, not shipped yet. "
            "Enterprise checkout impacted."
        ),
    ),
    InputItem(
        id="d2",
        source="jira",
        text="Sprint 42 status: 18/23 points done. Velocity on track. No impediments.",
    ),
    InputItem(
        id="d3",
        source="email",
        text=(
            "Acme Corp ($2.4M renewal) at risk — CTO asking why SSO feature promised in Q2 "
            "isn't on the roadmap. Need status by EOD today."
        ),
    ),
    InputItem(
        id="d4",
        source="slack",
        text=(
            "Staff eng started building real-time sync feature without PM sign-off — "
            "adds 3-4 weeks to scope. Gave heads up but already writing design doc."
        ),
    ),
    InputItem(
        id="d5",
        source="calendar",
        text="Sprint review rescheduled from Thursday 2pm to Friday 3pm.",
    ),
]


def main() -> None:
    console.print("\n[bold blue]Signal Detector Demo[/bold blue]\n")
    console.print(f"[dim]Analyzing {len(DEMO_ITEMS)} items...[/dim]\n")

    analyzer = SignalAnalyzer()
    report = analyzer.analyze_batch(DEMO_ITEMS)
    print_report(report, show_noise=True)


if __name__ == "__main__":
    main()
