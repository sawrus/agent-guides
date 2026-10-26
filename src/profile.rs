//! Role profiles. A profile has two axes: the role set and an optional model profile.
//! Built-in `lean` (default) installs two helper subagents and lets the native harness lead; `team` installs the
//! v1 SDLC role team. Custom profiles live in `~/.config/agentic/<host>/profiles/<id>/profile.json`:
//! `{"name","base":"lean|team","agents":[...],"models":"<model-profile-id>"|null}`. `base` drives host behavior
//! (Codex memories, `AGENTS.override.md`, the Claude main agent); `agents` selects the role files.
//! JEV works with both bases: under `lean` it only suggests a workflow and routes models; under `team` it also
//! delegates to the role agents.

use crate::app::App;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

pub const LEAN: &str = "lean";
pub const TEAM: &str = "team";
pub const CHOICES: [&str; 2] = [LEAN, TEAM];
/// Hosts with their own role profile store.
pub const HOSTS: [&str; 3] = ["claude", "codex", "opencode"];
pub const LEAN_AGENTS: [&str; 2] = ["explorer", "reviewer"];
pub const TEAM_AGENTS: [&str; 9] = [
    "product-owner",
    "pm",
    "team-lead",
    "analyst",
    "developer",
    "qa",
    "devops-engineer",
    "instruction-reviewer",
    "memory-curator",
];
const PROFILE_FILE: &str = "profile.json";
const CODEX_SKILL_REL: &str = ".agents/skills/agentic-profile/SKILL.md";
const CODEX_SKILL_SOURCE: &str = "extensions/codex/skills/agentic-profile/SKILL.md";

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Profile {
    #[serde(default)]
    pub name: String,
    pub base: String,
    pub agents: Vec<String>,
    #[serde(default)]
    pub models: Option<String>,
}

impl Profile {
    pub fn is_team(&self) -> bool {
        self.base == TEAM
    }

    pub fn has_agent(&self, name: &str) -> bool {
        self.agents.iter().any(|a| a == name)
    }

    fn validate(&self, id: &str) -> crate::Result<()> {
        if !CHOICES.contains(&self.base.as_str()) {
            return Err(format!("profile '{id}': base must be lean or team").into());
        }
        for agent in &self.agents {
            if !is_role(agent) {
                return Err(format!(
                    "profile '{id}': unknown agent '{agent}' (allowed: {})",
                    all_roles().join(", ")
                )
                .into());
            }
        }
        if self.models.as_deref().is_some_and(|m| !valid_id(m)) {
            return Err(format!("profile '{id}': invalid models id").into());
        }
        Ok(())
    }
}

fn is_role(name: &str) -> bool {
    LEAN_AGENTS.contains(&name) || TEAM_AGENTS.contains(&name)
}

fn all_roles() -> Vec<&'static str> {
    LEAN_AGENTS
        .iter()
        .chain(TEAM_AGENTS.iter())
        .copied()
        .collect()
}

/// Profile ids are directory names: lowercase letters, digits, `.`, `_`, `-`.
pub fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && !id.starts_with('.')
        && id
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '.' | '_' | '-'))
}

pub fn builtin(id: &str) -> Option<Profile> {
    let agents: &[&str] = match id {
        LEAN => &LEAN_AGENTS,
        TEAM => &TEAM_AGENTS,
        _ => return None,
    };
    Some(Profile {
        name: id.into(),
        base: id.into(),
        agents: agents.iter().map(|s| s.to_string()).collect(),
        models: None,
    })
}

pub fn profile_file(app: &App, host: &str, id: &str) -> PathBuf {
    app.user_profiles_dir(host).join(id).join(PROFILE_FILE)
}

/// The user file first (also for `lean`/`team`, so edited seeds count), then the built-in definition.
pub fn load(app: &App, host: &str, id: &str) -> crate::Result<Profile> {
    if !valid_id(id) {
        return Err(format!("invalid profile id '{id}'").into());
    }
    let path = profile_file(app, host, id);
    if path.is_file() {
        let text = std::fs::read_to_string(&path)?;
        let mut profile: Profile = serde_json::from_str(&text)
            .map_err(|e| format!("{}: invalid profile ({e})", path.display()))?;
        if profile.name.is_empty() {
            profile.name = id.into();
        }
        profile.validate(id)?;
        return Ok(profile);
    }
    if let Some(profile) = builtin(id) {
        return Ok(profile);
    }
    if let Some(profile) = snapshot(app, host, id) {
        profile.validate(id)?;
        return Ok(profile);
    }
    Err(format!(
        "unknown {host} profile '{id}' (expected {})",
        path.display()
    )
    .into())
}

/// The copy of a custom profile saved in the project manifest for this host.
fn snapshot(app: &App, host: &str, id: &str) -> Option<Profile> {
    let value = app.profile_snapshots.get(host)?;
    if value.get("id").and_then(Value::as_str) != Some(id) {
        return None;
    }
    let mut profile: Profile = serde_json::from_value(value.clone()).ok()?;
    if profile.name.is_empty() {
        profile.name = id.into();
    }
    Some(profile)
}

/// Profile id for a host: the per-host choice, then the install-wide one, then `lean`.
pub fn id_for(app: &App, host: &str) -> String {
    app.host_profiles
        .get(host)
        .filter(|id| !id.is_empty())
        .cloned()
        .or_else(|| Some(app.install_profile.clone()).filter(|id| !id.is_empty()))
        .unwrap_or_else(|| LEAN.into())
}

/// Resolved profile for a host. `prepare` rejects invalid input first, so a failure here falls back to `lean`.
pub fn resolve(app: &App, host: &str) -> Profile {
    let id = id_for(app, host);
    if HOSTS.contains(&host) {
        if let Ok(profile) = load(app, host, &id) {
            return profile;
        }
    } else if let Some(profile) = builtin(&id).or_else(|| snapshot(app, host, &id)) {
        return profile;
    } else {
        // Hosts without their own store (for example gemini) follow the first host that defines the id.
        for known in HOSTS {
            if let Ok(profile) = load(app, known, &id) {
                return profile;
            }
        }
    }
    builtin(LEAN).unwrap()
}

pub fn is_team_for(app: &App, host: &str) -> bool {
    resolve(app, host).is_team()
}

/// The install-wide base, for hosts without their own choice.
pub fn is_team(app: &App) -> bool {
    resolve(app, "").is_team()
}

/// Base recorded in `.agentic.json` `settings.profile` (the JEV hooks read it). It is `team` only when every
/// selected host uses a team base: a lean host must not be told to delegate to role agents it does not have.
pub fn effective(app: &App) -> &'static str {
    let hosts: Vec<&str> = HOSTS
        .iter()
        .copied()
        .filter(|h| app.selected_agent_os_contains(h))
        .collect();
    let team = if hosts.is_empty() {
        is_team(app)
    } else {
        hosts.iter().all(|h| is_team_for(app, h))
    };
    if team {
        TEAM
    } else {
        LEAN
    }
}

/// Per-host profile ids of the selected hosts, saved as `settings.profile_ids`.
pub fn manifest_ids(app: &App) -> Value {
    let mut map = serde_json::Map::new();
    for host in &app.selected_agent_os {
        map.insert(host.clone(), json!(id_for(app, host)));
    }
    Value::Object(map)
}

/// Resolved custom profiles of the selected hosts, saved as `settings.profile_defs`, so a sync or upgrade
/// keeps the same roles when the user file is missing.
pub fn manifest_defs(app: &App) -> Value {
    let mut map = serde_json::Map::new();
    for host in &app.selected_agent_os {
        let id = id_for(app, host);
        if builtin(&id).is_some() {
            continue;
        }
        let profile = resolve(app, host);
        if profile.name == LEAN && profile == builtin(LEAN).unwrap() {
            continue;
        }
        let mut value = serde_json::to_value(&profile).unwrap_or(Value::Null);
        if let Some(obj) = value.as_object_mut() {
            obj.insert("id".into(), json!(id));
        }
        map.insert(host.clone(), value);
    }
    Value::Object(map)
}

/// Reject unknown or invalid profiles of the selected hosts before the install writes anything.
pub fn validate_selected(app: &App) -> crate::Result<()> {
    for host in HOSTS {
        if app.selected_agent_os_contains(host) {
            load(app, host, &id_for(app, host))?;
        }
    }
    Ok(())
}

/// Validate the chosen profiles before any write and apply their model profiles.
pub fn prepare(app: &mut App) -> crate::Result<()> {
    for host in HOSTS {
        if !app.selected_agent_os_contains(host) {
            continue;
        }
        let id = id_for(app, host);
        let profile = load(app, host, &id)?;
        if builtin(&id).is_none() && !profile_file(app, host, &id).is_file() {
            crate::ui::warn(
                app,
                &format!(
                    "{host} profile '{id}' has no user file; using the copy saved in .agentic.json"
                ),
            );
        }
        let Some(models) = profile.models.clone() else {
            continue;
        };
        match host {
            "claude" if !app.claude_profile_explicit => app.selected_claude_profile = models,
            "opencode" if std::env::var("AGENTIC_OPENCODE_PROFILE").is_err() => {
                app.selected_opencode_profile = models
            }
            "codex" => crate::ui::warn(
                app,
                &format!(
                    "Codex has no model profiles; ignoring models '{models}' of profile '{id}'"
                ),
            ),
            _ => {}
        }
    }
    Ok(())
}

/// Write `lean/` and `team/` into the host store when they are missing. Existing files stay untouched.
pub fn seed(app: &App, host: &str) -> crate::Result<()> {
    for id in CHOICES {
        let path = profile_file(app, host, id);
        if path.exists() {
            continue;
        }
        std::fs::create_dir_all(path.parent().unwrap())?;
        std::fs::write(&path, profile_json(&builtin(id).unwrap()))?;
    }
    Ok(())
}

fn profile_json(profile: &Profile) -> String {
    crate::markers::to_pretty_json(&serde_json::to_value(profile).unwrap_or_default())
}

/// Role profile ids of a host: the built-ins first, then user directories with `profile.json`.
/// Directories with only `opencode.json` are model profiles and are not listed.
pub fn list_ids(app: &App, host: &str) -> Vec<String> {
    let mut ids: Vec<String> = CHOICES.iter().map(|s| s.to_string()).collect();
    let mut user: Vec<String> = std::fs::read_dir(app.user_profiles_dir(host))
        .into_iter()
        .flatten()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().join(PROFILE_FILE).is_file())
        .map(|e| e.file_name().to_string_lossy().to_string())
        .filter(|id| valid_id(id) && !CHOICES.contains(&id.as_str()))
        .collect();
    user.sort();
    ids.extend(user);
    ids
}

fn roles_summary(agents: &[String]) -> String {
    match agents.len() {
        0 => "no roles".into(),
        1..=3 => agents.join(", "),
        n => format!("{n} roles: {}, …", agents[..3].join(", ")),
    }
}

/// Select label that shows the role set and the profile kind.
pub fn label(id: &str, profile: &Profile) -> String {
    let unchanged = builtin(id).as_ref() == Some(profile);
    let mut text = if unchanged && id == LEAN {
        format!(
            "{LEAN} · {} · native main session",
            profile.agents.join(", ")
        )
    } else if unchanged {
        format!("{id} · {}", roles_summary(&profile.agents))
    } else {
        format!(
            "{id} · {} · base {}",
            roles_summary(&profile.agents),
            profile.base
        )
    };
    if let Some(models) = &profile.models {
        text.push_str(&format!(" · models: {models}"));
    }
    text
}

/// `(id, label)` pairs for the profile select of one host. Invalid user files are skipped.
pub fn options(app: &App, host: &str) -> Vec<(String, String)> {
    list_ids(app, host)
        .into_iter()
        .filter_map(|id| {
            let profile = load(app, host, &id).ok()?;
            let text = label(&id, &profile);
            Some((id, text))
        })
        .collect()
}

/// Extension files that the host profile does not select.
pub fn skips_extension_file(app: &App, src_rel: &str, rel: &str) -> bool {
    let host = src_rel.strip_prefix("extensions/").unwrap_or("");
    if host == "codex" && rel == "AGENTS.override.md" {
        return !is_team_for(app, host);
    }
    // Codex discovers skills in `.agents/skills`; `install_commands` writes them there.
    if host == "codex" && rel.starts_with("skills/") {
        return true;
    }
    let Some(name) = rel
        .strip_prefix("agents/")
        .and_then(|file| file.rsplit_once('.'))
        .map(|(stem, _)| stem)
    else {
        return false;
    };
    is_role(name) && !resolve(app, host).has_agent(name)
}

/// The OpenCode config declares only the profile roles; user agents stay.
pub fn opencode_agents(data: &mut Value, profile: &Profile) {
    let Some(agents) = data.get_mut("agent").and_then(Value::as_object_mut) else {
        return;
    };
    agents.retain(|name, _| !is_role(name) || profile.has_agent(name));
    for name in LEAN_AGENTS {
        if profile.has_agent(name) {
            agents
                .entry(name)
                .or_insert_with(|| json!({ "mode": "subagent" }));
        }
    }
}

pub fn apply_opencode(app: &mut App, project: &Path) -> crate::Result<()> {
    if app.dry_run || !app.selected_agent_os_contains("opencode") {
        return Ok(());
    }
    let profile = resolve(app, "opencode");
    let dest = project.join(".opencode/opencode.json");
    let Ok(text) = std::fs::read_to_string(&dest) else {
        return Ok(());
    };
    let mut data: Value = serde_json::from_str(&text)?;
    opencode_agents(&mut data, &profile);
    let output = crate::markers::to_pretty_json(&data);
    if output != text {
        std::fs::write(&dest, output)?;
    }
    Ok(())
}

/// Codex has no project slash commands; a skill tells it how to switch the profile.
/// Claude Code and OpenCode get `commands/profile.md` from their extension directories.
pub fn install_commands(app: &mut App, project: &Path) -> crate::Result<()> {
    if !app.selected_agent_os_contains("codex") {
        return Ok(());
    }
    let content = include_str!("../extensions/codex/skills/agentic-profile/SKILL.md");
    crate::manifest::write_file_with_agentic_marker(
        app,
        content,
        &project.join(CODEX_SKILL_REL),
        CODEX_SKILL_SOURCE,
    )
}

fn manifest_settings(project: &Path) -> Value {
    std::fs::read_to_string(project.join(crate::PROJECT_MANIFEST_NAME))
        .ok()
        .and_then(|s| serde_json::from_str::<Value>(&s).ok())
        .map(|v| v["settings"].clone())
        .unwrap_or(Value::Null)
}

pub const CLI_USAGE: &str = "Usage: agentic profile list [--host claude|codex|opencode]
       agentic profile show <id> [--host <host>]
       agentic profile use <id> [--host <host>] [--project DIR] [--dry-run]
       agentic profile create <id> --from lean|team [--host <host>]";

/// `agentic profile list|show|use|create`.
pub fn run_cli(app: &mut App, rest: &[String]) -> crate::Result<()> {
    let sub = rest.first().map(String::as_str).unwrap_or("");
    let mut positional: Vec<String> = Vec::new();
    let mut host: Option<String> = None;
    let mut project: Option<String> = None;
    let mut from: Option<String> = None;
    let mut i = 1;
    while i < rest.len() {
        let value = || {
            rest.get(i + 1)
                .filter(|v| !v.starts_with("--"))
                .cloned()
                .ok_or_else(|| format!("{} requires a value", rest[i]))
        };
        match rest[i].as_str() {
            "--host" => host = Some(value()?),
            "--project" | "--project-dir" => project = Some(value()?),
            "--from" => from = Some(value()?),
            "--dry-run" => {
                app.dry_run = true;
                i += 1;
                continue;
            }
            "-h" | "--help" => {
                println!("{CLI_USAGE}");
                return Ok(());
            }
            other if other.starts_with('-') => {
                return Err(format!("Unknown option: {other}\n{CLI_USAGE}").into())
            }
            other => {
                positional.push(other.to_string());
                i += 1;
                continue;
            }
        }
        i += 2;
    }
    if let Some(h) = &host {
        if !HOSTS.contains(&h.as_str()) {
            return Err(format!("--host must be one of {}", HOSTS.join(", ")).into());
        }
    }
    let hosts: Vec<String> = match &host {
        Some(h) => vec![h.clone()],
        None => HOSTS.iter().map(|s| s.to_string()).collect(),
    };
    if !app.dry_run {
        for h in &hosts {
            seed(app, h)?;
        }
    }
    let id = positional.first().cloned().unwrap_or_default();
    match sub {
        "list" => {
            for h in &hosts {
                for (id, text) in options(app, h) {
                    println!("{h}\t{id}\t{text}");
                }
            }
            Ok(())
        }
        "show" => {
            let mut found = false;
            for h in &hosts {
                if let Ok(profile) = load(app, h, &id) {
                    found = true;
                    let path = profile_file(app, h, &id);
                    let source = if path.is_file() {
                        path.display().to_string()
                    } else {
                        "built-in".into()
                    };
                    println!("{h}: {source}\n{}", profile_json(&profile));
                } else if host.is_some() {
                    load(app, h, &id)?;
                }
            }
            if !found {
                return Err(format!("unknown profile '{id}'").into());
            }
            Ok(())
        }
        "create" => {
            let from = from.unwrap_or_default();
            let template = builtin(&from).ok_or("--from must be lean or team")?;
            if !valid_id(&id) || CHOICES.contains(&id.as_str()) {
                return Err(format!(
                    "invalid profile id '{id}': use lowercase letters, digits, '.', '_', '-'; lean and team are built in"
                )
                .into());
            }
            for h in &hosts {
                let path = profile_file(app, h, &id);
                if path.exists() {
                    return Err(format!("{} already exists", path.display()).into());
                }
            }
            for h in &hosts {
                let path = profile_file(app, h, &id);
                let profile = Profile {
                    name: id.clone(),
                    ..template.clone()
                };
                if app.dry_run {
                    println!("DRY-RUN create {}", path.display());
                    continue;
                }
                std::fs::create_dir_all(path.parent().unwrap())?;
                std::fs::write(&path, profile_json(&profile))?;
                println!("Created {}", path.display());
            }
            Ok(())
        }
        "use" => use_profile(app, &id, host.as_deref(), project),
        _ => Err(CLI_USAGE.into()),
    }
}

/// Reinstall the project with another profile through the upgrade path: obsolete unmodified role files are
/// removed, edited ones are preserved, and `.agentic.json` records the new profile.
fn use_profile(
    app: &mut App,
    id: &str,
    host: Option<&str>,
    project: Option<String>,
) -> crate::Result<()> {
    let root = match project {
        Some(dir) => PathBuf::from(dir),
        None => std::env::current_dir()?,
    };
    if !root.join(crate::PROJECT_MANIFEST_NAME).is_file() {
        return Err(format!(
            "{} has no {}; run `agentic install` first",
            root.display(),
            crate::PROJECT_MANIFEST_NAME
        )
        .into());
    }
    let settings = manifest_settings(&root);
    let installed: Vec<String> = settings["agent_os"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .filter(|h| HOSTS.contains(h))
        .map(str::to_owned)
        .collect();
    let targets: Vec<String> = match host {
        Some(h) if !installed.iter().any(|x| x == h) => {
            return Err(format!("{h} is not installed in {}", root.display()).into())
        }
        Some(h) => vec![h.to_string()],
        None => installed,
    };
    for h in &targets {
        load(app, h, id)?;
    }
    match host {
        Some(h) => {
            app.host_profiles.insert(h.to_string(), id.to_string());
        }
        None => app.install_profile = id.to_string(),
    }
    app.project_dir = root.to_string_lossy().to_string();
    crate::project_update::synchronize(app)?;
    let scope = host.map_or("all hosts".to_string(), |h| h.to_string());
    println!(
        "Profile '{id}' applied to {scope} in {}. Restart the agent session to load the new roles.",
        root.display()
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_app(home: &Path) -> App {
        let mut app = App::new().unwrap();
        app.home = home.to_path_buf();
        app.config_home_override = Some(home.join(".config"));
        app.host_profiles.clear();
        app
    }

    fn write_profile(app: &App, host: &str, id: &str, body: Value) {
        let path = profile_file(app, host, id);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(path, body.to_string()).unwrap();
    }

    #[test]
    fn lean_skips_team_roles_and_codex_override() {
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(home.path());
        app.install_profile = LEAN.into();
        app.jev_enabled = Some(false);
        assert!(skips_extension_file(
            &app,
            "extensions/claude",
            "agents/product-owner.md"
        ));
        assert!(!skips_extension_file(
            &app,
            "extensions/claude",
            "agents/explorer.md"
        ));
        assert!(skips_extension_file(
            &app,
            "extensions/codex",
            "AGENTS.override.md"
        ));
        assert!(!skips_extension_file(
            &app,
            "extensions/claude",
            "CLAUDE.md"
        ));
        assert!(skips_extension_file(
            &app,
            "extensions/codex",
            "skills/agentic-profile/SKILL.md"
        ));
    }

    #[test]
    fn team_and_jev_keep_v1_roles() {
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(home.path());
        app.install_profile = TEAM.into();
        assert!(!skips_extension_file(
            &app,
            "extensions/codex",
            "agents/qa.toml"
        ));
        assert!(skips_extension_file(
            &app,
            "extensions/codex",
            "agents/reviewer.toml"
        ));
        app.jev_enabled = Some(true);
        assert_eq!(effective(&app), TEAM);
    }

    #[test]
    fn lean_jev_keeps_lean_helpers() {
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(home.path());
        app.install_profile = LEAN.into();
        app.jev_enabled = Some(true);
        assert_eq!(effective(&app), LEAN);
        assert!(skips_extension_file(
            &app,
            "extensions/codex",
            "agents/developer.toml"
        ));
        assert!(!skips_extension_file(
            &app,
            "extensions/codex",
            "agents/reviewer.toml"
        ));
        assert!(skips_extension_file(
            &app,
            "extensions/codex",
            "AGENTS.override.md"
        ));
    }

    #[test]
    fn lean_opencode_config_keeps_user_agents() {
        let mut data =
            json!({"agent": {"product-owner": {"mode": "primary"}, "mine": {"mode": "subagent"}}});
        opencode_agents(&mut data, &builtin(LEAN).unwrap());
        let agents = data["agent"].as_object().unwrap();
        assert!(!agents.contains_key("product-owner"));
        assert!(
            agents.contains_key("mine")
                && agents.contains_key("explorer")
                && agents.contains_key("reviewer")
        );
    }

    #[test]
    fn team_opencode_config_drops_lean_helpers() {
        let mut data =
            json!({"agent": {"explorer": {"mode": "subagent"}, "developer": {}, "mine": {}}});
        opencode_agents(&mut data, &builtin(TEAM).unwrap());
        let agents = data["agent"].as_object().unwrap();
        assert!(!agents.contains_key("explorer"));
        assert!(agents.contains_key("developer") && agents.contains_key("mine"));
    }

    #[test]
    fn saved_copy_resolves_hosts_without_a_user_file() {
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(home.path());
        app.selected_agent_os = vec!["claude".into(), "gemini".into()];
        app.install_profile = "my".into();
        let saved = json!({"id": "my", "name": "my", "base": "team", "agents": ["qa"]});
        app.profile_snapshots.insert("claude".into(), saved.clone());
        app.profile_snapshots.insert("gemini".into(), saved);
        assert!(validate_selected(&app).is_ok());
        for host in ["claude", "gemini"] {
            let profile = resolve(&app, host);
            assert_eq!(profile.agents, ["qa"], "{host}");
            assert!(profile.is_team());
        }
        assert_eq!(manifest_ids(&app)["gemini"], "my");
        assert_eq!(manifest_defs(&app)["gemini"]["agents"], json!(["qa"]));
        app.profile_snapshots.clear();
        assert!(validate_selected(&app).is_err());
    }

    #[test]
    fn custom_profile_selects_listed_agents_and_team_base() {
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(home.path());
        write_profile(
            &app,
            "claude",
            "my",
            json!({"name": "my", "base": "team", "agents": ["developer", "qa", "explorer"], "models": "anthropic"}),
        );
        app.host_profiles.insert("claude".into(), "my".into());
        let profile = resolve(&app, "claude");
        assert!(profile.is_team());
        assert_eq!(profile.models.as_deref(), Some("anthropic"));
        assert!(!skips_extension_file(
            &app,
            "extensions/claude",
            "agents/developer.md"
        ));
        assert!(!skips_extension_file(
            &app,
            "extensions/claude",
            "agents/explorer.md"
        ));
        assert!(skips_extension_file(
            &app,
            "extensions/claude",
            "agents/product-owner.md"
        ));
        // Other hosts keep the install-wide default.
        assert!(!is_team_for(&app, "codex"));
        app.selected_agent_os = vec!["claude".into(), "codex".into()];
        assert_eq!(effective(&app), LEAN);
        assert_eq!(manifest_ids(&app), json!({"codex": "lean", "claude": "my"}));
        app.selected_claude_profile.clear();
        prepare(&mut app).unwrap();
        assert_eq!(app.selected_claude_profile, "anthropic");
    }

    #[test]
    fn invalid_profiles_are_rejected() {
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(home.path());
        write_profile(
            &app,
            "codex",
            "bad",
            json!({"base": "team", "agents": ["ghost"]}),
        );
        write_profile(&app, "codex", "nobase", json!({"base": "x", "agents": []}));
        assert!(load(&app, "codex", "bad").is_err());
        assert!(load(&app, "codex", "nobase").is_err());
        assert!(load(&app, "codex", "missing").is_err());
        assert!(load(&app, "codex", "../x").is_err());
        app.selected_agent_os = vec!["codex".into()];
        app.install_profile = "missing".into();
        assert!(prepare(&mut app).is_err());
    }

    #[test]
    fn seed_keeps_user_files_and_model_dirs_stay_out_of_list() {
        let home = tempfile::tempdir().unwrap();
        let app = test_app(home.path());
        write_profile(
            &app,
            "opencode",
            "lean",
            json!({"base": "lean", "agents": ["explorer"]}),
        );
        let models = app.user_profiles_dir("opencode").join("fast");
        std::fs::create_dir_all(&models).unwrap();
        std::fs::write(models.join("opencode.json"), "{}").unwrap();
        seed(&app, "opencode").unwrap();
        assert_eq!(load(&app, "opencode", "lean").unwrap().agents, ["explorer"]);
        assert_eq!(
            load(&app, "opencode", "team").unwrap(),
            builtin(TEAM).unwrap()
        );
        assert_eq!(list_ids(&app, "opencode"), ["lean", "team"]);
        assert_eq!(
            app.opencode_user_profiles_dir(),
            app.user_profiles_dir("opencode")
        );
    }

    #[test]
    fn labels_show_roles_and_kind() {
        assert_eq!(
            label(LEAN, &builtin(LEAN).unwrap()),
            "lean · explorer, reviewer · native main session"
        );
        assert_eq!(
            label(TEAM, &builtin(TEAM).unwrap()),
            "team · 9 roles: product-owner, pm, team-lead, …"
        );
        let custom = Profile {
            name: "my".into(),
            base: TEAM.into(),
            agents: vec!["developer".into(), "qa".into()],
            models: Some("anthropic".into()),
        };
        assert_eq!(
            label("my", &custom),
            "my · developer, qa · base team · models: anthropic"
        );
    }

    #[test]
    fn cli_create_list_show() {
        let home = tempfile::tempdir().unwrap();
        let mut app = test_app(home.path());
        let args = |a: &[&str]| a.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        run_cli(
            &mut app,
            &args(&["create", "mine", "--from", "team", "--host", "codex"]),
        )
        .unwrap();
        assert!(profile_file(&app, "codex", "lean").is_file());
        assert_eq!(load(&app, "codex", "mine").unwrap().agents.len(), 9);
        assert!(run_cli(&mut app, &args(&["create", "mine", "--from", "team"])).is_err());
        assert!(run_cli(&mut app, &args(&["create", "lean", "--from", "team"])).is_err());
        assert!(run_cli(&mut app, &args(&["create", "x", "--from", "big"])).is_err());
        assert!(run_cli(&mut app, &args(&["list"])).is_ok());
        assert!(run_cli(&mut app, &args(&["show", "mine"])).is_ok());
        assert!(run_cli(&mut app, &args(&["show", "mine", "--host", "claude"])).is_err());
        assert!(run_cli(&mut app, &args(&["list", "--host", "gemini"])).is_err());
        assert!(run_cli(&mut app, &args(&["bogus"])).is_err());
        let project = tempfile::tempdir().unwrap();
        let dir = project.path().to_string_lossy().to_string();
        assert!(run_cli(&mut app, &args(&["use", "team", "--project", &dir])).is_err());
    }
}
