"""Flask web UI for Signal Detector — shareable demo server."""

from __future__ import annotations

import os
import threading
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request

load_dotenv()

app = Flask(__name__)
app.config["TIMEOUT"] = 120

# Demo run limit — set via DEMO_LIMIT env var or defaults to 2
DEMO_LIMIT = int(os.environ.get("DEMO_LIMIT", 2))
_run_count = 0
_run_lock = threading.Lock()

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
  .actions-box { background: #0f1117; border-radius: 10px; padding: 4px; margin-bottom: 24px; display: flex; flex-direction: column; gap: 6px; }
  .action-item { display: flex; align-items: flex-start; gap: 14px; padding: 14px 16px; border-radius: 8px; border: 1px solid #1e2438; background: #0f1117; }
  .action-num { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.85rem; flex-shrink: 0; }
  .action-num.a1 { background: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; }
  .action-num.a2 { background: #431407; color: #fb923c; border: 1px solid #7c2d12; }
  .action-num.a3 { background: #422006; color: #fcd34d; border: 1px solid #78350f; }
  .action-num.a4 { background: #0c2340; color: #93c5fd; border: 1px solid #1e3a5f; }
  .action-num.a5 { background: #0c2340; color: #93c5fd; border: 1px solid #1e3a5f; }
  .action-body { flex: 1; }
  .action-urgency { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 3px; }
  .action-urgency.u1 { color: #f87171; }
  .action-urgency.u2 { color: #fb923c; }
  .action-urgency.u3 { color: #fbbf24; }
  .action-urgency.u4 { color: #60a5fa; }
  .action-text { font-size: 0.9rem; line-height: 1.5; color: #e2e8f0; }
  /* Health banner */
  .health-banner { border-radius: 10px; padding: 20px 24px; margin-bottom: 20px; display: flex; align-items: center; gap: 20px; }
  .health-banner.red    { background: #1a0505; border: 1px solid #7f1d1d; }
  .health-banner.yellow { background: #1a1005; border: 1px solid #78350f; }
  .health-banner.green  { background: #051a0a; border: 1px solid #14532d; }
  .health-icon { font-size: 2.5rem; line-height: 1; }
  .health-text h3 { font-size: 1.1rem; font-weight: 800; margin: 0 0 4px; text-transform: none; letter-spacing: 0; color: #fff; }
  .health-text p  { font-size: 0.85rem; color: #94a3b8; margin: 0; }
  /* Progress bar */
  .signal-bar-wrap { margin-bottom: 24px; }
  .signal-bar-label { display: flex; justify-content: space-between; font-size: 0.78rem; color: #64748b; margin-bottom: 6px; }
  .signal-bar-track { background: #1e293b; border-radius: 99px; height: 10px; overflow: hidden; display: flex; }
  .signal-bar-fill  { background: linear-gradient(90deg, #ef4444, #f97316); border-radius: 99px; transition: width 0.6s ease; }
  .noise-bar-fill   { background: #1e3a2a; border-radius: 99px; }
  /* Key points list */
  .key-points { list-style: none; padding: 0; margin: 0 0 24px; display: flex; flex-direction: column; gap: 8px; }
  .key-points li { display: flex; gap: 10px; align-items: flex-start; font-size: 0.9rem; line-height: 1.5; padding: 10px 14px; border-radius: 8px; background: #0f1117; border: 1px solid #1e2438; }
  .key-points li .kp-icon { font-size: 1rem; flex-shrink: 0; margin-top: 1px; }
  /* Category breakdown */
  .cat-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px; }
  .cat-chip { display: flex; align-items: center; gap: 6px; background: #0f1117; border: 1px solid #2d3148; border-radius: 8px; padding: 6px 12px; font-size: 0.8rem; }
  .cat-chip-count { font-weight: 800; font-size: 1rem; }
  .cat-chip-label { color: #94a3b8; }
  h2 { font-size: 1rem; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
  h3 { font-size: 0.9rem; font-weight: 600; color: #94a3b8; margin: 20px 0 12px; text-transform: uppercase; letter-spacing: 0.05em; }
  table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
  th { text-align: left; padding: 8px 12px; color: #64748b; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #2d3148; }
  td { padding: 10px 12px; border-bottom: 1px solid #1e2438; vertical-align: top; line-height: 1.5; }
  tr:last-child td { border-bottom: none; }
  .p-badge { display: inline-flex; align-items: center; justify-content: center; padding: 3px 8px; border-radius: 6px; font-weight: 800; font-size: 0.78rem; white-space: nowrap; gap: 3px; }
  .p-p0 { background: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; }
  .p-p1 { background: #431407; color: #fb923c; border: 1px solid #7c2d12; }
  .p-p2 { background: #422006; color: #fcd34d; border: 1px solid #78350f; }
  .p-p3 { background: #1a2535; color: #64748b; border: 1px solid #2d3148; }
  .severity-legend { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; font-size: 0.75rem; color: #475569; align-items: center; }
  .severity-legend span { display: flex; align-items: center; gap: 4px; }
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
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
  .stat { background: #0f1117; border: 1px solid #2d3148; border-radius: 10px; padding: 16px 12px; text-align: center; }
  .stat-num { font-size: 2rem; font-weight: 800; line-height: 1; }
  .stat-lbl { font-size: 0.72rem; color: #64748b; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
  .stat-sub { font-size: 0.7rem; color: #334155; margin-top: 2px; }
  .limit-bar { background: #1e293b; border: 1px solid #2d3148; border-radius: 8px; padding: 10px 16px; margin-bottom: 16px; font-size: 0.85rem; color: #94a3b8; display: flex; align-items: center; gap: 10px; }
  .limit-dot { width: 8px; height: 8px; border-radius: 50%; background: #4ade80; flex-shrink: 0; }
  .limit-dot.warn { background: #fbbf24; }
  .limit-dot.empty { background: #f87171; }
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
  <div id="limit-bar" class="limit-bar" style="display:none">
    <span class="limit-dot" id="limit-dot"></span>
    <span id="limit-text"></span>
  </div>
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

    <!-- Health banner -->
    <div id="health-banner" class="health-banner">
      <div class="health-icon" id="health-icon"></div>
      <div class="health-text">
        <h3 id="health-title"></h3>
        <p id="health-sub"></p>
      </div>
    </div>

    <!-- Signal ratio bar -->
    <div class="signal-bar-wrap">
      <div class="signal-bar-label">
        <span id="bar-signal-pct"></span>
        <span id="bar-noise-pct"></span>
      </div>
      <div class="signal-bar-track">
        <div class="signal-bar-fill" id="signal-bar" style="width:0%"></div>
      </div>
    </div>

    <!-- Stats row -->
    <div class="stats">
      <div class="stat"><div class="stat-num blue" id="stat-total">0</div><div class="stat-lbl">Reviewed</div></div>
      <div class="stat"><div class="stat-num red" id="stat-signals">0</div><div class="stat-lbl">Signals</div><div class="stat-sub">Require action</div></div>
      <div class="stat"><div class="stat-num green" id="stat-noise">0</div><div class="stat-lbl">Noise</div><div class="stat-sub">No action needed</div></div>
      <div class="stat"><div class="stat-num" style="color:#fb923c" id="stat-critical">0</div><div class="stat-lbl">P0 / P1</div><div class="stat-sub">Critical</div></div>
    </div>

    <!-- Category breakdown -->
    <h2>Category Breakdown</h2>
    <div class="cat-grid" id="cat-grid"></div>

    <!-- Key points -->
    <h2>What You Need to Know</h2>
    <ul class="key-points" id="key-points"></ul>

    <!-- Top actions -->
    <h2>Top Actions for Today</h2>
    <div class="actions-box" id="top-actions"></div>

    <h2>🔴 Signals — Requires Attention</h2>
    <div class="severity-legend">
      Severity: <span><span class="p-badge p-p0">P0</span> Active blocker / escalation — act within hours</span>
      <span><span class="p-badge p-p1">P1</span> High risk — act today</span>
      <span><span class="p-badge p-p2">P2</span> Medium — act this week</span>
      <span><span class="p-badge p-p3">P3</span> Low — monitor</span>
    </div>
    <table id="signals-table">
      <thead><tr><th>Severity</th><th>Category</th><th>What happened</th><th>Recommended Action</th><th>Source</th></tr></thead>
      <tbody id="signals-body"></tbody>
    </table>

    <h3>🟢 Noise — Reviewed, No Action Needed</h3>
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

function severityLabel(p) {
  if (p >= 9) return { cls: 'p-p0', label: 'P0 Critical' };
  if (p >= 7) return { cls: 'p-p1', label: 'P1 High' };
  if (p >= 5) return { cls: 'p-p2', label: 'P2 Medium' };
  return { cls: 'p-p3', label: 'P3 Low' };
}

async function analyze() {
  const raw = document.getElementById('input').value.trim();
  if (!raw) { setStatus('Paste some items first.'); return; }

  const items = raw.split(/\\n---\\n|\\n---$|^---\\n/m)
    .map(t => t.trim()).filter(Boolean)
    .map((text, i) => ({ id: String(i+1).padStart(3,'0'), text }));

  setStatus('<span class="spinner"></span>Analyzing ' + items.length + ' item(s) in parallel with Claude — usually 10–20s...');
  document.getElementById('results').style.display = 'none';

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);
    const res = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items }),
      signal: controller.signal
    });
    clearTimeout(timeout);
    const data = await res.json();
    if (res.status === 429) { setStatus('⛔ ' + data.error); updateLimitBar(0); return; }
    if (data.error) { setStatus('Error: ' + data.error); return; }
    updateLimitBar(data.runs_remaining);
    renderReport(data);
    setStatus('');
  } catch(e) {
    setStatus('Request failed: ' + e.message);
  }
}

function renderReport(r) {
  const total    = r.total_items;
  const signals  = r.signals.length;
  const noise    = r.noise.length;
  const critical = r.signals.filter(s => s.priority >= 8).length;
  const signalPct = total ? Math.round(signals / total * 100) : 0;

  // Stats
  document.getElementById('stat-total').textContent    = total;
  document.getElementById('stat-signals').textContent  = signals;
  document.getElementById('stat-noise').textContent    = noise;
  document.getElementById('stat-critical').textContent = critical;

  // Health banner
  const banner = document.getElementById('health-banner');
  const icon   = document.getElementById('health-icon');
  const title  = document.getElementById('health-title');
  const sub    = document.getElementById('health-sub');
  if (critical > 0) {
    banner.className = 'health-banner red';
    icon.textContent = '🔴';
    title.textContent = 'Immediate Attention Required';
    sub.textContent  = `${critical} critical signal${critical>1?'s':''} (P0/P1) need action now — ${signalPct}% of items reviewed are signals.`;
  } else if (signals > 0) {
    banner.className = 'health-banner yellow';
    icon.textContent = '🟡';
    title.textContent = 'Action Needed This Week';
    sub.textContent  = `No critical blockers, but ${signals} signal${signals>1?'s':''} require follow-up — ${signalPct}% of items reviewed are signals.`;
  } else {
    banner.className = 'health-banner green';
    icon.textContent = '🟢';
    title.textContent = 'All Clear';
    sub.textContent  = 'No signals detected. All items reviewed are noise — no action required.';
  }

  // Signal ratio bar
  document.getElementById('signal-bar').style.width = signalPct + '%';
  document.getElementById('bar-signal-pct').textContent = signalPct + '% signals (' + signals + ' items need review)';
  document.getElementById('bar-noise-pct').textContent  = (100-signalPct) + '% noise (' + noise + ' items safe to ignore)';

  // Category breakdown
  const catCounts = {};
  r.signals.forEach(s => {
    const k = s.signal_category || 'unknown';
    catCounts[k] = (catCounts[k]||0) + 1;
  });
  const catGrid = document.getElementById('cat-grid');
  catGrid.innerHTML = '';
  Object.entries(catCounts).sort((a,b)=>b[1]-a[1]).forEach(([k,v]) => {
    const chip = document.createElement('div');
    chip.className = 'cat-chip';
    chip.innerHTML = `<span class="cat-tag ${CAT_CLASS[k]||''}">${CAT_LABEL[k]||k}</span><span class="cat-chip-count">${v}</span><span class="cat-chip-label">${v===1?'item':'items'}</span>`;
    catGrid.appendChild(chip);
  });
  if (noise > 0) {
    const chip = document.createElement('div');
    chip.className = 'cat-chip';
    chip.innerHTML = `<span class="cat-tag" style="background:#0f1a0f;color:#4ade80">Noise</span><span class="cat-chip-count">${noise}</span><span class="cat-chip-label">items</span>`;
    catGrid.appendChild(chip);
  }

  // Key points — split executive summary into sentences
  const sentences = r.executive_summary
    .split(/(?<=[.!?])\s+/)
    .map(s => s.trim()).filter(Boolean);
  const icons = ['📌','⚠️','💡','📊','🔎'];
  const kpList = document.getElementById('key-points');
  kpList.innerHTML = '';
  sentences.forEach((s, i) => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="kp-icon">${icons[i%icons.length]}</span><span>${s}</span>`;
    kpList.appendChild(li);
  });

  // Top actions — color-coded by rank
  const urgencyLabels = ['Act Now', 'Act Today', 'Act This Week', 'Schedule', 'Monitor'];
  const actionsBox = document.getElementById('top-actions');
  actionsBox.innerHTML = '';
  (r.top_actions || []).forEach((a, i) => {
    const rank = Math.min(i + 1, 5);
    const uClass = 'u' + Math.min(rank, 4);
    const aClass = 'a' + rank;
    const div = document.createElement('div');
    div.className = 'action-item';
    div.innerHTML = `
      <div class="action-num ${aClass}">${rank}</div>
      <div class="action-body">
        <div class="action-urgency ${uClass}">${urgencyLabels[i] || 'Action'}</div>
        <div class="action-text">${a}</div>
      </div>`;
    actionsBox.appendChild(div);
  });

  const tbody = document.getElementById('signals-body');
  tbody.innerHTML = '';
  r.signals.forEach(s => {
    const catKey = s.signal_category || '';
    const sev = severityLabel(s.priority);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="p-badge ${sev.cls}">${sev.label}</span></td>
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

function updateLimitBar(remaining) {
  const bar = document.getElementById('limit-bar');
  const dot = document.getElementById('limit-dot');
  const txt = document.getElementById('limit-text');
  bar.style.display = 'flex';
  if (remaining <= 0) {
    dot.className = 'limit-dot empty';
    txt.textContent = 'Demo limit reached — no runs remaining.';
    document.getElementById('btn-analyze').disabled = true;
    document.getElementById('btn-analyze').style.opacity = '0.4';
  } else if (remaining === 1) {
    dot.className = 'limit-dot warn';
    txt.textContent = remaining + ' demo run remaining.';
  } else {
    dot.className = 'limit-dot';
    txt.textContent = remaining + ' demo runs remaining.';
  }
}

async function checkLimit() {
  try {
    const res = await fetch('/status');
    const data = await res.json();
    updateLimitBar(data.runs_remaining);
  } catch(e) {}
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

window.addEventListener('load', checkLimit);

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


@app.route("/status")
def status():
    return jsonify({"runs_used": _run_count, "runs_remaining": max(0, DEMO_LIMIT - _run_count), "limit": DEMO_LIMIT})


@app.route("/analyze", methods=["POST"])
def analyze():
    global _run_count

    with _run_lock:
        if _run_count >= DEMO_LIMIT:
            return jsonify({
                "error": f"Demo limit reached ({DEMO_LIMIT} runs). Please contact the owner for access."
            }), 429
        _run_count += 1
        run_number = _run_count

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
        result = report.model_dump()
        result["runs_remaining"] = max(0, DEMO_LIMIT - run_number)
        return jsonify(result)
    except Exception as e:
        with _run_lock:
            _run_count -= 1  # refund the run if it failed
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Signal Detector running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
