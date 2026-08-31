//! Project manifest (.agentic.json) handling and managed-file write helpers.

use crate::app::{App, ManagedRecord};
use crate::markers;
use crate::ui;
use crate::util;
use chrono::{SecondsFormat, Utc};
use serde_json::{json, Map, Value};
use std::path::Path;

pub fn now_utc_iso() -> String {
    Utc::now().to_rfc3339_opts(SecondsFormat::Secs, true)
}

fn read_manifest(path: &Path) -> Option<Value> {
    let text = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&text).ok()
}

fn manifest_item_for_path<'a>(manifest: &'a Value, rel: &str) -> Option<&'a Value> {
    manifest
        .get("managed_files")?
        .as_array()?
        .iter()
        .find(|item| item.get("path").and_then(|p| p.as_str()) == Some(rel))
}

/// Mirror of `can_write_managed_file`: on rerun skip unmanaged existing
/// targets and user-modified managed files.
pub fn can_write_managed_file(app: &mut App, dest: &Path) -> bool {
    let rel = app.project_rel_path(dest);
    let manifest_path = app.project_manifest_path();
    if manifest_path.is_file() {
        let manifest = read_manifest(&manifest_path).unwrap_or(Value::Null);
        let item = manifest_item_for_path(&manifest, &rel).cloned();
        match item {
            None => {
                if dest.exists() {
                    ui::warn(app, &format!("Skipping unmanaged target on rerun: {rel}"));
                    app.record_skipped(&rel);
                    return false;
                }
                return true;
            }
            Some(item) => {
                if dest.is_file() {
                    let expected = item
                        .get("content_hash")
                        .and_then(|h| h.as_str())
                        .unwrap_or("");
                    if !expected.is_empty() {
                        if let Ok(current) = util::hash_file(dest) {
                            if current != expected {
                                ui::warn(
                                    app,
                                    &format!("Skipping user-modified managed file: {rel}"),
                                );
                                app.record_skipped(&rel);
                                return false;
                            }
                        }
                    }
                }
            }
        }
    }
    true
}

pub fn register_managed_file(
    app: &mut App,
    dest: &Path,
    source_ref: &str,
    marker: &str,
    copied: bool,
) {
    let rel = app.project_rel_path(dest);
    let digest = util::hash_file(dest).unwrap_or_default();
    app.managed_records.push(ManagedRecord {
        path: rel,
        source: source_ref.to_string(),
        content_hash: digest,
        marker: marker.to_string(),
    });
    if copied {
        app.record_copied(&dest.to_string_lossy());
    }
}

/// Copy `content` (source text) to `dest` with a marker; mirror of
/// `write_file_with_agentic_marker`.
pub fn write_file_with_agentic_marker(
    app: &mut App,
    src_content: &str,
    dest: &Path,
    source_ref: &str,
) -> crate::Result<()> {
    if app.dry_run {
        ui::log(
            app,
            &format!("DRY-RUN write managed file {}", dest.display()),
        );
        app.record_copied(&dest.to_string_lossy());
        return Ok(());
    }
    if !can_write_managed_file(app, dest) {
        return Ok(());
    }
    if let Some(parent) = dest.parent() {
        app.ensure_dir(parent);
    }
    let existing = std::fs::read_to_string(dest).ok();
    let output = markers::add_marker(
        src_content,
        &dest
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default(),
        source_ref,
        crate::APP_REPO_LINK,
        &crate::app_version_label(),
        existing.as_deref(),
    )
    .map_err(|e| -> crate::AnyError { e.into() })?;

    if existing.as_deref() == Some(output.as_str()) {
        register_managed_file(app, dest, source_ref, "internal", false);
        return Ok(());
    }
    std::fs::write(dest, &output)?;
    register_managed_file(app, dest, source_ref, "internal", true);
    Ok(())
}

/// Mirror of `write_json_config_file`: mutate destination JSON object via a
/// closure; register with marker "config".
pub fn write_json_config_file<F>(
    app: &mut App,
    dest: &Path,
    source_ref: &str,
    mutate: F,
) -> crate::Result<()>
where
    F: FnOnce(&mut Map<String, Value>, &str),
{
    if app.dry_run {
        ui::log(
            app,
            &format!("DRY-RUN update JSON config file {}", dest.display()),
        );
        app.record_copied(&dest.to_string_lossy());
        return Ok(());
    }
    if !can_write_managed_file(app, dest) {
        return Ok(());
    }
    if let Some(parent) = dest.parent() {
        app.ensure_dir(parent);
    }
    let existing = std::fs::read_to_string(dest).ok();
    let mut data: Value = existing
        .as_deref()
        .and_then(|t| serde_json::from_str(t).ok())
        .unwrap_or(Value::Null);
    if !data.is_object() {
        data = json!({});
    }
    let key = app.context7_api_key.clone();
    mutate(data.as_object_mut().unwrap(), &key);
    let output = markers::to_pretty_json(&data);
    if existing.as_deref() == Some(output.as_str()) {
        register_managed_file(app, dest, source_ref, "config", false);
        return Ok(());
    }
    std::fs::write(dest, &output)?;
    register_managed_file(app, dest, source_ref, "config", true);
    Ok(())
}

/// Mirror of `write_text_config_file`.
pub fn write_text_config_file(
    app: &mut App,
    dest: &Path,
    source_ref: &str,
    content: &str,
) -> crate::Result<()> {
    if app.dry_run {
        ui::log(
            app,
            &format!("DRY-RUN write text config file {}", dest.display()),
        );
        app.record_copied(&dest.to_string_lossy());
        return Ok(());
    }
    if !can_write_managed_file(app, dest) {
        return Ok(());
    }
    if let Some(parent) = dest.parent() {
        app.ensure_dir(parent);
    }
    let existing = std::fs::read_to_string(dest).ok();
    if existing.as_deref() == Some(content) {
        register_managed_file(app, dest, source_ref, "config", false);
        return Ok(());
    }
    std::fs::write(dest, content)?;
    register_managed_file(app, dest, source_ref, "config", true);
    Ok(())
}

/// Write the project manifest, preserving created_at/created_by and per-file
/// updated_at when content is unchanged. Skips rewriting when nothing except
/// updated_at/updated_by changed.
pub fn write_agentic_manifest(app: &mut App, project_dir: &Path) -> crate::Result<()> {
    let manifest_path = project_dir.join(crate::PROJECT_MANIFEST_NAME);
    if app.dry_run {
        ui::log(app, &format!("DRY-RUN write {}", manifest_path.display()));
        return Ok(());
    }

    crate::mcp::sync_legacy_mcp_env_from_selected(app);

    let now = now_utc_iso();
    let old_data = read_manifest(&manifest_path);
    let mut created_at = now.clone();
    let mut existing: Map<String, Value> = Map::new();
    if let Some(old) = &old_data {
        if let Some(v) = old.get("created_at").and_then(|v| v.as_str()) {
            created_at = v.to_string();
        }
        if let Some(items) = old.get("managed_files").and_then(|v| v.as_array()) {
            for item in items {
                if let Some(path) = item.get("path").and_then(|p| p.as_str()) {
                    existing.insert(path.to_string(), item.clone());
                }
            }
        }
    }
    let original_existing = existing.clone();

    for record in app.managed_records.clone() {
        let old_item = original_existing.get(&record.path);
        let old_updated_at = old_item
            .and_then(|i| i.get("updated_at"))
            .and_then(|v| v.as_str())
            .unwrap_or(&now)
            .to_string();
        let unchanged = old_item
            .map(|i| {
                i.get("source").and_then(|v| v.as_str()) == Some(record.source.as_str())
                    && i.get("content_hash").and_then(|v| v.as_str())
                        == Some(record.content_hash.as_str())
                    && i.get("marker").and_then(|v| v.as_str()) == Some(record.marker.as_str())
            })
            .unwrap_or(false);
        let item_updated_at = if unchanged {
            old_updated_at
        } else {
            now.clone()
        };
        existing.insert(
            record.path.clone(),
            json!({
                "path": record.path,
                "source": record.source,
                "content_hash": record.content_hash,
                "marker": record.marker,
                "updated_at": item_updated_at,
            }),
        );
    }

    let old_agentic = old_data
        .as_ref()
        .and_then(|d| d.get("_agentic"))
        .cloned()
        .unwrap_or(Value::Null);
    let old_settings = old_data
        .as_ref()
        .and_then(|d| d.get("settings"))
        .cloned()
        .unwrap_or(Value::Null);
    let created_by = old_agentic
        .get("created_by")
        .and_then(|v| v.as_str())
        .unwrap_or(&crate::app_version_label())
        .to_string();

    let mut opencode_plugins = old_settings
        .get("opencode_plugins")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();
    let mut telegram = opencode_plugins
        .get("telegram")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();
    let mut mapper = opencode_plugins
        .get("agentModelMapper")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();

    let telegram_enabled: Option<bool> = match app.opencode_telegram_enabled.as_str() {
        "true" => Some(true),
        "false" => Some(false),
        _ => None,
    };
    let mapper_enabled: Option<bool> = match app.opencode_agent_model_mapper_enabled.as_str() {
        "true" => Some(true),
        "false" => Some(false),
        _ => None,
    };
    if let Some(enabled) = telegram_enabled {
        telegram = Map::new();
        telegram.insert("enabled".to_string(), json!(enabled));
    }
    if let Some(enabled) = mapper_enabled {
        mapper = Map::new();
        mapper.insert("enabled".to_string(), json!(enabled));
    }
    if !telegram.is_empty() || !mapper.is_empty() {
        opencode_plugins = Map::new();
        opencode_plugins.insert(
            "telegram".to_string(),
            if telegram.is_empty() {
                json!({"enabled": false})
            } else {
                Value::Object(telegram)
            },
        );
        opencode_plugins.insert(
            "agentModelMapper".to_string(),
            if mapper.is_empty() {
                json!({"enabled": false})
            } else {
                Value::Object(mapper)
            },
        );
    }

    let mut managed_files: Vec<Value> = existing.into_iter().map(|(_, v)| v).collect();
    managed_files.sort_by(|a, b| {
        let pa = a.get("path").and_then(|v| v.as_str()).unwrap_or("");
        let pb = b.get("path").and_then(|v| v.as_str()).unwrap_or("");
        pa.cmp(pb)
    });

    let data = json!({
        "_agentic": {
            "generated_by": "agentic",
            "repository": crate::APP_REPO_LINK,
            "created_by": created_by,
            "updated_by": crate::app_version_label(),
        },
        "version": 1,
        "created_at": created_at,
        "updated_at": now,
        "settings": {
            "agent_os": app.selected_agent_os,
            "areas": app.selected_areas,
            "specializations": app.selected_specs,
            "mcp_integrations": app.selected_mcps,
            "opencode_profile": app.selected_opencode_profile,
            "opencode_plugins": Value::Object(opencode_plugins),
            "source_repo": crate::APP_REPO_LINK,
            "source_checkout": app.kb.root_label(),
        },
        "managed_files": managed_files,
        "skipped_files": app.skipped_managed_paths,
    });

    if let Some(old) = &old_data {
        let mut old_compare = old.clone();
        let mut new_compare = data.clone();
        for payload in [&mut old_compare, &mut new_compare] {
            if let Some(obj) = payload.as_object_mut() {
                obj.remove("updated_at");
                if let Some(agentic) = obj.get_mut("_agentic").and_then(|v| v.as_object_mut()) {
                    agentic.remove("updated_by");
                }
            }
        }
        if old_compare == new_compare {
            return Ok(());
        }
    }

    std::fs::write(&manifest_path, markers::to_pretty_json(&data))?;
    app.record_copied(&manifest_path.to_string_lossy());
    Ok(())
}

/// Load selections from an existing manifest for replay installs.
pub fn load_install_settings_from_manifest(
    app: &mut App,
    manifest_path: &Path,
) -> crate::Result<()> {
    let Some(data) = read_manifest(manifest_path) else {
        return Ok(());
    };
    app.install_settings_replay = true;
    let settings = data.get("settings").cloned().unwrap_or(Value::Null);

    let load_list = |key: &str| -> Vec<String> {
        settings
            .get(key)
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str())
                    .map(|s| s.to_string())
                    .collect()
            })
            .unwrap_or_default()
    };
    let loaded_agent_os = load_list("agent_os");
    let loaded_areas = load_list("areas");
    let loaded_specs = load_list("specializations");
    let loaded_mcps = load_list("mcp_integrations");

    if app.selected_agent_os == vec![crate::DEFAULT_AGENT_OS.to_string()]
        && !loaded_agent_os.is_empty()
    {
        app.selected_agent_os = loaded_agent_os;
    }
    if app.selected_areas.is_empty() && !loaded_areas.is_empty() {
        app.selected_areas = loaded_areas;
    }
    if app.selected_specs.is_empty() && !loaded_specs.is_empty() {
        app.selected_specs = loaded_specs;
    }
    if !loaded_mcps.is_empty() {
        for mcp in loaded_mcps {
            crate::mcp::add_selected_mcp(app, &mcp);
        }
        crate::mcp::sync_legacy_mcp_env_from_selected(app);
    }

    let plugins = settings
        .get("opencode_plugins")
        .cloned()
        .unwrap_or(Value::Null);
    if let Some(telegram) = plugins.get("telegram").and_then(|v| v.as_object()) {
        if let Some(enabled) = telegram.get("enabled").and_then(|v| v.as_bool()) {
            app.opencode_telegram_enabled = enabled.to_string();
            app.opencode_telegram_bot_token = telegram
                .get("botToken")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            app.opencode_telegram_chat_id = telegram
                .get("chatId")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            if app.opencode_telegram_bot_token.is_empty()
                || app.opencode_telegram_chat_id.is_empty()
            {
                let _ = crate::config::load_global_telegram_credentials(app);
            } else {
                let bot = app.opencode_telegram_bot_token.clone();
                let chat = app.opencode_telegram_chat_id.clone();
                let _ = crate::config::save_global_telegram_credentials(app, &bot, &chat);
            }
            app.opencode_plugins_configured = true;
        }
    }
    if let Some(mapper) = plugins.get("agentModelMapper").and_then(|v| v.as_object()) {
        if let Some(enabled) = mapper.get("enabled").and_then(|v| v.as_bool()) {
            app.opencode_agent_model_mapper_enabled = enabled.to_string();
            app.opencode_plugins_configured = true;
        }
    }
    if let Some(profile) = settings.get("opencode_profile").and_then(|v| v.as_str()) {
        if !profile.is_empty() {
            app.selected_opencode_profile = profile.to_string();
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_app(project: &Path) -> App {
        let mut app = App::new().unwrap();
        app.project_dir = project.to_string_lossy().to_string();
        app.selected_areas = vec!["software".into()];
        app.selected_specs = vec!["software.backend".into()];
        app
    }

    #[test]
    fn manifest_write_and_replay_roundtrip() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["opencode".into()];
        app.managed_records.push(ManagedRecord {
            path: "AGENTS.md".into(),
            source: "generated:AGENTS.md".into(),
            content_hash: "abc".into(),
            marker: "internal".into(),
        });
        write_agentic_manifest(&mut app, tmp.path()).unwrap();
        let manifest_path = tmp.path().join(".agentic.json");
        assert!(manifest_path.is_file());

        let mut app2 = App::new().unwrap();
        load_install_settings_from_manifest(&mut app2, &manifest_path).unwrap();
        assert!(app2.install_settings_replay);
        assert_eq!(app2.selected_agent_os, vec!["opencode"]);
        assert_eq!(app2.selected_areas, vec!["software"]);
        assert_eq!(app2.selected_specs, vec!["software.backend"]);
    }

    #[test]
    fn manifest_unchanged_rewrite_is_skipped() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        write_agentic_manifest(&mut app, tmp.path()).unwrap();
        let manifest_path = tmp.path().join(".agentic.json");
        let first = std::fs::read_to_string(&manifest_path).unwrap();
        // Rewrite with the same settings: file must stay byte-identical
        std::thread::sleep(std::time::Duration::from_millis(1100));
        let mut app2 = test_app(tmp.path());
        write_agentic_manifest(&mut app2, tmp.path()).unwrap();
        let second = std::fs::read_to_string(&manifest_path).unwrap();
        assert_eq!(first, second);
        assert!(!app2
            .copied_paths
            .contains(&manifest_path.to_string_lossy().to_string()));
    }

    #[test]
    fn can_write_skips_user_modified() {
        let tmp = tempfile::tempdir().unwrap();
        let dest = tmp.path().join("file.md");
        std::fs::write(&dest, "content").unwrap();
        let mut app = test_app(tmp.path());
        register_managed_file(&mut app, &dest, "src", "internal", true);
        write_agentic_manifest(&mut app, tmp.path()).unwrap();

        // unchanged -> allowed
        let mut app2 = test_app(tmp.path());
        assert!(can_write_managed_file(&mut app2, &dest));

        // user modifies -> skipped
        std::fs::write(&dest, "user changed").unwrap();
        let mut app3 = test_app(tmp.path());
        assert!(!can_write_managed_file(&mut app3, &dest));
        assert_eq!(app3.skipped_managed_paths, vec!["file.md"]);

        // unmanaged existing file -> skipped
        let other = tmp.path().join("other.md");
        std::fs::write(&other, "x").unwrap();
        let mut app4 = test_app(tmp.path());
        assert!(!can_write_managed_file(&mut app4, &other));
    }

    #[test]
    fn write_text_config_file_idempotent() {
        let tmp = tempfile::tempdir().unwrap();
        let dest = tmp.path().join("cfg.txt");
        let mut app = test_app(tmp.path());
        write_text_config_file(&mut app, &dest, "generated:test", "hello").unwrap();
        assert_eq!(std::fs::read_to_string(&dest).unwrap(), "hello");
        assert_eq!(app.managed_records.len(), 1);
        write_agentic_manifest(&mut app, tmp.path()).unwrap();

        let mut app2 = test_app(tmp.path());
        write_text_config_file(&mut app2, &dest, "generated:test", "hello").unwrap();
        // unchanged -> not recorded as copied
        assert!(!app2
            .copied_paths
            .contains(&dest.to_string_lossy().to_string()));
    }

    #[test]
    fn write_json_config_file_merges() {
        let tmp = tempfile::tempdir().unwrap();
        let dest = tmp.path().join("cfg.json");
        std::fs::write(&dest, "{\"keep\": 1}").unwrap();
        let mut app = test_app(tmp.path());
        write_json_config_file(&mut app, &dest, "generated:test", |data, _key| {
            data.insert("added".to_string(), json!(true));
        })
        .unwrap();
        let parsed: Value = serde_json::from_str(&std::fs::read_to_string(&dest).unwrap()).unwrap();
        assert_eq!(parsed["keep"], json!(1));
        assert_eq!(parsed["added"], json!(true));
    }

    #[test]
    fn dry_run_writes_nothing() {
        let tmp = tempfile::tempdir().unwrap();
        let dest = tmp.path().join("cfg.txt");
        let mut app = test_app(tmp.path());
        app.dry_run = true;
        write_text_config_file(&mut app, &dest, "generated:test", "hello").unwrap();
        assert!(!dest.exists());
        write_agentic_manifest(&mut app, tmp.path()).unwrap();
        assert!(!tmp.path().join(".agentic.json").exists());
    }
}
