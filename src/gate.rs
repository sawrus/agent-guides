//! Quality gate. Claude Code and Codex call the shared runtime from native Stop,
//! PreToolUse, and SessionStart (stale-checkout notice) hooks; the OpenCode
//! plugin forwards to the same runtime. On by default; `--disable-gate` removes
//! the managed hook groups and the runtime.

use crate::app::App;
use crate::hookmerge::{self, HookSet};
use crate::ui;
use std::path::Path;

pub const RUNTIME_REL: &str = ".agent/gate/gate.py";
const RUNTIME_SOURCE: &str = "extensions/codex/hooks/gate/gate.py";
const RUNTIME: &str = include_str!("../extensions/codex/hooks/gate/gate.py");
pub const OPENCODE_PLUGIN_REL: &str = "plugins/agentic-gate.ts";
const BASELINE_REL: &str = ".agentic/gate/baseline.json";
const CLAUDE_OWNERSHIP: &str = ".agentic/claude-gate-hook-entries.json";
const CODEX_OWNERSHIP: &str = ".agentic/codex-gate-hook-entries.json";
/// Project checks may take minutes; the gate bounds each command itself.
const STOP_TIMEOUT: u64 = 900;
const GUARD_TIMEOUT: u64 = 10;
/// Session start reads local refs only (stale-checkout notice, `src/gitstate.rs`).
const START_TIMEOUT: u64 = 10;
/// New and resumed sessions; `clear` and `compact` do not repeat the notice.
const START_MATCHER: &str = "startup|resume";

pub fn enabled(app: &App) -> bool {
    app.gate_enabled != Some(false)
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
            status_message: "Agentic gate",
            source_ref: "generated:claude-settings",
            label: "Gate",
            entries: vec![
                ("Stop", "", command("claude", "stop"), STOP_TIMEOUT),
                (
                    "SessionStart",
                    START_MATCHER,
                    command("claude", "start"),
                    START_TIMEOUT,
                ),
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
                    "SessionStart",
                    START_MATCHER,
                    command("codex", "start"),
                    START_TIMEOUT,
                ),
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

/// Record the uncommitted files as they stand after install, so the Stop gate does not take the
/// installed artifacts (or older uncommitted work) for agent changes. Hashes only; no contents.
pub fn write_baseline(app: &mut App, project: &Path) -> crate::Result<()> {
    if app.dry_run || !enabled(app) {
        return Ok(());
    }
    let Ok(out) = std::process::Command::new("git")
        .arg("-C")
        .arg(project)
        .args(["status", "--porcelain", "-z", "--untracked-files=all"])
        .output()
    else {
        return Ok(());
    };
    if !out.status.success() {
        return Ok(());
    }
    let text = String::from_utf8_lossy(&out.stdout);
    let mut files = serde_json::Map::new();
    let mut entries = text.split('\0').filter(|e| e.len() > 3);
    while let Some(entry) = entries.next() {
        let (status, rel) = entry.split_at(3);
        if status.starts_with('R') || status.starts_with('C') {
            entries.next(); // the original path of a rename or copy
        }
        if rel.starts_with(".agentic/") || rel.starts_with(".git/") {
            continue;
        }
        let hash = crate::util::hash_file(&project.join(rel)).ok();
        files.insert(rel.to_string(), serde_json::json!(hash));
    }
    let path = project.join(BASELINE_REL);
    std::fs::create_dir_all(path.parent().unwrap())?;
    std::fs::write(
        path,
        crate::markers::to_pretty_json(&serde_json::json!({ "files": files })),
    )?;
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
        let settings: serde_json::Value = serde_json::from_str(&claude).unwrap();
        assert_eq!(
            settings["hooks"]["SessionStart"][0]["matcher"],
            START_MATCHER
        );
        assert!(claude.contains("--event start"));
        let codex = std::fs::read_to_string(p.join(".codex/hooks.json")).unwrap();
        assert!(codex.contains(RUNTIME_REL) && codex.contains("--event start"));
        let owned = std::fs::read_to_string(p.join(CLAUDE_OWNERSHIP)).unwrap();
        assert!(owned.contains("SessionStart"));
        assert!(p.join(RUNTIME_REL).is_file());
        a.gate_enabled = Some(false);
        install(&mut a, p).unwrap();
        let claude = std::fs::read_to_string(p.join(".claude/settings.json")).unwrap();
        assert!(!claude.contains(RUNTIME_REL));
    }

    /// A release without SessionStart left Stop and PreToolUse ownership records; an upgrade adds
    /// SessionStart and keeps the owned groups, without conflicts.
    #[test]
    fn upgrade_adds_session_start_to_older_gate_hooks() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let mut a = app(p, &["claude", "codex"]);
        install(&mut a, p).unwrap();
        for (config, ownership) in [
            (".claude/settings.json", CLAUDE_OWNERSHIP),
            (".codex/hooks.json", CODEX_OWNERSHIP),
        ] {
            for rel in [config, ownership] {
                let path = p.join(rel);
                let mut data: serde_json::Value =
                    serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
                let map = if data.get("hooks").is_some() {
                    &mut data["hooks"]
                } else {
                    &mut data
                };
                map.as_object_mut().unwrap().remove("SessionStart");
                std::fs::write(&path, data.to_string()).unwrap();
            }
        }
        let mut b = app(p, &["claude", "codex"]);
        install(&mut b, p).unwrap();
        assert!(b.skipped_managed_paths.is_empty());
        for config in [".claude/settings.json", ".codex/hooks.json"] {
            let data: serde_json::Value =
                serde_json::from_str(&std::fs::read_to_string(p.join(config)).unwrap()).unwrap();
            for event in ["Stop", "PreToolUse", "SessionStart"] {
                assert_eq!(
                    data["hooks"][event].as_array().unwrap().len(),
                    1,
                    "{config} {event}"
                );
            }
        }
    }

    #[test]
    fn baseline_records_uncommitted_files() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let git = |args: &[&str]| {
            std::process::Command::new("git")
                .arg("-C")
                .arg(p)
                .args(args)
                .output()
                .unwrap()
        };
        git(&["init", "-q"]);
        std::fs::write(p.join("AGENTS.md"), "guide\n").unwrap();
        std::fs::create_dir_all(p.join(".agentic")).unwrap();
        std::fs::write(p.join(".agentic/x.json"), "{}").unwrap();
        let mut a = app(p, &["claude"]);
        write_baseline(&mut a, p).unwrap();
        let data: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(p.join(BASELINE_REL)).unwrap()).unwrap();
        assert_eq!(
            data["files"]["AGENTS.md"],
            serde_json::json!(crate::util::sha256_hex(b"guide\n"))
        );
        assert_eq!(data["files"].as_object().unwrap().len(), 1);
    }
}
