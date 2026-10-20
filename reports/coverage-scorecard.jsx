import React from "react";

// Generated data: run `python3 scripts/render_coverage_scorecard.py` to refresh from the catalog,
// reports/area-quality.json and docs/jev-integration/epic/pilot-results.json.
// DATA:BEGIN
const DATA = {
  "date": "2026-10-20",
  "version": "1.6.0",
  "catalog": {
    "specs": 18,
    "software": 10,
    "devops": 8,
    "roles": 9,
    "skills": 98,
    "workflows": 73,
    "rules": 85,
    "hosts_verified": 3,
    "hosts_configured": 7
  },
  "hosts": [
    {
      "name": "Codex",
      "short": "CX",
      "status": "verified",
      "detail": "v0.163.0 · 13 pilot runs · 4 accepted"
    },
    {
      "name": "Claude Code",
      "short": "CC",
      "status": "verified",
      "detail": "v2.1.304 · 13 pilot runs · 5 accepted"
    },
    {
      "name": "OpenCode",
      "short": "OC",
      "status": "verified",
      "detail": "v2.0.29 · 13 pilot runs · 6 accepted"
    },
    {
      "name": "Antigravity",
      "short": "AG",
      "status": "configs",
      "detail": "agents, rules and workflows ship; no recorded run yet"
    },
    {
      "name": "Gemini",
      "short": "GM",
      "status": "configs",
      "detail": "agents, rules and workflows ship; no recorded run yet"
    },
    {
      "name": "Cursor",
      "short": "CU",
      "status": "configs",
      "detail": "agents, rules and workflows ship; no recorded run yet"
    },
    {
      "name": "Kilocode",
      "short": "KC",
      "status": "configs",
      "detail": "agents, rules and workflows ship; no recorded run yet"
    }
  ],
  "quality": {
    "overall": 98,
    "specs": [
      {
        "id": "areas/devops/ci-cd",
        "area": "devops",
        "name": "ci-cd",
        "score": 99
      },
      {
        "id": "areas/devops/database-ops",
        "area": "devops",
        "name": "database-ops",
        "score": 99
      },
      {
        "id": "areas/devops/devsecops",
        "area": "devops",
        "name": "devsecops",
        "score": 99
      },
      {
        "id": "areas/devops/infrastructure",
        "area": "devops",
        "name": "infrastructure",
        "score": 98
      },
      {
        "id": "areas/devops/kubernetes",
        "area": "devops",
        "name": "kubernetes",
        "score": 99
      },
      {
        "id": "areas/devops/networking",
        "area": "devops",
        "name": "networking",
        "score": 99
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
        "score": 99
      },
      {
        "id": "areas/software/backend",
        "area": "software",
        "name": "backend",
        "score": 99
      },
      {
        "id": "areas/software/data-engineering",
        "area": "software",
        "name": "data-engineering",
        "score": 98
      },
      {
        "id": "areas/software/frontend",
        "area": "software",
        "name": "frontend",
        "score": 97
      },
      {
        "id": "areas/software/full-stack",
        "area": "software",
        "name": "full-stack",
        "score": 98
      },
      {
        "id": "areas/software/general",
        "area": "software",
        "name": "general",
        "score": 99
      },
      {
        "id": "areas/software/mlops",
        "area": "software",
        "name": "mlops",
        "score": 99
      },
      {
        "id": "areas/software/mobile",
        "area": "software",
        "name": "mobile",
        "score": 98
      },
      {
        "id": "areas/software/platform",
        "area": "software",
        "name": "platform",
        "score": 96
      },
      {
        "id": "areas/software/qa",
        "area": "software",
        "name": "qa",
        "score": 99
      },
      {
        "id": "areas/software/security",
        "area": "software",
        "name": "security",
        "score": 99
      }
    ]
  },
  "pilot": {
    "cells": 39,
    "headline": "Small, bounded tasks: a plain agent was cheapest. The agentic team used 2.7× its tokens — the price of shared process and guardrails, not yet a saving.",
    "modes": [
      {
        "mode": "plain",
        "title": "Plain agent (no agentic)",
        "runs": 9,
        "accepted": 8,
        "median_uncached": 19803,
        "median_seconds": 34
      },
      {
        "mode": "fixed",
        "title": "Agentic, fixed workflow",
        "runs": 9,
        "accepted": 1,
        "median_uncached": 53880,
        "median_seconds": 64
      },
      {
        "mode": "jev",
        "title": "Agentic + JEV routing",
        "runs": 9,
        "accepted": 3,
        "median_uncached": 49717,
        "median_seconds": 55
      },
      {
        "mode": "workflow_only",
        "title": "JEV workflow only",
        "runs": 6,
        "accepted": 2,
        "median_uncached": 46944,
        "median_seconds": 51
      },
      {
        "mode": "models_only",
        "title": "JEV models only",
        "runs": 6,
        "accepted": 1,
        "median_uncached": 55679,
        "median_seconds": 69
      }
    ],
    "note": "Hosts: claude, codex, opencode · tasks: infra feasibility, code review, calculator · cap 50k uncached tokens and 6 min per run."
  }
};
// DATA:END

const C = { bg: "#0b1020", card: "#121a2e", line: "#24304d", text: "#e6ebf5", dim: "#8b97b3", ok: "#22c55e", warn: "#f59e0b", bad: "#ef4444", info: "#60a5fa" };
const scoreColor = v => (v >= 97 ? C.ok : v >= 93 ? C.info : v >= 85 ? C.warn : C.bad);
const card = { background: C.card, border: `1px solid ${C.line}`, borderRadius: 14, padding: 18 };
const label = { color: C.dim, fontSize: 12, letterSpacing: 0.6, textTransform: "uppercase" };
const fmtK = n => (n == null ? "—" : n >= 1000 ? (n / 1000).toFixed(1) + "k" : String(n));

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

function Pilot({ pilot }) {
  return (
    <div style={{ ...card, flex: 1.25 }}>
      <div style={label}>Reality check · {pilot.cells} measured runs</div>
      <div style={{ color: C.text, fontSize: 15, margin: "8px 0 12px" }}>{pilot.headline}</div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ color: C.dim, textAlign: "left" }}>
            <th style={{ padding: "6px 4px" }}>Mode</th><th>Accepted</th><th>Median uncached tokens</th><th>Median time</th>
          </tr>
        </thead>
        <tbody>
          {pilot.modes.map(m => (
            <tr key={m.mode} style={{ borderTop: `1px solid ${C.line}`, color: C.text }}>
              <td style={{ padding: "7px 4px" }}>{m.title}</td>
              <td style={{ color: m.accepted / m.runs >= 0.6 ? C.ok : m.accepted / m.runs >= 0.35 ? C.warn : C.bad, fontWeight: 700 }}>{m.accepted}/{m.runs}</td>
              <td>{fmtK(m.median_uncached)}</td>
              <td>{m.median_seconds}s</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ color: C.dim, fontSize: 12, marginTop: 10 }}>{pilot.note}</div>
    </div>
  );
}

function Quality({ quality }) {
  return (
    <div style={card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div style={label}>Guidance quality per specialization (static checks, 6 environments)</div>
        <div style={{ color: scoreColor(quality.overall), fontWeight: 800, fontSize: 20 }}>{quality.overall}/100</div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(9, 1fr)", gap: 8, marginTop: 12 }}>
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
          <div style={{ fontSize: 26, fontWeight: 800 }}>agentic · one AI engineering team for every coding agent</div>
          <div style={{ color: C.dim, fontSize: 14, marginTop: 4 }}>Same roles, rules and quality gates in Codex, Claude Code and OpenCode — installed with one command.</div>
        </div>
        <div style={{ color: C.dim, fontSize: 13, textAlign: "right" }}>Coverage & real-run report<br />v{DATA.version} · {DATA.date}</div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12, marginBottom: 14 }}>
        <Stat value={c.specs} title="specializations" note={`${c.software} software · ${c.devops} devops`} />
        <Stat value={c.roles} title="agent roles" note="7 SDLC + 2 reviewers" />
        <Stat value={c.skills} title="skills" note="loaded on demand" />
        <Stat value={c.workflows} title="workflows" note="feature, review, incident…" />
        <Stat value={c.rules} title="rules" note="hard guardrails" />
        <Stat value={c.hosts_verified} title="hosts verified" note={`${c.hosts_configured} with shipped configs`} />
      </div>
      <div style={{ display: "flex", gap: 14, marginBottom: 14 }}>
        <div style={{ ...card, flex: 1 }}>
          <div style={label}>Where it runs</div>
          <div style={{ marginTop: 6 }}>{DATA.hosts.map(h => <Host key={h.name} host={h} />)}</div>
        </div>
        <Pilot pilot={DATA.pilot} />
      </div>
      <Quality quality={DATA.quality} />
      <div style={{ color: C.dim, fontSize: 12, marginTop: 12 }}>
        Static quality: scripts/assess_area_quality.py · Real runs: scripts/pilot_jev.py (single exploratory runs per cell, not a statistical benchmark).
      </div>
    </div>
  );
}
