//! Application state: mirrors the bash script's global variables.

use crate::kb::Kb;
use crate::theme::{self, Colors};
use crate::util;
use std::io::IsTerminal;
use std::path::PathBuf;

pub struct App {
    pub kb: Kb,
    pub dry_run: bool,
    pub project_dir: String,
    pub theme: String,
    pub theme_explicit: bool,
    pub theme_loaded_from_config: bool,
    pub active_theme: String,
    pub colors: Colors,

    pub selected_agent_os: Vec<String>,
    pub selected_areas: Vec<String>,
    pub selected_specs: Vec<String>,
    pub selected_mcps: Vec<String>,
    pub selected_opencode_profile: String,
    pub install_settings_replay: bool,

    pub self_install_force: bool,
    pub self_install_bin_dir: String,

    pub created_paths: Vec<String>,
    pub copied_paths: Vec<String>,
    pub managed_records: Vec<ManagedRecord>,
    pub skipped_managed_paths: Vec<String>,
    pub warnings: Vec<String>,

    pub context7_api_key: String,
    pub context7_api_key_mode: Option<String>,
    pub enable_context7_env: Option<String>,
    pub enable_mempalace_env: Option<String>,
    pub doctor_enabled_env: bool,

    pub opencode_telegram_enabled: String,
    pub opencode_telegram_bot_token: String,
    pub opencode_telegram_chat_id: String,
    pub opencode_agent_model_mapper_enabled: String,
    pub opencode_plugins_configured: bool,

    pub run_log_active: bool,
    pub run_log_file: String,
    pub changed_paths_report_file: String,

    pub home: PathBuf,
    /// Test-only override for XDG_CONFIG_HOME to avoid env races.
    pub config_home_override: Option<PathBuf>,
    /// Test-only override for interactive terminal detection.
    pub interactive_override: Option<bool>,
    /// True while running the ratatui wizard flow: interactive questions are
    /// rendered as fullscreen TUI screens instead of line prompts.
    pub tui_mode: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ManagedRecord {
    pub path: String,
    pub source: String,
    pub content_hash: String,
    pub marker: String,
}

impl App {
    pub fn new() -> crate::Result<App> {
        let home = util::home_dir();
        Ok(App {
            kb: Kb::resolve(),
            dry_run: false,
            project_dir: String::new(),
            theme: "auto".to_string(),
            theme_explicit: false,
            theme_loaded_from_config: false,
            active_theme: "dark".to_string(),
            colors: Colors::default(),
            selected_agent_os: vec![crate::DEFAULT_AGENT_OS.to_string()],
            selected_areas: Vec::new(),
            selected_specs: Vec::new(),
            selected_mcps: Vec::new(),
            selected_opencode_profile: String::new(),
            install_settings_replay: false,
            self_install_force: false,
            self_install_bin_dir: home.join(".local/bin").to_string_lossy().to_string(),
            created_paths: Vec::new(),
            copied_paths: Vec::new(),
            managed_records: Vec::new(),
            skipped_managed_paths: Vec::new(),
            warnings: Vec::new(),
            context7_api_key: std::env::var("CONTEXT7_API_KEY").unwrap_or_default(),
            context7_api_key_mode: None,
            enable_context7_env: std::env::var("AGENTIC_ENABLE_CONTEXT7")
                .ok()
                .filter(|v| !v.is_empty()),
            enable_mempalace_env: std::env::var("AGENTIC_ENABLE_MEMPALACE")
                .ok()
                .filter(|v| !v.is_empty()),
            doctor_enabled_env: std::env::var("AGENTIC_DOCTOR")
                .map(|v| v != "0")
                .unwrap_or(true),
            opencode_telegram_enabled: String::new(),
            opencode_telegram_bot_token: String::new(),
            opencode_telegram_chat_id: String::new(),
            opencode_agent_model_mapper_enabled: String::new(),
            opencode_plugins_configured: false,
            run_log_active: false,
            run_log_file: String::new(),
            changed_paths_report_file: String::new(),
            home,
            config_home_override: None,
            interactive_override: None,
            tui_mode: false,
        })
    }

    pub fn xdg_config_home(&self) -> PathBuf {
        if let Some(dir) = &self.config_home_override {
            return dir.clone();
        }
        std::env::var("XDG_CONFIG_HOME")
            .ok()
            .filter(|v| !v.is_empty())
            .map(PathBuf::from)
            .unwrap_or_else(|| self.home.join(".config"))
    }

    pub fn app_config_dir(&self) -> PathBuf {
        self.xdg_config_home().join(crate::APP_NAME)
    }

    pub fn app_config_file(&self) -> PathBuf {
        self.app_config_dir().join("config")
    }

    pub fn app_config_json_file(&self) -> PathBuf {
        self.home
            .join(".config")
            .join(crate::APP_NAME)
            .join("config.json")
    }

    pub fn opencode_plugin_config_file(&self) -> PathBuf {
        self.app_config_dir().join("opencode-plugins.json")
    }

    pub fn opencode_user_profiles_dir(&self) -> PathBuf {
        self.home
            .join(".config")
            .join(crate::APP_NAME)
            .join("opencode")
            .join("profiles")
    }

    pub fn is_interactive_terminal(&self) -> bool {
        if let Some(value) = self.interactive_override {
            return value;
        }
        if std::env::var("AGENTIC_FORCE_INTERACTIVE")
            .map(|v| v == "1")
            .unwrap_or(false)
            || std::env::var("AGENTOS_FORCE_INTERACTIVE")
                .map(|v| v == "1")
                .unwrap_or(false)
        {
            return true;
        }
        std::io::stdin().is_terminal() && std::io::stdout().is_terminal()
    }

    pub fn set_theme_colors(&mut self) {
        let use_ansi = theme::supports_color();
        let (active, colors) = theme::resolve(&self.theme, use_ansi);
        self.active_theme = active;
        self.colors = colors;
    }

    pub fn load_user_config(&mut self) {
        crate::config::load_user_config(self);
    }

    pub fn project_manifest_path(&self) -> PathBuf {
        PathBuf::from(&self.project_dir).join(crate::PROJECT_MANIFEST_NAME)
    }

    pub fn project_rel_path(&self, path: &std::path::Path) -> String {
        match path.strip_prefix(std::path::Path::new(&self.project_dir)) {
            // Manifest paths always use forward slashes, also on Windows.
            Ok(rel) if !rel.as_os_str().is_empty() => rel.to_string_lossy().replace('\\', "/"),
            _ => path.to_string_lossy().to_string(),
        }
    }

    pub fn selected_agent_os_contains(&self, expected: &str) -> bool {
        self.selected_agent_os.iter().any(|a| a == expected)
    }

    pub fn selected_mcp_contains(&self, expected: &str) -> bool {
        self.selected_mcps.iter().any(|m| m == expected)
    }

    pub fn record_created(&mut self, path: &str) {
        util::unique_append(&mut self.created_paths, path);
    }

    pub fn record_copied(&mut self, path: &str) {
        util::unique_append(&mut self.copied_paths, path);
    }

    pub fn record_skipped(&mut self, rel: &str) {
        util::unique_append(&mut self.skipped_managed_paths, rel);
    }

    pub fn ensure_dir(&mut self, path: &std::path::Path) {
        if self.dry_run {
            crate::ui::log(self, &format!("DRY-RUN mkdir -p {}", path.display()));
        } else {
            let _ = std::fs::create_dir_all(path);
        }
        self.record_created(&path.to_string_lossy());
    }
}

/// Detect platform: linux/macos/windows/unknown with env override.
pub fn detect_platform() -> String {
    if let Ok(value) = std::env::var("AGENTIC_PLATFORM_OVERRIDE") {
        if !value.is_empty() {
            return value;
        }
    }
    if let Ok(value) = std::env::var("AGENTOS_PLATFORM_OVERRIDE") {
        if !value.is_empty() {
            return value;
        }
    }
    match std::env::consts::OS {
        "linux" => "linux".to_string(),
        "macos" => "macos".to_string(),
        "windows" => "windows".to_string(),
        _ => "unknown".to_string(),
    }
}

pub fn detect_runtime_platform_label() -> String {
    let platform = detect_platform();
    if platform == "linux" {
        if let Ok(version) = std::fs::read_to_string("/proc/version") {
            let lower = version.to_lowercase();
            if lower.contains("microsoft") || lower.contains("wsl") {
                return "wsl".to_string();
            }
        }
    }
    platform
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_rel_path_strips_prefix() {
        let mut app = App::new().unwrap();
        app.project_dir = "/tmp/demo".to_string();
        assert_eq!(
            app.project_rel_path(std::path::Path::new("/tmp/demo/a/b.md")),
            "a/b.md"
        );
        assert_eq!(
            app.project_rel_path(std::path::Path::new("/other/x")),
            "/other/x"
        );
    }

    #[test]
    fn selected_contains() {
        let mut app = App::new().unwrap();
        app.selected_agent_os = vec!["opencode".into(), "codex".into()];
        assert!(app.selected_agent_os_contains("codex"));
        assert!(!app.selected_agent_os_contains("claude"));
    }
}
