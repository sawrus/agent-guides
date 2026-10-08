//! Project reconciliation in an isolated staging tree.
use crate::project_inventory::{inventory, owned_files, recognized, safe_path};
use crate::{app::App, manifest, ui, util};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

pub const BASELINES: &str = ".agentic/baselines";
fn old_manifest(app: &App) -> Value {
    std::fs::read(app.project_manifest_path())
        .ok()
        .and_then(|v| serde_json::from_slice(&v).ok())
        .unwrap_or(Value::Null)
}

fn old_item(app: &App, rel: &str) -> Option<Value> {
    old_manifest(app)["managed_files"]
        .as_array()?
        .iter()
        .find(|v| v["path"] == rel)
        .cloned()
}

pub fn can_write(app: &mut App, dest: &Path, config: bool) -> bool {
    let root = Path::new(&app.project_dir);
    let Ok(relative) = dest.strip_prefix(root) else {
        ui::log(
            app,
            &format!("Preserved global configuration: {}", dest.display()),
        );
        return false;
    };
    let rel = relative.to_string_lossy().to_string();
    if let Err(error) = safe_path(root, &rel) {
        ui::warn(app, &error.to_string());
        app.record_skipped(&rel);
        return false;
    }
    if config
        || !dest.exists()
        || old_item(app, &rel).is_some()
        || std::fs::read_to_string(dest)
            .ok()
            .is_some_and(|s| recognized(&s))
    {
        return true;
    }
    app.record_skipped(&rel);
    app.upgrade_actions.push(format!(
        "Preserved user file (manual integration required): {rel}"
    ));
    false
}

pub fn baseline_path(root: &Path, rel: &str) -> PathBuf {
    root.join(BASELINES).join(util::sha256_hex(rel.as_bytes()))
}

pub fn instruction_output(
    app: &mut App,
    dest: &Path,
    generated: &str,
    existing: Option<&str>,
) -> crate::Result<String> {
    // JSON configurations may contain credentials; they never enter baseline storage.
    if dest.extension().and_then(|s| s.to_str()) == Some("json") {
        return Ok(generated.into());
    }
    let rel = app.project_rel_path(dest);
    let baseline = baseline_path(Path::new(&app.project_dir), &rel);
    let mut output = generated.to_owned();
    if app.upgrade_mode && !app.upgrade_force {
        if let Some(local) = existing.filter(|s| *s != generated) {
            let base = std::fs::read_to_string(&baseline).ok().filter(|s| {
                old_item(app, &rel)
                    .and_then(|v| v["generated_hash"].as_str().map(str::to_owned))
                    .is_some_and(|hash| hash == util::sha256_hex(s.as_bytes()))
            });
            if let Some(base) = base {
                match diffy::merge(&base, local, generated) {
                    Ok(merged) => {
                        output = merged;
                        app.upgrade_actions.push(format!("Merged: {rel}"));
                    }
                    Err(_) => app
                        .upgrade_actions
                        .push(format!("Replaced conflict (local copy in backup): {rel}")),
                }
            } else if old_item(app, &rel)
                .is_none_or(|v| v["content_hash"] != util::sha256_hex(local.as_bytes()))
            {
                app.upgrade_actions.push(format!(
                    "Replaced without baseline (local copy in backup): {rel}"
                ));
            }
        }
    }
    safe_path(Path::new(&app.project_dir), BASELINES)?;
    std::fs::create_dir_all(baseline.parent().unwrap())?;
    if std::fs::read_to_string(&baseline).ok().as_deref() != Some(generated) {
        std::fs::write(&baseline, generated)?;
    }
    Ok(output)
}

fn settings_valid(app: &App, data: &Value) -> bool {
    matches!(data["version"].as_u64(), None | Some(1 | 2))
        && ["agent_os", "areas", "specializations"].iter().all(|key| {
            data["settings"][key]
                .as_array()
                .is_some_and(|a| !a.is_empty() && a.iter().all(Value::is_string))
        })
        && app
            .selected_areas
            .iter()
            .all(|a| app.kb.list_areas().contains(a))
        && app.selected_specs.iter().all(|s| {
            s.split_once('.').is_some_and(|(a, spec)| {
                app.selected_areas.contains(&a.to_string())
                    && app.kb.dir_exists(&format!("areas/{a}/{spec}"))
            })
        })
        && app
            .selected_agent_os
            .iter()
            .all(|a| a == crate::DEFAULT_AGENT_OS || app.kb.agentos_choices().contains(a))
        && app
            .selected_mcps
            .iter()
            .all(|id| crate::mcp::registry_entry(id).is_some())
}

fn reset_settings(app: &mut App) {
    app.selected_agent_os = vec!["default".into()];
    app.selected_areas = vec!["software".into()];
    app.selected_specs = vec!["software.general".into()];
    app.selected_mcps.clear();
    app.selected_opencode_profile.clear();
    app.opencode_telegram_enabled = "false".into();
    app.opencode_agent_model_mapper_enabled = "false".into();
    app.opencode_plugins_configured = true;
}

fn cleanup(
    app: &mut App,
    owned: &BTreeMap<String, Value>,
    desired: &BTreeSet<String>,
    force: bool,
) -> crate::Result<()> {
    for (rel, item) in owned {
        if desired.contains(rel) || item["marker"] == "config" {
            continue;
        }
        let path = safe_path(Path::new(&app.project_dir), rel)?;
        if !path.is_file() {
            continue;
        }
        let hash = util::hash_file(&path)?;
        if force || item["content_hash"].as_str() == Some(&hash) {
            std::fs::remove_file(&path)?;
            let baseline = baseline_path(Path::new(&app.project_dir), rel);
            if baseline.is_file() {
                std::fs::remove_file(baseline)?;
            }
            app.upgrade_actions
                .push(format!("Removed obsolete artifact: {rel}"));
        } else {
            app.upgrade_actions
                .push(format!("Preserved customized obsolete artifact: {rel}"));
        }
    }
    Ok(())
}

pub fn synchronize(app: &mut App) -> crate::Result<()> {
    let requested = if app.project_dir.is_empty() {
        std::env::current_dir()?
    } else {
        PathBuf::from(&app.project_dir)
    };
    let root = PathBuf::from(util::normalize_project_dir_path(
        &requested.to_string_lossy(),
    ));
    let before = if root.is_dir() {
        inventory(&root)?
    } else {
        BTreeMap::new()
    };
    let data: Value = before
        .get(crate::PROJECT_MANIFEST_NAME)
        .and_then(|v| serde_json::from_slice(v).ok())
        .unwrap_or(Value::Null);
    let owned = owned_files(&before, &data);
    if !app.upgrade_force && !before.contains_key(crate::PROJECT_MANIFEST_NAME) && owned.is_empty()
    {
        ui::log(
            app,
            "No .agentic.json or recognized artifacts; knowledge base upgrade complete",
        );
        return Ok(());
    }
    app.upgrade_mode = true;
    app.project_dir = root.to_string_lossy().to_string();
    app.interactive_override = Some(false);
    // Replay must not import environment selections or write global credentials.
    app.enable_context7_env = Some("n".into());
    app.enable_mempalace_env = Some("n".into());
    app.selected_mcps.clear();
    manifest::load_install_settings_from_manifest(app, &root.join(crate::PROJECT_MANIFEST_NAME))?;
    if !settings_valid(app, &data) {
        reset_settings(app);
        ui::warn(
            app,
            "No valid install settings; using default + software.general (MCPs/plugins off)",
        );
    }
    app.enable_context7_env = Some(
        if app.selected_mcp_contains("context7") {
            "y"
        } else {
            "n"
        }
        .into(),
    );
    app.enable_mempalace_env = Some(
        if app.selected_mcp_contains("mempalace") {
            "y"
        } else {
            "n"
        }
        .into(),
    );
    app.install_settings_replay = true;
    ui::log(
        app,
        &format!(
            "Detected managed project in {}; syncing instructions",
            root.display()
        ),
    );
    ui::log(app, &format!("Knowledge base: {}", app.kb.root_label()));
    ui::log(
        app,
        &format!("Agent OS targets: {}", app.selected_agent_os.join(", ")),
    );
    let staging = tempfile::tempdir()?;
    for (rel, bytes) in &before {
        let path = safe_path(staging.path(), rel)?;
        std::fs::create_dir_all(path.parent().unwrap())?;
        std::fs::write(path, bytes)?;
    }
    app.project_dir = staging.path().to_string_lossy().to_string();
    let dry_run = app.dry_run;
    app.dry_run = false;
    let result = prepare(app, staging.path(), &data, &owned);
    app.project_dir = root.to_string_lossy().to_string();
    app.dry_run = dry_run;
    let after = result?;
    for action in &app.upgrade_actions {
        ui::log(app, action);
    }
    crate::project_transaction::apply(app, &root, &before, &after)?;
    if !dry_run {
        crate::doctor::run_agentic_doctor(app);
        if app.selected_mcp_contains("mempalace") {
            crate::mempalace::setup_mempalace_for_agentic(app, true);
            crate::mempalace::upgrade_mempalace_graph(app);
        }
    }
    Ok(())
}

fn prepare(
    app: &mut App,
    staging: &Path,
    data: &Value,
    owned: &BTreeMap<String, Value>,
) -> crate::Result<BTreeMap<String, Vec<u8>>> {
    if app.upgrade_force {
        for (rel, item) in owned {
            let path = safe_path(staging, rel)?;
            if !path.is_file() {
                continue;
            }
            if item["marker"] == "config"
                || matches!(path.extension().and_then(|s| s.to_str()), Some("json"))
            {
                crate::upgrade_config::clean(app, &path, data)?;
            } else {
                std::fs::remove_file(path)?;
            }
        }
        let baselines = staging.join(BASELINES);
        if baselines.is_dir() {
            std::fs::remove_dir_all(baselines)?;
        }
    }
    crate::install::run_install(app)?;
    let desired = app.managed_records.iter().map(|r| r.path.clone()).collect();
    cleanup(app, owned, &desired, app.upgrade_force)?;
    // Rebuild records after cleanup instead of retaining paths removed upstream.
    manifest::write_agentic_manifest(app, staging)?;
    inventory(staging)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    fn app_at(root: &Path) -> App {
        let mut app = App::new().unwrap();
        app.project_dir = root.to_string_lossy().to_string();
        app
    }

    #[test]
    fn merges_separate_changes_but_replaces_conflicting_changes() {
        let root = tempfile::tempdir().unwrap();
        let mut app = app_at(root.path());
        let path = root.path().join("guide.md");
        let base = "first\nsecond\nthird\n";
        let generated = instruction_output(&mut app, &path, base, None).unwrap();
        std::fs::write(&path, generated).unwrap();
        manifest::register_managed_file(&mut app, &path, "generated:test", "internal", false);
        manifest::write_agentic_manifest(&mut app, root.path()).unwrap();
        app.upgrade_mode = true;
        let merged = instruction_output(
            &mut app,
            &path,
            "FIRST\nsecond\nthird\n",
            Some("first\nsecond\nTHIRD\n"),
        )
        .unwrap();
        assert_eq!(merged, "FIRST\nsecond\nTHIRD\n");
        assert_eq!(
            std::fs::read_to_string(baseline_path(root.path(), "guide.md")).unwrap(),
            "FIRST\nsecond\nthird\n"
        );
        // Reset baseline and ownership to reproduce intersecting edits.
        std::fs::write(baseline_path(root.path(), "guide.md"), base).unwrap();
        let replaced = instruction_output(
            &mut app,
            &path,
            "new\nsecond\nthird\n",
            Some("local\nsecond\nthird\n"),
        )
        .unwrap();
        assert_eq!(replaced, "new\nsecond\nthird\n");
        assert!(app
            .upgrade_actions
            .iter()
            .any(|s| s.contains("Replaced conflict")));
    }

    #[test]
    fn instruction_metadata_and_paths_require_positive_evidence() {
        assert!(!recognized(
            "# My docs\nGenerated by agentic in the example below"
        ));
        assert!(recognized(
            "# Agentic Project Guidelines\n\nGenerated by agentic.\n"
        ));
        let root = tempfile::tempdir().unwrap();
        assert!(safe_path(root.path(), "../file").is_err());
        assert!(safe_path(root.path(), "/etc/file").is_err());
        assert!(safe_path(root.path(), "rules/file").is_ok());
    }

    #[test]
    fn obsolete_owned_files_are_removed_or_preserved_by_local_hash() {
        let root = tempfile::tempdir().unwrap();
        let mut app = app_at(root.path());
        std::fs::write(root.path().join("old.md"), "old").unwrap();
        std::fs::write(root.path().join("modified.md"), "edited").unwrap();
        let owned = BTreeMap::from([
            (
                "old.md".into(),
                json!({"content_hash": util::sha256_hex(b"old")}),
            ),
            (
                "modified.md".into(),
                json!({"content_hash": util::sha256_hex(b"old")}),
            ),
        ]);
        cleanup(&mut app, &owned, &BTreeSet::new(), false).unwrap();
        assert!(!root.path().join("old.md").exists());
        assert!(root.path().join("modified.md").exists());
        cleanup(&mut app, &owned, &BTreeSet::new(), true).unwrap();
        assert!(!root.path().join("modified.md").exists());
    }
}
