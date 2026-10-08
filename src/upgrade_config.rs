//! Ownership of shared configuration keys; metadata contains paths, never values.
use crate::{app::App, util};
use serde_json::{json, Value};
use std::path::Path;

pub fn merge_json(base: &mut Value, incoming: &Value) {
    if let (Some(base), Some(incoming)) = (base.as_object_mut(), incoming.as_object()) {
        for (key, value) in incoming {
            if value.is_object() && base.get(key).is_some_and(Value::is_object) {
                merge_json(base.get_mut(key).unwrap(), value);
            } else if key == "plugin" && value.is_array() {
                let entries = base.entry(key).or_insert(json!([]));
                if let Some(entries) = entries.as_array_mut() {
                    for entry in value.as_array().unwrap() {
                        if !entries.contains(entry) {
                            entries.push(entry.clone());
                        }
                    }
                }
            } else {
                base.insert(key.clone(), value.clone());
            }
        }
    }
}

fn json_keys(value: &Value, prefix: &str, out: &mut Vec<String>) {
    if let Some(map) = value.as_object().filter(|m| !m.is_empty()) {
        for (key, value) in map {
            let key = key.replace('~', "~0").replace('/', "~1");
            json_keys(value, &format!("{prefix}/{key}"), out);
        }
    } else if !prefix.is_empty() {
        util::unique_append(out, prefix);
    }
}

pub fn record_json_keys(app: &mut App, dest: &Path, generated: &Value) {
    let rel = app.project_rel_path(dest);
    let keys = app.config_owned_keys.entry(rel).or_default();
    json_keys(generated, "", keys);
}

pub fn record_text_keys(app: &mut App, dest: &Path, source: &str, content: &str) {
    if dest.extension().and_then(|s| s.to_str()) != Some("toml") {
        return;
    }
    let rel = app.project_rel_path(dest);
    let keys = app.config_owned_keys.entry(rel).or_default();
    if source == "generated:codex-features-config" {
        util::unique_append(keys, "features.memories");
    } else {
        let servers: Vec<_> = if source.contains("context7") {
            vec!["context7".to_string()]
        } else if source.contains("mempalace") {
            vec!["mempalace".to_string()]
        } else {
            app.selected_mcps
                .iter()
                .filter_map(|id| {
                    crate::mcp::registry_entry(id).map(|entry| entry.server.to_string())
                })
                .collect()
        };
        for server in servers {
            util::unique_append(keys, &format!("mcp_servers.{server}"));
        }
        if content.contains("network_access = true") {
            util::unique_append(keys, "sandbox_workspace_write.network_access");
        }
    }
}

pub fn manifest_keys(app: &App, old: Option<&Value>) -> Value {
    let mut keys = old
        .and_then(|v| v["config_owned_keys"].as_object())
        .cloned()
        .unwrap_or_default();
    for (path, owned) in &app.config_owned_keys {
        let mut merged: Vec<String> = keys
            .get(path)
            .and_then(Value::as_array)
            .map(|a| {
                a.iter()
                    .filter_map(Value::as_str)
                    .map(str::to_owned)
                    .collect()
            })
            .unwrap_or_default();
        for key in owned {
            util::unique_append(&mut merged, key);
        }
        merged.sort();
        keys.insert(path.clone(), json!(merged));
    }
    Value::Object(keys)
}

fn remove_json_key(value: &mut Value, pointer: &str) {
    let Some((parent, key)) = pointer.rsplit_once('/') else {
        return;
    };
    if pointer == "/plugin" {
        if let Some(plugins) = value.pointer_mut(pointer).and_then(Value::as_array_mut) {
            plugins.retain(|v| {
                !matches!(
                    v.as_str(),
                    Some("telegram-notification" | "agent-model-mapper")
                )
            });
        }
        return;
    }
    if let Some(map) = value.pointer_mut(parent).and_then(Value::as_object_mut) {
        map.remove(&key.replace("~1", "/").replace("~0", "~"));
        if map.is_empty() && !parent.is_empty() {
            remove_json_key(value, parent);
        }
    }
}

/// Clean only recorded fields. Legacy manifests fall back to selected servers.
pub fn clean(app: &App, path: &Path, manifest: &Value) -> crate::Result<()> {
    let rel = app.project_rel_path(path);
    let mut keys: Vec<String> = manifest["config_owned_keys"][&rel]
        .as_array()
        .map(|a| {
            a.iter()
                .filter_map(Value::as_str)
                .map(str::to_owned)
                .collect()
        })
        .unwrap_or_else(|| {
            let mut keys = vec![];
            for id in manifest["settings"]["mcp_integrations"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
            {
                if let Some(entry) = crate::mcp::registry_entry(id) {
                    for prefix in ["/mcp/", "/mcpServers/", "mcp_servers."] {
                        keys.push(format!("{prefix}{}", entry.server));
                    }
                }
            }
            if rel == ".codex/config.toml" {
                keys.extend([
                    "features.memories".into(),
                    "sandbox_workspace_write.network_access".into(),
                ]);
            }
            keys
        });
    if app.context7_api_key_mode.as_deref() == Some("api_key") && app.context7_api_key.is_empty() {
        keys.retain(|key| {
            !key.starts_with("/mcp/context7")
                && !key.starts_with("/mcpServers/context7")
                && key != "mcp_servers.context7"
        });
    }
    let text = std::fs::read_to_string(path)?;
    if path.extension().and_then(|s| s.to_str()) == Some("json") {
        let mut value: Value = serde_json::from_str(&text)?;
        for key in &keys {
            remove_json_key(&mut value, key);
        }
        std::fs::write(path, crate::markers::to_pretty_json(&value))?;
    } else if path.extension().and_then(|s| s.to_str()) == Some("toml") {
        let mut section = "";
        let mut out = String::new();
        for line in text.split_inclusive('\n') {
            let trimmed = line.trim();
            if let Some(s) = trimmed.strip_prefix('[').and_then(|s| s.strip_suffix(']')) {
                section = s;
            }
            let field = line
                .split_once('=')
                .map(|(key, _)| format!("{section}.{}", key.trim()));
            if keys
                .iter()
                .any(|key| key == section || field.as_ref() == Some(key))
            {
                continue;
            }
            out.push_str(line);
        }
        std::fs::write(path, out)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn clean_recorded_json_keys_preserves_other_servers_plugins_and_fields() {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("config.json");
        let mut app = App::new().unwrap();
        app.project_dir = root.path().to_string_lossy().into();
        let value = json!({"mcp":{"playwright":{"command":["old"]},"custom":{"command":["mine"]}},"plugin":["telegram-notification","custom-plugin"],"unrelated":true});
        std::fs::write(&path, crate::markers::to_pretty_json(&value)).unwrap();
        let manifest =
            json!({"config_owned_keys":{"config.json":["/mcp/playwright/command","/plugin"]}});
        clean(&app, &path, &manifest).unwrap();
        let result: Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
        assert!(result["mcp"].get("playwright").is_none());
        assert_eq!(result["mcp"]["custom"], value["mcp"]["custom"]);
        assert_eq!(result["plugin"], json!(["custom-plugin"]));
        assert_eq!(result["unrelated"], true);
        let mut incoming = result.clone();
        merge_json(
            &mut incoming,
            &json!({"plugin":["telegram-notification"],"mcp":{"new":{"command":["new"]}}}),
        );
        assert_eq!(
            incoming["plugin"],
            json!(["custom-plugin", "telegram-notification"])
        );
        assert_eq!(incoming["mcp"]["custom"], value["mcp"]["custom"]);
    }

    #[test]
    fn toml_metadata_never_claims_unselected_user_servers() {
        let root = tempfile::tempdir().unwrap();
        let mut app = App::new().unwrap();
        app.project_dir = root.path().to_string_lossy().into();
        app.selected_mcps = vec!["playwright".into()];
        record_text_keys(&mut app, &root.path().join("config.toml"), "generated:mcp-codex-config", "[mcp_servers.custom]\ncommand = \"custom\"\n[mcp_servers.playwright]\ncommand = \"npx\"\n");
        assert_eq!(
            app.config_owned_keys["config.toml"],
            vec!["mcp_servers.playwright"]
        );
    }
}
