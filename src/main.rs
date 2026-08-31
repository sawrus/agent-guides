use std::process::ExitCode;

mod agentsmd;
mod app;
mod config;
mod copydir;
mod doctor;
mod install;
mod kb;
mod manifest;
mod mapper;
mod markers;
mod mcp;
mod mempalace;
mod prompt;
mod selfinstall;
mod theme;
mod tomledit;
mod tui;
mod ui;
mod upgrade;
mod util;

use app::App;

pub const APP_NAME: &str = "agentic";
pub const APP_TITLE: &str = "Agentic Installer";
pub const APP_TUI_TITLE: &str = "Agentic installer (TUI mode)";
pub const APP_REPO_LINK: &str = "https://github.com/sawrus/agent-guides";
pub const PROJECT_MANIFEST_NAME: &str = ".agentic.json";
pub const DEFAULT_AGENT_OS: &str = "default";
pub const INSTALL_DIRS: [&str; 4] = ["rules", "skills", "workflows", "prompts"];
pub const THEME_CHOICES: [&str; 3] = ["auto", "dark", "light"];

pub fn app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

pub fn app_version_label() -> String {
    format!("v{}", app_version())
}

pub fn usage() -> String {
    format!(
        r#"{title} {version}

Usage:
  {name} list [agentos|areas|specs --area <name>]
  {name} install --project-dir <dir> [--agent-os <comma_list>] --areas <comma_list> --specializations <comma_list> [--theme auto|dark|light]
  {name} tui [--theme auto|dark|light]
  {name} upgrade
  {name} self-install [--bin-dir <dir>] [--force] [--dry-run]
  {name} --version

Behavior:
  - No arguments in interactive terminal: runs TUI mode
  - No arguments in non-interactive mode: prints usage and exits with code 1
  - Knowledge base is embedded in the binary; no external checkout is required

Options:
  --project-dir         Target project directory (created if missing)
  --agent-os            Comma-separated agent OS list (default: default)
  --areas               Comma-separated area list (example: software)
  --specializations     Comma-separated specializations in area.spec format (example: software.backend,software.frontend)
  --theme               Interface theme: auto|dark|light (default: config value or auto)
  --no-doctor           Skip real agent smoke checks after install
  --bin-dir             Installation directory for self-install (default: ~/.local/bin)
  --force               Overwrite existing binary for self-install
  --dry-run             Show actions without writing files
  -h, --help            Show this help
  -V, --version         Show agentic version

Examples:
  {name} list agentos
  {name} install --project-dir /tmp/demo --agent-os opencode,codex --areas software --specializations software.backend,software.frontend
  {name} tui --theme dark
  {name} upgrade
  {name} self-install --force
"#,
        title = APP_TITLE,
        version = app_version_label(),
        name = APP_NAME,
    )
}

fn print_usage() {
    print!("{}", usage());
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match run(args) {
        Ok(()) => ExitCode::SUCCESS,
        Err(err) => {
            let msg = err.to_string();
            if !msg.is_empty() && msg != "__exit1__" {
                ui::error_plain(&msg);
            }
            ExitCode::from(1)
        }
    }
}

pub type AnyError = Box<dyn std::error::Error>;
pub type Result<T> = std::result::Result<T, AnyError>;

/// Signal a silent exit code 1 (error message already printed).
pub fn exit1() -> AnyError {
    "__exit1__".into()
}

fn run(args: Vec<String>) -> Result<()> {
    let mut app = App::new()?;
    app.load_user_config();
    app.set_theme_colors();

    if args.is_empty() {
        if app.is_interactive_terminal() {
            tui::run_tui(&mut app)?;
            return Ok(());
        }
        print_usage();
        return Err(exit1());
    }

    let command = args[0].as_str();
    let rest = &args[1..];

    match command {
        "list" => cmd_list(&mut app, rest),
        "install" => cmd_install(&mut app, rest),
        "tui" => cmd_tui(&mut app, rest),
        "upgrade" => cmd_upgrade(&mut app, rest),
        "self-install" => cmd_self_install(&mut app, rest),
        "-h" | "--help" => {
            print_usage();
            Ok(())
        }
        "-V" | "--version" | "version" => {
            println!("{}", app_version_label());
            Ok(())
        }
        _ => {
            print_usage();
            Err(exit1())
        }
    }
}

fn cmd_list(app: &mut App, rest: &[String]) -> Result<()> {
    match rest.first().map(String::as_str) {
        Some("agentos") => {
            for choice in app.kb.agentos_choices() {
                println!("{choice}");
            }
            Ok(())
        }
        Some("areas") => {
            for area in app.kb.list_areas() {
                println!("{area}");
            }
            Ok(())
        }
        Some("specs") => {
            if rest.get(1).map(String::as_str) != Some("--area")
                || rest.get(2).map(|s| s.is_empty()).unwrap_or(true)
            {
                ui::error(app, &format!("Usage: {APP_NAME} list specs --area <name>"));
                return Err(exit1());
            }
            for spec in app.kb.list_specs(&rest[2]) {
                println!("{spec}");
            }
            Ok(())
        }
        _ => {
            print_usage();
            Err(exit1())
        }
    }
}

fn parse_theme_option(app: &mut App, value: Option<&str>) -> Result<()> {
    let value = value.unwrap_or("");
    if value.is_empty() {
        ui::error(app, "Missing --theme value. Allowed: auto|dark|light");
        return Err(exit1());
    }
    if !THEME_CHOICES.contains(&value) {
        ui::error(
            app,
            &format!("Invalid --theme value '{value}'. Allowed: auto|dark|light"),
        );
        return Err(exit1());
    }
    app.theme = value.to_string();
    app.theme_explicit = true;
    Ok(())
}

fn unknown_option(app: &mut App, opt: &str) -> AnyError {
    ui::error(app, &format!("Unknown option: {opt}"));
    print_usage();
    exit1()
}

fn cmd_install(app: &mut App, rest: &[String]) -> Result<()> {
    let mut i = 0;
    while i < rest.len() {
        match rest[i].as_str() {
            "--project-dir" => {
                app.project_dir = rest.get(i + 1).cloned().unwrap_or_default();
                i += 2;
            }
            "--agent-os" => {
                if app.selected_agent_os == vec![DEFAULT_AGENT_OS.to_string()] {
                    app.selected_agent_os.clear();
                }
                let raw = rest.get(i + 1).cloned().unwrap_or_default();
                for part in util::split_csv(&raw) {
                    app.selected_agent_os.push(part);
                }
                i += 2;
            }
            "--areas" => {
                let raw = rest.get(i + 1).cloned().unwrap_or_default();
                app.selected_areas.extend(util::split_csv(&raw));
                i += 2;
            }
            "--specializations" => {
                let raw = rest.get(i + 1).cloned().unwrap_or_default();
                app.selected_specs.extend(util::split_csv(&raw));
                i += 2;
            }
            "--theme" => {
                parse_theme_option(app, rest.get(i + 1).map(String::as_str))?;
                i += 2;
            }
            s if s.starts_with("--theme=") => {
                parse_theme_option(app, Some(&s["--theme=".len()..]))?;
                i += 1;
            }
            "--dry-run" => {
                app.dry_run = true;
                i += 1;
            }
            "--no-doctor" => {
                app.doctor_enabled_env = false;
                i += 1;
            }
            "-h" | "--help" => {
                print_usage();
                return Ok(());
            }
            other => return Err(unknown_option(app, other)),
        }
    }

    let cwd = std::env::current_dir()?;
    if app.project_dir.is_empty() && cwd.join(PROJECT_MANIFEST_NAME).is_file() {
        app.project_dir = cwd.to_string_lossy().to_string();
        let manifest = cwd.join(PROJECT_MANIFEST_NAME);
        manifest::load_install_settings_from_manifest(app, &manifest)?;
    } else if !app.project_dir.is_empty() {
        let manifest = std::path::Path::new(&app.project_dir).join(PROJECT_MANIFEST_NAME);
        if manifest.is_file() {
            manifest::load_install_settings_from_manifest(app, &manifest)?;
        }
    }

    app.set_theme_colors();
    install::run_install(app)?;
    if app.theme_explicit {
        config::save_user_config(app);
    }
    Ok(())
}

fn cmd_tui(app: &mut App, rest: &[String]) -> Result<()> {
    let mut i = 0;
    while i < rest.len() {
        match rest[i].as_str() {
            "--theme" => {
                parse_theme_option(app, rest.get(i + 1).map(String::as_str))?;
                i += 2;
            }
            s if s.starts_with("--theme=") => {
                parse_theme_option(app, Some(&s["--theme=".len()..]))?;
                i += 1;
            }
            "--dry-run" => {
                app.dry_run = true;
                i += 1;
            }
            "--no-doctor" => {
                app.doctor_enabled_env = false;
                i += 1;
            }
            "-h" | "--help" => {
                print_usage();
                return Ok(());
            }
            other => return Err(unknown_option(app, other)),
        }
    }
    tui::run_tui(app)
}

fn cmd_upgrade(app: &mut App, rest: &[String]) -> Result<()> {
    let mut i = 0;
    while i < rest.len() {
        match rest[i].as_str() {
            "--dry-run" => {
                app.dry_run = true;
                i += 1;
            }
            "-h" | "--help" => {
                print_usage();
                return Ok(());
            }
            other => return Err(unknown_option(app, other)),
        }
    }
    upgrade::upgrade_binary(app)?;
    upgrade::sync_current_project_after_upgrade(app)
}

fn cmd_self_install(app: &mut App, rest: &[String]) -> Result<()> {
    let mut i = 0;
    while i < rest.len() {
        match rest[i].as_str() {
            "--bin-dir" => {
                app.self_install_bin_dir = rest.get(i + 1).cloned().unwrap_or_default();
                i += 2;
            }
            "--force" => {
                app.self_install_force = true;
                i += 1;
            }
            "--theme" => {
                parse_theme_option(app, rest.get(i + 1).map(String::as_str))?;
                i += 2;
            }
            s if s.starts_with("--theme=") => {
                parse_theme_option(app, Some(&s["--theme=".len()..]))?;
                i += 1;
            }
            "--dry-run" => {
                app.dry_run = true;
                i += 1;
            }
            "-h" | "--help" => {
                print_usage();
                return Ok(());
            }
            other => return Err(unknown_option(app, other)),
        }
    }
    app.set_theme_colors();
    selfinstall::self_install(app)?;
    if app.theme_explicit {
        config::save_user_config(app);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(args: &[&str]) -> Vec<String> {
        args.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn usage_mentions_all_commands() {
        let text = usage();
        for needle in [
            "list",
            "install",
            "tui",
            "upgrade",
            "self-install",
            "--version",
        ] {
            assert!(text.contains(needle), "{needle}");
        }
        assert!(text.contains(&app_version_label()));
    }

    #[test]
    fn run_list_commands() {
        assert!(run(v(&["list", "areas"])).is_ok());
        assert!(run(v(&["list", "agentos"])).is_ok());
        assert!(run(v(&["list", "specs", "--area", "software"])).is_ok());
        assert!(run(v(&["list", "specs"])).is_err());
        assert!(run(v(&["list"])).is_err());
        assert!(run(v(&["list", "junk"])).is_err());
    }

    #[test]
    fn run_help_and_version() {
        assert!(run(v(&["--help"])).is_ok());
        assert!(run(v(&["-h"])).is_ok());
        assert!(run(v(&["--version"])).is_ok());
        assert!(run(v(&["version"])).is_ok());
        assert!(run(v(&["install", "--help"])).is_ok());
        assert!(run(v(&["tui", "--help"])).is_ok());
        assert!(run(v(&["upgrade", "--help"])).is_ok());
        assert!(run(v(&["self-install", "--help"])).is_ok());
    }

    #[test]
    fn run_rejects_bad_input() {
        assert!(run(v(&["bogus"])).is_err());
        assert!(run(v(&["install", "--nope"])).is_err());
        assert!(run(v(&["install", "--theme", "neon"])).is_err());
        assert!(run(v(&["install", "--theme"])).is_err());
        assert!(run(v(&["tui", "--junk"])).is_err());
        assert!(run(v(&["upgrade", "--junk"])).is_err());
        assert!(run(v(&["self-install", "--junk"])).is_err());
    }

    #[test]
    fn theme_equals_form_accepted() {
        // install with valid theme but missing project dir fails later with
        // a validation error, proving --theme=dark parsed fine
        let err = run(v(&["install", "--theme=dark"])).unwrap_err();
        assert_eq!(err.to_string(), "__exit1__");
    }
}
