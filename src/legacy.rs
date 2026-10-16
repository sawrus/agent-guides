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

fn drop_renamed_keys(config: &mut Value) -> bool {
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
        if drop_renamed_keys(&mut data) {
            std::fs::write(&path, crate::markers::to_pretty_json(&data))?;
            app.upgrade_actions
                .push(format!("Removed renamed role keys: {rel}"));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

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
}
