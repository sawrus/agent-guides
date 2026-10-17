//! Claude Code native integration: model profiles, workflow slash commands,
//! and ownership-tracked `.claude/settings.json` entries.

use crate::app::App;
use crate::manifest::write_file_with_agentic_marker;
use crate::ui;
use serde_json::{json, Map, Value};
use std::path::Path;

pub const DEFAULT_PROFILE: &str = "anthropic";
pub const PROFILE_IDS: [&str; 1] = ["anthropic"];
pub const SETTINGS_REL: &str = ".claude/settings.json";
pub const SETTINGS_OWNERSHIP: &str = ".agentic/claude-settings-entries.json";
const MAIN_AGENT: &str = "product-owner";

pub fn profile_is_none(id: &str) -> bool {
    crate::install::opencode_profile_is_none(id) && !id.trim().is_empty()
}

/// Effective profile id, or `None` when model pinning is disabled.
pub fn selected_profile(app: &App) -> Option<String> {
    let raw = app.selected_claude_profile.trim();
    if profile_is_none(raw) {
        return None;
    }
    if raw.is_empty() {
        return Some(DEFAULT_PROFILE.into());
    }
    Some(raw.to_string())
}

fn profile_agents(app: &App, id: &str) -> Option<Map<String, Value>> {
    let text = app
        .kb
        .read_file(&format!("extensions/claude/profiles/{id}/profile.json"))?;
    serde_json::from_str::<Value>(&text).ok()?["agents"]
        .as_object()
        .cloned()
}

/// Choose and validate the profile; unknown ids warn and fall back to no pinning.
pub fn configure_profile(app: &mut App) -> crate::Result<()> {
    if !app.selected_agent_os_contains("claude") {
        return Ok(());
    }
    if let Ok(env) = std::env::var("AGENTIC_CLAUDE_PROFILE") {
        if !env.trim().is_empty() && !app.upgrade_mode && !app.claude_profile_explicit {
            app.selected_claude_profile = env.trim().to_string();
            app.claude_profile_explicit = true;
        }
    }
    if !app.claude_profile_explicit
        && !app.install_settings_replay
        && !app.upgrade_mode
        && !app.dry_run
        && app.is_interactive_terminal()
    {
        let mut options: Vec<String> = PROFILE_IDS
            .iter()
            .map(|id| format!("{id}: model alias per role"))
            .collect();
        options.push("none: every agent inherits the session model".into());
        let choice = crate::prompt::choose_single_by_index(app, "Claude model profile:", &options)?;
        app.selected_claude_profile = choice.split(':').next().unwrap_or("none").to_string();
    }
    if let Some(id) = selected_profile(app) {
        if profile_agents(app, &id).is_none() {
            ui::warn(app, &format!("Ignoring unknown Claude profile '{id}'"));
            app.selected_claude_profile = "none".into();
            return Ok(());
        }
        app.selected_claude_profile = id;
    }
    Ok(())
}

/// Role → model alias for JEV candidate pools (falls back to the default profile).
pub fn profile_models(app: &App) -> Map<String, Value> {
    let id = selected_profile(app).unwrap_or_else(|| DEFAULT_PROFILE.into());
    profile_agents(app, &id)
        .or_else(|| profile_agents(app, DEFAULT_PROFILE))
        .unwrap_or_default()
}

/// Rewrite a bundled `.claude/agents/<role>.md` frontmatter `model:` line.
/// JEV leaves models open so hooks can route each spawn.
pub fn apply_agent_model(app: &App, rel: &str, content: &str) -> String {
    let role = rel
        .strip_prefix("agents/")
        .and_then(|r| r.strip_suffix(".md"))
        .unwrap_or("");
    let model = if app.jev_enabled == Some(true) {
        None
    } else {
        selected_profile(app)
            .and_then(|id| profile_agents(app, &id))
            .and_then(|agents| agents.get(role).and_then(Value::as_str).map(str::to_owned))
    };
    // Windows checkouts may embed CRLF sources; the frontmatter scan below expects LF.
    let content = &content.replace("\r\n", "\n");
    let Some(rest) = content.strip_prefix("---\n") else {
        return content.to_string();
    };
    let Some(end) = rest.find("\n---") else {
        return content.to_string();
    };
    let mut lines: Vec<String> = rest[..end]
        .lines()
        .filter(|l| !l.starts_with("model:"))
        .map(str::to_owned)
        .collect();
    if let Some(model) = model {
        let at = lines
            .iter()
            .position(|l| l.starts_with("description:"))
            .map_or(lines.len(), |i| i + 1);
        lines.insert(at, format!("model: {model}"));
    }
    format!("---\n{}{}", lines.join("\n"), &rest[end..])
}

struct WorkflowMeta {
    description: String,
    inputs: Vec<String>,
    initiator: String,
}

fn workflow_meta(text: &str) -> WorkflowMeta {
    let text = text.replace("\r\n", "\n");
    let front = text
        .strip_prefix("---\n")
        .and_then(|rest| rest.find("\n---").map(|end| &rest[..end]))
        .unwrap_or("");
    let mut meta = WorkflowMeta {
        description: String::new(),
        inputs: Vec::new(),
        initiator: String::new(),
    };
    let mut section = "";
    for line in front.lines() {
        if let Some(value) = line.strip_prefix("description:") {
            meta.description = value.trim().trim_matches('"').to_string();
        }
        if !line.starts_with(' ') {
            section = line.split(':').next().unwrap_or("");
            continue;
        }
        let item = line.trim();
        match section {
            "inputs" => {
                if let Some(value) = item.strip_prefix("- ") {
                    meta.inputs.push(value.trim().to_string());
                }
            }
            "execution" => {
                if let Some(value) = item.strip_prefix("initiator:") {
                    meta.initiator = value.trim().to_string();
                }
            }
            _ => {}
        }
    }
    meta
}

fn command_text(id: &str, meta: &WorkflowMeta) -> String {
    let hint = meta
        .inputs
        .iter()
        .map(|i| format!("[{i}]"))
        .collect::<Vec<_>>()
        .join(" ");
    let description = if meta.description.is_empty() {
        format!("Run the {id} workflow")
    } else {
        meta.description.clone()
    };
    let initiator = if meta.initiator.is_empty() {
        "the workflow initiator".to_string()
    } else {
        format!("`{}`", meta.initiator)
    };
    format!(
        "---\ndescription: {}\nargument-hint: {}\n---\n\nRun the `{id}` workflow from @.agent/workflows/{id}.md for this request:\n\n$ARGUMENTS\n\nAct as its initiator ({initiator}) in this main session. Delegate each step to the role it names through the Agent tool (`subagent_type` = role name, for example `developer`). Follow the step order, handoff outputs, and quality gates in the workflow. When the workflow has a Post-task review section, follow `REVIEW_PIPELINE.md` after successful delivery.\n",
        serde_json::to_string(&description).unwrap_or_default(),
        serde_json::to_string(&hint).unwrap_or_default(),
    )
}

/// Thin `.claude/commands/<id>.md` wrappers: `.agent/workflows` stays the single source.
pub fn generate_commands(app: &mut App, project: &Path) -> crate::Result<()> {
    if !app.selected_agent_os_contains("claude") {
        return Ok(());
    }
    for spec_key in app.selected_specs.clone() {
        let (area, spec) = spec_key.split_once('.').unwrap_or((spec_key.as_str(), ""));
        let src = format!("areas/{area}/{spec}/workflows");
        for (rel, text) in app.kb.walk_files(&src) {
            let Some(id) = rel.strip_suffix(".md").filter(|r| !r.contains('/')) else {
                continue;
            };
            let content = command_text(id, &workflow_meta(&text));
            let dest = project.join(format!(".claude/commands/{id}.md"));
            write_file_with_agentic_marker(app, &content, &dest, "generated:claude-command")?;
        }
    }
    Ok(())
}

fn mcp_server_names(app: &App, project: &Path) -> Vec<String> {
    let configured: Value = std::fs::read_to_string(project.join(".mcp.json"))
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();
    let mut names: Vec<String> = app
        .selected_mcps
        .iter()
        .filter_map(|id| crate::mcp::registry_entry(id))
        .map(|e| e.server.to_string())
        .filter(|server| configured["mcpServers"].get(server).is_some())
        .collect();
    names.sort();
    names.dedup();
    names
}

fn read_json(path: &Path) -> crate::Result<Option<Value>> {
    if !path.exists() {
        return Ok(None);
    }
    let value: Value = serde_json::from_str(&std::fs::read_to_string(path)?)?;
    Ok(value.is_object().then_some(value))
}

/// Merge owned non-hook keys into `.claude/settings.json`: the main-session
/// agent and the approved project MCP servers. User values always win.
pub fn write_settings(app: &mut App, project: &Path) -> crate::Result<()> {
    if app.dry_run {
        return Ok(());
    }
    let selected = app.selected_agent_os_contains("claude");
    let path = crate::project_inventory::safe_path(project, SETTINGS_REL)?;
    let ownership_path = crate::project_inventory::safe_path(project, SETTINGS_OWNERSHIP)?;
    let mut owned = read_json(&ownership_path)
        .ok()
        .flatten()
        .unwrap_or_else(|| json!({}));
    if !selected && owned.as_object().is_none_or(|o| o.is_empty()) {
        return Ok(());
    }
    let mut data = match read_json(&path) {
        Ok(v) => v.unwrap_or_else(|| json!({})),
        Err(error) => {
            ui::warn(
                app,
                &format!("Skipping {SETTINGS_REL}: invalid JSON ({error}); reconcile manually"),
            );
            app.record_skipped(SETTINGS_REL);
            return Ok(());
        }
    };
    let obj = data.as_object_mut().ok_or("Invalid Claude settings")?;

    // Main-session agent: set only when absent; remove only our unchanged value.
    let owned_agent = owned["agent"].as_str().map(str::to_owned);
    if let Some(previous) = &owned_agent {
        if obj.get("agent").and_then(Value::as_str) == Some(previous.as_str()) {
            obj.remove("agent");
        }
        owned.as_object_mut().unwrap().remove("agent");
    }
    if selected && !obj.contains_key("agent") {
        obj.insert("agent".into(), json!(MAIN_AGENT));
        owned["agent"] = json!(MAIN_AGENT);
    }

    // Approved .mcp.json servers: track each name we added.
    let previous: Vec<String> = owned["enabledMcpjsonServers"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|v| v.as_str().map(str::to_owned))
        .collect();
    let mut list: Vec<Value> = obj
        .get("enabledMcpjsonServers")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    list.retain(|v| v.as_str().is_none_or(|s| !previous.iter().any(|p| p == s)));
    let mut added: Vec<String> = Vec::new();
    if selected {
        for name in mcp_server_names(app, project) {
            if !list.iter().any(|v| v.as_str() == Some(name.as_str())) {
                list.push(json!(name));
                added.push(name);
            }
        }
    }
    if list.is_empty() {
        obj.remove("enabledMcpjsonServers");
    } else {
        obj.insert("enabledMcpjsonServers".into(), Value::Array(list));
    }
    if added.is_empty() {
        owned
            .as_object_mut()
            .unwrap()
            .remove("enabledMcpjsonServers");
    } else {
        owned["enabledMcpjsonServers"] = json!(added);
    }

    std::fs::create_dir_all(path.parent().unwrap())?;
    std::fs::create_dir_all(ownership_path.parent().unwrap())?;
    let output = serde_json::to_string_pretty(&data)? + "\n";
    if std::fs::read_to_string(&path).ok().as_deref() != Some(output.as_str()) {
        std::fs::write(&path, output)?;
    }
    std::fs::write(
        &ownership_path,
        serde_json::to_string_pretty(&owned)? + "\n",
    )?;
    crate::manifest::register_managed_file(app, &path, "generated:claude-settings", "config", true);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn app() -> App {
        let mut app = App::new().unwrap();
        app.selected_agent_os = vec!["claude".into()];
        app
    }

    #[test]
    fn profile_pins_models_and_jev_leaves_them_open() {
        let mut a = app();
        let body = "---\nname: developer\ndescription: Dev\nmodel: opus\n---\nbody\n";
        let pinned = apply_agent_model(&a, "agents/developer.md", body);
        assert!(pinned.starts_with("---\nname: developer\ndescription: Dev\nmodel: sonnet\n---"));
        a.jev_enabled = Some(true);
        let open = apply_agent_model(&a, "agents/developer.md", body);
        assert!(!open.contains("model:"));
        a.jev_enabled = None;
        a.selected_claude_profile = "none".into();
        assert!(!apply_agent_model(&a, "agents/developer.md", body).contains("model:"));
    }

    #[test]
    fn unknown_profile_is_ignored() {
        let mut a = app();
        a.claude_profile_explicit = true;
        a.selected_claude_profile = "ghost".into();
        configure_profile(&mut a).unwrap();
        assert_eq!(selected_profile(&a), None);
    }

    #[test]
    fn command_wrapper_has_claude_frontmatter() {
        let meta = workflow_meta("---\nname: x\ntrigger: /x\ndescription: Do X.\ninputs:\n  - feature_request\n  - acceptance_criteria\nroles:\n  - qa\nexecution:\n  initiator: product-owner\n---\nbody");
        let text = command_text("x", &meta);
        assert!(text.starts_with("---\ndescription: \"Do X.\"\nargument-hint: \"[feature_request] [acceptance_criteria]\"\n---\n"));
        assert!(text.contains("@.agent/workflows/x.md"));
        assert!(text.contains("`product-owner`"));
        assert!(!text.contains("trigger:"));
    }

    #[test]
    fn command_wrapper_reads_crlf_workflow() {
        let meta = workflow_meta("---\r\ndescription: Do X.\r\ninputs:\r\n  - feature_request\r\nexecution:\r\n  initiator: qa\r\n---\r\nbody");
        let text = command_text("x", &meta);
        assert!(text.contains("argument-hint: \"[feature_request]\"\n"));
        assert!(text.contains("`qa`"));
    }

    #[test]
    fn settings_merge_respects_user_agent_and_removes_owned_values() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let mut a = app();
        a.project_dir = p.to_string_lossy().into();
        std::fs::write(
            p.join(".mcp.json"),
            r#"{"mcpServers":{"playwright":{"command":"npx"}}}"#,
        )
        .unwrap();
        a.selected_mcps = vec!["playwright".into()];
        std::fs::create_dir_all(p.join(".claude")).unwrap();
        std::fs::write(
            p.join(SETTINGS_REL),
            r#"{"env":{"X":"1"},"enabledMcpjsonServers":["mine"]}"#,
        )
        .unwrap();
        write_settings(&mut a, p).unwrap();
        let data: Value =
            serde_json::from_str(&std::fs::read_to_string(p.join(SETTINGS_REL)).unwrap()).unwrap();
        assert_eq!(data["agent"], "product-owner");
        assert_eq!(data["enabledMcpjsonServers"], json!(["mine", "playwright"]));
        a.selected_agent_os = vec!["codex".into()];
        write_settings(&mut a, p).unwrap();
        let data: Value =
            serde_json::from_str(&std::fs::read_to_string(p.join(SETTINGS_REL)).unwrap()).unwrap();
        assert_eq!(
            data,
            json!({"env":{"X":"1"},"enabledMcpjsonServers":["mine"]})
        );
    }

    #[test]
    fn user_agent_is_never_replaced() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let mut a = app();
        a.project_dir = p.to_string_lossy().into();
        std::fs::create_dir_all(p.join(".claude")).unwrap();
        std::fs::write(p.join(SETTINGS_REL), r#"{"agent":"developer"}"#).unwrap();
        write_settings(&mut a, p).unwrap();
        let data: Value =
            serde_json::from_str(&std::fs::read_to_string(p.join(SETTINGS_REL)).unwrap()).unwrap();
        assert_eq!(data["agent"], "developer");
    }
}
