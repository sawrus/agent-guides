//! Project setup of the `pocock` skill pack preset (docs/skill-packs.md). It replaces the upstream
//! skill `setup-matt-pocock-skills`: agentic writes the files that the other skills expect
//! (`docs/agents/*.md`) and the `## Agent skills` section of the generated AGENTS.md.

use crate::app::App;

/// Id of the preset that needs the setup.
pub const PACK_ID: &str = "pocock";
pub const TRACKERS: [&str; 3] = ["local", "github", "gitlab"];
pub const DEFAULT_TRACKER: &str = "local";

const DOMAIN: &str = include_str!("pocock_setup/domain.md");
const TRIAGE_LABELS: &str = include_str!("pocock_setup/triage-labels.md");
const TRACKER_LOCAL: &str = include_str!("pocock_setup/issue-tracker-local.md");
const TRACKER_GITHUB: &str = include_str!("pocock_setup/issue-tracker-github.md");
const TRACKER_GITLAB: &str = include_str!("pocock_setup/issue-tracker-gitlab.md");

/// Validate `--issue-tracker`.
pub fn parse_tracker(value: &str) -> crate::Result<String> {
    let value = value.trim().to_lowercase();
    if TRACKERS.contains(&value.as_str()) {
        Ok(value)
    } else {
        Err(format!(
            "--issue-tracker: expected {}, got '{value}'",
            TRACKERS.join(", ")
        )
        .into())
    }
}

/// True when the preset `pocock` is installed in this run.
pub fn active(app: &App) -> bool {
    app.skill_packs.iter().any(|p| p.id == PACK_ID)
}

/// The chosen issue tracker; `local` without a choice.
pub fn tracker(app: &App) -> &str {
    app.issue_tracker
        .as_deref()
        .filter(|t| TRACKERS.contains(t))
        .unwrap_or(DEFAULT_TRACKER)
}

/// Files of the setup: (project-relative path, text, manifest source name without `/`).
pub fn files(app: &App) -> Vec<(&'static str, String, &'static str)> {
    if !active(app) {
        return Vec::new();
    }
    let tracker_doc = match tracker(app) {
        "github" => TRACKER_GITHUB,
        "gitlab" => TRACKER_GITLAB,
        _ => TRACKER_LOCAL,
    };
    vec![
        (
            "docs/agents/issue-tracker.md",
            tracker_doc.to_string(),
            "setup.issue-tracker.md",
        ),
        (
            "docs/agents/triage-labels.md",
            TRIAGE_LABELS.to_string(),
            "setup.triage-labels.md",
        ),
        (
            "docs/agents/domain.md",
            DOMAIN.to_string(),
            "setup.domain.md",
        ),
    ]
}

/// First line of the managed `## Agent skills` block in the generated AGENTS.md.
pub const SECTION_BEGIN: &str = "<!-- agentic:agent-skills:begin -->";
/// Last line of that block.
pub const SECTION_END: &str = "<!-- agentic:agent-skills:end -->";

/// True when `text` has a `## Agent skills` heading outside the agentic block: the project wrote its
/// own section, and agentic must not add a second one.
pub fn has_own_section(text: &str) -> bool {
    let mut inside = false;
    for line in text.lines() {
        let line = line.trim_end();
        if line == SECTION_BEGIN {
            inside = true;
        } else if line == SECTION_END {
            inside = false;
        } else if !inside && line == "## Agent skills" {
            return true;
        }
    }
    false
}

/// The `## Agent skills` section of the generated AGENTS.md, in the shape of the upstream setup skill,
/// between [`SECTION_BEGIN`] and [`SECTION_END`]. The generator puts it right after the header, so
/// that project edits at the end of the file merge without a conflict.
pub fn agents_section(app: &App) -> Option<String> {
    if !active(app) {
        return None;
    }
    let summary = match tracker(app) {
        "github" => "Issues live in GitHub Issues (`gh` CLI).",
        "gitlab" => "Issues live in GitLab Issues (`glab` CLI).",
        _ => "Issues live as markdown files under `.scratch/<feature>/`.",
    };
    Some(format!(
        "{SECTION_BEGIN}\n## Agent skills\n\n\
         ### Issue tracker\n\n{summary} See `docs/agents/issue-tracker.md`.\n\n\
         ### Triage labels\n\nDefault vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. \
         See `docs/agents/triage-labels.md`.\n\n\
         ### Domain docs\n\nSingle-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.\n{SECTION_END}\n"
    ))
}

/// Name of the agentic-authored skill that stands in for the upstream `setup-matt-pocock-skills`.
pub const SETUP_SKILL: &str = "setup-matt-pocock-skills";

/// Text of that skill: upstream skills still say "run `/setup-matt-pocock-skills`".
pub const SETUP_SKILL_TEXT: &str = "---
name: setup-matt-pocock-skills
description: Project setup for the pocock skill pack is managed by agentic.
disable-model-invocation: true
---

# Setup of the pocock skills

agentic configured this repo for the pocock skills. Do not set it up by hand.

- Read `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, and `docs/agents/domain.md`.
- To change the issue tracker, run `agentic skills add pocock --issue-tracker local|github|gitlab`
  (or `agentic install` and the TUI).
- `GLOSSARY.md` and `docs/adr/` do not need setup. The `domain-modeling` skill creates them when needed.
- If a file in `docs/agents/` is missing, tell the user to run the command above. Do not create it by hand.
";
