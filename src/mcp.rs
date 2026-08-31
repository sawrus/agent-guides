//! MCP registry and per-agent configuration writers.

use crate::app::App;
use crate::manifest::{write_json_config_file, write_text_config_file};
use crate::tomledit;
use crate::ui;
use crate::util;
use serde_json::{json, Map, Value};
use std::path::{Path, PathBuf};

pub const MCP_REGISTRY_IDS: [&str; 8] = [
    "opencode-docs",
    "playwright",
    "kubernetes",
    "youtube-transcript",
    "docker-mcp",
    "context7",
    "mempalace",
    "anydb",
];
pub const MCP_NONE_OPTION: &str = "None / skip";
pub const CONTEXT7_URL: &str = "https://mcp.context7.com/mcp";

pub struct McpEntry {
    #[allow(dead_code)]
    pub id: &'static str,
    pub server: &'static str,
    pub command: &'static str,
    pub args: &'static [&'static str],
    pub remote: Option<&'static str>,
    pub codex_network: bool,
    pub codex_startup_timeout_sec: Option<u32>,
    pub codex_tool_timeout_sec: Option<u32>,
}

pub fn registry_entry(id: &str) -> Option<McpEntry> {
    let entry = match id {
        "opencode-docs" => McpEntry {
            id: "opencode-docs",
            server: "opencode",
            command: "npx",
            args: &["-y", "opencode-docs-mcp"],
            remote: None,
            codex_network: true,
            codex_startup_timeout_sec: Some(60),
            codex_tool_timeout_sec: None,
        },
        "playwright" => McpEntry {
            id: "playwright",
            server: "playwright",
            command: "npx",
            args: &["-y", "@playwright/mcp@latest"],
            remote: None,
            codex_network: true,
            codex_startup_timeout_sec: Some(60),
            codex_tool_timeout_sec: None,
        },
        "kubernetes" => McpEntry {
            id: "kubernetes",
            server: "kubernetes",
            command: "npx",
            args: &["-y", "kubernetes-mcp-server"],
            remote: None,
            codex_network: true,
            codex_startup_timeout_sec: Some(60),
            codex_tool_timeout_sec: None,
        },
        "youtube-transcript" => McpEntry {
            id: "youtube-transcript",
            server: "youtube-transcript",
            command: "npx",
            args: &["-y", "@kimtaeyoon83/mcp-server-youtube-transcript"],
            remote: None,
            codex_network: true,
            codex_startup_timeout_sec: Some(60),
            codex_tool_timeout_sec: None,
        },
        "docker-mcp" => McpEntry {
            id: "docker-mcp",
            server: "docker",
            command: "docker",
            args: &["mcp", "gateway", "run"],
            remote: None,
            codex_network: false,
            codex_startup_timeout_sec: Some(30),
            codex_tool_timeout_sec: None,
        },
        "context7" => McpEntry {
            id: "context7",
            server: "context7",
            command: "npx",
            args: &["-y", "@upstash/context7-mcp"],
            remote: Some(CONTEXT7_URL),
            codex_network: true,
            codex_startup_timeout_sec: None,
            codex_tool_timeout_sec: Some(60),
        },
        "mempalace" => McpEntry {
            id: "mempalace",
            server: "mempalace",
            command: "mempalace-mcp",
            args: &[],
            remote: None,
            codex_network: false,
            codex_startup_timeout_sec: Some(30),
            codex_tool_timeout_sec: None,
        },
        "anydb" => McpEntry {
            id: "anydb",
            server: "anydb",
            command: "npx",
            args: &["-y", "anydb-mcp"],
            remote: None,
            codex_network: true,
            codex_startup_timeout_sec: Some(60),
            codex_tool_timeout_sec: None,
        },
        _ => return None,
    };
    Some(entry)
}

pub fn mcp_description(id: &str) -> &'static str {
    match id {
        "opencode-docs" => "OpenCode docs MCP",
        "playwright" => "Browser automation via Playwright MCP",
        "kubernetes" => "Kubernetes pods/logs/exec management",
        "youtube-transcript" => "YouTube transcript extraction",
        "docker-mcp" => "Docker MCP Gateway",
        "context7" => "Fresh library documentation",
        "mempalace" => "Persistent project memory",
        "anydb" => "Database access MCP",
        _ => "MCP server",
    }
}

#[cfg_attr(not(test), allow(dead_code))]
pub fn mcp_display_row(id: &str, checked: bool) -> String {
    let mark = if checked { "[x]" } else { "[ ]" };
    format!("{mark} {id:<20} {}", mcp_description(id))
}

pub fn mcp_id_from_display_row(row: &str) -> String {
    let mut row = row;
    for prefix in ["[ ] ", "[x] ", "[X] "] {
        if let Some(rest) = row.strip_prefix(prefix) {
            row = rest;
            break;
        }
    }
    row.split_whitespace().next().unwrap_or("").to_string()
}

pub fn add_selected_mcp(app: &mut App, id: &str) {
    if registry_entry(id).is_none() {
        ui::warn(app, &format!("Ignoring unknown MCP integration '{id}'"));
        return;
    }
    util::unique_append(&mut app.selected_mcps, id);
}

pub fn sync_selected_mcps_from_env(app: &mut App) {
    if let Ok(raw) = std::env::var("AGENTIC_ENABLE_MCPS") {
        for item in util::split_csv(&raw) {
            add_selected_mcp(app, &item);
        }
    }
    let ctx7 = app.enable_context7_env.clone();
    if let Some(value) = ctx7 {
        let v = value.trim().to_lowercase();
        if v == "y" || v == "yes" {
            add_selected_mcp(app, "context7");
        }
    }
    let mp = app.enable_mempalace_env.clone();
    if let Some(value) = mp {
        let v = value.trim().to_lowercase();
        if v == "y" || v == "yes" {
            add_selected_mcp(app, "mempalace");
        }
    }
}

pub fn sync_legacy_mcp_env_from_selected(app: &mut App) {
    if app.selected_mcp_contains("context7") {
        app.enable_context7_env = Some("y".to_string());
    } else if app.enable_context7_env.is_none() {
        app.enable_context7_env = Some("n".to_string());
    }
    if app.selected_mcp_contains("mempalace") {
        app.enable_mempalace_env = Some("y".to_string());
    } else if app.enable_mempalace_env.is_none() {
        app.enable_mempalace_env = Some("n".to_string());
    }
}

/// Detect MCP servers already configured in the target project.
pub fn detect_configured_mcps(project_dir: &Path, home: &Path) -> Vec<String> {
    let server_to_id: &[(&str, &str)] = &[
        ("opencode", "opencode-docs"),
        ("playwright", "playwright"),
        ("kubernetes", "kubernetes"),
        ("youtube-transcript", "youtube-transcript"),
        ("docker", "docker-mcp"),
        ("MCP_DOCKER", "docker-mcp"),
        ("context7", "context7"),
        ("mempalace", "mempalace"),
        ("anydb", "anydb"),
    ];
    let mut found: Vec<String> = Vec::new();
    let json_paths: Vec<PathBuf> = vec![
        project_dir.join("opencode.json"),
        project_dir.join(".opencode/opencode.json"),
        project_dir.join(".mcp.json"),
        project_dir.join(".cursor/mcp.json"),
        project_dir.join(".gemini/settings.json"),
        project_dir.join(".kilocode/mcp.json"),
        home.join(".gemini/antigravity/mcp_config.json"),
    ];
    for path in json_paths {
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        let Ok(data) = serde_json::from_str::<Value>(&text) else {
            continue;
        };
        for section in ["mcpServers", "mcp"] {
            if let Some(map) = data.get(section).and_then(|v| v.as_object()) {
                for server in map.keys() {
                    if let Some((_, id)) = server_to_id.iter().find(|(s, _)| s == server) {
                        util::unique_append(&mut found, id);
                    }
                }
            }
        }
    }
    let config = project_dir.join(".codex/config.toml");
    if let Ok(text) = std::fs::read_to_string(&config) {
        for (server, id) in server_to_id {
            let needle = format!("[mcp_servers.{server}]");
            if text.lines().any(|line| line == needle) {
                util::unique_append(&mut found, id);
            }
        }
    }
    found.sort();
    found
}

fn opencode_local(command: &str, args: &[&str]) -> Value {
    let mut values = vec![json!(command)];
    values.extend(args.iter().map(|a| json!(a)));
    json!({"type": "local", "command": values, "enabled": true})
}

fn opencode_remote(url: &str, headers: Option<Value>) -> Value {
    let mut cfg = json!({"type": "remote", "url": url, "enabled": true});
    if let Some(headers) = headers {
        cfg.as_object_mut()
            .unwrap()
            .insert("headers".to_string(), headers);
    }
    cfg
}

/// Migrate legacy `mcpServers` entries into opencode `mcp` section.
pub fn migrate_opencode_legacy_servers(data: &mut Map<String, Value>) {
    let legacy = data.remove("mcpServers").unwrap_or(Value::Null);
    if !data.contains_key("mcp") {
        data.insert("mcp".to_string(), json!({}));
    }
    if let Some(legacy_map) = legacy.as_object() {
        let mcp = data.get_mut("mcp").unwrap().as_object_mut().unwrap();
        for (server, cfg) in legacy_map {
            if mcp.contains_key(server) {
                continue;
            }
            let Some(cfg) = cfg.as_object() else { continue };
            let Some(command) = cfg.get("command").and_then(|c| c.as_str()) else {
                continue;
            };
            let args: Vec<Value> = cfg
                .get("args")
                .and_then(|a| a.as_array())
                .cloned()
                .unwrap_or_default();
            let mut values = vec![json!(command)];
            values.extend(args);
            mcp.insert(
                server.clone(),
                json!({"type": "local", "command": values, "enabled": true}),
            );
        }
    }
}

/// JSON MCP config writer for opencode/generic/gemini platforms.
pub fn write_selected_mcp_json_config(
    app: &mut App,
    dest: &Path,
    source_ref: &str,
    platform: &str,
    selected_ids: &[String],
) -> crate::Result<()> {
    if selected_ids.is_empty() {
        return Ok(());
    }
    let platform = platform.to_string();
    let ids: Vec<String> = selected_ids.to_vec();
    write_json_config_file(app, dest, source_ref, move |data, context7_api_key| {
        if platform == "opencode" {
            if !data.contains_key("$schema") {
                data.insert(
                    "$schema".to_string(),
                    json!("https://opencode.ai/config.json"),
                );
            }
            migrate_opencode_legacy_servers(data);
        }
        for id in &ids {
            let Some(entry) = registry_entry(id) else {
                continue;
            };
            let server = entry.server.to_string();
            if platform == "opencode" {
                let value = if id == "docker-mcp" {
                    json!({"type": "local", "command": ["docker", "mcp", "gateway", "run"], "enabled": true})
                } else if id == "context7" {
                    let headers = if context7_api_key.is_empty() {
                        None
                    } else {
                        Some(json!({"CONTEXT7_API_KEY": context7_api_key}))
                    };
                    opencode_remote(entry.remote.unwrap_or(""), headers)
                } else {
                    opencode_local(entry.command, entry.args)
                };
                if !data.contains_key("mcp") {
                    data.insert("mcp".to_string(), json!({}));
                }
                data.get_mut("mcp")
                    .unwrap()
                    .as_object_mut()
                    .unwrap()
                    .insert(server, value);
                continue;
            }
            let cfg = if id == "docker-mcp" {
                json!({"command": "docker", "args": ["mcp", "gateway", "run"]})
            } else {
                let mut cfg = json!({"command": entry.command});
                if !entry.args.is_empty() {
                    cfg.as_object_mut()
                        .unwrap()
                        .insert("args".to_string(), json!(entry.args));
                }
                if id == "context7" && !context7_api_key.is_empty() {
                    cfg.as_object_mut().unwrap().insert(
                        "env".to_string(),
                        json!({"CONTEXT7_API_KEY": context7_api_key}),
                    );
                }
                cfg
            };
            if !data.contains_key("mcpServers") {
                data.insert("mcpServers".to_string(), json!({}));
            }
            data.get_mut("mcpServers")
                .unwrap()
                .as_object_mut()
                .unwrap()
                .insert(server, cfg);
        }
    })
}

/// Codex `.codex/config.toml` writer for generic MCP selections.
pub fn write_selected_mcp_codex_config(
    app: &mut App,
    selected_ids: &[String],
) -> crate::Result<()> {
    if selected_ids.is_empty() {
        return Ok(());
    }
    let dest = PathBuf::from(&app.project_dir).join(".codex/config.toml");
    let mut text = std::fs::read_to_string(&dest).unwrap_or_default();

    if selected_ids
        .iter()
        .filter_map(|id| registry_entry(id))
        .any(|e| e.codex_network)
    {
        text = tomledit::set_table_key(&text, "sandbox_workspace_write", "network_access", "true");
    }

    for id in selected_ids {
        let Some(entry) = registry_entry(id) else {
            continue;
        };
        let server = entry.server;
        text = tomledit::remove_server_block(&text, server);
        let mut block = if let Some(remote) = entry.remote {
            let mut block = format!(
                "[mcp_servers.{server}]\nurl = {}\n",
                tomledit::toml_string(remote)
            );
            if id == "context7" && !app.context7_api_key.is_empty() {
                block += &format!(
                    "http_headers = {{ \"CONTEXT7_API_KEY\" = {} }}\n",
                    tomledit::toml_string(&app.context7_api_key)
                );
            }
            block
        } else {
            let (command, args): (&str, Vec<&str>) = if id == "docker-mcp" {
                ("docker", vec!["mcp", "gateway", "run"])
            } else {
                (entry.command, entry.args.to_vec())
            };
            let mut block = format!(
                "[mcp_servers.{server}]\ncommand = {}\n",
                tomledit::toml_string(command)
            );
            if !args.is_empty() {
                let joined: Vec<String> = args.iter().map(|a| tomledit::toml_string(a)).collect();
                block += &format!("args = [{}]\n", joined.join(", "));
            }
            if id == "context7" && !app.context7_api_key.is_empty() {
                block += &format!(
                    "env = {{ \"CONTEXT7_API_KEY\" = {} }}\n",
                    tomledit::toml_string(&app.context7_api_key)
                );
            }
            block
        };
        if let Some(timeout) = entry.codex_startup_timeout_sec {
            block += &format!("startup_timeout_sec = {timeout}\n");
        }
        if let Some(timeout) = entry.codex_tool_timeout_sec {
            block += &format!("tool_timeout_sec = {timeout}\n");
        }
        text = if text.is_empty() {
            block.trim().to_string()
        } else {
            format!("{}\n\n{}", text.trim_end(), block)
                .trim()
                .to_string()
        };
    }
    let body = format!("{}\n", text.trim_end());
    write_text_config_file(app, &dest, "generated:mcp-codex-config", &body)
}

pub fn configure_selected_mcps_if_needed(app: &mut App) -> crate::Result<()> {
    sync_selected_mcps_from_env(app);
    sync_legacy_mcp_env_from_selected(app);
    if app.selected_mcps.is_empty() {
        return Ok(());
    }
    let generic: Vec<String> = app
        .selected_mcps
        .iter()
        .filter(|id| id.as_str() != "context7" && id.as_str() != "mempalace")
        .cloned()
        .collect();
    if generic.is_empty() {
        return Ok(());
    }
    let project = PathBuf::from(&app.project_dir);
    if app.selected_agent_os_contains("opencode") {
        write_selected_mcp_json_config(
            app,
            &project.join("opencode.json"),
            "generated:mcp-opencode-config",
            "opencode",
            &generic,
        )?;
        write_selected_mcp_json_config(
            app,
            &project.join(".opencode/opencode.json"),
            "generated:mcp-opencode-legacy-config",
            "opencode",
            &generic,
        )?;
    }
    if app.selected_agent_os_contains("codex") {
        write_selected_mcp_codex_config(app, &generic)?;
    }
    if app.selected_agent_os_contains("claude") {
        write_selected_mcp_json_config(
            app,
            &project.join(".mcp.json"),
            "generated:mcp-claude-config",
            "generic",
            &generic,
        )?;
    }
    if app.selected_agent_os_contains("cursor") {
        write_selected_mcp_json_config(
            app,
            &project.join(".cursor/mcp.json"),
            "generated:mcp-cursor-config",
            "generic",
            &generic,
        )?;
    }
    if app.selected_agent_os_contains("gemini") {
        write_selected_mcp_json_config(
            app,
            &project.join(".gemini/settings.json"),
            "generated:mcp-gemini-config",
            "gemini",
            &generic,
        )?;
    }
    if app.selected_agent_os_contains("kilocode") {
        write_selected_mcp_json_config(
            app,
            &project.join(".kilocode/mcp.json"),
            "generated:mcp-kilocode-config",
            "generic",
            &generic,
        )?;
    }
    if app.selected_agent_os_contains("antigravity") {
        let dest = app.home.join(".gemini/antigravity/mcp_config.json");
        write_selected_mcp_json_config(
            app,
            &dest,
            "generated:mcp-antigravity-config",
            "generic",
            &generic,
        )?;
    }
    Ok(())
}

fn command_succeeds(cmd: &str, args: &[&str]) -> bool {
    std::process::Command::new(cmd)
        .args(args)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

pub fn check_selected_mcp_runtime_prerequisites(app: &mut App) {
    if app.selected_mcp_contains("kubernetes") && !command_succeeds("kubectl", &["version"]) {
        ui::warn(app, "Kubernetes MCP selected, but 'kubectl version' did not complete successfully. Install or configure kubectl: https://kubernetes.io/docs/tasks/tools/");
    }
    if app.selected_mcp_contains("docker-mcp") && !command_succeeds("docker", &["mcp", "--version"])
    {
        ui::warn(app, "Docker MCP selected, but 'docker mcp --version' did not complete successfully. Install Docker and Docker MCP support: https://docs.docker.com/get-started/get-docker/ and https://docs.docker.com/ai/mcp-catalog-and-toolkit/");
    }
}

fn context7_value_with_url_key(url_key: &str, api_key: &str) -> Value {
    let mut ctx = json!({url_key: CONTEXT7_URL});
    if !api_key.is_empty() {
        ctx.as_object_mut()
            .unwrap()
            .insert("headers".to_string(), json!({"CONTEXT7_API_KEY": api_key}));
    }
    ctx
}

pub fn write_context7_opencode_config(
    app: &mut App,
    dest: &Path,
    source_ref: &str,
) -> crate::Result<()> {
    write_json_config_file(app, dest, source_ref, |data, api_key| {
        migrate_opencode_legacy_servers(data);
        let mut ctx = json!({"type": "remote", "url": CONTEXT7_URL, "enabled": true});
        if !api_key.is_empty() {
            ctx.as_object_mut()
                .unwrap()
                .insert("headers".to_string(), json!({"CONTEXT7_API_KEY": api_key}));
        }
        data.get_mut("mcp")
            .unwrap()
            .as_object_mut()
            .unwrap()
            .insert("context7".to_string(), ctx);
    })
}

pub fn write_context7_codex_config(app: &mut App) -> crate::Result<()> {
    let dest = PathBuf::from(&app.project_dir).join(".codex/config.toml");
    let text = std::fs::read_to_string(&dest).unwrap_or_default();
    let text = tomledit::set_table_key(&text, "sandbox_workspace_write", "network_access", "true");
    let text = tomledit::remove_server_block(&text, "context7");
    let mut block =
        format!("[mcp_servers.context7]\nurl = \"{CONTEXT7_URL}\"\ntool_timeout_sec = 60\n");
    if !app.context7_api_key.is_empty() {
        let escaped = app
            .context7_api_key
            .replace('\\', "\\\\")
            .replace('"', "\\\"");
        block += &format!("http_headers = {{ \"CONTEXT7_API_KEY\" = \"{escaped}\" }}\n");
    }
    let body = if text.is_empty() {
        block
    } else {
        format!("{block}\n{}\n", text.trim_end())
    };
    write_text_config_file(app, &dest, "generated:context7-codex-config", &body)
}

pub fn write_context7_generic_config(
    app: &mut App,
    dest: &Path,
    source_ref: &str,
    style: &str,
) -> crate::Result<()> {
    let style = style.to_string();
    write_json_config_file(app, dest, source_ref, move |data, api_key| {
        let ctx = match style.as_str() {
            "claude" => {
                let mut ctx = json!({"type": "http", "url": CONTEXT7_URL});
                if !api_key.is_empty() {
                    ctx.as_object_mut()
                        .unwrap()
                        .insert("headers".to_string(), json!({"CONTEXT7_API_KEY": api_key}));
                }
                ctx
            }
            "gemini" => context7_value_with_url_key("httpUrl", api_key),
            _ => context7_value_with_url_key("url", api_key),
        };
        if !data.contains_key("mcpServers") {
            data.insert("mcpServers".to_string(), json!({}));
        }
        data.get_mut("mcpServers")
            .unwrap()
            .as_object_mut()
            .unwrap()
            .insert("context7".to_string(), ctx);
    })
}

pub fn configure_context7_if_needed(app: &mut App) -> crate::Result<()> {
    let any_agent = [
        "opencode",
        "codex",
        "claude",
        "cursor",
        "gemini",
        "kilocode",
        "antigravity",
    ]
    .iter()
    .any(|a| app.selected_agent_os_contains(a));
    if !any_agent {
        return Ok(());
    }

    let mut enable = app
        .enable_context7_env
        .clone()
        .map(|v| v.trim().to_string())
        .unwrap_or_default();

    if app.is_interactive_terminal() {
        if enable.is_empty() {
            enable = if crate::prompt::read_yes_no(app, "Enable Context7 MCP configuration?") {
                "y".to_string()
            } else {
                "n".to_string()
            };
        }
        if !enable.to_lowercase().starts_with('y') {
            ui::log(app, "Context7 MCP configuration disabled");
            return Ok(());
        }
        crate::prompt::configure_context7_key_interactive(app)?;
    } else if !enable.is_empty() {
        if !enable.to_lowercase().starts_with('y') {
            ui::log(app, "Context7 MCP configuration disabled");
            return Ok(());
        }
    } else if app.context7_api_key.is_empty() {
        ui::log(app, "Context7 MCP configuration skipped; set CONTEXT7_API_KEY or use an interactive install to enable it");
        return Ok(());
    }

    let project = PathBuf::from(&app.project_dir);
    if app.selected_agent_os_contains("opencode") {
        write_context7_opencode_config(
            app,
            &project.join("opencode.json"),
            "generated:context7-opencode-config",
        )?;
        write_context7_opencode_config(
            app,
            &project.join(".opencode/opencode.json"),
            "generated:context7-opencode-legacy-config",
        )?;
    }
    if app.selected_agent_os_contains("codex") {
        write_context7_codex_config(app)?;
    }
    if app.selected_agent_os_contains("claude") {
        write_context7_generic_config(
            app,
            &project.join(".mcp.json"),
            "generated:context7-claude-config",
            "claude",
        )?;
    }
    if app.selected_agent_os_contains("cursor") {
        write_context7_generic_config(
            app,
            &project.join(".cursor/mcp.json"),
            "generated:context7-cursor-config",
            "generic",
        )?;
    }
    if app.selected_agent_os_contains("gemini") {
        write_context7_generic_config(
            app,
            &project.join(".gemini/settings.json"),
            "generated:context7-gemini-config",
            "gemini",
        )?;
    }
    if app.selected_agent_os_contains("kilocode") {
        write_context7_generic_config(
            app,
            &project.join(".kilocode/mcp.json"),
            "generated:context7-kilocode-config",
            "generic",
        )?;
    }
    if app.selected_agent_os_contains("antigravity") {
        let dest = app.home.join(".gemini/antigravity/mcp_config.json");
        write_context7_generic_config(
            app,
            &dest,
            "generated:context7-antigravity-config",
            "generic",
        )?;
    }

    if app.context7_api_key.is_empty() {
        ui::out(app, "Context7 MCP configured without an API key.");
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
    fn registry_covers_all_ids() {
        for id in MCP_REGISTRY_IDS {
            assert!(registry_entry(id).is_some(), "{id}");
        }
        assert!(registry_entry("nope").is_none());
    }

    #[test]
    fn display_row_roundtrip() {
        let row = mcp_display_row("context7", true);
        assert!(row.starts_with("[x] context7"));
        assert_eq!(mcp_id_from_display_row(&row), "context7");
        let row = mcp_display_row("anydb", false);
        assert_eq!(mcp_id_from_display_row(&row), "anydb");
    }

    #[test]
    fn add_selected_rejects_unknown() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        add_selected_mcp(&mut app, "context7");
        add_selected_mcp(&mut app, "context7");
        add_selected_mcp(&mut app, "bogus");
        assert_eq!(app.selected_mcps, vec!["context7"]);
        assert_eq!(app.warnings.len(), 1);
    }

    #[test]
    fn legacy_env_sync() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_mcps = vec!["context7".into()];
        sync_legacy_mcp_env_from_selected(&mut app);
        assert_eq!(app.enable_context7_env.as_deref(), Some("y"));
        assert_eq!(app.enable_mempalace_env.as_deref(), Some("n"));
    }

    #[test]
    fn opencode_json_config_written() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        let dest = tmp.path().join("opencode.json");
        write_selected_mcp_json_config(
            &mut app,
            &dest,
            "generated:test",
            "opencode",
            &["playwright".to_string(), "docker-mcp".to_string()],
        )
        .unwrap();
        let data: Value = serde_json::from_str(&std::fs::read_to_string(&dest).unwrap()).unwrap();
        assert_eq!(data["$schema"], json!("https://opencode.ai/config.json"));
        assert_eq!(data["mcp"]["playwright"]["type"], json!("local"));
        assert_eq!(
            data["mcp"]["docker"]["command"],
            json!(["docker", "mcp", "gateway", "run"])
        );
    }

    #[test]
    fn generic_json_config_with_context7_key() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.context7_api_key = "secret".to_string();
        let dest = tmp.path().join(".mcp.json");
        write_selected_mcp_json_config(
            &mut app,
            &dest,
            "generated:test",
            "generic",
            &["context7".to_string()],
        )
        .unwrap();
        let data: Value = serde_json::from_str(&std::fs::read_to_string(&dest).unwrap()).unwrap();
        assert_eq!(data["mcpServers"]["context7"]["command"], json!("npx"));
        assert_eq!(
            data["mcpServers"]["context7"]["env"]["CONTEXT7_API_KEY"],
            json!("secret")
        );
    }

    #[test]
    fn codex_config_blocks() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        write_selected_mcp_codex_config(&mut app, &["playwright".to_string()]).unwrap();
        let text = std::fs::read_to_string(tmp.path().join(".codex/config.toml")).unwrap();
        assert!(text.contains("[sandbox_workspace_write]\nnetwork_access = true"));
        assert!(text.contains("[mcp_servers.playwright]"));
        assert!(text.contains("startup_timeout_sec = 60"));
    }

    #[test]
    fn context7_codex_config() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.context7_api_key = "k\"ey".to_string();
        write_context7_codex_config(&mut app).unwrap();
        let text = std::fs::read_to_string(tmp.path().join(".codex/config.toml")).unwrap();
        assert!(text.contains("[mcp_servers.context7]"));
        assert!(text.contains("tool_timeout_sec = 60"));
        assert!(text.contains("http_headers = { \"CONTEXT7_API_KEY\" = \"k\\\"ey\" }"));
    }

    #[test]
    fn detect_configured_from_json_and_toml() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(
            tmp.path().join("opencode.json"),
            r#"{"mcp": {"context7": {}, "unknown": {}}}"#,
        )
        .unwrap();
        std::fs::create_dir_all(tmp.path().join(".codex")).unwrap();
        std::fs::write(
            tmp.path().join(".codex/config.toml"),
            "[mcp_servers.playwright]\ncommand = \"npx\"\n",
        )
        .unwrap();
        let home = tempfile::tempdir().unwrap();
        let found = detect_configured_mcps(tmp.path(), home.path());
        assert_eq!(found, vec!["context7", "playwright"]);
    }

    #[test]
    fn context7_interactive_enable_writes_configs() {
        let tmp = tempfile::tempdir().unwrap();
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.home = home.path().to_path_buf();
        app.selected_agent_os = vec!["opencode".to_string(), "cursor".to_string()];
        app.interactive_override = Some(true);
        // enable, use without API key
        crate::prompt::set_test_answers(&["y", "1"]);
        configure_context7_if_needed(&mut app).unwrap();
        let data: Value = serde_json::from_str(
            &std::fs::read_to_string(tmp.path().join("opencode.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(data["mcp"]["context7"]["url"], json!(CONTEXT7_URL));
        let cursor: Value = serde_json::from_str(
            &std::fs::read_to_string(tmp.path().join(".cursor/mcp.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(cursor["mcpServers"]["context7"]["url"], json!(CONTEXT7_URL));
    }

    #[test]
    fn context7_interactive_decline() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["claude".to_string()];
        app.interactive_override = Some(true);
        crate::prompt::set_test_answers(&["n"]);
        configure_context7_if_needed(&mut app).unwrap();
        assert!(!tmp.path().join(".mcp.json").exists());
    }

    #[test]
    fn context7_skipped_for_default_target() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["default".to_string()];
        app.interactive_override = Some(true);
        configure_context7_if_needed(&mut app).unwrap();
        assert!(!tmp.path().join(".mcp.json").exists());
    }

    #[test]
    fn gemini_and_claude_context7_styles() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.context7_api_key = "k".to_string();
        let gem = tmp.path().join("gem.json");
        write_context7_generic_config(&mut app, &gem, "generated:test", "gemini").unwrap();
        let data: Value = serde_json::from_str(&std::fs::read_to_string(&gem).unwrap()).unwrap();
        assert_eq!(
            data["mcpServers"]["context7"]["httpUrl"],
            json!(CONTEXT7_URL)
        );
        assert_eq!(
            data["mcpServers"]["context7"]["headers"]["CONTEXT7_API_KEY"],
            json!("k")
        );
        let cl = tmp.path().join("claude.json");
        write_context7_generic_config(&mut app, &cl, "generated:test", "claude").unwrap();
        let data: Value = serde_json::from_str(&std::fs::read_to_string(&cl).unwrap()).unwrap();
        assert_eq!(data["mcpServers"]["context7"]["type"], json!("http"));
    }

    #[test]
    fn migrate_legacy_servers() {
        let mut data: Map<String, Value> = serde_json::from_str(
            r#"{"mcpServers": {"anydb": {"command": "npx", "args": ["-y", "anydb-mcp"]}}}"#,
        )
        .unwrap();
        migrate_opencode_legacy_servers(&mut data);
        assert!(!data.contains_key("mcpServers"));
        assert_eq!(
            data["mcp"]["anydb"]["command"],
            json!(["npx", "-y", "anydb-mcp"])
        );
    }
}
