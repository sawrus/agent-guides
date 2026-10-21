//! Install profile. `lean` (default) installs two helper subagents and lets the native harness lead;
//! `team` installs the v1 SDLC role team. JEV routes between team roles, so it always uses `team`.

use crate::app::App;
use serde_json::{json, Value};
use std::path::Path;

pub const LEAN: &str = "lean";
pub const TEAM: &str = "team";
pub const CHOICES: [&str; 2] = [LEAN, TEAM];
pub const LEAN_AGENTS: [&str; 2] = ["explorer", "reviewer"];
pub const TEAM_AGENTS: [&str; 9] = [
    "product-owner",
    "pm",
    "team-lead",
    "analyst",
    "developer",
    "qa",
    "devops-engineer",
    "instruction-reviewer",
    "memory-curator",
];

pub fn is_team(app: &App) -> bool {
    app.install_profile == TEAM || app.jev_enabled == Some(true)
}

pub fn effective(app: &App) -> &'static str {
    if is_team(app) {
        TEAM
    } else {
        LEAN
    }
}

/// Extension files that belong to the other profile.
pub fn skips_extension_file(app: &App, src_rel: &str, rel: &str) -> bool {
    if src_rel == "extensions/codex" && rel == "AGENTS.override.md" {
        return !is_team(app);
    }
    let Some(name) = rel
        .strip_prefix("agents/")
        .and_then(|file| file.rsplit_once('.'))
        .map(|(stem, _)| stem)
    else {
        return false;
    };
    if is_team(app) {
        LEAN_AGENTS.contains(&name)
    } else {
        TEAM_AGENTS.contains(&name)
    }
}

/// The lean OpenCode config keeps the native primary agent and declares only the helper subagents.
pub fn lean_opencode_agents(data: &mut Value) {
    let Some(agents) = data.get_mut("agent").and_then(Value::as_object_mut) else {
        return;
    };
    agents.retain(|name, _| !TEAM_AGENTS.contains(&name.as_str()));
    for name in LEAN_AGENTS {
        agents
            .entry(name)
            .or_insert_with(|| json!({ "mode": "subagent" }));
    }
}

pub fn apply_opencode(app: &mut App, project: &Path) -> crate::Result<()> {
    if is_team(app) || app.dry_run || !app.selected_agent_os_contains("opencode") {
        return Ok(());
    }
    let dest = project.join(".opencode/opencode.json");
    let Ok(text) = std::fs::read_to_string(&dest) else {
        return Ok(());
    };
    let mut data: Value = serde_json::from_str(&text)?;
    lean_opencode_agents(&mut data);
    let output = crate::markers::to_pretty_json(&data);
    if output != text {
        std::fs::write(&dest, output)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lean_skips_team_roles_and_codex_override() {
        let mut app = App::new().unwrap();
        app.install_profile = LEAN.into();
        app.jev_enabled = Some(false);
        assert!(skips_extension_file(
            &app,
            "extensions/claude",
            "agents/product-owner.md"
        ));
        assert!(!skips_extension_file(
            &app,
            "extensions/claude",
            "agents/explorer.md"
        ));
        assert!(skips_extension_file(
            &app,
            "extensions/codex",
            "AGENTS.override.md"
        ));
        assert!(!skips_extension_file(
            &app,
            "extensions/claude",
            "CLAUDE.md"
        ));
    }

    #[test]
    fn team_and_jev_keep_v1_roles() {
        let mut app = App::new().unwrap();
        app.install_profile = TEAM.into();
        assert!(!skips_extension_file(
            &app,
            "extensions/codex",
            "agents/qa.toml"
        ));
        assert!(skips_extension_file(
            &app,
            "extensions/codex",
            "agents/reviewer.toml"
        ));
        app.install_profile = LEAN.into();
        app.jev_enabled = Some(true);
        assert_eq!(effective(&app), TEAM);
    }

    #[test]
    fn lean_opencode_config_keeps_user_agents() {
        let mut data =
            json!({"agent": {"product-owner": {"mode": "primary"}, "mine": {"mode": "subagent"}}});
        lean_opencode_agents(&mut data);
        let agents = data["agent"].as_object().unwrap();
        assert!(!agents.contains_key("product-owner"));
        assert!(
            agents.contains_key("mine")
                && agents.contains_key("explorer")
                && agents.contains_key("reviewer")
        );
    }
}
