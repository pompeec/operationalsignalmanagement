# Signal Detector — Operational Intelligence for Program & Product Managers

Cut through the noise. Surface what matters.

Signal Detector uses Claude AI to classify the stream of updates, tickets, Slack messages, and status reports that PMs and PgMs receive every day into two buckets: **signal** (requires action) and **noise** (can be safely deprioritized).

---

## What It Does

Given a batch of program management inputs — standup notes, JIRA updates, Slack threads, email excerpts — Signal Detector:

1. **Classifies** each item as signal or noise using Claude's reasoning
2. **Categorizes** signals into actionable types (Blocker, Risk, Escalation, Decision Needed, etc.)
3. **Prioritizes** signals on a 1–10 scale
4. **Recommends** a specific, time-bound action for each signal
5. **Synthesizes** an executive digest with top actions for the day

---

## Signal Categories

| Category | Description |
|----------|-------------|
| Blocker | Actively preventing progress right now |
| Risk | Potential future problem that could derail plans |
| Decision Needed | Requires PM decision before work can continue |
| Escalation | Customer or executive escalation |
| Dependency Issue | External dependency causing delays |
| Scope Change | Unauthorized or problematic scope change |
| Milestone Concern | Threat to a deadline or release |
| Resource Issue | Team capacity, budget, or tooling problem |

---

## Installation

```bash
# Clone and install
pip install -e .

# Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

---

## Usage

### Analyze a batch of items

```bash
signal-detector analyze examples/sample_inputs.json
```

### Analyze a single text snippet

```bash
signal-detector analyze --text "Auth service throwing 500s since 2pm, hotfix not shipped yet" --source slack
```

### Interactive mode — paste items one at a time

```bash
signal-detector interactive
```

### Executive digest (critical signals only)

```bash
signal-detector digest examples/sample_inputs.json --critical-only
```

### JSON output (for integration with other tools)

```bash
signal-detector analyze examples/sample_inputs.json --json > report.json
```

---

## Input Format

Items are provided as a JSON array. Each item supports:

```json
[
  {
    "id": "001",
    "source": "slack",
    "author": "eng-lead",
    "timestamp": "2026-04-30T09:15:00Z",
    "text": "Auth service throwing 500s on ~5% of login attempts..."
  }
]
```

Only `text` is required. All other fields are optional metadata.

---

## Claude Code Skill

Use the `/signal-review` slash command in Claude Code to run an interactive, conversational signal review directly in your terminal:

```
/signal-review
```

Paste items separated by `---` and get an instant structured digest.

---

## Architecture

```
signal_detector/
├── analyzer.py     # Claude API integration (tool use + prompt caching)
├── models.py       # Pydantic data models
├── reporter.py     # Rich terminal output
└── cli.py          # Typer CLI

.claude/commands/
└── signal-review.md  # Claude Code slash command skill

examples/
├── sample_inputs.json  # 12 realistic PM scenarios
└── demo.py             # Quick demo script
```

### Claude API Features Used

- **Prompt caching** — the system prompt is cached at the API level, reducing latency and cost on repeated calls
- **Tool use** — structured JSON output via `classify_item` and `build_digest` tools for reliable parsing
- **Batch analysis** — items are processed sequentially with a single cached system prompt

---

## Environment

```
ANTHROPIC_API_KEY=your_key_here
```
