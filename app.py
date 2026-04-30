"""Flask web UI for Signal Detector — shareable demo server."""

from __future__ import annotations

import json
import os
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request

load_dotenv()

app = Flask(__name__)

MOCK_ITEMS = [
    {"id": "001", "source": "pagerduty", "text": "Payments service timing out for all EU users since 14:47 UTC — 100% failure rate on /api/payments"},
    {"id": "002", "source": "slack",     "text": "Sprint 42 standup: 18/23 points done, velocity on track, no impediments reported"},
    {"id": "003", "source": "email",     "text": "Acme Corp CTO emailed — unable to complete checkout for 45 minutes, threatening to escalate to VP. This is a $1.8M renewal account."},
    {"id": "004", "source": "datadog",   "text": "500 error rate on /api/checkout spiked from 0.2% to 11.4% at 14:32 UTC, coinciding with v2.4.1 deploy"},
    {"id": "005", "source": "slack",     "text": "Restarted the pod, looks fine on my end"},
    {"id": "006", "source": "jira",      "text": "Backend engineer blocked 3 days on PROJ-441 — data-platform team unresponsive to API access requests"},
    {"id": "007", "source": "pagerduty", "text": "Memory alert on cache-node-02 — auto-resolved after 90 seconds"},
    {"id": "008", "source": "grafana",   "text": "Search latency increased 180ms vs baseline — still within 500ms SLA threshold"},
    {"id": "009", "source": "slack",     "text": "Staff engineer started building real-time sync feature without PM sign-off — adds 3–4 weeks to Q3 scope"},
    {"id": "010", "source": "datadog",   "text": "Disk usage on logging-node-07 at 72% — slow upward trend, not urgent"},
    {"id": "011", "source": "slack",     "text": "AWS Q2 budget at 78% with 2 months left, on track to overshoot by $45K"},
    {"id": "012", "source": "email",     "text": "FYI: contractor agreement template updated with new IP clauses. No action needed for existing contracts."},
]

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Signal Detector — PM Operational Intelligence</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }
  header { background: #1a1d2e; border-bottom: 1px solid #2d3148; padding: 20px 32px; display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 1.25rem; font-weight: 700; color: #fff; }
  header span { font-size: 0.85rem; color: #64748b; }
  .badge { background: #3b4fd8; color: #fff; font-size: 0.7rem; font-weight: 600; padding: 3px 8px; border-radius: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
  main { max-width: 960px; margin: 0 auto; padding: 32px 24px; }
  .card { background: #1a1d2e; border: 1px solid #2d3148; border-radius: 12px; padding: 24px; margin-bottom: 24px; }
  label { display: block; font-size: 0.85rem; font-weight: 600; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; }
  textarea { width: 100%; background: #0f1117; border: 1px solid #2d3148; border-radius: 8px; color: #e2e8f0; font-size: 0.9rem; padding: 12px; resize: vertical; min-height: 160px; font-family: inherit; line-height: 1.6; }
  textarea:focus { outline: none; border-color: #3b4fd8; }
  textarea::placeholder { color: #475569; }
  .hint { font-size: 0.8rem; color: #475569; margin-top: 6px; }
  .actions { display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
  button { padding: 10px 24px; border-radius: 8px; font-size: 0.9rem; font-weight: 600; cursor: pointer; border: none; transition: opacity 0.15s; }
  button:hover { opacity: 0.85; }
  #btn-analyze { background: #3b4fd8; color: #fff; }
  #btn-mock { background: #1e293b; color: #94a3b8; border: 1px solid #2d3148; }
  #btn-clear { background: transparent; color: #475569; border: 1px solid #2d3148; }
  #status { font-size: 0.85rem; color: #64748b; margin-top: 12px; min-height: 20px; }
  #results { display: none; }
  .summary-box { background: #0f1117; border-left: 4px solid #3b4fd8; border-radius: 0 8px 8px 0; padding: 16px 20px; margin-bottom: 20px; line-height: 1.7; font-size: 0.95rem; }
  .actions-box { background: #0f1117; border-left: 4px solid #eab308; border-radius: 0 8px 8px 0; padding: 16px 20px; margin-bottom: 24px; }
  .actions-box ol { padding-left: 20px; }
  .actions-box li { padding: 4px 0; line-height: 1.6; font-size: 0.95rem; }
  h2 { font-size: 1rem; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
  h3 { font-size: 0.9rem; font-weight: 600; color: #94a3b8; margin: 20px 0 12px; text-transform: uppercase; letter-spacing: 0.05em; }
  table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
  th { text-align: left; padding: 8px 12px; color: #64748b; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #2d3148; }
  td { padding: 10px 12px; border-bottom: 1px solid #1e2438; vertical-align: top; line-height: 1.5; }
  tr:last-child td { border-bottom: none; }
  .p-badge { display: inline-block; width: 28px; height: 28px; border-radius: 50%; font-weight: 700; font-size: 0.85rem; text-align: center; line-height: 28px; }
  .p-critical { background: #7f1d1d; color: #fca5a5; }
  .p-high     { background: #78350f; color: #fcd34d; }
  .p-medium   { background: #1e3a5f; color: #93c5fd; }
  .p-low      { background: #1a2535; color: #64748b; }
  .cat-tag { display: inline-block; font-size: 0.72rem; font-weight: 600; padding: 2px 8px; border-radius: 10px; white-space: nowrap; }
  .cat-blocker    { background: #450a0a; color: #fca5a5; }
  .cat-escalation { background: #450a0a; color: #fca5a5; }
  .cat-risk       { background: #431407; color: #fb923c; }
  .cat-milestone  { background: #431407; color: #fb923c; }
  .cat-decision   { background: #422006; color: #fcd34d; }
  .cat-scope      { background: #422006; color: #fcd34d; }
  .cat-dependency { background: #2e1065; color: #c4b5fd; }
  .cat-resource   { background: #0c2340; color: #93c5fd; }
  .noise-item { font-size: 0.875rem; color: #475569; padding: 6px 0; border-bottom: 1px solid #1e2438; display: flex; gap: 10px; }
  .noise-item:last-child { border-bottom: none; }
  .noise-label { font-size: 0.72rem; font-weight: 600; color: #334155; background: #1e293b; padding: 2px 8px; border-radius: 10px; white-space: nowrap; align-self: flex-start; margin-top: 2px; }
  .src-tag { font-size: 0.72rem; color: #334155; font-weight: 500; }
  .stats { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
  .stat { background: #0f1117; border: 1px solid #2d3148; border-radius: 8px; padding: 12px 20px; text-align: center; }
  .stat-num { font-size: 1.5rem; font-weight: 700; }
  .stat-lbl { font-size: 0.75rem; color: #64748b; margin-top: 2px; }
  .red { color: #f87171; } .yellow { color: #fbbf24; } .green { color: #4ade80; } .blue { color: #60a5fa; }
  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #2d3148; border-top-color: #3b4fd8; border-radius: 50%; animation: spin 0.7s linear infinite; vertical-align: middle; margin-right: 8px; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<header>
  <div>
    <h1>Signal Detector</h1>
    <span>Operational Intelligence for Program &amp; Product Managers</span>
  </div>
  <span class="badge">Claude AI</span>
</header>
<main>
  <div class="card">
    <label>Paste your updates, alerts, or tickets</label>
    <textarea id="input" placeholder="Auth service throwing 500s on 5% of login attempts since 2pm...
---
Sprint standup: all green, velocity on track
---
Acme Corp CTO asking why SSO feature isn't on roadmap — $2.4M renewal at risk
---
Staff eng building real-time sync without PM sign-off, adds 3-4 weeks to scope"></textarea>
    <p class="hint">Separate multiple items with <code>---</code> on its own line. Or click "Load Mock Data" to use 12 pre-built scenarios.</p>
    <div class="actions">
      <button id="btn-analyze" onclick="analyze()">Analyze</button>
      <button id="btn-mock" onclick="loadMock()">Load Mock Data</button>
      <button id="btn-clear" onclick="clearAll()">Clear</button>
    </div>
    <p id="status"></p>
  </div>

  <div id="results" class="card">
    <div class="stats">
      <div class="stat"><div class="stat-num blue" id="stat-total">0</div><div class="stat-lbl">Items Reviewed</div></div>
      <div class="stat"><div class="stat-num red"  id="stat-signals">0</div><div class="stat-lbl">Signals</div></div>
      <div class="stat"><div class="stat-num green" id="stat-noise">0</div><div class="stat-lbl">Noise</div></div>
      <div class="stat"><div class="stat-num yellow" id="stat-critical">0</div><div class="stat-lbl">Critical (P8+)</div></div>
    </div>

    <h2>Executive Summary</h2>
    <div class="summary-box" id="summary"></div>

    <h2>Top Actions for Today</h2>
    <div class="actions-box"><ol id="top-actions"></ol></div>

    <h2>🔴 Signals — Requires Attention</h2>
    <table id="signals-table">
      <thead><tr><th>P</th><th>Category</th><th>Summary</th><th>Recommended Action</th><th>Source</th></tr></thead>
      <tbody id="signals-body"></tbody>
    </table>

    <h3>🟢 Noise — No Immediate Action</h3>
    <div id="noise-list"></div>
  </div>
</main>

<script>
const CAT_CLASS = {
  blocker:'cat-blocker', escalation:'cat-escalation', risk:'cat-risk',
  milestone_concern:'cat-milestone', decision_needed:'cat-decision',
  scope_change:'cat-scope', dependency_issue:'cat-dependency', resource_issue:'cat-resource'
};
const CAT_LABEL = {
  blocker:'Blocker', escalation:'Escalation', risk:'Risk',
  milestone_concern:'Milestone Concern', decision_needed:'Decision Needed',
  scope_change:'Scope Change', dependency_issue:'Dependency Issue', resource_issue:'Resource Issue',
  routine_update:'Routine Update', administrative:'Administrative',
  duplicate_info:'Duplicate Info', low_priority:'Low Priority', informational:'Informational'
};

function priorityClass(p) {
  if (p >= 9) return 'p-critical';
  if (p >= 7) return 'p-high';
  if (p >= 5) return 'p-medium';
  return 'p-low';
}

async function analyze() {
  const raw = document.getElementById('input').value.trim();
  if (!raw) { setStatus('Paste some items first.'); return; }

  const items = raw.split(/\\n---\\n|\\n---$|^---\\n/m)
    .map(t => t.trim()).filter(Boolean)
    .map((text, i) => ({ id: String(i+1).padStart(3,'0'), text }));

  setStatus('<span class="spinner"></span>Analyzing ' + items.length + ' item(s) with Claude...');
  document.getElementById('results').style.display = 'none';

  try {
    const res = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items })
    });
    const data = await res.json();
    if (data.error) { setStatus('Error: ' + data.error); return; }
    renderReport(data);
    setStatus('');
  } catch(e) {
    setStatus('Request failed: ' + e.message);
  }
}

function renderReport(r) {
  document.getElementById('stat-total').textContent    = r.total_items;
  document.getElementById('stat-signals').textContent  = r.signals.length;
  document.getElementById('stat-noise').textContent    = r.noise.length;
  document.getElementById('stat-critical').textContent = r.signals.filter(s => s.priority >= 8).length;

  document.getElementById('summary').textContent = r.executive_summary;

  const ol = document.getElementById('top-actions');
  ol.innerHTML = '';
  (r.top_actions || []).forEach(a => {
    const li = document.createElement('li'); li.textContent = a; ol.appendChild(li);
  });

  const tbody = document.getElementById('signals-body');
  tbody.innerHTML = '';
  r.signals.forEach(s => {
    const catKey = s.signal_category || '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="p-badge ${priorityClass(s.priority)}">${s.priority}</span></td>
      <td><span class="cat-tag ${CAT_CLASS[catKey]||''}">${CAT_LABEL[catKey]||catKey}</span></td>
      <td>${s.summary}</td>
      <td>${s.recommended_action||'—'}</td>
      <td><span class="src-tag">${s.source||'—'}</span></td>`;
    tbody.appendChild(tr);
  });

  const noiseDiv = document.getElementById('noise-list');
  noiseDiv.innerHTML = '';
  r.noise.forEach(n => {
    const d = document.createElement('div');
    d.className = 'noise-item';
    d.innerHTML = `<span class="noise-label">${CAT_LABEL[n.noise_category]||n.noise_category||'Noise'}</span><span>${n.summary}</span>`;
    noiseDiv.appendChild(d);
  });

  document.getElementById('results').style.display = 'block';
  document.getElementById('results').scrollIntoView({ behavior:'smooth' });
}

function setStatus(msg) {
  document.getElementById('status').innerHTML = msg;
}

async function loadMock() {
  setStatus('<span class="spinner"></span>Loading mock data...');
  const res = await fetch('/mock-items');
  const items = await res.json();
  document.getElementById('input').value = items.map(i => i.text).join('\\n---\\n');
  setStatus('12 mock scenarios loaded. Click Analyze to run.');
}

function clearAll() {
  document.getElementById('input').value = '';
  document.getElementById('results').style.display = 'none';
  setStatus('');
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/mock-items")
def mock_items():
    return jsonify(MOCK_ITEMS)


@app.route("/analyze", methods=["POST"])
def analyze():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not set on the server"}), 500

    data = request.get_json()
    raw_items = data.get("items", [])
    if not raw_items:
        return jsonify({"error": "No items provided"}), 400

    try:
        from signal_detector.analyzer import SignalAnalyzer
        from signal_detector.models import InputItem

        analyzer = SignalAnalyzer(api_key=api_key)
        items = [
            InputItem(id=entry.get("id", str(uuid.uuid4())[:8]), text=entry["text"])
            for entry in raw_items
        ]
        report = analyzer.analyze_batch(items)
        return jsonify(report.model_dump())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Signal Detector running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
