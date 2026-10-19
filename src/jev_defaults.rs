//! JEV model defaults (`.agent/jev/model-defaults.json` v2) and the persisted `settings.jev` keys.

use crate::app::App;
use serde_json::{json, Map, Value};

/// Matches `VERSION` in the hook runtime (`routing.load_defaults`); older runtimes read the flat role map.
pub const DEFAULTS_VERSION: u64 = 2;
pub const CODEX_TIERS_SOURCE: &str = "extensions/codex/model-tiers.json";
pub const OPENCODE_TIERS_SOURCE: &str = "extensions/opencode/model-tiers.json";
/// User-tuned JEV settings that a reinstall must not reset.
const PRESERVED_SETTINGS: [&str; 3] = ["thresholds", "lightweight_model", "tiers"];

/// Role -> model from the bundled Codex agent profiles.
fn codex_roles(app: &App) -> Map<String, Value> {
    app.kb
        .walk_files("extensions/codex/agents")
        .into_iter()
        .filter_map(|(path, text)| {
            let model = text.lines().find_map(|line| {
                line.trim()
                    .strip_prefix("model =")
                    .map(|v| v.trim().trim_matches('"').to_string())
            })?;
            Some((
                path.trim_end_matches(".toml").to_string(),
                Value::String(model),
            ))
        })
        .collect()
}

/// Tier -> model for Codex hosts.
pub fn codex_tiers(app: &App) -> Map<String, Value> {
    app.kb
        .read_file(CODEX_TIERS_SOURCE)
        .and_then(|text| serde_json::from_str::<Value>(&text).ok())
        .and_then(|value| value.as_object().cloned())
        .unwrap_or_default()
}

/// `{"version": 2, "roles": {...}, "tiers": {...}}`. Claude's Agent tool accepts aliases only,
/// so a Claude-only install uses its profile; any Codex host keeps Codex model ids (D7).
pub fn model_defaults(app: &App) -> Value {
    let claude_only =
        app.selected_agent_os_contains("claude") && !app.selected_agent_os_contains("codex");
    let (roles, tiers) = if claude_only {
        (
            crate::claude::profile_models(app),
            crate::claude::profile_tiers(app),
        )
    } else {
        (codex_roles(app), codex_tiers(app))
    };
    json!({"version": DEFAULTS_VERSION, "roles": roles, "tiers": tiers})
}

/// Role -> explicit model of the selected OpenCode profile; `{}` for the default install.
pub fn opencode_profile_defaults(app: &App) -> Value {
    let profile = crate::install::opencode_profile_source(app, &app.selected_opencode_profile)
        .and_then(|s| serde_json::from_str::<Value>(&s).ok())
        .unwrap_or_default();
    let roles: Map<String, Value> = profile["agent"]
        .as_object()
        .into_iter()
        .flatten()
        .filter_map(|(role, config)| {
            config["model"]
                .as_str()
                .map(|model| (role.clone(), json!(model)))
        })
        .collect();
    Value::Object(roles)
}

/// `settings.jev` for `.agentic.json`: current selections plus preserved user tuning.
pub fn manifest_settings(app: &App, old_settings: &Value) -> Value {
    let mut jev = Map::new();
    jev.insert("enabled".into(), json!(app.jev_enabled.unwrap_or(false)));
    jev.insert(
        "api_url".into(),
        json!(app
            .jev_api_url
            .as_deref()
            .unwrap_or(crate::jev_hooks::DEFAULT_API_URL)),
    );
    for key in PRESERVED_SETTINGS {
        if let Some(value) = old_settings["jev"].get(key) {
            jev.insert(key.into(), value.clone());
        }
    }
    Value::Object(jev)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn app_for(hosts: &[&str]) -> App {
        let mut app = App::new().unwrap();
        app.selected_agent_os = hosts.iter().map(|h| h.to_string()).collect();
        app
    }

    #[test]
    fn codex_defaults_are_v2_with_bundled_tiers() {
        let defaults = model_defaults(&app_for(&["codex"]));
        assert_eq!(defaults["version"], 2);
        assert_eq!(defaults["roles"]["developer"], "gpt-6.1-sol");
        assert_eq!(
            defaults["tiers"],
            json!({"fast":"gpt-6-luna","balanced":"gpt-6.1-sol","frontier":"gpt-6-astra"})
        );
    }

    #[test]
    fn claude_only_defaults_use_profile_aliases_and_combined_install_keeps_codex() {
        let claude = model_defaults(&app_for(&["claude"]));
        assert_eq!(claude["roles"]["developer"], "sonnet");
        assert_eq!(
            claude["tiers"],
            json!({"fast":"haiku","balanced":"sonnet","frontier":"opus"})
        );
        let combined = model_defaults(&app_for(&["claude", "codex"]));
        assert_eq!(combined["tiers"]["fast"], "gpt-6-luna");
    }

    #[test]
    fn codex_role_defaults_are_tier_models() {
        let defaults = model_defaults(&app_for(&["codex"]));
        assert_eq!(defaults["roles"]["qa"], "gpt-6.1-sol");
        let tiers: Vec<&Value> = defaults["tiers"].as_object().unwrap().values().collect();
        for (role, model) in defaults["roles"].as_object().unwrap() {
            assert!(
                tiers.contains(&model),
                "{role} default {model} is not a tier"
            );
        }
    }

    #[test]
    fn opencode_profile_defaults_follow_the_selected_profile() {
        let mut app = app_for(&["opencode"]);
        app.selected_opencode_profile = "openai".into();
        let defaults = opencode_profile_defaults(&app);
        assert_eq!(defaults["developer"], "openai/gpt-6.1-sol");
        app.selected_opencode_profile = "no-such-profile".into();
        assert_eq!(opencode_profile_defaults(&app), json!({}));
    }

    #[test]
    fn opencode_install_writes_the_tier_map_verbatim() {
        let project = tempfile::tempdir().unwrap();
        let mut app = app_for(&["opencode"]);
        app.project_dir = project.path().to_string_lossy().into();
        app.selected_opencode_profile = "no-such-profile".into();
        app.jev_enabled = Some(true);
        crate::jev_hooks::install(&mut app, project.path()).unwrap();
        let read = |rel: &str| std::fs::read_to_string(project.path().join(rel)).unwrap();
        let shipped = include_str!("../extensions/opencode/model-tiers.json");
        assert_eq!(read(".agent/jev/opencode-model-tiers.json"), shipped);
        assert_eq!(
            app.kb.read_file(OPENCODE_TIERS_SOURCE).as_deref(),
            Some(shipped)
        );
        let profile: Value =
            serde_json::from_str(&read(".agent/jev/opencode-profile-defaults.json")).unwrap();
        assert_eq!(profile, json!({}));
    }

    #[test]
    fn manifest_settings_keep_user_tuning_only() {
        let mut app = app_for(&["codex"]);
        app.jev_enabled = Some(true);
        let old = json!({"jev": {"enabled": false, "api_url": "https://old.example",
            "thresholds": {"model": 0.7}, "lightweight_model": "gpt-6-luna",
            "tiers": {"fast": "x"}, "unknown": 1}});
        let settings = manifest_settings(&app, &old);
        assert_eq!(settings["enabled"], true);
        assert_eq!(settings["api_url"], crate::jev_hooks::DEFAULT_API_URL);
        assert_eq!(settings["thresholds"]["model"], 0.7);
        assert_eq!(settings["lightweight_model"], "gpt-6-luna");
        assert_eq!(settings["tiers"]["fast"], "x");
        assert!(settings.get("unknown").is_none());
    }
}
