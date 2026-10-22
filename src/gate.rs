//! Quality gate. Claude Code and Codex call the shared runtime from native Stop
//! and PreToolUse hooks; the OpenCode plugin forwards to the same runtime. On by
//! default; `--disable-gate` removes the managed hook groups and the runtime.

use crate::app::App;
use crate::hookmerge::{self, HookSet};
use crate::ui;
use std::path::Path;

pub const RUNTIME_REL: &str = ".agent/gate/gate.py";
const RUNTIME_SOURCE: &str = "extensions/codex/hooks/gate/gate.py";
const RUNTIME: &str = include_str!("../extensions/codex/hooks/gate/gate.py");
pub const OPENCODE_PLUGIN_REL: &str = "plugins/agentic-gate.ts";
const CLAUDE_OWNERSHIP: &str = ".agentic/claude-gate-hook-entries.json";
const CODEX_OWNERSHIP: &str = ".agentic/codex-gate-hook-entries.json";
/// Project checks may take minutes; the gate bounds each command itself.
const STOP_TIMEOUT: u64 = 900;
const GUARD_TIMEOUT: u64 = 10;

pub fn enabled(app: &App) -> bool {
    app.gate_enabled != Some(false)
}

fn command(host: &str, event: &str) -> String {
    if host == "claude" {
        // Claude may run hooks from a subdirectory; anchor them to the project root.
        return format!(
            "{} \"$CLAUDE_PROJECT_DIR/{RUNTIME_REL}\" --event {event} --project-dir \"$CLAUDE_PROJECT_DIR\"",
            hookmerge::python()
        );
    }
    format!("{} {RUNTIME_REL} --event {event}", hookmerge::python())
}

fn hook_sets() -> [HookSet<'static>; 2] {
    [
        HookSet {
            config_rel: ".claude/settings.json",
            ownership_rel: CLAUDE_OWNERSHIP,
            command_marker: RUNTIME_REL,
            status_message: "Agentic gate",
            source_ref: "generated:claude-settings",
            label: "Gate",
            entries: vec![
                ("Stop", "", command("claude", "stop"), STOP_TIMEOUT),
                (
                    "PreToolUse",
                    "Bash|Read|Edit|Write|MultiEdit",
                    command("claude", "guard"),
                    GUARD_TIMEOUT,
                ),
            ],
        },
        HookSet {
            config_rel: ".codex/hooks.json",
            ownership_rel: CODEX_OWNERSHIP,
            command_marker: RUNTIME_REL,
            status_message: "Agentic gate",
            source_ref: "generated:codex-jev-hooks",
            label: "Gate",
            entries: vec![
                ("Stop", "*", command("codex", "stop"), STOP_TIMEOUT),
                (
                    "PreToolUse",
                    "Bash|apply_patch",
                    command("codex", "guard"),
                    GUARD_TIMEOUT,
                ),
            ],
        },
    ]
}

pub fn install(app: &mut App, project: &Path) -> crate::Result<()> {
    let on = enabled(app);
    for (set, host) in hook_sets().iter().zip(["claude", "codex"]) {
        let selected = app.selected_agent_os_contains(host);
        if selected || project.join(set.ownership_rel).exists() {
            hookmerge::sync(app, project, set, on && selected)?;
        }
    }
    let hosts = ["claude", "codex", "opencode"]
        .iter()
        .any(|h| app.selected_agent_os_contains(h));
    let path = project.join(RUNTIME_REL);
    if on && hosts {
        crate::manifest::write_file_with_agentic_marker(app, RUNTIME, &path, RUNTIME_SOURCE)?;
        if app.selected_agent_os_contains("codex") && !app.dry_run {
            ui::log(
                app,
                "Codex gate hooks installed. Review and trust them through /hooks in the target project.",
            );
        }
    } else if !app.dry_run && path.is_file() {
        crate::legacy::remove_if_unmodified(app, project, RUNTIME_REL, "Gate runtime")?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn app(project: &Path, hosts: &[&str]) -> App {
        let mut app = App::new().unwrap();
        app.project_dir = project.to_string_lossy().to_string();
        app.selected_agent_os = hosts.iter().map(|h| h.to_string()).collect();
        app
    }

    #[test]
    fn gate_hooks_follow_enablement() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let mut a = app(p, &["claude", "codex"]);
        install(&mut a, p).unwrap();
        let claude = std::fs::read_to_string(p.join(".claude/settings.json")).unwrap();
        assert!(claude.contains("--event stop") && claude.contains("--event guard"));
        let codex = std::fs::read_to_string(p.join(".codex/hooks.json")).unwrap();
        assert!(codex.contains(RUNTIME_REL));
        assert!(p.join(RUNTIME_REL).is_file());
        a.gate_enabled = Some(false);
        install(&mut a, p).unwrap();
        let claude = std::fs::read_to_string(p.join(".claude/settings.json")).unwrap();
        assert!(!claude.contains(RUNTIME_REL));
    }
}
