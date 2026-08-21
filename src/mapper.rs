//! OpenCode agent-model-mapper: interactive per-role model mapping.

use crate::app::App;
use crate::config;
use crate::manifest;
use crate::markers;
use crate::prompt;
use crate::ui;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq)]
pub struct Role {
    pub name: String,
    pub mode: String,
    pub description: String,
}

/// Parse a simple `key: value` frontmatter block from markdown text.
pub fn parse_frontmatter(text: &str) -> Vec<(String, String)> {
    if !text.starts_with("---\n") {
        return Vec::new();
    }
    let Some(end) = text[4..].find("\n---") else {
        return Vec::new();
    };
    let block = &text[4..end + 4];
    let mut out = Vec::new();
    for line in block.lines() {
        if let Some((key, value)) = line.split_once(':') {
            let value = value.trim().trim_matches(|c| c == '\'' || c == '"');
            out.push((key.trim().to_string(), value.to_string()));
        }
    }
    out
}

pub fn read_roles(agents_dir: &Path) -> Vec<Role> {
    let mut roles = Vec::new();
    let Ok(entries) = std::fs::read_dir(agents_dir) else {
        return roles;
    };
    let mut paths: Vec<PathBuf> = entries
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().map(|e| e == "md").unwrap_or(false))
        .collect();
    paths.sort();
    for path in paths {
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        let fm = parse_frontmatter(&text);
        let get = |key: &str| -> Option<String> {
            fm.iter().find(|(k, _)| k == key).map(|(_, v)| v.clone())
        };
        let name = path
            .file_stem()
            .map(|s| s.to_string_lossy().replace('\t', " "))
            .unwrap_or_default();
        let mode = get("mode")
            .filter(|v| !v.is_empty())
            .unwrap_or_else(|| "subagent".to_string())
            .replace('\t', " ");
        let description = get("description")
            .filter(|v| !v.is_empty())
            .unwrap_or_else(|| "OpenCode agent".to_string())
            .replace('\t', " ");
        roles.push(Role {
            name,
            mode,
            description,
        });
    }
    roles
}

fn add_model(models: &mut Vec<String>, model: &str) {
    let model = model.trim();
    if !model.is_empty() && model.contains('/') && !models.iter().any(|m| m == model) {
        models.push(model.to_string());
    }
}

fn collect_provider_models(models: &mut Vec<String>, data: &Value) {
    let Some(providers) = data.get("provider").and_then(|v| v.as_object()) else {
        return;
    };
    for (provider_name, provider_data) in providers {
        if let Some(provider_models) = provider_data.get("models").and_then(|v| v.as_object()) {
            for model_name in provider_models.keys() {
                if !model_name.trim().is_empty() {
                    add_model(models, &format!("{provider_name}/{model_name}"));
                }
            }
        }
    }
}

fn collect_recursive(models: &mut Vec<String>, value: &Value) {
    match value {
        Value::Array(items) => {
            for item in items {
                collect_recursive(models, item);
            }
        }
        Value::Object(map) => {
            for (key, item) in map {
                if key == "model" || key == "id" {
                    if let Some(s) = item.as_str() {
                        if s.contains('/') {
                            add_model(models, s);
                        }
                    }
                }
                if key == "fallback" {
                    if let Some(arr) = item.as_array() {
                        for model in arr {
                            if let Some(s) = model.as_str() {
                                add_model(models, s);
                            }
                        }
                    }
                }
                collect_recursive(models, item);
            }
        }
        _ => {}
    }
}

fn is_deprecated(model_data: &Value) -> bool {
    let Some(obj) = model_data.as_object() else {
        return false;
    };
    if obj.get("deprecated") == Some(&Value::Bool(true)) {
        return true;
    }
    let status = obj
        .get("status")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_lowercase();
    let lifecycle = obj
        .get("lifecycle")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_lowercase();
    matches!(status.as_str(), "deprecated" | "retired" | "removed")
        || matches!(lifecycle.as_str(), "deprecated" | "retired" | "removed")
}

fn collect_authenticated_provider_models(models: &mut Vec<String>, auth: &Value, cache: &Value) {
    let (Some(auth_map), Some(cache_map)) = (auth.as_object(), cache.as_object()) else {
        return;
    };
    for (provider_name, auth_value) in auth_map {
        if provider_name.trim().is_empty() {
            continue;
        }
        if auth_value.is_null() || auth_value == &Value::Bool(false) {
            continue;
        }
        let Some(provider_data) = cache_map.get(provider_name).and_then(|v| v.as_object()) else {
            continue;
        };
        match provider_data.get("models") {
            Some(Value::Object(provider_models)) => {
                for (model_name, model_data) in provider_models {
                    if !model_name.trim().is_empty() && !is_deprecated(model_data) {
                        add_model(models, &format!("{provider_name}/{model_name}"));
                    }
                }
            }
            Some(Value::Array(items)) => {
                for item in items {
                    if let Some(s) = item.as_str() {
                        add_model(models, &format!("{provider_name}/{s}"));
                    } else if item.is_object() && !is_deprecated(item) {
                        let name = item
                            .get("id")
                            .or_else(|| item.get("name"))
                            .and_then(|v| v.as_str())
                            .unwrap_or("");
                        if !name.trim().is_empty() {
                            add_model(models, &format!("{provider_name}/{name}"));
                        }
                    }
                }
            }
            _ => {}
        }
    }
}

fn read_json(path: &Path) -> Value {
    std::fs::read_to_string(path)
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or(Value::Null)
}

pub const FALLBACK_MODEL: &str = "opencode/minimax-m2.5-free";

pub fn discover_models(home: &Path) -> Vec<String> {
    let config_path = home.join(".config/opencode/opencode.json");
    let auth_path = home.join(".local/share/opencode/auth.json");
    let cache_path = home.join(".cache/opencode/models.json");
    let mut models: Vec<String> = Vec::new();
    let config = read_json(&config_path);
    if !config.is_null() {
        collect_provider_models(&mut models, &config);
        collect_recursive(&mut models, &config);
    }
    collect_authenticated_provider_models(
        &mut models,
        &read_json(&auth_path),
        &read_json(&cache_path),
    );
    if models.is_empty() {
        vec![FALLBACK_MODEL.to_string()]
    } else {
        models
    }
}

pub fn has_complete_mapping(roles: &[Role], config_path: &Path, state_path: &Path) -> bool {
    let state = read_json(state_path);
    let config = read_json(config_path);
    if state.get("configured") != Some(&Value::Bool(true)) {
        return false;
    }
    let Some(agents) = config.get("agent").and_then(|v| v.as_object()) else {
        return false;
    };
    for role in roles {
        let Some(agent) = agents.get(&role.name).and_then(|v| v.as_object()) else {
            return false;
        };
        let model = agent.get("model").and_then(|v| v.as_str()).unwrap_or("");
        if model.trim().is_empty() {
            return false;
        }
    }
    true
}

fn choose_model(app: &mut App, role: &Role, kind: &str, models: &[String]) -> String {
    eprintln!();
    eprintln!("{} ({}) - {}", role.name, role.mode, role.description);
    for (i, model) in models.iter().enumerate() {
        eprintln!("  {}) {model}", i + 1);
    }
    let answer = prompt::read_line_prompt(&format!("Select {kind} model for {} [1]: ", role.name));
    if answer.is_empty() {
        return models[0].clone();
    }
    if let Ok(idx) = answer.parse::<usize>() {
        if idx >= 1 && idx <= models.len() {
            return models[idx - 1].clone();
        }
    }
    if models.iter().any(|m| m == &answer) {
        return answer;
    }
    ui::warn(
        app,
        &format!("Unknown model '{answer}', using {}", models[0]),
    );
    models[0].clone()
}

/// Apply a mapping (role -> main/fallback models) to `.opencode/opencode.json`
/// and write the mapper state file.
pub fn write_agent_model_mapping(
    app: &mut App,
    roles: &[Role],
    mapping: &[(String, String, String)],
) -> crate::Result<()> {
    let project = PathBuf::from(&app.project_dir);
    let config_path = project.join(".opencode/opencode.json");
    let state_path = project.join(".opencode/agent-model-mapper.state.json");

    let mut data = read_json(&config_path);
    if !data.is_object() {
        data = json!({});
    }
    if !data.as_object().unwrap().contains_key("agent") {
        data.as_object_mut()
            .unwrap()
            .insert("agent".to_string(), json!({}));
    }
    {
        let agents = data
            .as_object_mut()
            .unwrap()
            .get_mut("agent")
            .unwrap()
            .as_object_mut()
            .unwrap();
        for role in roles {
            let Some((_, model, fallback)) = mapping.iter().find(|(n, _, _)| n == &role.name)
            else {
                continue;
            };
            let mut current = agents
                .get(&role.name)
                .and_then(|v| v.as_object())
                .cloned()
                .unwrap_or_default();
            let mode = current
                .get("mode")
                .and_then(|v| v.as_str())
                .filter(|s| !s.is_empty())
                .unwrap_or(&role.mode)
                .to_string();
            let description = current
                .get("description")
                .and_then(|v| v.as_str())
                .filter(|s| !s.is_empty())
                .unwrap_or(&role.description)
                .to_string();
            current.insert("mode".to_string(), json!(mode));
            current.insert("description".to_string(), json!(description));
            current.insert("model".to_string(), json!(model));
            let fallback_list: Vec<String> = if !fallback.is_empty() && fallback != model {
                vec![fallback.clone()]
            } else {
                Vec::new()
            };
            current.insert("fallback".to_string(), json!(fallback_list));
            agents.insert(role.name.clone(), Value::Object(current));
        }
    }
    if let Some(parent) = config_path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(&config_path, markers::to_pretty_json(&data))?;
    let state = json!({
        "configured": true,
        "roles": roles.iter().map(|r| r.name.clone()).collect::<Vec<_>>(),
    });
    std::fs::write(&state_path, markers::to_pretty_json(&state))?;
    manifest::register_managed_file(
        app,
        &config_path,
        "generated:opencode-agent-model-mapper-config",
        "config",
        true,
    );
    manifest::register_managed_file(
        app,
        &state_path,
        "generated:opencode-agent-model-mapper-state",
        "config",
        true,
    );
    Ok(())
}

pub fn configure_opencode_agent_model_mapper_if_needed(app: &mut App) -> crate::Result<()> {
    if !app.selected_agent_os_contains("opencode") {
        return Ok(());
    }
    if !config::opencode_agent_model_mapper_config_enabled(app) {
        return Ok(());
    }
    if !app.is_interactive_terminal() {
        ui::log(
            app,
            "agent-model-mapper install-time setup skipped because no interactive terminal is available",
        );
        return Ok(());
    }
    let project = PathBuf::from(&app.project_dir);
    let config_path = project.join(".opencode/opencode.json");
    let state_path = project.join(".opencode/agent-model-mapper.state.json");
    if !manifest::can_write_managed_file(app, &config_path) {
        return Ok(());
    }
    if state_path.exists() && !manifest::can_write_managed_file(app, &state_path) {
        return Ok(());
    }

    let roles = read_roles(&project.join(".opencode/agents"));
    if roles.is_empty() {
        ui::log(
            app,
            "agent-model-mapper: skipped because .opencode/agents/*.md was not found",
        );
        return Ok(());
    }
    if has_complete_mapping(&roles, &config_path, &state_path) {
        ui::log(
            app,
            "agent-model-mapper: skipped because all Agentic roles already have model mappings",
        );
        return Ok(());
    }
    let models = discover_models(&app.home);
    ui::out(
        app,
        "agent-model-mapper: choose OpenCode models for Agentic roles",
    );
    let mut mapping: Vec<(String, String, String)> = Vec::new();
    for role in &roles {
        let model = choose_model(app, role, "main", &models);
        let fallback = choose_model(app, role, "fallback", &models);
        mapping.push((role.name.clone(), model, fallback));
    }
    ui::out(app, "agent-model-mapper selected mapping:");
    for (name, model, fallback) in &mapping {
        ui::out(
            app,
            &format!("  - {name}: main={model} fallback={fallback}"),
        );
    }
    if !prompt::confirm_action_interactive("Write .opencode/opencode.json agent model mapping?") {
        ui::log(app, "agent-model-mapper: skipped by user; no files changed");
        return Ok(());
    }
    write_agent_model_mapping(app, &roles, &mapping)?;
    ui::log(app, "agent-model-mapper: updated .opencode/opencode.json");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn frontmatter_parsing() {
        let text = "---\nname: dev\nmode: 'primary'\ndescription: \"Builds things\"\n---\nbody";
        let fm = parse_frontmatter(text);
        assert_eq!(fm.iter().find(|(k, _)| k == "mode").unwrap().1, "primary");
        assert_eq!(
            fm.iter().find(|(k, _)| k == "description").unwrap().1,
            "Builds things"
        );
        assert!(parse_frontmatter("no frontmatter").is_empty());
        assert!(parse_frontmatter("---\nunclosed").is_empty());
    }

    #[test]
    fn roles_from_agent_files() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(
            tmp.path().join("developer.md"),
            "---\nmode: subagent\ndescription: Dev role\n---\nbody",
        )
        .unwrap();
        std::fs::write(tmp.path().join("plain.md"), "no frontmatter").unwrap();
        std::fs::write(tmp.path().join("ignored.txt"), "x").unwrap();
        let roles = read_roles(tmp.path());
        assert_eq!(roles.len(), 2);
        assert_eq!(roles[0].name, "developer");
        assert_eq!(roles[0].description, "Dev role");
        assert_eq!(roles[1].name, "plain");
        assert_eq!(roles[1].mode, "subagent");
        assert_eq!(roles[1].description, "OpenCode agent");
    }

    #[test]
    fn model_discovery_fallback_and_config() {
        let tmp = tempfile::tempdir().unwrap();
        assert_eq!(discover_models(tmp.path()), vec![FALLBACK_MODEL]);

        std::fs::create_dir_all(tmp.path().join(".config/opencode")).unwrap();
        std::fs::write(
            tmp.path().join(".config/opencode/opencode.json"),
            r#"{"model": "openai/gpt-4", "provider": {"acme": {"models": {"m1": {}}}}}"#,
        )
        .unwrap();
        let models = discover_models(tmp.path());
        assert!(models.contains(&"acme/m1".to_string()));
        assert!(models.contains(&"openai/gpt-4".to_string()));
    }

    #[test]
    fn model_discovery_from_auth_and_cache() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(tmp.path().join(".local/share/opencode")).unwrap();
        std::fs::create_dir_all(tmp.path().join(".cache/opencode")).unwrap();
        std::fs::write(
            tmp.path().join(".local/share/opencode/auth.json"),
            r#"{"prov": {"token": "x"}, "off": false}"#,
        )
        .unwrap();
        std::fs::write(
            tmp.path().join(".cache/opencode/models.json"),
            r#"{"prov": {"models": {"good": {}, "old": {"deprecated": true}}}, "off": {"models": {"never": {}}}}"#,
        )
        .unwrap();
        let models = discover_models(tmp.path());
        assert!(models.contains(&"prov/good".to_string()));
        assert!(!models.contains(&"prov/old".to_string()));
        assert!(!models.contains(&"off/never".to_string()));
    }

    #[test]
    fn mapping_write_and_complete_check() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = App::new().unwrap();
        app.project_dir = tmp.path().to_string_lossy().to_string();
        let roles = vec![Role {
            name: "developer".to_string(),
            mode: "subagent".to_string(),
            description: "Dev".to_string(),
        }];
        let mapping = vec![(
            "developer".to_string(),
            "openai/gpt-4".to_string(),
            "acme/m1".to_string(),
        )];
        write_agent_model_mapping(&mut app, &roles, &mapping).unwrap();
        let config_path = tmp.path().join(".opencode/opencode.json");
        let state_path = tmp.path().join(".opencode/agent-model-mapper.state.json");
        let data = read_json(&config_path);
        assert_eq!(data["agent"]["developer"]["model"], json!("openai/gpt-4"));
        assert_eq!(data["agent"]["developer"]["fallback"], json!(["acme/m1"]));
        assert!(has_complete_mapping(&roles, &config_path, &state_path));

        // same fallback as model -> empty fallback list
        let mapping2 = vec![(
            "developer".to_string(),
            "x/y".to_string(),
            "x/y".to_string(),
        )];
        write_agent_model_mapping(&mut app, &roles, &mapping2).unwrap();
        let data = read_json(&config_path);
        assert_eq!(data["agent"]["developer"]["fallback"], json!([]));
    }
}
