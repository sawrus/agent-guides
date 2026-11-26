//! Migration of artifacts that earlier releases installed under other names.

use crate::app::{App, ManagedRecord};
use serde_json::Value;
use std::path::Path;

/// v1.4.0 role renames (old → new).
pub const RENAMED_ROLES: [(&str, &str); 3] = [
    ("designer", "analyst"),
    ("instruction_reviewer", "instruction-reviewer"),
    ("memory_curator", "memory-curator"),
];

fn manifest_item(app: &App, rel: &str) -> Option<Value> {
    let data: Value = std::fs::read_to_string(app.project_manifest_path())
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())?;
    data["managed_files"]
        .as_array()?
        .iter()
        .find(|i| i["path"] == rel)
        .cloned()
}

/// Delete a managed file whose content still matches the manifest hash.
/// Edited or unmanaged files are preserved, reported, and kept tracked.
pub fn remove_if_unmodified(
    app: &mut App,
    project: &Path,
    rel: &str,
    label: &str,
) -> crate::Result<bool> {
    let path = crate::project_inventory::safe_path(project, rel)?;
    if !path.is_file() {
        return Ok(false);
    }
    let item = manifest_item(app, rel);
    let unchanged = item.as_ref().is_some_and(|i| {
        crate::util::hash_file(&path).ok().as_deref() == i["content_hash"].as_str()
    });
    if unchanged {
        std::fs::remove_file(&path)?;
        let baseline = crate::project_update::baseline_path(project, rel);
        if baseline.is_file() {
            std::fs::remove_file(baseline)?;
        }
        app.upgrade_actions
            .push(format!("Removed obsolete artifact: {rel}"));
        return Ok(true);
    }
    crate::ui::warn(
        app,
        &format!("Preserving user-modified or unmanaged {label}: {rel}"),
    );
    app.record_skipped(rel);
    if let Some(item) = item {
        app.managed_records.push(ManagedRecord {
            path: rel.to_string(),
            source: item["source"].as_str().unwrap_or("legacy").to_string(),
            content_hash: item["content_hash"].as_str().unwrap_or("").to_string(),
            marker: item["marker"].as_str().unwrap_or("internal").to_string(),
        });
    }
    Ok(false)
}

pub fn drop_renamed_keys(config: &mut Value) -> bool {
    let mut changed = false;
    let Some(agents) = config.get_mut("agent").and_then(Value::as_object_mut) else {
        return false;
    };
    for (old, _) in RENAMED_ROLES {
        changed |= agents.remove(old).is_some();
    }
    for agent in agents.values_mut() {
        if let Some(task) = agent
            .pointer_mut("/permission/task")
            .and_then(Value::as_object_mut)
        {
            for (old, _) in RENAMED_ROLES {
                changed |= task.remove(old).is_some();
            }
        }
    }
    changed
}

/// Bundled plugins are local files under `.opencode/plugins/`, loaded
/// automatically. Older releases also listed them in `plugin`, which OpenCode
/// treats as npm packages (install fails with 404).
const LOCAL_PLUGIN_REFS: [&str; 2] = ["telegram-notification", "agent-model-mapper"];

pub fn drop_local_plugin_refs(config: &mut Value) -> bool {
    let Some(map) = config.as_object_mut() else {
        return false;
    };
    let Some(plugins) = map.get_mut("plugin").and_then(Value::as_array_mut) else {
        return false;
    };
    let before = plugins.len();
    plugins.retain(|v| !v.as_str().is_some_and(|s| LOCAL_PLUGIN_REFS.contains(&s)));
    let changed = plugins.len() != before;
    if plugins.is_empty() {
        map.remove("plugin");
    }
    changed
}

/// Remove role files and OpenCode role keys that use pre-1.4 names.
pub fn migrate_renamed_roles(app: &mut App, project: &Path) -> crate::Result<()> {
    if app.dry_run {
        return Ok(());
    }
    for os in ["claude", "opencode", "gemini", "codex"] {
        let ext = if os == "codex" { "toml" } else { "md" };
        for (old, new) in RENAMED_ROLES {
            let rel = format!(".{os}/agents/{old}.{ext}");
            if crate::project_inventory::safe_path(project, &rel)?.is_file()
                && !remove_if_unmodified(app, project, &rel, "legacy role agent")?
            {
                crate::ui::warn(
                    app,
                    &format!("Role '{old}' was renamed to '{new}'; merge {rel} manually"),
                );
            }
        }
    }
    for rel in [".opencode/opencode.json", "opencode.json"] {
        let path = crate::project_inventory::safe_path(project, rel)?;
        if manifest_item(app, rel).is_none() || !path.is_file() {
            continue;
        }
        let Ok(mut data) = serde_json::from_str::<Value>(&std::fs::read_to_string(&path)?) else {
            continue;
        };
        let renamed = drop_renamed_keys(&mut data);
        let plugins = drop_local_plugin_refs(&mut data);
        if renamed || plugins {
            std::fs::write(&path, crate::markers::to_pretty_json(&data))?;
            app.upgrade_actions.push(format!(
                "Removed legacy role keys or npm plugin refs: {rel}"
            ));
        }
    }
    Ok(())
}

/// v9.0.0 removed the MemPalace integration. Earlier releases wrote a `mempalace` MCP server into host
/// configs and a `.mempalaceignore` file. Remove the config keys the manifest records as agentic-owned and the
/// ignore file when the user did not edit it. Unrecorded entries stay; `UPGRADE.md` lists them for manual removal.
pub fn remove_mempalace(app: &mut App, project: &Path) -> crate::Result<()> {
    if app.dry_run {
        return Ok(());
    }
    let manifest: Value = std::fs::read_to_string(app.project_manifest_path())
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or(Value::Null);
    if let Some(owned) = manifest["config_owned_keys"].as_object() {
        for (rel, keys) in owned {
            let keys: Vec<String> = keys
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
                .filter(|key| is_mempalace_key(key))
                .map(str::to_owned)
                .collect();
            if keys.is_empty() {
                continue;
            }
            // Global configs (absolute paths) and symlinked paths stay for manual removal.
            let Ok(path) = crate::project_inventory::safe_path(project, rel) else {
                continue;
            };
            if path.is_file() {
                crate::upgrade_config::remove_keys(&path, &keys)?;
                app.upgrade_actions
                    .push(format!("Removed MemPalace MCP server from {rel}"));
            }
            app.config_owned_keys.entry(rel.clone()).or_default();
            let released = app.config_released_keys.entry(rel.clone()).or_default();
            for key in keys {
                crate::util::unique_append(released, &key);
            }
        }
    }
    if crate::project_inventory::safe_path(project, MEMPALACE_IGNORE).is_ok_and(|p| p.is_file())
        && manifest_item(app, MEMPALACE_IGNORE).is_some()
    {
        remove_if_unmodified(app, project, MEMPALACE_IGNORE, "MemPalace ignore file")?;
    }
    Ok(())
}

const MEMPALACE_IGNORE: &str = ".mempalaceignore";

fn is_mempalace_key(key: &str) -> bool {
    [
        "/mcp/mempalace",
        "/mcpServers/mempalace",
        "mcp_servers.mempalace",
    ]
    .iter()
    .any(|prefix| {
        key.strip_prefix(prefix)
            .is_some_and(|rest| rest.is_empty() || rest.starts_with(['/', '.']))
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn local_plugin_refs_are_not_npm_packages() {
        let mut config = json!({"plugin": ["telegram-notification", "custom-plugin"]});
        assert!(drop_local_plugin_refs(&mut config));
        assert_eq!(config, json!({"plugin": ["custom-plugin"]}));
        let mut config = json!({"plugin": ["agent-model-mapper"], "agent": {}});
        assert!(drop_local_plugin_refs(&mut config));
        assert_eq!(config, json!({"agent": {}}));
        assert!(!drop_local_plugin_refs(&mut config));
    }

    #[test]
    fn renamed_role_keys_are_removed() {
        let mut config = json!({"agent": {
            "designer": {"mode": "subagent"},
            "analyst": {"mode": "subagent"},
            "product-owner": {"permission": {"task": {"designer": "allow", "memory_curator": "allow", "qa": "allow"}}}
        }});
        assert!(drop_renamed_keys(&mut config));
        assert_eq!(
            config,
            json!({"agent": {
                "analyst": {"mode": "subagent"},
                "product-owner": {"permission": {"task": {"qa": "allow"}}}
            }})
        );
        assert!(!drop_renamed_keys(&mut config));
    }

    #[test]
    fn unmodified_legacy_agent_is_removed_and_edited_one_kept() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let mut app = App::new().unwrap();
        app.project_dir = p.to_string_lossy().into();
        let agents = p.join(".claude/agents");
        std::fs::create_dir_all(&agents).unwrap();
        std::fs::write(agents.join("designer.md"), "old").unwrap();
        std::fs::write(agents.join("memory_curator.md"), "old").unwrap();
        for name in ["designer.md", "memory_curator.md"] {
            crate::manifest::register_managed_file(
                &mut app,
                &agents.join(name),
                "extensions/claude/agents/x",
                "internal",
                false,
            );
        }
        crate::manifest::write_agentic_manifest(&mut app, p).unwrap();
        std::fs::write(agents.join("memory_curator.md"), "edited").unwrap();
        let mut app2 = App::new().unwrap();
        app2.project_dir = p.to_string_lossy().into();
        migrate_renamed_roles(&mut app2, p).unwrap();
        assert!(!agents.join("designer.md").exists());
        assert!(agents.join("memory_curator.md").exists());
        assert!(app2
            .skipped_managed_paths
            .contains(&".claude/agents/memory_curator.md".to_string()));
    }

    #[test]
    fn removed_mempalace_entries_are_cleaned() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        let mut app = App::new().unwrap();
        app.project_dir = root.to_string_lossy().to_string();
        std::fs::write(
            root.join(".mcp.json"),
            r#"{"mcpServers":{"mempalace":{"command":"mempalace-mcp"},"custom":{"command":"x"}}}"#,
        )
        .unwrap();
        std::fs::create_dir_all(root.join(".codex")).unwrap();
        std::fs::write(
            root.join(".codex/config.toml"),
            "[mcp_servers.mempalace]\ncommand = \"mempalace-mcp\"\nstartup_timeout_sec = 30\n\n[mcp_servers.mine]\ncommand = \"mine\"\n",
        )
        .unwrap();
        let ignore = "target/\n";
        std::fs::write(root.join(".mempalaceignore"), ignore).unwrap();
        let manifest = json!({
            "config_owned_keys": {
                ".mcp.json": ["/mcpServers/mempalace/command"],
                ".codex/config.toml": ["mcp_servers.mempalace"],
                "/outside/mcp_config.json": ["/mcpServers/mempalace/command"]
            },
            "managed_files": [{
                "path": ".mempalaceignore",
                "content_hash": crate::util::sha256_hex(ignore.as_bytes()),
                "marker": "config"
            }]
        });
        std::fs::write(
            root.join(crate::PROJECT_MANIFEST_NAME),
            manifest.to_string(),
        )
        .unwrap();
        remove_mempalace(&mut app, root).unwrap();
        let mcp: Value =
            serde_json::from_str(&std::fs::read_to_string(root.join(".mcp.json")).unwrap())
                .unwrap();
        assert_eq!(mcp, json!({"mcpServers": {"custom": {"command": "x"}}}));
        let toml = std::fs::read_to_string(root.join(".codex/config.toml")).unwrap();
        assert!(!toml.contains("mempalace"));
        assert!(toml.contains("[mcp_servers.mine]"));
        assert!(!root.join(".mempalaceignore").exists());
        assert_eq!(
            app.config_released_keys[".codex/config.toml"],
            vec!["mcp_servers.mempalace"]
        );
        assert!(!app
            .config_released_keys
            .contains_key("/outside/mcp_config.json"));
        assert!(!is_mempalace_key("/mcp/mempalace-other"));
    }
}
