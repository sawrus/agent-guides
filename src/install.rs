//! The install pipeline (mirror of bash `run_install`).

use crate::agentsmd;
use crate::app::App;
use crate::config;
use crate::copydir::copy_dir_contents;
use crate::doctor;
use crate::manifest;
use crate::markers;
use crate::mcp;
use crate::mempalace;
use crate::prompt;
use crate::tomledit;
use crate::ui;
use crate::util;
use serde_json::Value;
use std::path::{Path, PathBuf};

pub fn normalize_selected_agent_os(app: &mut App) {
    let mut normalized: Vec<String> = Vec::new();
    for agent in &app.selected_agent_os {
        let agent = agent.trim();
        if agent.is_empty() {
            continue;
        }
        util::unique_append(&mut normalized, agent);
    }
    if normalized.is_empty() {
        normalized.push(crate::DEFAULT_AGENT_OS.to_string());
    }
    app.selected_agent_os = normalized;
}

pub fn validate_inputs(app: &mut App) -> crate::Result<()> {
    let available_areas = app.kb.list_areas();

    if app.project_dir.is_empty() {
        ui::error(app, "--project-dir is required");
        return Err(crate::exit1());
    }
    if app.selected_areas.is_empty() {
        ui::error(app, "--areas is required");
        return Err(crate::exit1());
    }
    if app.selected_specs.is_empty() {
        ui::error(app, "--specializations is required");
        return Err(crate::exit1());
    }
    for area in &app.selected_areas {
        if !available_areas.contains(area) {
            ui::error(app, &format!("unknown area '{area}'"));
            return Err(crate::exit1());
        }
    }
    for spec_key in &app.selected_specs {
        let Some((area_name, spec_name)) = spec_key.split_once('.') else {
            ui::error(
                app,
                &format!("specialization must be in area.spec format: {spec_key}"),
            );
            return Err(crate::exit1());
        };
        if !app.kb.dir_exists(&format!("areas/{area_name}/{spec_name}")) {
            ui::error(app, &format!("specialization not found: {spec_key}"));
            return Err(crate::exit1());
        }
        if !app.selected_areas.iter().any(|a| a == area_name) {
            ui::error(
                app,
                &format!("specialization '{spec_key}' not included by selected areas"),
            );
            return Err(crate::exit1());
        }
    }
    let agentos_choices = app.kb.agentos_choices();
    for agent in &app.selected_agent_os {
        if agent != crate::DEFAULT_AGENT_OS && !agentos_choices.contains(agent) {
            ui::error(app, &format!("unknown agent OS '{agent}'"));
            return Err(crate::exit1());
        }
    }
    Ok(())
}

pub fn opencode_profile_is_none(profile_id: &str) -> bool {
    matches!(
        profile_id.trim(),
        "" | "none" | "None" | "skip" | "Skip" | "no" | "No"
    )
}

pub const OPENCODE_PROFILE_IDS: [&str; 2] = ["openai", "githubcopilot"];

pub fn opencode_profile_label(id: &str) -> String {
    match id {
        "openai" => "OpenAI Model Profile".to_string(),
        "githubcopilot" => "GitHub Copilot Model Profile".to_string(),
        _ => format!("{id} profile"),
    }
}

pub fn opencode_profile_id_from_label(label: &str) -> String {
    for id in OPENCODE_PROFILE_IDS {
        if label == opencode_profile_label(id) {
            return id.to_string();
        }
    }
    if let Some(stripped) = label.strip_suffix(" profile") {
        return stripped.to_string();
    }
    label.to_string()
}

pub fn opencode_plugin_label(id: &str) -> String {
    match id {
        "telegram-notification" => "Telegram Notifications".to_string(),
        "agent-model-mapper" => "Agent Model Mapping".to_string(),
        _ => id.to_string(),
    }
}

pub fn opencode_plugin_id_from_label(label: &str) -> String {
    match label {
        "Telegram Notifications" => "telegram-notification".to_string(),
        "Agent Model Mapping" => "agent-model-mapper".to_string(),
        _ => label.to_string(),
    }
}

pub fn opencode_user_profile_ids(app: &App) -> Vec<String> {
    let dir = app.opencode_user_profiles_dir();
    let mut ids: Vec<String> = Vec::new();
    if let Ok(entries) = std::fs::read_dir(&dir) {
        for entry in entries.filter_map(|e| e.ok()) {
            let path = entry.path();
            if path.is_dir() && path.join("opencode.json").is_file() {
                ids.push(entry.file_name().to_string_lossy().to_string());
            }
        }
    }
    ids.sort();
    ids
}

pub fn opencode_profile_contains(app: &App, id: &str) -> bool {
    if OPENCODE_PROFILE_IDS.contains(&id) {
        return true;
    }
    app.opencode_user_profiles_dir()
        .join(id)
        .join("opencode.json")
        .is_file()
}

fn opencode_profile_source(app: &App, profile_id: &str) -> Option<String> {
    if let Some(content) = app.kb.read_file(&format!(
        "extensions/opencode/profiles/{profile_id}/opencode.json"
    )) {
        return Some(content);
    }
    std::fs::read_to_string(
        app.opencode_user_profiles_dir()
            .join(profile_id)
            .join("opencode.json"),
    )
    .ok()
}

fn merge_json(base: &mut Value, incoming: &Value) {
    if let (Some(base_obj), Some(inc_obj)) = (base.as_object_mut(), incoming.as_object()) {
        for (key, value) in inc_obj {
            if value.is_object() && base_obj.get(key).map(|v| v.is_object()).unwrap_or(false) {
                merge_json(base_obj.get_mut(key).unwrap(), value);
            } else {
                base_obj.insert(key.clone(), value.clone());
            }
        }
    }
}

pub fn configure_opencode_profile_if_needed(app: &mut App) -> crate::Result<()> {
    if !app.selected_agent_os_contains("opencode") {
        return Ok(());
    }
    let profile_id = std::env::var("AGENTIC_OPENCODE_PROFILE")
        .ok()
        .filter(|v| !v.is_empty())
        .unwrap_or_else(|| app.selected_opencode_profile.clone());
    let profile_id = profile_id.trim().to_string();
    if matches!(
        profile_id.as_str(),
        "none" | "None" | "skip" | "Skip" | "no" | "No"
    ) {
        return Ok(());
    }
    if profile_id.is_empty() {
        return Ok(());
    }
    if !opencode_profile_contains(app, &profile_id) {
        ui::warn(
            app,
            &format!("Ignoring unknown OpenCode profile '{profile_id}'"),
        );
        return Ok(());
    }
    app.selected_opencode_profile = profile_id.clone();

    let Some(profile_text) = opencode_profile_source(app, &profile_id) else {
        ui::warn(app, &format!("OpenCode profile not found: {profile_id}"));
        return Ok(());
    };
    let dest = PathBuf::from(&app.project_dir).join(".opencode/opencode.json");
    if app.dry_run {
        ui::log(
            app,
            &format!(
                "DRY-RUN apply OpenCode profile {} to {}",
                opencode_profile_label(&profile_id),
                dest.display()
            ),
        );
        app.record_copied(&dest.to_string_lossy());
        return Ok(());
    }
    if !manifest::can_write_managed_file(app, &dest) {
        return Ok(());
    }
    if let Some(parent) = dest.parent() {
        app.ensure_dir(parent);
    }
    let profile: Value = serde_json::from_str(&profile_text).map_err(|e| -> crate::AnyError {
        format!("OpenCode profile must be a JSON object: {e}").into()
    })?;
    if !profile.is_object() {
        return Err("OpenCode profile must be a JSON object".into());
    }
    let existing = std::fs::read_to_string(&dest).ok();
    let mut data: Value = existing
        .as_deref()
        .and_then(|t| serde_json::from_str(t).ok())
        .unwrap_or(Value::Null);
    if !data.is_object() {
        data = serde_json::json!({});
    }
    merge_json(&mut data, &profile);
    let output = markers::to_pretty_json(&data);
    let source_ref = format!("generated:opencode-profile-{profile_id}");
    if existing.as_deref() == Some(output.as_str()) {
        manifest::register_managed_file(app, &dest, &source_ref, "config", false);
    } else {
        std::fs::write(&dest, &output)?;
        manifest::register_managed_file(app, &dest, &source_ref, "config", true);
    }
    ui::log(
        app,
        &format!(
            "Applied OpenCode profile: {}",
            opencode_profile_label(&profile_id)
        ),
    );
    Ok(())
}

pub fn configure_opencode_plugins_if_needed(app: &mut App) -> crate::Result<()> {
    if !app.selected_agent_os_contains("opencode") {
        return Ok(());
    }
    if app.dry_run {
        ui::log(app, "DRY-RUN configure optional opencode plugins");
        return Ok(());
    }
    let dir = app.app_config_dir();
    app.ensure_dir(&dir);

    if app.install_settings_replay && app.opencode_plugins_configured {
        ui::log(app, "OpenCode plugin settings loaded from .agentic.json");
        return Ok(());
    }
    if app.install_settings_replay && app.opencode_plugin_config_file().is_file() {
        let _ = config::load_opencode_plugin_config_globals(app);
        ui::log(
            app,
            "OpenCode plugin config already exists; keeping current settings",
        );
        return Ok(());
    }
    if !app.is_interactive_terminal() {
        if !app.opencode_plugin_config_file().is_file() {
            config::write_default_opencode_plugin_config(app);
        } else {
            let _ = config::load_opencode_plugin_config_globals(app);
        }
        return Ok(());
    }

    let mut plugin_options = vec![
        opencode_plugin_label("telegram-notification"),
        opencode_plugin_label("agent-model-mapper"),
        opencode_profile_label("openai"),
        opencode_profile_label("githubcopilot"),
    ];
    for user_profile in opencode_user_profile_ids(app) {
        if OPENCODE_PROFILE_IDS.contains(&user_profile.as_str()) {
            continue;
        }
        plugin_options.push(opencode_profile_label(&user_profile));
    }

    let selected_plugins =
        prompt::choose_multi_by_index(app, "Select optional OpenCode plugin(s):", &plugin_options)?;

    let mut enable_telegram = false;
    let mut enable_mapper = false;
    for selected in selected_plugins {
        let id = opencode_plugin_id_from_label(&selected);
        match id.as_str() {
            "telegram-notification" | "telegram-opencode-notifier" => enable_telegram = true,
            "agent-model-mapper" => enable_mapper = true,
            other => {
                let profile_id = opencode_profile_id_from_label(other);
                if opencode_profile_contains(app, &profile_id) {
                    app.selected_opencode_profile = profile_id;
                }
            }
        }
    }

    if enable_telegram {
        if config::load_global_telegram_credentials(app) {
            let saved_bot = app.opencode_telegram_bot_token.clone();
            let saved_chat = app.opencode_telegram_chat_id.clone();
            let options = vec![
                "Use saved Telegram credentials".to_string(),
                "Enter new Telegram credentials".to_string(),
                "Disable Telegram Notifications".to_string(),
            ];
            let choice = prompt::choose_single_by_index(app, "Telegram credentials:", &options)?;
            match choice.as_str() {
                "Use saved Telegram credentials" => {
                    app.opencode_telegram_bot_token = saved_bot;
                    app.opencode_telegram_chat_id = saved_chat;
                    let file = app.app_config_json_file();
                    ui::log(
                        app,
                        &format!(
                            "Telegram plugin enabled; using credentials from {}",
                            file.display()
                        ),
                    );
                }
                "Disable Telegram Notifications" => {
                    enable_telegram = false;
                    app.opencode_telegram_bot_token.clear();
                    app.opencode_telegram_chat_id.clear();
                }
                _ => {
                    app.opencode_telegram_bot_token =
                        prompt::prompt_text_interactive("Telegram botToken", "");
                    app.opencode_telegram_chat_id =
                        prompt::prompt_text_interactive("Telegram chatId", "");
                }
            }
        } else {
            let bot = app.opencode_telegram_bot_token.clone();
            let chat = app.opencode_telegram_chat_id.clone();
            app.opencode_telegram_bot_token =
                prompt::prompt_text_interactive("Telegram botToken", &bot);
            app.opencode_telegram_chat_id =
                prompt::prompt_text_interactive("Telegram chatId", &chat);
        }
        if enable_telegram {
            if app.opencode_telegram_bot_token.is_empty()
                || app.opencode_telegram_chat_id.is_empty()
            {
                ui::warn(
                    app,
                    "Telegram plugin credentials are incomplete; disabling telegram-notification",
                );
                enable_telegram = false;
                app.opencode_telegram_bot_token.clear();
                app.opencode_telegram_chat_id.clear();
            } else {
                let bot = app.opencode_telegram_bot_token.clone();
                let chat = app.opencode_telegram_chat_id.clone();
                config::save_global_telegram_credentials(app, &bot, &chat);
                let file = app.app_config_json_file();
                ui::log(
                    app,
                    &format!(
                        "Telegram plugin enabled; credentials stored in {}",
                        file.display()
                    ),
                );
            }
        }
    }
    app.opencode_telegram_enabled = enable_telegram.to_string();
    app.opencode_agent_model_mapper_enabled = enable_mapper.to_string();
    app.opencode_plugins_configured = true;
    config::write_opencode_plugin_config(app, enable_telegram, enable_mapper);
    Ok(())
}

pub fn copy_extensions(app: &mut App, project_dir: &Path) -> crate::Result<()> {
    for agent_os in app.selected_agent_os.clone() {
        if agent_os == crate::DEFAULT_AGENT_OS || agent_os == "agents" {
            continue;
        }
        let src_rel = format!("extensions/{agent_os}");
        if !app.kb.dir_exists(&src_rel) {
            ui::warn(
                app,
                &format!("No extension directory found for '{agent_os}' (skipped)"),
            );
            continue;
        }
        let dest = project_dir.join(format!(".{agent_os}"));
        let mut skip_opencode_base_config = false;
        if agent_os == "opencode" {
            let profile_id = std::env::var("AGENTIC_OPENCODE_PROFILE")
                .ok()
                .filter(|v| !v.is_empty())
                .unwrap_or_else(|| app.selected_opencode_profile.clone());
            if opencode_profile_is_none(&profile_id)
                && app.opencode_telegram_enabled != "true"
                && app.opencode_agent_model_mapper_enabled != "true"
            {
                skip_opencode_base_config = true;
            }
        }
        copy_dir_contents(app, &src_rel, &dest, skip_opencode_base_config)?;
    }
    Ok(())
}

pub fn copy_specialization_assets(app: &mut App, project_dir: &Path) -> crate::Result<()> {
    for spec_key in app.selected_specs.clone() {
        let (area, spec) = spec_key.split_once('.').unwrap_or((spec_key.as_str(), ""));
        let src_root = format!("areas/{area}/{spec}");
        if !app.kb.dir_exists(&src_root) {
            ui::warn(app, &format!("Specialization path not found: {src_root}"));
            continue;
        }
        for bucket in crate::INSTALL_DIRS {
            let src = format!("{src_root}/{bucket}");
            if !app.kb.dir_exists(&src) {
                continue;
            }
            let mut targets: Vec<String> = Vec::new();
            for target in &app.selected_agent_os {
                util::unique_append(&mut targets, target);
            }
            util::unique_append(&mut targets, "agents");

            let mut dest_dirs: Vec<String> = Vec::new();
            for target in &targets {
                let dest_dir = agentsmd::get_dest_dir(target, bucket);
                if dest_dir == "-" {
                    continue;
                }
                util::unique_append(&mut dest_dirs, &dest_dir);
            }
            for resolved in dest_dirs {
                let dest = project_dir.join(&resolved);
                copy_dir_contents(app, &src, &dest, false)?;
            }
        }
    }
    Ok(())
}

pub fn write_codex_features_config(app: &mut App) -> crate::Result<()> {
    let dest = PathBuf::from(&app.project_dir).join(".codex/config.toml");
    let text = std::fs::read_to_string(&dest).unwrap_or_default();
    let body = tomledit::enable_codex_memories(&text);
    manifest::write_text_config_file(app, &dest, "generated:codex-features-config", &body)
}

fn print_report(app: &mut App) {
    ui::write_changed_paths_report(app);
    ui::out(app, "");
    ui::out_color(
        app,
        "=== Installation report ===",
        &app.colors.header.clone(),
    );
    ui::out(
        app,
        &format!("Agentic version: {}", crate::app_version_label()),
    );
    ui::out(app, &format!("Project dir: {}", app.project_dir));
    ui::out(
        app,
        &format!("Knowledge base repo: {}", app.kb.root_label()),
    );
    ui::out(
        app,
        &format!("Config file: {}", app.app_config_file().display()),
    );
    ui::out(
        app,
        &format!("JSON config file: {}", app.app_config_json_file().display()),
    );
    ui::out(
        app,
        &format!("Agent OS targets: {}", app.selected_agent_os.join(" ")),
    );
    ui::out(app, &format!("Areas: {}", app.selected_areas.join(" ")));
    ui::out(
        app,
        &format!("Specializations: {}", app.selected_specs.join(" ")),
    );
    ui::out(app, "");
    ui::out(
        app,
        &format!("Created directories: {}", app.created_paths.len()),
    );
    ui::out(
        app,
        &format!("Copied/generated paths: {}", app.copied_paths.len()),
    );
    ui::out(
        app,
        &format!("Changed paths report: {}", app.changed_paths_report_file),
    );
    ui::out(app, "");
    ui::out(app, "Warnings:");
    if app.warnings.is_empty() {
        ui::out(app, "- (none)");
    } else {
        for warning in app.warnings.clone() {
            ui::out(app, &format!("- {warning}"));
        }
    }
}

pub fn get_agent_binary_name(agent_os: &str) -> &'static str {
    match agent_os {
        "codex" => "codex",
        "claude" => "claude",
        "opencode" => "opencode",
        "cursor" => "cursor-agent",
        "gemini" => "gemini",
        "antigravity" => "antigravity",
        _ => "",
    }
}

fn binary_available(name: &str) -> bool {
    let Ok(path_var) = std::env::var("PATH") else {
        return false;
    };
    std::env::split_paths(&path_var).any(|dir| {
        let candidate = dir.join(name);
        candidate.is_file()
    })
}

fn print_missing_agent_binary_guides(app: &mut App) {
    let platform_label = crate::app::detect_runtime_platform_label();
    let mut missing_lines: Vec<String> = Vec::new();
    for agent_os in app.selected_agent_os.clone() {
        let binary = get_agent_binary_name(&agent_os);
        if binary.is_empty() || binary_available(binary) {
            continue;
        }
        let install_link = match agent_os.as_str() {
            "codex" => "https://github.com/openai/codex",
            "claude" => "https://docs.anthropic.com/en/docs/claude-code/quickstart",
            "opencode" => "https://opencode.ai/docs",
            "cursor" => "https://docs.cursor.com/get-started/installation",
            "gemini" => "https://github.com/google-gemini/gemini-cli",
            "antigravity" => "https://github.com/getantigravity/antigravity",
            _ => "",
        };
        missing_lines.push(format!(
            "- {agent_os}: binary '{binary}' is not installed on {platform_label}."
        ));
        if !install_link.is_empty() {
            missing_lines.push(format!("  Install guide: {install_link}"));
        }
    }
    if missing_lines.is_empty() {
        return;
    }
    ui::out(app, "");
    ui::out_color(
        app,
        "=== Agent binary setup recommendations ===",
        &app.colors.header.clone(),
    );
    for line in missing_lines {
        ui::out(app, &line);
    }
}

pub fn changelog_section(changelog: &str, version_label: &str) -> Option<String> {
    let wanted = format!("## {version_label}");
    let mut in_section = false;
    let mut lines: Vec<&str> = Vec::new();
    for line in changelog.lines() {
        if line == wanted {
            in_section = true;
            lines.push(line);
            continue;
        }
        if in_section && line.starts_with("## ") {
            break;
        }
        if in_section {
            lines.push(line);
        }
    }
    if lines.is_empty() {
        None
    } else {
        Some(lines.join("\n"))
    }
}

fn print_current_changelog(app: &mut App) {
    let version = crate::app_version_label();
    let Some(changelog) = app.kb.read_file("CHANGELOG.md") else {
        ui::warn(app, "CHANGELOG.md not found; skipping changelog output");
        return;
    };
    let Some(section) = changelog_section(&changelog, &version) else {
        ui::warn(app, &format!("No changelog section found for {version}"));
        return;
    };
    ui::out(app, "");
    ui::out_color(
        app,
        &format!("=== Changelog {version} ==="),
        &app.colors.header.clone(),
    );
    for line in section.lines() {
        if line == format!("## {version}") {
            continue;
        }
        ui::out(app, line);
    }
}

pub fn run_install(app: &mut App) -> crate::Result<()> {
    ui::init_run_logging(app);
    normalize_selected_agent_os(app);
    validate_inputs(app)?;

    app.project_dir = util::normalize_project_dir_path(&app.project_dir);
    let project_dir = PathBuf::from(&app.project_dir);
    app.ensure_dir(&project_dir);

    configure_opencode_plugins_if_needed(app)?;
    copy_extensions(app, &project_dir)?;
    configure_opencode_profile_if_needed(app)?;
    crate::mapper::configure_opencode_agent_model_mapper_if_needed(app)?;
    copy_specialization_assets(app, &project_dir)?;
    agentsmd::generate_agents_md(app, &project_dir)?;
    agentsmd::copy_memory_md(app, &project_dir)?;
    if app.selected_agent_os_contains("codex") {
        write_codex_features_config(app)?;
    }
    mcp::sync_selected_mcps_from_env(app);
    mcp::sync_legacy_mcp_env_from_selected(app);
    mcp::configure_context7_if_needed(app)?;
    mempalace::configure_mempalace_if_needed(app)?;
    mcp::configure_selected_mcps_if_needed(app)?;
    mcp::check_selected_mcp_runtime_prerequisites(app);
    manifest::write_agentic_manifest(app, &project_dir)?;
    print_report(app);
    print_missing_agent_binary_guides(app);
    print_current_changelog(app);
    doctor::run_agentic_doctor(app);
    ui::out(app, &format!("Agentic log file: {}", app.run_log_file));
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn test_app(project: &Path) -> App {
        let mut app = App::new().unwrap();
        app.project_dir = project.to_string_lossy().to_string();
        app.selected_agent_os = vec!["default".to_string()];
        app.selected_areas = vec!["software".to_string()];
        app.selected_specs = vec!["software.backend".to_string()];
        app
    }

    #[test]
    fn normalize_agent_os_defaults() {
        let mut app = App::new().unwrap();
        app.selected_agent_os = vec![" ".to_string(), "".to_string()];
        normalize_selected_agent_os(&mut app);
        assert_eq!(app.selected_agent_os, vec!["default"]);
        app.selected_agent_os = vec!["opencode".to_string(), "opencode".to_string()];
        normalize_selected_agent_os(&mut app);
        assert_eq!(app.selected_agent_os, vec!["opencode"]);
    }

    #[test]
    fn validate_rejects_bad_inputs() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_areas = vec!["ghost".to_string()];
        assert!(validate_inputs(&mut app).is_err());

        let mut app = test_app(tmp.path());
        app.selected_specs = vec!["nodot".to_string()];
        assert!(validate_inputs(&mut app).is_err());

        let mut app = test_app(tmp.path());
        app.selected_specs = vec!["software.ghost".to_string()];
        assert!(validate_inputs(&mut app).is_err());

        let mut app = test_app(tmp.path());
        app.selected_specs = vec!["devops.sre".to_string()];
        assert!(validate_inputs(&mut app).is_err());

        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["ghostos".to_string()];
        assert!(validate_inputs(&mut app).is_err());

        let mut app = test_app(tmp.path());
        assert!(validate_inputs(&mut app).is_ok());
    }

    #[test]
    fn profile_labels_roundtrip() {
        assert_eq!(opencode_profile_label("openai"), "OpenAI Model Profile");
        assert_eq!(
            opencode_profile_id_from_label("OpenAI Model Profile"),
            "openai"
        );
        assert_eq!(opencode_profile_id_from_label("custom profile"), "custom");
        assert_eq!(
            opencode_plugin_id_from_label("Telegram Notifications"),
            "telegram-notification"
        );
        assert_eq!(
            opencode_plugin_label("agent-model-mapper"),
            "Agent Model Mapping"
        );
        assert!(opencode_profile_is_none(""));
        assert!(opencode_profile_is_none("none"));
        assert!(!opencode_profile_is_none("openai"));
    }

    #[test]
    fn changelog_section_extraction() {
        let changelog = "# Changelog\n\n## v2.0.0\n- new\n\n## v1.0.0\n- old\n";
        let section = changelog_section(changelog, "v2.0.0").unwrap();
        assert!(section.contains("- new"));
        assert!(!section.contains("- old"));
        assert!(changelog_section(changelog, "v9.9.9").is_none());
    }

    #[test]
    fn full_install_non_interactive() {
        let tmp = tempfile::tempdir().unwrap();
        let config_home = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.config_home_override = Some(config_home.path().to_path_buf());
        app.home = config_home.path().to_path_buf();
        app.doctor_enabled_env = false;
        run_install(&mut app).unwrap();
        assert!(tmp.path().join("AGENTS.md").is_file());
        assert!(tmp.path().join("MEMORY.md").is_file());
        assert!(tmp.path().join(".agent/rules").is_dir());
        assert!(tmp.path().join(".agentic.json").is_file());
    }

    #[test]
    fn codex_features_written() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        write_codex_features_config(&mut app).unwrap();
        let text = std::fs::read_to_string(tmp.path().join(".codex/config.toml")).unwrap();
        assert_eq!(text, "[features]\nmemories = true\n");
    }

    #[test]
    fn extension_copy_targets() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["codex".to_string(), "default".to_string()];
        copy_extensions(&mut app, tmp.path()).unwrap();
        assert!(tmp.path().join(".codex").is_dir());
        assert!(!tmp.path().join(".default").exists());
    }

    #[test]
    fn interactive_plugins_telegram_and_mapper() {
        let tmp = tempfile::tempdir().unwrap();
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["opencode".to_string()];
        app.home = home.path().to_path_buf();
        app.config_home_override = Some(home.path().to_path_buf());
        app.interactive_override = Some(true);
        crate::prompt::set_test_answers(&["1,2", "tok", "chat"]);
        configure_opencode_plugins_if_needed(&mut app).unwrap();
        assert_eq!(app.opencode_telegram_enabled, "true");
        assert_eq!(app.opencode_agent_model_mapper_enabled, "true");
        assert_eq!(app.opencode_telegram_bot_token, "tok");
        let plugin_file = app.opencode_plugin_config_file();
        let data: Value =
            serde_json::from_str(&std::fs::read_to_string(&plugin_file).unwrap()).unwrap();
        assert_eq!(data["telegram"]["enabled"], serde_json::json!(true));
        // saved credentials flow on second run
        let mut app2 = test_app(tmp.path());
        app2.selected_agent_os = vec!["opencode".to_string()];
        app2.home = home.path().to_path_buf();
        app2.config_home_override = Some(home.path().to_path_buf());
        app2.interactive_override = Some(true);
        crate::prompt::set_test_answers(&["1", "1"]);
        configure_opencode_plugins_if_needed(&mut app2).unwrap();
        assert_eq!(app2.opencode_telegram_bot_token, "tok");
        assert_eq!(app2.opencode_telegram_chat_id, "chat");
    }

    #[test]
    fn interactive_plugins_incomplete_credentials_disable_telegram() {
        let tmp = tempfile::tempdir().unwrap();
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["opencode".to_string()];
        app.home = home.path().to_path_buf();
        app.config_home_override = Some(home.path().to_path_buf());
        app.interactive_override = Some(true);
        crate::prompt::set_test_answers(&["1", "", ""]);
        configure_opencode_plugins_if_needed(&mut app).unwrap();
        assert_eq!(app.opencode_telegram_enabled, "false");
        assert!(app.warnings.iter().any(|w| w.contains("incomplete")));
    }

    #[test]
    fn interactive_plugins_profile_selection() {
        let tmp = tempfile::tempdir().unwrap();
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["opencode".to_string()];
        app.home = home.path().to_path_buf();
        app.config_home_override = Some(home.path().to_path_buf());
        app.interactive_override = Some(true);
        crate::prompt::set_test_answers(&["3"]);
        configure_opencode_plugins_if_needed(&mut app).unwrap();
        assert_eq!(app.selected_opencode_profile, "openai");
    }

    #[test]
    fn profile_applied_and_merged() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["opencode".to_string()];
        app.selected_opencode_profile = "openai".to_string();
        std::fs::create_dir_all(tmp.path().join(".opencode")).unwrap();
        std::fs::write(
            tmp.path().join(".opencode/opencode.json"),
            r#"{"keepme": 1}"#,
        )
        .unwrap();
        configure_opencode_profile_if_needed(&mut app).unwrap();
        let data: Value = serde_json::from_str(
            &std::fs::read_to_string(tmp.path().join(".opencode/opencode.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(data["keepme"], serde_json::json!(1));
        assert!(data.as_object().unwrap().len() > 1);
    }

    #[test]
    fn user_profile_discovery() {
        let home = tempfile::tempdir().unwrap();
        let mut app = App::new().unwrap();
        app.home = home.path().to_path_buf();
        assert!(opencode_user_profile_ids(&app).is_empty());
        let dir = app.opencode_user_profiles_dir().join("custom");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("opencode.json"), "{}").unwrap();
        assert_eq!(opencode_user_profile_ids(&app), vec!["custom"]);
        assert!(opencode_profile_contains(&app, "custom"));
        assert!(opencode_profile_contains(&app, "openai"));
        assert!(!opencode_profile_contains(&app, "ghost"));
    }

    #[test]
    fn spec_assets_multi_target_dedup() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["kilocode".to_string(), "antigravity".to_string()];
        copy_specialization_assets(&mut app, tmp.path()).unwrap();
        assert!(tmp.path().join(".kilocode/rules").is_dir());
        assert!(tmp.path().join(".agent/rules").is_dir());
    }
}
