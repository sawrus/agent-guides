import React from "react";

// Generated data: run `python3 scripts/render_coverage_scorecard.py` to refresh from the catalog,
// reports/area-quality.json, scripts/context_budget.py and reports/bench-round6.json.
// DATA:BEGIN
const DATA = {
  "date": "2026-10-27",
  "version": "8.1.1",
  "catalog": {
    "specs": 16,
    "software": 8,
    "devops": 8,
    "rules": 64,
    "skills": 14,
    "workflows": 10,
    "budget": {
      "max": 2110,
      "host": "claude",
      "per_host": {
        "claude": 2110,
        "codex": 1780,
        "opencode": 1939
      },
      "selections": 23
    },
    "hosts_verified": 3,
    "hosts_configured": 7
  },
  "hosts": [
    {
      "name": "Codex",
      "short": "CX",
      "status": "verified",
      "detail": "v0.164.0 · benchmark round 6, 2026-10-27"
    },
    {
      "name": "Claude Code",
      "short": "CC",
      "status": "verified",
      "detail": "v2.1.311 · benchmark round 6, 2026-10-27"
    },
    {
      "name": "OpenCode",
      "short": "OC",
      "status": "verified",
      "detail": "v2.0.29 · benchmark round 4, 2026-10-24"
    },
    {
      "name": "Antigravity",
      "short": "AG",
      "status": "configs",
      "detail": "configs ship; no recorded run yet"
    },
    {
      "name": "Gemini",
      "short": "GM",
      "status": "configs",
      "detail": "configs ship; no recorded run yet"
    },
    {
      "name": "Cursor",
      "short": "CU",
      "status": "configs",
      "detail": "configs ship; no recorded run yet"
    },
    {
      "name": "Kilocode",
      "short": "KC",
      "status": "configs",
      "detail": "configs ship; no recorded run yet"
    }
  ],
  "quality": {
    "overall": 98,
    "environments": 6,
    "artifact_findings": 0,
    "specs": [
      {
        "id": "areas/devops/ci-cd",
        "area": "devops",
        "name": "ci-cd",
        "score": 100
      },
      {
        "id": "areas/devops/database-ops",
        "area": "devops",
        "name": "database-ops",
        "score": 98
      },
      {
        "id": "areas/devops/devsecops",
        "area": "devops",
        "name": "devsecops",
        "score": 100
      },
      {
        "id": "areas/devops/infrastructure",
        "area": "devops",
        "name": "infrastructure",
        "score": 100
      },
      {
        "id": "areas/devops/kubernetes",
        "area": "devops",
        "name": "kubernetes",
        "score": 100
      },
      {
        "id": "areas/devops/networking",
        "area": "devops",
        "name": "networking",
        "score": 96
      },
      {
        "id": "areas/devops/observability",
        "area": "devops",
        "name": "observability",
        "score": 98
      },
      {
        "id": "areas/devops/sre",
        "area": "devops",
        "name": "sre",
        "score": 100
      },
      {
        "id": "areas/software/backend",
        "area": "software",
        "name": "backend",
        "score": 100
      },
      {
        "id": "areas/software/data-engineering",
        "area": "software",
        "name": "data-engineering",
        "score": 96
      },
      {
        "id": "areas/software/frontend",
        "area": "software",
        "name": "frontend",
        "score": 96
      },
      {
        "id": "areas/software/general",
        "area": "software",
        "name": "general",
        "score": 98
      },
      {
        "id": "areas/software/mlops",
        "area": "software",
        "name": "mlops",
        "score": 96
      },
      {
        "id": "areas/software/mobile",
        "area": "software",
        "name": "mobile",
        "score": 96
      },
      {
        "id": "areas/software/qa",
        "area": "software",
        "name": "qa",
        "score": 96
      },
      {
        "id": "areas/software/security",
        "area": "software",
        "name": "security",
        "score": 98
      }
    ]
  },
  "bench": {
    "cells": 50,
    "headline": "Rules carry the result: on the devops task T11 a plain agent passed 0 of 3 runs, lean passed 3 of 3.",
    "models": "Claude sonnet · Codex gpt-6.1-terra (codex-cli 0.164)",
    "rows": [
      {
        "task": "T11 devops, after cleanup",
        "host": "Claude",
        "mode": "plain",
        "accepted": 0,
        "runs": 3,
        "cost_per_run": 0.076
      },
      {
        "task": "T11 devops, after cleanup",
        "host": "Claude",
        "mode": "lean",
        "accepted": 3,
        "runs": 3,
        "cost_per_run": 0.123
      },
      {
        "task": "T1–T7, T10, after cleanup",
        "host": "Claude",
        "mode": "lean",
        "accepted": 8,
        "runs": 8,
        "cost_per_run": 0.096
      },
      {
        "task": "T6–T8",
        "host": "Codex",
        "mode": "lean",
        "accepted": 9,
        "runs": 9,
        "cost_per_run": 0.088
      },
      {
        "task": "T6–T8",
        "host": "Codex",
        "mode": "lean + JEV",
        "accepted": 9,
        "runs": 9,
        "cost_per_run": 0.096
      },
      {
        "task": "T8v2",
        "host": "Codex",
        "mode": "lean",
        "accepted": 9,
        "runs": 9,
        "cost_per_run": 0.083
      },
      {
        "task": "T8v2",
        "host": "Codex",
        "mode": "lean, no reviewer",
        "accepted": 9,
        "runs": 9,
        "cost_per_run": 0.081
      }
    ],
    "notes": [
      "After the content cleanup, T11 lean: uncached tokens × 0.72, cost × 0.85; core tasks 8/8 before and after.",
      "Lean + JEV costs × 1.09 of lean; every lean helper ran on the session model.",
      "T8v2: no cell started the reviewer, so it left the lean default."
    ],
    "source": "docs/agentic-v2-lean/results.md"
  }
};
// DATA:END

const C = { bg: "#0b1020", card: "#121a2e", line: "#24304d", text: "#e6ebf5", dim: "#8b97b3", ok: "#22c55e", warn: "#f59e0b", bad: "#ef4444", info: "#60a5fa" };
const scoreColor = v => (v >= 97 ? C.ok : v >= 93 ? C.info : v >= 85 ? C.warn : C.bad);
const card = { background: C.card, border: `1px solid ${C.line}`, borderRadius: 14, padding: 18 };
const label = { color: C.dim, fontSize: 12, letterSpacing: 0.6, textTransform: "uppercase" };
const hostName = { claude: "Claude Code", codex: "Codex", opencode: "OpenCode" };

function Stat({ value, title, note }) {
  return (
    <div style={{ ...card, padding: "14px 16px" }}>
      <div style={{ fontSize: 30, fontWeight: 800, color: C.text }}>{value}</div>
      <div style={{ fontSize: 14, color: C.text, marginTop: 2 }}>{title}</div>
      {note && <div style={{ fontSize: 12, color: C.dim, marginTop: 2 }}>{note}</div>}
    </div>
  );
}

function Host({ host }) {
  const verified = host.status === "verified";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "9px 0", borderTop: `1px solid ${C.line}` }}>
      <div style={{ width: 34, height: 34, borderRadius: 9, background: verified ? "#123524" : "#2a2412", color: verified ? C.ok : C.warn,
                    display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 13 }}>{host.short}</div>
      <div style={{ flex: 1 }}>
        <div style={{ color: C.text, fontSize: 15, fontWeight: 600 }}>{host.name}</div>
        <div style={{ color: C.dim, fontSize: 12 }}>{host.detail}</div>
      </div>
      <div style={{ fontSize: 12, fontWeight: 700, color: verified ? C.ok : C.warn }}>{verified ? "✓ real runs" : "configs only"}</div>
    </div>
  );
}

function Bench({ bench }) {
  return (
    <div style={{ ...card, flex: 1.35 }}>
      <div style={label}>Reality check · benchmark round 6 · {bench.cells} runs in this table</div>
      <div style={{ color: C.text, fontSize: 15, margin: "8px 0 12px" }}>{bench.headline}</div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ color: C.dim, textAlign: "left" }}>
            <th style={{ padding: "6px 4px" }}>Task</th><th>Agent</th><th>Mode</th><th>Accepted</th><th>Cost per run</th>
          </tr>
        </thead>
        <tbody>
          {bench.rows.map(r => (
            <tr key={r.task + r.host + r.mode} style={{ borderTop: `1px solid ${C.line}`, color: C.text }}>
              <td style={{ padding: "7px 4px" }}>{r.task}</td>
              <td>{r.host}</td>
              <td>{r.mode}</td>
              <td style={{ color: r.accepted === r.runs ? C.ok : r.accepted === 0 ? C.bad : C.warn, fontWeight: 700 }}>{r.accepted}/{r.runs}</td>
              <td>${r.cost_per_run.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ color: C.dim, fontSize: 12, marginTop: 10 }}>
        {bench.notes.map(n => <div key={n}>· {n}</div>)}
        <div style={{ marginTop: 4 }}>{bench.models} · Codex cost is an API-equivalent estimate.</div>
      </div>
    </div>
  );
}

function Quality({ quality }) {
  return (
    <div style={card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div style={label}>Guidance quality per specialization (static checks, {quality.environments} environments) · check-artifacts: {quality.artifact_findings} findings</div>
        <div style={{ color: scoreColor(quality.overall), fontWeight: 800, fontSize: 20 }}>{quality.overall}/100</div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 8, marginTop: 12 }}>
        {quality.specs.map(s => (
          <div key={s.id} style={{ border: `1px solid ${C.line}`, borderRadius: 10, padding: "8px 8px", background: "#0f1628" }}>
            <div style={{ color: C.dim, fontSize: 11 }}>{s.area}</div>
            <div style={{ color: C.text, fontSize: 13, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.name}</div>
            <div style={{ color: scoreColor(s.score), fontSize: 18, fontWeight: 800 }}>{s.score}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const c = DATA.catalog;
  return (
    <div style={{ background: C.bg, color: C.text, fontFamily: "Inter, system-ui, sans-serif", padding: 26, width: 1400, boxSizing: "border-box" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 18 }}>
        <div>
          <div style={{ fontSize: 26, fontWeight: 800 }}>agentic · shared rules and a quality gate for every coding agent</div>
          <div style={{ color: C.dim, fontSize: 14, marginTop: 4 }}>Rules are the base. The gate runs the checks and records acceptance. Lean (main session + explorer) is the default; the role team is optional.</div>
        </div>
        <div style={{ color: C.dim, fontSize: 13, textAlign: "right" }}>Coverage & benchmark report<br />v{DATA.version} · {DATA.date}</div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12, marginBottom: 14 }}>
        <Stat value={c.specs} title="specializations" note={`${c.software} software · ${c.devops} devops`} />
        <Stat value={c.rules} title="rules" note="path-scoped, checkable items" />
        <Stat value={c.skills} title="skills" note="loaded on demand" />
        <Stat value={c.workflows} title="workflows" note="feature, debug, incident…" />
        <Stat value={c.budget.max.toLocaleString("en-US")} title="always-on tokens (max)" note={`${hostName[c.budget.host]}, worst of ${c.budget.selections} selections`} />
        <Stat value={c.hosts_verified} title="hosts verified" note={`${c.hosts_configured} with shipped configs`} />
      </div>
      <div style={{ display: "flex", gap: 14, marginBottom: 14 }}>
        <div style={{ ...card, flex: 1 }}>
          <div style={label}>Where it runs</div>
          <div style={{ marginTop: 6 }}>{DATA.hosts.map(h => <Host key={h.name} host={h} />)}</div>
        </div>
        <Bench bench={DATA.bench} />
      </div>
      <Quality quality={DATA.quality} />
      <div style={{ color: C.dim, fontSize: 12, marginTop: 12 }}>
        Sources: areas/ catalog · scripts/assess_area_quality.py · scripts/context_budget.py --all-selections · make check-artifacts · {DATA.bench.source} (round 6).
      </div>
    </div>
  );
}
