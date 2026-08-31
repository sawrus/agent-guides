//! Copy a knowledge-base directory into the project with marker injection and
//! managed-file protection (mirror of bash `copy_dir_contents`).

use crate::app::App;
use crate::manifest;
use crate::markers;
use crate::ui;
use serde_json::Value;
use std::path::Path;

/// `src_rel` is a knowledge-base relative directory such as
/// `extensions/opencode` or `areas/software/backend/rules`.
pub fn copy_dir_contents(
    app: &mut App,
    src_rel: &str,
    dest_root: &Path,
    skip_opencode_base_config: bool,
) -> crate::Result<()> {
    app.ensure_dir(dest_root);
    if app.dry_run {
        ui::log(
            app,
            &format!(
                "DRY-RUN copy managed contents {src_rel} -> {}",
                dest_root.display()
            ),
        );
        app.record_copied(&dest_root.to_string_lossy());
        return Ok(());
    }

    let manifest_path = app.project_manifest_path();
    let managed: Option<serde_json::Map<String, Value>> = if manifest_path.is_file() {
        let mut map = serde_json::Map::new();
        if let Ok(text) = std::fs::read_to_string(&manifest_path) {
            if let Ok(data) = serde_json::from_str::<Value>(&text) {
                if let Some(items) = data.get("managed_files").and_then(|v| v.as_array()) {
                    for item in items {
                        if let Some(rel) = item.get("path").and_then(|p| p.as_str()) {
                            map.insert(rel.to_string(), item.clone());
                        }
                    }
                }
            }
        }
        Some(map)
    } else {
        None
    };

    let is_opencode_ext =
        src_rel.ends_with("extensions/opencode") || src_rel == "extensions/opencode";
    let version = crate::app_version_label();

    for (rel, content) in app.kb.walk_files(src_rel) {
        if is_opencode_ext {
            if rel.starts_with("profiles/") {
                continue;
            }
            if skip_opencode_base_config
                && (rel == "opencode.json" || rel == "plugins/telegram-notification.ts")
            {
                continue;
            }
        }
        let target = dest_root.join(&rel);
        let project_rel = app.project_rel_path(&target);
        let source_ref = format!("{src_rel}/{rel}");

        if let Some(managed) = &managed {
            match managed.get(&project_rel) {
                None => {
                    if target.exists() {
                        ui::warn(
                            app,
                            &format!("Skipping unmanaged target on rerun: {project_rel}"),
                        );
                        app.record_skipped(&project_rel);
                        continue;
                    }
                }
                Some(item) => {
                    if item.get("marker").and_then(|m| m.as_str()) == Some("config") {
                        continue;
                    }
                    let expected = item
                        .get("content_hash")
                        .and_then(|h| h.as_str())
                        .unwrap_or("");
                    if target.exists() && !expected.is_empty() {
                        if let Ok(current) = crate::util::hash_file(&target) {
                            if current != expected {
                                ui::warn(
                                    app,
                                    &format!("Skipping user-modified managed file: {project_rel}"),
                                );
                                app.record_skipped(&project_rel);
                                continue;
                            }
                        }
                    }
                }
            }
        }

        let existing = std::fs::read_to_string(&target).ok();
        let file_name = target
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();
        let output = markers::add_marker(
            &content,
            &file_name,
            &source_ref,
            crate::APP_REPO_LINK,
            &version,
            existing.as_deref(),
        )
        .map_err(|e| -> crate::AnyError { e.into() })?;

        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent)?;
            app.record_created(&parent.to_string_lossy());
        }
        if existing.as_deref() == Some(output.as_str()) {
            manifest::register_managed_file(app, &target, &source_ref, "internal", false);
            continue;
        }
        std::fs::write(&target, &output)?;
        manifest::register_managed_file(app, &target, &source_ref, "internal", true);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_app(project: &Path) -> App {
        let mut app = App::new().unwrap();
        app.project_dir = project.to_string_lossy().to_string();
        app
    }

    #[test]
    fn copies_specialization_rules_with_markers() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        let dest = tmp.path().join(".agent/rules");
        copy_dir_contents(&mut app, "areas/software/backend/rules", &dest, false).unwrap();
        let entries: Vec<_> = std::fs::read_dir(&dest).unwrap().collect();
        assert!(!entries.is_empty());
        let first = entries[0].as_ref().unwrap().path();
        let content = std::fs::read_to_string(&first).unwrap();
        assert!(content.contains("agentic:") || content.contains("Generated by agentic"));
        assert!(!app.managed_records.is_empty());
    }

    #[test]
    fn opencode_extension_skips_profiles() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        let dest = tmp.path().join(".opencode");
        copy_dir_contents(&mut app, "extensions/opencode", &dest, false).unwrap();
        assert!(!dest.join("profiles").exists());
        assert!(dest.join("opencode.json").exists());
    }

    #[test]
    fn opencode_extension_skip_base_config() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        let dest = tmp.path().join(".opencode");
        copy_dir_contents(&mut app, "extensions/opencode", &dest, true).unwrap();
        assert!(!dest.join("opencode.json").exists());
        assert!(!dest.join("plugins/telegram-notification.ts").exists());
    }

    #[test]
    fn rerun_skips_user_modified() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        let dest = tmp.path().join(".agent/rules");
        copy_dir_contents(&mut app, "areas/software/backend/rules", &dest, false).unwrap();
        crate::manifest::write_agentic_manifest(&mut app, tmp.path()).unwrap();

        // modify a managed file
        let entries: Vec<_> = std::fs::read_dir(&dest)
            .unwrap()
            .filter_map(|e| e.ok())
            .collect();
        let victim = entries[0].path();
        std::fs::write(&victim, "user override").unwrap();

        let mut app2 = test_app(tmp.path());
        copy_dir_contents(&mut app2, "areas/software/backend/rules", &dest, false).unwrap();
        assert_eq!(std::fs::read_to_string(&victim).unwrap(), "user override");
        assert!(!app2.skipped_managed_paths.is_empty());
    }

    #[test]
    fn dry_run_copies_nothing() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.dry_run = true;
        let dest = tmp.path().join(".agent/rules");
        copy_dir_contents(&mut app, "areas/software/backend/rules", &dest, false).unwrap();
        assert!(!dest.exists());
    }
}
