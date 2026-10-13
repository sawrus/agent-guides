//! Installer-only JEV enablement and shared skill assets; decisions live in Markdown.

use crate::{app::App, manifest::write_file_with_agentic_marker};
use std::path::Path;

pub const DEFAULT_API_URL: &str = "https://api.typesafe.ai/v1/systemone";

pub fn configure(app: &mut App) -> crate::Result<()> {
    let enabled = if let Some(enabled) = app.jev_enabled {
        enabled
    } else if app.selected_mcp_contains("jev") {
        true
    } else {
        app.is_interactive_terminal()
            && crate::prompt::read_yes_no(app, "Enable JEV workflow skill?")
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

pub fn install(app: &mut App, project: &Path) -> crate::Result<()> {
    if app.jev_enabled != Some(true) {
        return Ok(());
    }
    let mut roots = vec![".agent/skills/jev".to_string()];
    for target in &app.selected_agent_os {
        let root = match target.as_str() {
            "codex" => ".agents/skills/jev".to_string(),
            "claude" => ".claude/skills/jev".to_string(),
            "gemini" => ".gemini/skills/jev".to_string(),
            _ => format!("{}/jev", crate::agentsmd::get_dest_dir(target, "skills")),
        };
        if !roots.contains(&root) {
            roots.push(root);
        }
    }
    for root in roots {
        for (path, content) in [
            ("SKILL.md", include_str!("../skills/jev/SKILL.md")),
            (
                "scripts/decide.py",
                include_str!("../skills/jev/scripts/decide.py"),
            ),
            (
                "references/questions.json",
                include_str!("../skills/jev/references/questions.json"),
            ),
            (
                "references/checkpoints.md",
                include_str!("../skills/jev/references/checkpoints.md"),
            ),
            (
                "references/hosts.md",
                include_str!("../skills/jev/references/hosts.md"),
            ),
        ] {
            write_file_with_agentic_marker(
                app,
                content,
                &project.join(&root).join(path),
                &format!("skills/jev/{path}"),
            )?;
        }
    }
    crate::ui::log(app,"JEV skill installed: key stays in environment or project .env; no paid call made. Reload the agent session to discover the skill.");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
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
