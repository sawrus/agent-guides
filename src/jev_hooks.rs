//! JEV activation and installation of shared runtime and native hook adapters.

use crate::{app::App, hookmerge, manifest::write_file_with_agentic_marker};
use std::path::Path;

pub const DEFAULT_API_URL: &str = "https://api.typesafe.ai/v1/systemone";

pub fn configure(app: &mut App) -> crate::Result<()> {
    let enabled = if let Some(enabled) = app.jev_enabled {
        enabled
    } else if app.selected_mcp_contains("jev") {
        true
    } else {
        app.is_interactive_terminal() && crate::prompt::read_yes_no(app, "Enable JEV native hooks?")
    };
    app.jev_enabled = Some(enabled);
    app.selected_mcps.retain(|id| id != "jev");
    if enabled {
        crate::mcp::add_selected_mcp(app, "jev");
    }
    if app.jev_api_url.is_none() {
        let existing = std::fs::read_to_string(app.project_manifest_path())
            .ok()
            .and_then(|s| serde_json::from_str::<serde_json::Value>(&s).ok());
        app.jev_api_url =
            existing.and_then(|v| v["settings"]["jev"]["api_url"].as_str().map(str::to_owned));
    }
    let api_url = app
        .jev_api_url
        .get_or_insert_with(|| DEFAULT_API_URL.into());
    let url = reqwest::Url::parse(api_url).map_err(|_| "Invalid JEV API URL")?;
    if url.scheme() != "https"
        || url.host_str().is_none()
        || !url.username().is_empty()
        || url.password().is_some()
        || url.fragment().is_some()
    {
        return Err("JEV API URL must be HTTPS without credentials or fragment".into());
    }
    if enabled && app.tui_mode {
        let choice = crate::prompt::choose_single_by_index(
            app,
            "JEV API key:",
            &[
                "Use environment or existing project .env".into(),
                "Enter key and save in project .env".into(),
            ],
        )?;
        if choice == "Enter key and save in project .env" {
            let name = if url.host_str() == Some("api.typesafe.ai") {
                "TYPESAFE_API_KEY"
            } else {
                "JEV_API_KEY"
            };
            let key =
                crate::tui::screen_secret_input(app, name).ok_or("JEV key entry cancelled")?;
            if !app.dry_run {
                save_key(Path::new(&app.project_dir), name, &key)?;
            }
        }
    }
    Ok(())
}

fn save_key(project: &Path, name: &str, key: &str) -> crate::Result<()> {
    use std::io::Write;
    if key.is_empty()
        || !key
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || "_-.+/=".contains(c))
    {
        return Err("Invalid JEV key; value omitted".into());
    }
    let path = project.join(".env");
    let ignore = project.join(".gitignore");
    if std::fs::symlink_metadata(&ignore).is_ok_and(|m| m.file_type().is_symlink()) {
        return Err("Refusing to modify a symlinked .gitignore".into());
    }
    if std::fs::symlink_metadata(&path).is_ok_and(|m| m.file_type().is_symlink()) {
        return Err("Refusing to replace a symlinked .env".into());
    }
    let read_existing = |file: &Path| -> std::io::Result<String> {
        match std::fs::read_to_string(file) {
            Ok(text) => Ok(text),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(String::new()),
            Err(e) => Err(e),
        }
    };
    let existing = read_existing(&path)?;
    let mut rules = read_existing(&ignore)?;
    let mut content = String::new();
    for line in existing.lines() {
        let assignment = line.trim().strip_prefix("export ").unwrap_or(line.trim());
        if assignment
            .split_once('=')
            .is_some_and(|(field, _)| field.trim() == name)
        {
            continue;
        }
        content.push_str(line);
        content.push('\n');
    }
    content.push_str(&format!("{name}=\"{key}\"\n"));
    let mut options = std::fs::OpenOptions::new();
    options.write(true).create(true).truncate(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(&path)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        file.set_permissions(std::fs::Permissions::from_mode(0o600))?;
    }
    file.write_all(content.as_bytes())?;
    if !rules
        .lines()
        .any(|line| matches!(line.trim(), ".env" | "/.env"))
    {
        if !rules.is_empty() && !rules.ends_with('\n') {
            rules.push('\n');
        }
        rules.push_str(".env\n");
        std::fs::write(ignore, rules)?;
    }
    Ok(())
}

/// Ignore runtime directories independently of JEV/key enablement.
pub fn ensure_ignores(app: &mut App, project: &Path) -> crate::Result<()> {
    if app.dry_run {
        return Ok(());
    }
    let path = project.join(".gitignore");
    if std::fs::symlink_metadata(&path).is_ok_and(|m| m.file_type().is_symlink()) {
        return Err("Refusing to modify a symlinked .gitignore".into());
    }
    let mut content = match std::fs::read_to_string(&path) {
        Ok(s) => s,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => String::new(),
        Err(e) => return Err(e.into()),
    };
    for rule in [".agentic*/", ".review*/"] {
        if !content.lines().any(|line| line.trim() == rule) {
            if !content.is_empty() && !content.ends_with('\n') {
                content.push('\n');
            }
            content.push_str(rule);
            content.push('\n');
        }
    }
    std::fs::write(path, content)?;
    Ok(())
}

fn cleanup_legacy(app: &mut App, project: &Path) -> crate::Result<()> {
    if app.dry_run {
        return Ok(());
    }
    let old: serde_json::Value = std::fs::read_to_string(app.project_manifest_path())
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();
    for item in old["managed_files"].as_array().into_iter().flatten() {
        let Some(rel) = item["path"].as_str() else {
            continue;
        };
        if !rel.contains("/skills/jev/") {
            continue;
        }
        let path = crate::project_inventory::safe_path(project, rel)?;
        if !path.is_file() {
            continue;
        }
        if crate::util::hash_file(&path).ok().as_deref() == item["content_hash"].as_str() {
            std::fs::remove_file(path)?;
        } else {
            crate::ui::warn(
                app,
                &format!("Preserving locally edited legacy JEV asset: {rel}"),
            );
            app.record_skipped(rel);
            // Keep edited legacy assets in the desired set even during force cleanup.
            app.managed_records.push(crate::app::ManagedRecord {
                path: rel.to_string(),
                source: item["source"].as_str().unwrap_or("legacy:jev").to_string(),
                content_hash: item["content_hash"].as_str().unwrap_or("").to_string(),
                marker: item["marker"].as_str().unwrap_or("internal").to_string(),
            });
        }
    }
    Ok(())
}

pub const CODEX_OWNERSHIP: &str = ".agentic/jev-hook-entries.json";
pub const CLAUDE_OWNERSHIP: &str = ".agentic/claude-jev-hook-entries.json";

/// Each native hook handler is owned individually; unrelated handlers survive.
fn codex_hooks(app: &mut App, project: &Path, enabled: bool) -> crate::Result<()> {
    let command = format!("{} .agent/jev/hook.py --host codex", hookmerge::python());
    let set = hookmerge::HookSet {
        config_rel: ".codex/hooks.json",
        ownership_rel: CODEX_OWNERSHIP,
        command_marker: ".agent/jev/hook.py",
        status_message: "Agentic JEV",
        source_ref: "generated:codex-jev-hooks",
        label: "JEV",
        entries: vec![
            ("UserPromptSubmit", "*", command.clone(), 12),
            (
                "PreToolUse",
                r"spawn_agent|Agent|collaborationspawn_agent|collaboration\.spawn_agent|functions\.spawn_agent",
                command.clone(),
                12,
            ),
            ("PermissionRequest", "*", command.clone(), 12),
            ("PostToolUse", "*", command.clone(), 12),
            ("SubagentStart", "*", command, 12),
        ],
    };
    hookmerge::sync(app, project, &set, enabled)?;
    if enabled && !app.dry_run {
        crate::ui::log(app, "Codex JEV hooks installed. Review and trust them through /hooks in the target project; hook trust is never bypassed.");
    }
    Ok(())
}

/// Claude Code reads hooks from `.claude/settings.json`; the Agent tool accepts model aliases only.
fn claude_hooks(app: &mut App, project: &Path, enabled: bool) -> crate::Result<()> {
    // Claude may run hooks from a subdirectory; anchor them to the project root.
    let command = format!(
        "{} \"$CLAUDE_PROJECT_DIR/.agent/jev/hook.py\" --host claude --project-dir \"$CLAUDE_PROJECT_DIR\"",
        hookmerge::python()
    );
    let set = hookmerge::HookSet {
        config_rel: ".claude/settings.json",
        ownership_rel: CLAUDE_OWNERSHIP,
        command_marker: ".agent/jev/hook.py",
        status_message: "Agentic JEV",
        source_ref: "generated:claude-settings",
        label: "JEV",
        entries: vec![
            ("UserPromptSubmit", "", command.clone(), 12),
            ("PreToolUse", "Agent|Task", command.clone(), 12),
            ("PermissionRequest", "", command.clone(), 12),
            ("PostToolUse", "", command.clone(), 12),
            ("SubagentStart", "", command.clone(), 12),
            ("SubagentStop", "", command, 12),
        ],
    };
    hookmerge::sync(app, project, &set, enabled)
}

/// `/jev on|off|status`: the hooks handle the switch before any model turn.
const CLAUDE_SWITCH_COMMAND: &str = ".claude/commands/jev.md";
const OPENCODE_SWITCH_COMMAND: &str = ".opencode/commands/jev.md";
const SWITCH_COMMAND_SOURCE: &str = "extensions/codex/hooks/jev/jev-command.md";

/// Runtime data that only the OpenCode plugin and its hook events read.
const OPENCODE_ONLY: [&str; 2] = [
    ".agent/jev/opencode-profile-defaults.json",
    ".agent/jev/opencode-model-tiers.json",
];

pub fn install(app: &mut App, project: &Path) -> crate::Result<()> {
    cleanup_legacy(app, project)?;
    let enabled = app.jev_enabled == Some(true);
    if app.selected_agent_os_contains("codex") || project.join(CODEX_OWNERSHIP).exists() {
        codex_hooks(
            app,
            project,
            enabled && app.selected_agent_os_contains("codex"),
        )?;
    }
    if app.selected_agent_os_contains("claude") || project.join(CLAUDE_OWNERSHIP).exists() {
        claude_hooks(
            app,
            project,
            enabled && app.selected_agent_os_contains("claude"),
        )?;
    }
    // Edited hooks may still reference the managed runtime after disablement.
    // Keep a disabled no-op runtime rather than leaving those preserved commands broken.
    let retained_reference = [".codex/hooks.json", ".claude/settings.json"]
        .iter()
        .any(|rel| {
            std::fs::read_to_string(project.join(rel))
                .ok()
                .is_some_and(|s| s.contains(".agent/jev/hook.py"))
        });
    let defaults = crate::jev_defaults::model_defaults(app);
    let defaults_json = serde_json::to_string_pretty(&defaults)?;
    let opencode_defaults_json =
        serde_json::to_string_pretty(&crate::jev_defaults::opencode_profile_defaults(app))?;
    let assets = [
        (
            ".agent/jev/api.py",
            include_str!("../extensions/codex/hooks/jev/api.py"),
        ),
        (
            ".agent/jev/hook.py",
            include_str!("../extensions/codex/hooks/jev/hook.py"),
        ),
        (
            ".agent/jev/questions.py",
            include_str!("../extensions/codex/hooks/jev/questions.py"),
        ),
        (
            ".agent/jev/routing.py",
            include_str!("../extensions/codex/hooks/jev/routing.py"),
        ),
        (
            ".agent/jev/adapters.py",
            include_str!("../extensions/codex/hooks/jev/adapters.py"),
        ),
        (".agent/jev/model-defaults.json", defaults_json.as_str()),
        (
            ".agent/jev/opencode-profile-defaults.json",
            opencode_defaults_json.as_str(),
        ),
        (
            ".agent/jev/opencode-model-tiers.json",
            include_str!("../extensions/opencode/model-tiers.json"),
        ),
        (
            ".opencode/plugins/agentic-jev/index.ts",
            include_str!("../extensions/opencode/hooks/agentic-jev.ts"),
        ),
        (
            CLAUDE_SWITCH_COMMAND,
            include_str!("../extensions/codex/hooks/jev/jev-command.md"),
        ),
        (
            OPENCODE_SWITCH_COMMAND,
            include_str!("../extensions/codex/hooks/jev/jev-command.md"),
        ),
    ];
    for (rel, content) in assets {
        let host_specific = OPENCODE_ONLY.contains(&rel) || rel == ".agent/jev/model-defaults.json";
        let wanted = (OPENCODE_ONLY.contains(&rel)
            && enabled
            && app.selected_agent_os_contains("opencode"))
            || (rel == ".agent/jev/model-defaults.json"
                && enabled
                && (app.selected_agent_os_contains("codex")
                    || app.selected_agent_os_contains("claude")))
            || (rel.starts_with(".agent/") && !host_specific && (enabled || retained_reference))
            || (enabled
                && app.selected_agent_os_contains("opencode")
                && rel.starts_with(".opencode/"))
            || (rel == CLAUDE_SWITCH_COMMAND
                && enabled
                && app.selected_agent_os_contains("claude"));
        let path = project.join(rel);
        if wanted {
            let source = match rel {
                ".agent/jev/api.py" => "extensions/codex/hooks/jev/api.py",
                ".agent/jev/hook.py" => "extensions/codex/hooks/jev/hook.py",
                ".agent/jev/questions.py" => "extensions/codex/hooks/jev/questions.py",
                ".agent/jev/routing.py" => "extensions/codex/hooks/jev/routing.py",
                ".agent/jev/adapters.py" => "extensions/codex/hooks/jev/adapters.py",
                ".opencode/plugins/agentic-jev/index.ts" => {
                    "extensions/opencode/hooks/agentic-jev.ts"
                }
                ".agent/jev/opencode-model-tiers.json" => {
                    crate::jev_defaults::OPENCODE_TIERS_SOURCE
                }
                CLAUDE_SWITCH_COMMAND | OPENCODE_SWITCH_COMMAND => SWITCH_COMMAND_SOURCE,
                _ => "generated:jev-profile-model-defaults",
            };
            write_file_with_agentic_marker(app, content, &path, source)?;
        } else if !app.dry_run && path.is_file() {
            crate::project_inventory::safe_path(project, rel)?;
            let old: serde_json::Value = std::fs::read_to_string(app.project_manifest_path())
                .ok()
                .and_then(|s| serde_json::from_str(&s).ok())
                .unwrap_or_default();
            let item = old["managed_files"]
                .as_array()
                .into_iter()
                .flatten()
                .find(|i| i["path"] == rel);
            if item.is_some_and(|i| {
                crate::util::hash_file(&path).ok().as_deref() == i["content_hash"].as_str()
            }) {
                std::fs::remove_file(path)?;
            } else {
                crate::ui::warn(
                    app,
                    &format!("Preserving user-modified or unmanaged JEV adapter: {rel}"),
                );
                app.record_skipped(rel);
                if let Some(item) = item {
                    app.managed_records.push(crate::app::ManagedRecord {
                        path: rel.to_string(),
                        source: item["source"].as_str().unwrap_or("hooks:jev").to_string(),
                        content_hash: item["content_hash"].as_str().unwrap_or("").to_string(),
                        marker: item["marker"].as_str().unwrap_or("internal").to_string(),
                    });
                }
            }
        }
    }
    if enabled
        && !app
            .selected_agent_os
            .iter()
            .any(|s| matches!(s.as_str(), "codex" | "opencode" | "claude"))
    {
        crate::ui::warn(app, "JEV hooks currently support Codex, OpenCode V2, and Claude Code only; other hosts retain their native behavior.");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn opencode_selected_profile_defaults_are_recorded_for_routing() {
        let project = tempfile::tempdir().unwrap();
        let mut app = App::new().unwrap();
        app.project_dir = project.path().to_string_lossy().into();
        app.selected_agent_os = vec!["opencode".into()];
        app.selected_opencode_profile = "openai".into();
        app.jev_enabled = Some(true);
        install(&mut app, project.path()).unwrap();
        let defaults: serde_json::Value = serde_json::from_str(
            &std::fs::read_to_string(
                project
                    .path()
                    .join(".agent/jev/opencode-profile-defaults.json"),
            )
            .unwrap(),
        )
        .unwrap();
        let profile: serde_json::Value =
            serde_json::from_str(&crate::install::opencode_profile_source(&app, "openai").unwrap())
                .unwrap();
        assert_eq!(
            defaults["developer"],
            profile["agent"]["developer"]["model"]
        );
        assert!(!project
            .path()
            .join(".agent/jev/model-defaults.json")
            .exists());
        assert!(project.path().join(OPENCODE_SWITCH_COMMAND).is_file());
        assert!(!project.path().join(CLAUDE_SWITCH_COMMAND).exists());
    }

    #[test]
    fn switch_command_follows_the_selected_host() {
        let project = tempfile::tempdir().unwrap();
        let mut app = App::new().unwrap();
        app.project_dir = project.path().to_string_lossy().into();
        app.selected_agent_os = vec!["claude".into()];
        app.jev_enabled = Some(true);
        install(&mut app, project.path()).unwrap();
        let command = project.path().join(CLAUDE_SWITCH_COMMAND);
        assert!(std::fs::read_to_string(&command)
            .unwrap()
            .contains("Agentic JEV switch: $ARGUMENTS"));
        assert!(!project.path().join(OPENCODE_SWITCH_COMMAND).exists());
    }

    #[test]
    fn key_storage_preserves_other_values_and_stays_out_of_manifest() {
        let project = tempfile::tempdir().unwrap();
        std::fs::write(
            project.path().join(".env"),
            "OTHER=value\nexport JEV_API_KEY=old\nTYPESAFE_API_KEY=official\n",
        )
        .unwrap();
        save_key(project.path(), "JEV_API_KEY", "mock-hosted-key").unwrap();
        let content = std::fs::read_to_string(project.path().join(".env")).unwrap();
        assert!(content.contains("OTHER=value"));
        assert!(content.contains("TYPESAFE_API_KEY=official"));
        assert!(!content.contains("=old"));
        assert!(content.contains("JEV_API_KEY=\"mock-hosted-key\""));
        assert!(std::fs::read_to_string(project.path().join(".gitignore"))
            .unwrap()
            .contains(".env"));
        assert!(!project.path().join(".agentic.json").exists());
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                std::fs::metadata(project.path().join(".env"))
                    .unwrap()
                    .permissions()
                    .mode()
                    & 0o777,
                0o600
            );
        }
    }
}
