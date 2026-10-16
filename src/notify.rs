//! Telegram notifications for Claude Code and Codex through native hooks.
//! OpenCode keeps its plugin; all hosts share one enablement flag and the
//! global credentials in `~/.config/agentic/config.json`.

use crate::app::App;
use crate::hookmerge::{self, HookSet};
use crate::{config, ui};
use std::path::Path;

pub const RUNTIME_REL: &str = ".agent/notify/telegram.py";
const RUNTIME_SOURCE: &str = "extensions/codex/hooks/notify/telegram.py";
const RUNTIME: &str = include_str!("../extensions/codex/hooks/notify/telegram.py");
const CLAUDE_OWNERSHIP: &str = ".agentic/claude-notify-hook-entries.json";
const CODEX_OWNERSHIP: &str = ".agentic/codex-notify-hook-entries.json";

fn hook_hosts(app: &App) -> bool {
    app.selected_agent_os_contains("claude") || app.selected_agent_os_contains("codex")
}

pub fn enabled(app: &App) -> bool {
    app.opencode_telegram_enabled == "true"
}

/// Resolve enablement: explicit flag, then saved settings, then an interactive question.
pub fn configure(app: &mut App) -> crate::Result<()> {
    if let Some(explicit) = app.telegram_cli {
        app.opencode_telegram_enabled = explicit.to_string();
        if explicit && !config::load_global_telegram_credentials(app) {
            ui::warn(app, &format!("Telegram enabled without saved credentials; hooks stay silent until botToken/chatId exist in {}", app.app_config_json_file().display()));
        }
        return Ok(());
    }
    if !hook_hosts(app)
        || app.selected_agent_os_contains("opencode")
        || app.upgrade_mode
        || app.dry_run
        || !app.opencode_telegram_enabled.is_empty()
    {
        return Ok(());
    }
    let wanted = app.is_interactive_terminal()
        && crate::prompt::read_yes_no(app, "Enable Telegram notifications (Claude/Codex hooks)?");
    let wanted = wanted && crate::install::prompt_telegram_credentials(app)?;
    app.opencode_telegram_enabled = wanted.to_string();
    Ok(())
}

fn command(host: &str, event: &str) -> String {
    if host == "claude" {
        // Claude may run hooks from a subdirectory; anchor them to the project root.
        return format!(
            "{} \"$CLAUDE_PROJECT_DIR/{RUNTIME_REL}\" --host claude --event {event} --project-dir \"$CLAUDE_PROJECT_DIR\"",
            hookmerge::python()
        );
    }
    format!(
        "{} {RUNTIME_REL} --host {host} --event {event}",
        hookmerge::python()
    )
}

fn hook_sets() -> [HookSet<'static>; 2] {
    [
        HookSet {
            config_rel: ".claude/settings.json",
            ownership_rel: CLAUDE_OWNERSHIP,
            command_marker: RUNTIME_REL,
            status_message: "Agentic Telegram",
            source_ref: "generated:claude-settings",
            label: "Telegram",
            entries: vec![
                ("Stop", "", command("claude", "stop"), 10),
                (
                    "Notification",
                    "permission_prompt|idle_prompt",
                    command("claude", "waiting"),
                    10,
                ),
            ],
        },
        HookSet {
            config_rel: ".codex/hooks.json",
            ownership_rel: CODEX_OWNERSHIP,
            command_marker: RUNTIME_REL,
            status_message: "Agentic Telegram",
            source_ref: "generated:codex-jev-hooks",
            label: "Telegram",
            entries: vec![
                ("Stop", "*", command("codex", "stop"), 10),
                ("PermissionRequest", "*", command("codex", "waiting"), 10),
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
    let path = project.join(RUNTIME_REL);
    let referenced = [".claude/settings.json", ".codex/hooks.json"]
        .iter()
        .any(|rel| {
            std::fs::read_to_string(project.join(rel))
                .ok()
                .is_some_and(|s| s.contains(RUNTIME_REL))
        });
    if (on && hook_hosts(app)) || referenced {
        crate::manifest::write_file_with_agentic_marker(app, RUNTIME, &path, RUNTIME_SOURCE)?;
        if on && app.selected_agent_os_contains("codex") && !app.dry_run {
            ui::log(app, "Codex Telegram hooks installed. Review and trust them through /hooks in the target project.");
        }
    } else if !app.dry_run && path.is_file() {
        crate::legacy::remove_if_unmodified(app, project, RUNTIME_REL, "Telegram runtime")?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hooks_and_runtime_follow_enablement() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let mut app = App::new().unwrap();
        app.project_dir = p.to_string_lossy().into();
        app.selected_agent_os = vec!["claude".into(), "codex".into()];
        app.opencode_telegram_enabled = "true".into();
        install(&mut app, p).unwrap();
        let claude = std::fs::read_to_string(p.join(".claude/settings.json")).unwrap();
        assert!(claude.contains("--host claude --event stop"));
        assert!(claude.contains("permission_prompt|idle_prompt"));
        let codex = std::fs::read_to_string(p.join(".codex/hooks.json")).unwrap();
        assert!(codex.contains("--host codex --event waiting"));
        assert!(p.join(RUNTIME_REL).is_file());
        crate::manifest::write_agentic_manifest(&mut app, p).unwrap();

        let mut app = App::new().unwrap();
        app.project_dir = p.to_string_lossy().into();
        app.selected_agent_os = vec!["claude".into(), "codex".into()];
        app.opencode_telegram_enabled = "false".into();
        install(&mut app, p).unwrap();
        assert!(!std::fs::read_to_string(p.join(".claude/settings.json"))
            .unwrap()
            .contains(RUNTIME_REL));
        assert!(!p.join(RUNTIME_REL).exists());
    }
}
