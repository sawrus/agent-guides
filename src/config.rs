//! User configuration files under ~/.config/agentic/.

use crate::app::App;
use crate::ui;
use serde_json::{json, Value};

pub fn load_user_config(app: &mut App) {
    app.theme_loaded_from_config = false;
    let config_file = app.app_config_file();
    let Ok(content) = std::fs::read_to_string(&config_file) else {
        return;
    };
    for raw_line in content.lines() {
        let line = raw_line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            ui::warn(
                app,
                &format!(
                    "Ignoring malformed config line in {}: {line}",
                    config_file.display()
                ),
            );
            continue;
        };
        let key = key.trim();
        let value = value.trim();
        if key == "theme" {
            if crate::THEME_CHOICES.contains(&value) {
                app.theme = value.to_string();
                app.theme_loaded_from_config = true;
            } else {
                ui::warn(
                    app,
                    &format!(
                        "Ignoring invalid theme '{value}' in {}; falling back to auto",
                        config_file.display()
                    ),
                );
                app.theme = "auto".to_string();
            }
        }
    }
}

pub fn save_user_config(app: &mut App) {
    let dir = app.app_config_dir();
    app.ensure_dir(&dir);
    let config_file = app.app_config_file();
    if app.dry_run {
        ui::log(
            app,
            &format!("DRY-RUN write config to {}", config_file.display()),
        );
        return;
    }
    let body = format!(
        "# {} user configuration\ntheme={}\n",
        crate::APP_NAME,
        app.theme
    );
    if std::fs::write(&config_file, body).is_ok() {
        app.record_copied(&config_file.to_string_lossy());
    }
}

fn read_json_file(path: &std::path::Path) -> Value {
    std::fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or(Value::Null)
}

pub fn load_global_telegram_credentials(app: &mut App) -> bool {
    let path = app.app_config_json_file();
    if !path.is_file() {
        return false;
    }
    let data = read_json_file(&path);
    let telegram = data
        .get("opencode")
        .and_then(|v| v.get("plugins"))
        .and_then(|v| v.get("telegram"))
        .cloned()
        .unwrap_or(Value::Null);
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
    !app.opencode_telegram_bot_token.is_empty() && !app.opencode_telegram_chat_id.is_empty()
}

pub fn save_global_telegram_credentials(app: &mut App, bot_token: &str, chat_id: &str) -> bool {
    if bot_token.is_empty() || chat_id.is_empty() {
        return false;
    }
    let path = app.app_config_json_file();
    if let Some(parent) = path.parent() {
        app.ensure_dir(parent);
    }
    if app.dry_run {
        ui::log(
            app,
            &format!("DRY-RUN write Telegram credentials to {}", path.display()),
        );
        return true;
    }
    let mut data = read_json_file(&path);
    if !data.is_object() {
        data = json!({});
    }
    let obj = data.as_object_mut().unwrap();
    let opencode = obj.entry("opencode").or_insert_with(|| json!({}));
    if !opencode.is_object() {
        *opencode = json!({});
    }
    let plugins = opencode
        .as_object_mut()
        .unwrap()
        .entry("plugins")
        .or_insert_with(|| json!({}));
    if !plugins.is_object() {
        *plugins = json!({});
    }
    let telegram = plugins
        .as_object_mut()
        .unwrap()
        .entry("telegram")
        .or_insert_with(|| json!({}));
    if !telegram.is_object() {
        *telegram = json!({});
    }
    let tg = telegram.as_object_mut().unwrap();
    tg.insert("botToken".to_string(), json!(bot_token));
    tg.insert("chatId".to_string(), json!(chat_id));
    let output = crate::markers::to_pretty_json(&data);
    if std::fs::write(&path, output).is_ok() {
        app.record_copied(&path.to_string_lossy());
        return true;
    }
    false
}

pub fn write_default_opencode_plugin_config(app: &mut App) {
    let dir = app.app_config_dir();
    app.ensure_dir(&dir);
    app.opencode_telegram_enabled = "false".to_string();
    app.opencode_telegram_bot_token.clear();
    app.opencode_telegram_chat_id.clear();
    app.opencode_agent_model_mapper_enabled = "false".to_string();
    app.opencode_plugins_configured = true;
    let path = app.opencode_plugin_config_file();
    if app.dry_run {
        ui::log(
            app,
            &format!(
                "DRY-RUN write disabled opencode plugin config to {}",
                path.display()
            ),
        );
        return;
    }
    let data = json!({
        "telegram": {"enabled": false},
        "agentModelMapper": {"enabled": false},
    });
    let _ = std::fs::write(&path, crate::markers::to_pretty_json(&data));
}

pub fn write_opencode_plugin_config(app: &App, enable_telegram: bool, enable_mapper: bool) {
    let data = json!({
        "telegram": {"enabled": enable_telegram},
        "agentModelMapper": {"enabled": enable_mapper},
    });
    let _ = std::fs::write(
        app.opencode_plugin_config_file(),
        crate::markers::to_pretty_json(&data),
    );
}

pub fn load_opencode_plugin_config_globals(app: &mut App) -> bool {
    let path = app.opencode_plugin_config_file();
    if !path.is_file() {
        return false;
    }
    let data = read_json_file(&path);
    let telegram = data.get("telegram").cloned().unwrap_or(Value::Null);
    let mapper = data.get("agentModelMapper").cloned().unwrap_or(Value::Null);
    app.opencode_telegram_enabled = if telegram.get("enabled") == Some(&Value::Bool(true)) {
        "true".to_string()
    } else {
        "false".to_string()
    };
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
    app.opencode_agent_model_mapper_enabled = if mapper.get("enabled") == Some(&Value::Bool(true)) {
        "true".to_string()
    } else {
        "false".to_string()
    };
    app.opencode_plugins_configured = true;
    true
}

pub fn opencode_agent_model_mapper_config_enabled(app: &App) -> bool {
    if app.opencode_agent_model_mapper_enabled == "true" {
        return true;
    }
    if app.opencode_agent_model_mapper_enabled == "false" {
        return false;
    }
    let path = app.opencode_plugin_config_file();
    if !path.is_file() {
        return false;
    }
    let data = read_json_file(&path);
    data.get("agentModelMapper")
        .and_then(|v| v.get("enabled"))
        .map(|v| v == &Value::Bool(true))
        .unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn app_with_home(home: &std::path::Path) -> App {
        let mut app = App::new().unwrap();
        app.home = home.to_path_buf();
        app.config_home_override = Some(home.to_path_buf());
        app
    }

    #[test]
    fn user_config_roundtrip() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = app_with_home(tmp.path());
        app.theme = "light".to_string();
        save_user_config(&mut app);
        let mut app2 = app_with_home(tmp.path());
        load_user_config(&mut app2);
        assert_eq!(app2.theme, "light");
        assert!(app2.theme_loaded_from_config);
    }

    #[test]
    fn invalid_theme_falls_back_to_auto() {
        let tmp = tempfile::tempdir().unwrap();
        let app = app_with_home(tmp.path());
        std::fs::create_dir_all(app.app_config_dir()).unwrap();
        std::fs::write(app.app_config_file(), "theme=neon\nbadline\n").unwrap();
        let mut app2 = app_with_home(tmp.path());
        load_user_config(&mut app2);
        assert_eq!(app2.theme, "auto");
        assert!(!app2.theme_loaded_from_config);
        assert_eq!(app2.warnings.len(), 2);
    }

    #[test]
    fn telegram_credentials_roundtrip() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = app_with_home(tmp.path());
        assert!(!load_global_telegram_credentials(&mut app));
        assert!(save_global_telegram_credentials(&mut app, "token", "chat"));
        let mut app2 = app_with_home(tmp.path());
        assert!(load_global_telegram_credentials(&mut app2));
        assert_eq!(app2.opencode_telegram_bot_token, "token");
        assert_eq!(app2.opencode_telegram_chat_id, "chat");
        assert!(!save_global_telegram_credentials(&mut app2, "", "chat"));
    }

    #[test]
    fn plugin_config_defaults_and_load() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = app_with_home(tmp.path());
        write_default_opencode_plugin_config(&mut app);
        assert!(!opencode_agent_model_mapper_config_enabled(&app));
        write_opencode_plugin_config(&app, true, true);
        let mut app2 = app_with_home(tmp.path());
        assert!(load_opencode_plugin_config_globals(&mut app2));
        assert_eq!(app2.opencode_telegram_enabled, "true");
        assert_eq!(app2.opencode_agent_model_mapper_enabled, "true");
    }
}
