//! Copy a knowledge-base directory into the project with marker injection and
//! managed-file protection (mirror of bash `copy_dir_contents`).

use crate::app::App;
use crate::manifest;
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

    let is_opencode_ext =
        src_rel.ends_with("extensions/opencode") || src_rel == "extensions/opencode";

    for (rel, mut content) in app.kb.walk_files(src_rel) {
        if autoloads_every_rule(dest_root) && is_manual_rule(&content) {
            continue;
        }
        if crate::profile::skips_extension_file(app, src_rel, &rel) {
            continue;
        }
        if src_rel == "extensions/opencode"
            && rel == crate::gate::OPENCODE_PLUGIN_REL
            && !crate::gate::enabled(app)
        {
            continue;
        }
        if src_rel.ends_with("/workflows") {
            content = strip_agent_diagram(&content);
        }
        if matches!(src_rel, "extensions/codex" | "extensions/opencode")
            && rel.starts_with("hooks/")
        {
            continue;
        }
        // JEV reads tiers through `.agent/jev/` (Codex: model-defaults.json, OpenCode:
        // opencode-model-tiers.json), never from the host config directories.
        if matches!(src_rel, "extensions/codex" | "extensions/opencode")
            && rel == "model-tiers.json"
        {
            continue;
        }
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
        // Custom-agent model settings override even explicit spawn settings in
        // Codex. Leave bundled defaults open for JEV; managed-file protection
        // below still preserves user-edited role profiles. The lean helpers keep
        // their reasoning effort: JEV routes the model, not the depth.
        if app.jev_enabled == Some(true)
            && src_rel == "extensions/codex"
            && rel.starts_with("agents/")
            && rel.ends_with(".toml")
        {
            let team = crate::profile::is_team_for(app, "codex");
            content = content
                .lines()
                .filter(|line| {
                    let effort = team && line.starts_with("model_reasoning_effort =");
                    !(line.starts_with("model =") || effort)
                })
                .map(|line| format!("{line}\n"))
                .collect();
        }
        if src_rel == "extensions/claude" {
            if rel.starts_with("profiles/") {
                continue;
            }
            if rel.starts_with("agents/") && rel.ends_with(".md") {
                content = crate::claude::apply_agent_model(app, &rel, &content);
            }
        }
        let target = dest_root.join(&rel);
        let project_rel = app.project_rel_path(&target);
        let source_ref = format!("{src_rel}/{rel}");

        if !app.upgrade_mode && manifest::is_config_record(app, &project_rel) {
            continue;
        }
        if target.extension().and_then(|s| s.to_str()) == Some("json") && app.upgrade_mode {
            let incoming: Value = serde_json::from_str(&content)?;
            manifest::write_json_config_file(app, &target, &source_ref, move |data, _| {
                let mut base = Value::Object(std::mem::take(data));
                crate::upgrade_config::merge_json(&mut base, &incoming);
                *data = base.as_object().cloned().unwrap_or_default();
            })?;
        } else {
            manifest::write_file_with_agentic_marker(app, &content, &target, &source_ref)?;
        }
    }
    Ok(())
}

/// The generated mermaid diagram restates the steps for human readers (docs site); agents read the steps.
fn strip_agent_diagram(content: &str) -> String {
    let content = &content.replace("\r\n", "\n");
    let (Some(start), Some(end)) = (
        content.find("<!-- agent-diagram:start -->"),
        content.find("<!-- agent-diagram:end -->"),
    ) else {
        return content.to_string();
    };
    let tail = &content[end + "<!-- agent-diagram:end -->".len()..];
    format!("{}{}", &content[..start], tail.trim_start_matches('\n'))
}

/// Claude Code loads every file in `.claude/rules/` into context, so on-demand rules stay in `.agent/rules/`.
fn autoloads_every_rule(dest_root: &Path) -> bool {
    dest_root.ends_with(".claude/rules")
}

fn is_manual_rule(content: &str) -> bool {
    let content = content.replace("\r\n", "\n");
    let front = content
        .strip_prefix("---\n")
        .and_then(|rest| rest.split_once("\n---"))
        .map(|(meta, _)| meta)
        .unwrap_or("");
    front.lines().any(|line| line.trim() == "trigger: manual")
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
    fn claude_rules_skip_manual_rules() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        let dest = tmp.path().join(".claude/rules");
        copy_dir_contents(&mut app, "areas/software/general/rules", &dest, false).unwrap();
        assert!(dest.join("makefile-guide.md").is_file());
        assert!(!dest.join("sdlc-role-responsibilities.md").exists());
        assert!(is_manual_rule("---\ntrigger: manual\n---\nbody"));
        let workflow =
            "a\n<!-- agent-diagram:start -->\n```mermaid\n```\n<!-- agent-diagram:end -->\n\nb";
        assert_eq!(strip_agent_diagram(workflow), "a\nb");
        assert!(!is_manual_rule(
            "---\ntrigger: glob\npaths:\n  - \"Makefile\"\n---\n"
        ));
    }

    #[test]
    fn parses_crlf_checkouts() {
        assert!(is_manual_rule("---\r\ntrigger: manual\r\n---\r\nbody"));
        let workflow = "a\r\n<!-- agent-diagram:start -->\r\n```mermaid\r\n```\r\n<!-- agent-diagram:end -->\r\n\r\nb";
        assert_eq!(strip_agent_diagram(workflow), "a\nb");
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

#[cfg(test)]
mod jev_model_tests {
    use super::*;
    #[test]
    fn codex_bundled_models_are_open_in_both_kb_sources() {
        for kb in [
            crate::kb::Kb::Embedded,
            crate::kb::Kb::Checkout(std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))),
        ] {
            let project = tempfile::tempdir().unwrap();
            let mut app = App::new().unwrap();
            app.project_dir = project.path().to_string_lossy().into();
            app.jev_enabled = Some(true);
            app.install_profile = crate::profile::TEAM.into();
            app.kb = kb;
            assert!(app
                .kb
                .walk_files("extensions/codex")
                .iter()
                .all(|(p, _)| !p.contains('\\')));
            copy_dir_contents(
                &mut app,
                "extensions/codex",
                &project.path().join(".codex"),
                false,
            )
            .unwrap();
            let text = std::fs::read_to_string(project.path().join(".codex/agents/developer.toml"))
                .unwrap();
            assert!(!text.contains("\nmodel ="));
            assert!(!text.contains("\nmodel_reasoning_effort ="));
            assert!(text.contains("sandbox_mode = \"workspace-write\""));
        }
    }

    #[test]
    fn lean_jev_opens_helper_models_and_keeps_effort() {
        let project = tempfile::tempdir().unwrap();
        let mut app = App::new().unwrap();
        app.project_dir = project.path().to_string_lossy().into();
        app.jev_enabled = Some(true);
        app.install_profile = crate::profile::LEAN.into();
        let dest = project.path().join(".codex");
        copy_dir_contents(&mut app, "extensions/codex", &dest, false).unwrap();
        let text = std::fs::read_to_string(dest.join("agents/reviewer.toml")).unwrap();
        assert!(!text.contains("\nmodel ="));
        assert!(text.contains("\nmodel_reasoning_effort ="));
        assert!(!dest.join("agents/developer.toml").exists());
    }
}
