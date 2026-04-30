"""CLI entry point for the Signal Detector tool."""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt

from .analyzer import SignalAnalyzer
from .models import InputItem
from .reporter import console, print_item, print_json, print_report

load_dotenv()

app = typer.Typer(
    name="signal-detector",
    help=(
        "Noise vs. Signal detection for Program Managers and Product Managers.\n\n"
        "Uses Claude AI to classify updates, messages, and tickets as actionable "
        "signals or background noise — so you can focus on what matters."
    ),
    add_completion=False,
    rich_markup_mode="rich",
)


def _get_analyzer(api_key: Optional[str]) -> SignalAnalyzer:
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        console.print(
            "[bold red]Error:[/bold red] ANTHROPIC_API_KEY not set. "
            "Pass --api-key or set the environment variable."
        )
        raise typer.Exit(1)
    return SignalAnalyzer(api_key=key)


@app.command("analyze")
def analyze(
    input_file: Optional[Path] = typer.Argument(
        None,
        help="JSON file with a list of items to analyze. See examples/sample_inputs.json.",
    ),
    text: Optional[str] = typer.Option(
        None, "--text", "-t", help="Analyze a single text string directly."
    ),
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Source label (e.g. 'slack', 'jira', 'email')."
    ),
    show_noise: bool = typer.Option(
        False, "--show-noise", help="Include the noise table in the output."
    ),
    output_json: bool = typer.Option(
        False, "--json", help="Output the full report as JSON."
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key."
    ),
) -> None:
    """Analyze items from a JSON file or a single text string."""
    analyzer = _get_analyzer(api_key)

    if text:
        console.print("\n[dim]Analyzing...[/dim]")
        item = analyzer.analyze_text(text, source=source)
        print_item(item)
        return

    if input_file is None:
        console.print(
            "[bold red]Error:[/bold red] Provide an input file or use --text for a single item.\n"
            "Example: [cyan]signal-detector analyze examples/sample_inputs.json[/cyan]"
        )
        raise typer.Exit(1)

    if not input_file.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: {input_file}")
        raise typer.Exit(1)

    raw = json.loads(input_file.read_text())
    if not isinstance(raw, list):
        console.print("[bold red]Error:[/bold red] Input file must be a JSON array of items.")
        raise typer.Exit(1)

    items = [
        InputItem(
            id=entry.get("id", str(uuid.uuid4())[:8]),
            text=entry["text"],
            source=entry.get("source"),
            author=entry.get("author"),
            timestamp=entry.get("timestamp"),
            context=entry.get("context"),
        )
        for entry in raw
    ]

    console.print(f"\n[dim]Analyzing {len(items)} item(s)...[/dim]")
    report = analyzer.analyze_batch(items)

    if output_json:
        print_json(report)
    else:
        print_report(report, show_noise=show_noise)


@app.command("interactive")
def interactive(
    source: Optional[str] = typer.Option(
        "interactive", "--source", "-s", help="Source label for items entered in this session."
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key."
    ),
) -> None:
    """Interactive mode: paste updates one at a time and get instant signal/noise feedback."""
    analyzer = _get_analyzer(api_key)

    console.print(
        "\n[bold blue]Signal Detector — Interactive Mode[/bold blue]\n"
        "[dim]Paste or type an update and press Enter twice to classify it.\n"
        "Type [bold]quit[/bold] or [bold]exit[/bold] to leave.[/dim]\n"
    )

    session_items: list = []

    while True:
        try:
            console.print("[bold cyan]>[/bold cyan] ", end="")
            lines = []
            while True:
                line = input()
                if line.strip().lower() in ("quit", "exit", "q"):
                    _print_session_summary(session_items)
                    return
                if line == "" and lines:
                    break
                lines.append(line)

            text = "\n".join(lines).strip()
            if not text:
                continue

            console.print("[dim]Classifying...[/dim]")
            item = analyzer.analyze_text(text, source=source)
            session_items.append(item)
            print_item(item)

        except (KeyboardInterrupt, EOFError):
            _print_session_summary(session_items)
            return


@app.command("digest")
def digest(
    input_file: Path = typer.Argument(
        ..., help="JSON file with items to digest. See examples/sample_inputs.json."
    ),
    critical_only: bool = typer.Option(
        False, "--critical-only", "-c", help="Show only priority 8+ signals."
    ),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key."
    ),
) -> None:
    """Generate a prioritized executive digest from a batch of items."""
    analyzer = _get_analyzer(api_key)

    if not input_file.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: {input_file}")
        raise typer.Exit(1)

    raw = json.loads(input_file.read_text())
    if not isinstance(raw, list):
        console.print("[bold red]Error:[/bold red] Input file must be a JSON array of items.")
        raise typer.Exit(1)

    items = [
        InputItem(
            id=entry.get("id", str(uuid.uuid4())[:8]),
            text=entry["text"],
            source=entry.get("source"),
            author=entry.get("author"),
            timestamp=entry.get("timestamp"),
            context=entry.get("context"),
        )
        for entry in raw
    ]

    console.print(f"\n[dim]Building digest from {len(items)} item(s)...[/dim]")
    report = analyzer.analyze_batch(items)

    if critical_only:
        report.signals = report.critical_signals

    if output_json:
        print_json(report)
    else:
        print_report(report, show_noise=False)


def _print_session_summary(items: list) -> None:
    if not items:
        console.print("\n[dim]No items classified this session.[/dim]")
        return

    signals = [i for i in items if i.is_signal]
    console.print(
        f"\n[bold]Session summary:[/bold] {len(items)} items — "
        f"[bold red]{len(signals)} signals[/bold red], "
        f"[dim green]{len(items) - len(signals)} noise[/dim green]"
    )
    if signals:
        console.print("[bold yellow]Don't forget to action:[/bold yellow]")
        for s in sorted(signals, key=lambda x: x.priority, reverse=True)[:5]:
            console.print(f"  [dim]P{s.priority}[/dim]  {s.summary}")


if __name__ == "__main__":
    app()
