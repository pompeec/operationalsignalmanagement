"""Rich-formatted terminal output for PM signal/noise reports."""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .models import AnalysisReport, AnalyzedItem, Classification, SignalCategory

console = Console()

# Priority color bands
_PRIORITY_COLORS = {
    range(9, 11): "bold red",
    range(7, 9): "red",
    range(5, 7): "yellow",
    range(3, 5): "cyan",
    range(1, 3): "dim",
}

_SIGNAL_CATEGORY_COLORS: dict[SignalCategory, str] = {
    SignalCategory.BLOCKER: "bold red",
    SignalCategory.ESCALATION: "bold red",
    SignalCategory.RISK: "red",
    SignalCategory.MILESTONE_CONCERN: "red",
    SignalCategory.DECISION_NEEDED: "yellow",
    SignalCategory.SCOPE_CHANGE: "yellow",
    SignalCategory.DEPENDENCY_ISSUE: "magenta",
    SignalCategory.RESOURCE_ISSUE: "cyan",
}


def _priority_color(priority: int) -> str:
    for r, color in _PRIORITY_COLORS.items():
        if priority in r:
            return color
    return "white"


def _priority_bar(priority: int) -> str:
    filled = round(priority / 2)
    return "█" * filled + "░" * (5 - filled)


def print_report(report: AnalysisReport, show_noise: bool = False) -> None:
    """Print a full analysis report to the terminal."""
    console.print()
    _print_header(report)
    _print_executive_summary(report)
    _print_top_actions(report)
    _print_signals_table(report)
    if show_noise and report.noise:
        _print_noise_table(report)
    console.print()


def print_item(item: AnalyzedItem) -> None:
    """Print a single analyzed item."""
    if item.is_signal:
        _print_signal_item(item)
    else:
        _print_noise_item(item)


def print_json(report: AnalysisReport) -> None:
    """Print the full report as JSON."""
    console.print_json(report.model_dump_json(indent=2))


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _print_header(report: AnalysisReport) -> None:
    signal_pct = int(report.signal_ratio * 100)
    noise_pct = 100 - signal_pct

    header = Text()
    header.append("  SIGNAL DETECTOR  ", style="bold white on blue")
    header.append("  Operational Intelligence for Program & Product Managers\n\n", style="dim")
    header.append(f"  {report.total_items}", style="bold white")
    header.append(" items analyzed   ", style="dim")
    header.append(f"{report.signal_count} signals", style="bold red" if report.signal_count else "green")
    header.append("  /  ", style="dim")
    header.append(f"{report.noise_count} noise", style="dim green")
    header.append(f"   ({signal_pct}% signal rate)", style="dim")

    console.print(Panel(header, box=box.DOUBLE_EDGE, border_style="blue", padding=(0, 1)))


def _print_executive_summary(report: AnalysisReport) -> None:
    if not report.executive_summary:
        return
    console.print(
        Panel(
            report.executive_summary,
            title="[bold blue]Executive Summary[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
    )


def _print_top_actions(report: AnalysisReport) -> None:
    if not report.top_actions:
        return

    text = Text()
    for i, action in enumerate(report.top_actions, 1):
        text.append(f"  {i}. ", style="bold yellow")
        text.append(action + "\n")

    console.print(
        Panel(
            text,
            title="[bold yellow]Top Actions for Today[/bold yellow]",
            border_style="yellow",
            padding=(0, 1),
        )
    )


def _print_signals_table(report: AnalysisReport) -> None:
    if not report.signals:
        console.print("\n[bold green]  No signals detected — all clear.[/bold green]\n")
        return

    table = Table(
        title="[bold red]Signals — Requires Attention[/bold red]",
        box=box.ROUNDED,
        border_style="red",
        show_lines=True,
        header_style="bold white on dark_red",
        expand=True,
    )

    table.add_column("P", style="bold", width=4, justify="center")
    table.add_column("Category", width=18)
    table.add_column("Summary", ratio=2)
    table.add_column("Action", ratio=2)
    table.add_column("Tags", width=22)
    table.add_column("Source", width=14)

    for item in report.signals:
        p_color = _priority_color(item.priority)
        cat_color = (
            _SIGNAL_CATEGORY_COLORS.get(item.signal_category, "white")
            if item.signal_category
            else "white"
        )
        tag_text = " ".join(f"[dim]#{t}[/dim]" for t in item.tags[:4])

        table.add_row(
            f"[{p_color}]{item.priority}[/{p_color}]\n[dim]{_priority_bar(item.priority)}[/dim]",
            f"[{cat_color}]{item.category_label}[/{cat_color}]",
            item.summary,
            item.recommended_action or "[dim]—[/dim]",
            tag_text or "[dim]—[/dim]",
            f"[dim]{item.source or '—'}[/dim]",
        )

    console.print(table)


def _print_noise_table(report: AnalysisReport) -> None:
    table = Table(
        title="[dim]Noise — No Immediate Action Required[/dim]",
        box=box.SIMPLE,
        border_style="dim",
        header_style="dim",
        expand=True,
    )

    table.add_column("Category", width=18)
    table.add_column("Summary", ratio=3)
    table.add_column("Source", width=14)

    for item in sorted(report.noise, key=lambda x: x.priority, reverse=True):
        table.add_row(
            f"[dim]{item.category_label}[/dim]",
            f"[dim]{item.summary}[/dim]",
            f"[dim]{item.source or '—'}[/dim]",
        )

    console.print(table)


def _print_signal_item(item: AnalyzedItem) -> None:
    p_color = _priority_color(item.priority)
    cat_color = (
        _SIGNAL_CATEGORY_COLORS.get(item.signal_category, "white")
        if item.signal_category
        else "white"
    )
    text = Text()
    text.append(f"SIGNAL", style=f"bold {p_color}")
    text.append(f"  [{item.category_label}]", style=cat_color)
    text.append(f"  Priority {item.priority}/10  {_priority_bar(item.priority)}\n\n", style="dim")
    text.append(item.summary + "\n", style="white")
    if item.recommended_action:
        text.append("\nAction: ", style="bold yellow")
        text.append(item.recommended_action + "\n", style="yellow")
    if item.tags:
        text.append("\nTags: ", style="dim")
        text.append("  ".join(f"#{t}" for t in item.tags) + "\n", style="dim")

    console.print(Panel(text, border_style=p_color, padding=(0, 1)))


def _print_noise_item(item: AnalyzedItem) -> None:
    text = Text()
    text.append("NOISE", style="dim green")
    text.append(f"  [{item.category_label}]", style="dim")
    text.append(f"\n\n{item.summary}", style="dim")

    console.print(Panel(text, border_style="dim", padding=(0, 1)))
