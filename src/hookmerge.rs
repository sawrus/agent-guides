//! Ownership-tracked merge of native hook groups into shared JSON configs
//! (`.codex/hooks.json`, `.claude/settings.json`). Each managed group is
//! recorded in an ownership file so unrelated or user-edited handlers survive
//! enable, disable, and upgrade.

use crate::app::App;
use serde_json::{json, Value};
use std::path::Path;

pub struct HookSet<'a> {
    /// Project-relative config path, e.g. `.claude/settings.json`.
    pub config_rel: &'a str,
    /// Project-relative ownership record, e.g. `.agentic/claude-jev-hook-entries.json`.
    pub ownership_rel: &'a str,
    /// Command substring that identifies groups managed by this feature.
    pub command_marker: &'a str,
    pub status_message: &'a str,
    pub source_ref: &'a str,
    pub label: &'a str,
    /// `(event, matcher, command, timeout_seconds)`.
    pub entries: Vec<(&'a str, &'a str, String, u64)>,
}

pub fn group(matcher: &str, command: &str, timeout: u64, status: &str) -> Value {
    json!({"matcher": matcher, "hooks": [{"type": "command", "command": command, "timeout": timeout, "statusMessage": status}]})
}

fn read_object(path: &Path) -> crate::Result<Option<Value>> {
    if !path.exists() {
        return Ok(None);
    }
    let value: Value = serde_json::from_str(&std::fs::read_to_string(path)?)?;
    if !value.is_object() {
        return Err(format!("Not a JSON object: {}", path.display()).into());
    }
    Ok(Some(value))
}

/// Add (enabled) or remove (disabled) the managed groups. Never adopts or
/// overwrites a similarly named foreign/user-edited group.
pub fn sync(app: &mut App, project: &Path, set: &HookSet, enabled: bool) -> crate::Result<()> {
    if app.dry_run {
        return Ok(());
    }
    let path = crate::project_inventory::safe_path(project, set.config_rel)?;
    let ownership_path = crate::project_inventory::safe_path(project, set.ownership_rel)?;
    let mut owned = match read_object(&ownership_path) {
        Ok(v) => v.unwrap_or_else(|| json!({})),
        Err(_) => json!({}),
    };
    let existing = match read_object(&path) {
        Ok(v) => v,
        Err(error) => {
            crate::ui::warn(
                app,
                &format!(
                    "Skipping {} hooks: {} is not valid JSON ({error}); reconcile manually",
                    set.label, set.config_rel
                ),
            );
            app.record_skipped(set.config_rel);
            return Ok(());
        }
    };
    let has_owned = owned.as_object().is_some_and(|o| !o.is_empty());
    if !enabled && !has_owned {
        return Ok(());
    }
    let mut data = existing.unwrap_or_else(|| json!({}));
    let hooks = data
        .as_object_mut()
        .ok_or("Invalid hook config object")?
        .entry("hooks")
        .or_insert_with(|| json!({}));
    if !hooks.is_object() {
        crate::ui::warn(
            app,
            &format!("Skipping {} hooks: invalid hooks map", set.label),
        );
        return Ok(());
    }
    let hooks = hooks.as_object_mut().unwrap();
    let mut seen_events: Vec<&str> = Vec::new();
    for (event, matcher, command, timeout) in &set.entries {
        seen_events.push(event);
        let entry = group(matcher, command, *timeout, set.status_message);
        let groups = hooks
            .entry(event.to_string())
            .or_insert_with(|| json!([]))
            .as_array_mut()
            .ok_or("Invalid hook event array")?;
        let mut previous = owned.get(*event).cloned();
        let matching: Vec<Value> = groups
            .iter()
            .filter(|g| is_managed(g, set))
            .cloned()
            .collect();
        // v2.1.0 upgrades lost the gate ownership records; a group equal to ours is ours.
        if previous.is_none() && matching == [entry.clone()] {
            previous = Some(entry.clone());
        }
        if matching.iter().any(|g| Some(g) != previous.as_ref()) || matching.len() > 1 {
            crate::ui::warn(
                app,
                &format!(
                    "Preserving conflicting {} hook entry: {event}; reconcile manually",
                    set.label
                ),
            );
            app.record_skipped(&format!("{}:{event}", set.config_rel));
            continue;
        }
        if let Some(old) = previous {
            groups.retain(|g| g != &old);
        }
        if enabled {
            groups.push(entry.clone());
            owned[*event] = entry;
        } else if let Some(map) = owned.as_object_mut() {
            map.remove(*event);
        }
    }
    // Events dropped from a newer release: remove their unmodified groups.
    let stale: Vec<String> = owned
        .as_object()
        .map(|o| {
            o.keys()
                .filter(|k| !seen_events.contains(&k.as_str()))
                .cloned()
                .collect()
        })
        .unwrap_or_default();
    for event in stale {
        let old = owned[&event].clone();
        if let Some(groups) = hooks.get_mut(&event).and_then(Value::as_array_mut) {
            groups.retain(|g| g != &old);
        }
        owned.as_object_mut().unwrap().remove(&event);
    }
    hooks.retain(|_, v| v.as_array().is_none_or(|a| !a.is_empty()));
    if hooks.is_empty() {
        data.as_object_mut().unwrap().remove("hooks");
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
    crate::manifest::register_managed_file(app, &path, set.source_ref, "config", true);
    Ok(())
}

fn is_managed(group: &Value, set: &HookSet) -> bool {
    group["hooks"].as_array().is_some_and(|a| {
        a.iter().any(|h| {
            h["statusMessage"] == set.status_message
                || h["command"]
                    .as_str()
                    .is_some_and(|c| c.contains(set.command_marker))
        })
    })
}

pub fn python() -> &'static str {
    if cfg!(windows) {
        "python"
    } else {
        "python3"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn set<'a>(entries: Vec<(&'a str, &'a str, String, u64)>) -> HookSet<'a> {
        HookSet {
            config_rel: ".claude/settings.json",
            ownership_rel: ".agentic/test-entries.json",
            command_marker: ".agent/test/hook.py",
            status_message: "Agentic Test",
            source_ref: "generated:test",
            label: "Test",
            entries,
        }
    }

    fn app(project: &Path) -> App {
        let mut app = App::new().unwrap();
        app.project_dir = project.to_string_lossy().into();
        app
    }

    fn read(project: &Path) -> Value {
        serde_json::from_str(
            &std::fs::read_to_string(project.join(".claude/settings.json")).unwrap(),
        )
        .unwrap()
    }

    #[test]
    fn adds_and_removes_owned_groups_preserving_user_content() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        std::fs::create_dir_all(p.join(".claude")).unwrap();
        let user = json!({"env": {"A": "1"}, "hooks": {"Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "echo user"}]}]}});
        std::fs::write(p.join(".claude/settings.json"), user.to_string()).unwrap();
        let cmd = "python3 .agent/test/hook.py".to_string();
        let mut a = app(p);
        sync(&mut a, p, &set(vec![("Stop", "", cmd.clone(), 10)]), true).unwrap();
        let data = read(p);
        assert_eq!(data["env"]["A"], "1");
        assert_eq!(data["hooks"]["Stop"].as_array().unwrap().len(), 2);
        // Idempotent re-enable.
        sync(&mut a, p, &set(vec![("Stop", "", cmd.clone(), 10)]), true).unwrap();
        assert_eq!(read(p)["hooks"]["Stop"].as_array().unwrap().len(), 2);
        sync(&mut a, p, &set(vec![("Stop", "", cmd, 10)]), false).unwrap();
        assert_eq!(read(p), user);
    }

    #[test]
    fn identical_group_without_ownership_is_adopted() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let cmd = "python3 .agent/test/hook.py".to_string();
        let ours = group("", &cmd, 10, "Agentic Test");
        std::fs::create_dir_all(p.join(".claude")).unwrap();
        let config = json!({"hooks": {"Stop": [ours.clone()]}});
        std::fs::write(p.join(".claude/settings.json"), config.to_string()).unwrap();
        let mut a = app(p);
        sync(&mut a, p, &set(vec![("Stop", "", cmd.clone(), 10)]), true).unwrap();
        assert!(a.skipped_managed_paths.is_empty());
        assert_eq!(read(p)["hooks"]["Stop"], json!([ours]));
        let owned: Value = serde_json::from_str(
            &std::fs::read_to_string(p.join(".agentic/test-entries.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(owned["Stop"], ours);
        // A user-edited group without ownership stays foreign.
        let mut edited = config.clone();
        edited["hooks"]["Stop"][0]["hooks"][0]["timeout"] = json!(99);
        std::fs::write(p.join(".claude/settings.json"), edited.to_string()).unwrap();
        std::fs::remove_file(p.join(".agentic/test-entries.json")).unwrap();
        let mut b = app(p);
        sync(&mut b, p, &set(vec![("Stop", "", cmd, 10)]), true).unwrap();
        assert!(!b.skipped_managed_paths.is_empty());
        assert_eq!(read(p)["hooks"]["Stop"][0]["hooks"][0]["timeout"], 99);
    }

    #[test]
    fn user_edited_group_is_preserved_on_disable() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let cmd = "python3 .agent/test/hook.py".to_string();
        let mut a = app(p);
        sync(&mut a, p, &set(vec![("Stop", "", cmd.clone(), 10)]), true).unwrap();
        let mut data = read(p);
        data["hooks"]["Stop"][0]["hooks"][0]["timeout"] = json!(99);
        std::fs::write(p.join(".claude/settings.json"), data.to_string()).unwrap();
        sync(&mut a, p, &set(vec![("Stop", "", cmd, 10)]), false).unwrap();
        assert_eq!(read(p)["hooks"]["Stop"][0]["hooks"][0]["timeout"], 99);
        assert!(!a.skipped_managed_paths.is_empty());
    }

    #[test]
    fn invalid_json_is_never_overwritten() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        std::fs::create_dir_all(p.join(".claude")).unwrap();
        std::fs::write(p.join(".claude/settings.json"), "{ broken").unwrap();
        let mut a = app(p);
        let cmd = "python3 .agent/test/hook.py".to_string();
        sync(&mut a, p, &set(vec![("Stop", "", cmd, 10)]), true).unwrap();
        assert_eq!(
            std::fs::read_to_string(p.join(".claude/settings.json")).unwrap(),
            "{ broken"
        );
    }

    #[test]
    fn disabled_without_ownership_writes_nothing() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let mut a = app(p);
        let cmd = "python3 .agent/test/hook.py".to_string();
        sync(&mut a, p, &set(vec![("Stop", "", cmd, 10)]), false).unwrap();
        assert!(!p.join(".claude/settings.json").exists());
    }

    #[test]
    fn dropped_events_are_removed() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path();
        let mut a = app(p);
        let cmd = "python3 .agent/test/hook.py".to_string();
        sync(
            &mut a,
            p,
            &set(vec![
                ("Stop", "", cmd.clone(), 10),
                ("Notification", "x", cmd.clone(), 10),
            ]),
            true,
        )
        .unwrap();
        sync(&mut a, p, &set(vec![("Stop", "", cmd, 10)]), true).unwrap();
        assert!(read(p)["hooks"].get("Notification").is_none());
    }
}
