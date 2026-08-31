//! Post-install smoke checks ("doctor") running real agent binaries.

use crate::app::App;
use crate::install::get_agent_binary_name;
use crate::mempalace::run_with_timeout;
use crate::ui;
use regex::Regex;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{Duration, Instant};

pub const DOCTOR_PROMPT: &str = "Reply with exactly: AGENTIC_DOCTOR_OK";

pub fn doctor_agent_supported(agent_os: &str) -> bool {
    matches!(agent_os, "codex" | "opencode" | "claude" | "gemini")
}

pub fn doctor_enabled(app: &App) -> bool {
    !app.dry_run && app.doctor_enabled_env
}

pub fn doctor_timeout_seconds() -> u64 {
    std::env::var("AGENTIC_DOCTOR_TIMEOUT_SECONDS")
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
        .filter(|v| *v >= 1)
        .unwrap_or(10)
}

pub fn output_has_fatal_patterns(output: &str) -> bool {
    let re = Regex::new(
        r"(?i)MCP.*(error|failed|failure|connection|connect|startup)|plugin.*(error|failed|failure)|auth.*(required|failed)|login required|permission.*(denied|required)|SyntaxError|Traceback|Invalid regular expression flags|An unexpected critical error occurred|FatalError|RuntimeError|EPERM|EACCES|panic:",
    )
    .unwrap();
    output.lines().any(|line| re.is_match(line))
}

fn binary_available(name: &str) -> bool {
    let Ok(path_var) = std::env::var("PATH") else {
        return false;
    };
    std::env::split_paths(&path_var).any(|dir| dir.join(name).is_file())
}

fn copy_dir_recursive(src: &Path, dest: &Path) -> std::io::Result<()> {
    std::fs::create_dir_all(dest)?;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let target = dest.join(entry.file_name());
        let path = entry.path();
        if path.is_dir() {
            copy_dir_recursive(&path, &target)?;
        } else if path.is_file() {
            std::fs::copy(&path, &target)?;
        }
    }
    Ok(())
}

fn doctor_copy_path_if_present(src: &Path, dest: &Path) {
    if src.is_dir() {
        let _ = copy_dir_recursive(src, dest);
    } else if src.is_file() {
        if let Some(parent) = dest.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let _ = std::fs::copy(src, dest);
    }
}

struct OpencodeRuntime {
    home: PathBuf,
    config_home: PathBuf,
    data_home: PathBuf,
    cache_home: PathBuf,
}

fn prepare_opencode_doctor_runtime(app: &App, doctor_root: &Path) -> OpencodeRuntime {
    let isolated_home = doctor_root.join("opencode-home");
    let config_home = isolated_home.join(".config");
    let data_home = isolated_home.join(".local/share");
    let cache_home = isolated_home.join(".cache");
    let _ = std::fs::create_dir_all(&config_home);
    let _ = std::fs::create_dir_all(&data_home);
    let _ = std::fs::create_dir_all(&cache_home);

    let source_config = std::env::var("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| app.home.join(".config"));
    let source_data = std::env::var("XDG_DATA_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| app.home.join(".local/share"));
    let source_cache = std::env::var("XDG_CACHE_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| app.home.join(".cache"));

    doctor_copy_path_if_present(
        &source_config.join("opencode"),
        &config_home.join("opencode"),
    );
    doctor_copy_path_if_present(
        &source_data.join("opencode/auth.json"),
        &data_home.join("opencode/auth.json"),
    );
    doctor_copy_path_if_present(
        &source_cache.join("opencode/models.json"),
        &cache_home.join("opencode/models.json"),
    );

    OpencodeRuntime {
        home: isolated_home,
        config_home,
        data_home,
        cache_home,
    }
}

fn build_doctor_command(
    app: &App,
    agent_os: &str,
    work_dir: &Path,
    doctor_root: &Path,
) -> Option<Command> {
    match agent_os {
        "codex" => {
            let mut cmd = Command::new("codex");
            cmd.args([
                "exec",
                "--skip-git-repo-check",
                "--ephemeral",
                "--sandbox",
                "workspace-write",
                "-C",
            ])
            .arg(work_dir)
            .arg(DOCTOR_PROMPT)
            .stdin(std::process::Stdio::null());
            Some(cmd)
        }
        "opencode" => {
            let runtime = prepare_opencode_doctor_runtime(app, doctor_root);
            let mut cmd = Command::new("opencode");
            cmd.args(["run", "--pure", "--dir"])
                .arg(work_dir)
                .args([
                    "--dangerously-skip-permissions",
                    "--format",
                    "json",
                    "--log-level",
                    "ERROR",
                ])
                .arg(DOCTOR_PROMPT)
                .env("HOME", &runtime.home)
                .env("XDG_CONFIG_HOME", &runtime.config_home)
                .env("XDG_DATA_HOME", &runtime.data_home)
                .env("XDG_CACHE_HOME", &runtime.cache_home)
                .env("OPENCODE_DISABLE_AUTOUPDATE", "1");
            Some(cmd)
        }
        "claude" => {
            let mut cmd = Command::new("claude");
            cmd.args([
                "-p",
                "--permission-mode",
                "bypassPermissions",
                "--output-format",
                "stream-json",
            ])
            .arg(DOCTOR_PROMPT)
            .current_dir(work_dir);
            Some(cmd)
        }
        "gemini" => {
            let mut cmd = Command::new("gemini");
            cmd.args(["--prompt", DOCTOR_PROMPT]).current_dir(work_dir);
            Some(cmd)
        }
        _ => None,
    }
}

fn run_doctor_for_agent(app: &mut App, agent_os: &str, doctor_root: &Path) -> bool {
    let binary = get_agent_binary_name(agent_os);
    if binary.is_empty() || !binary_available(binary) {
        ui::out(
            app,
            &format!("❌ {agent_os}: binary '{binary}' is not installed"),
        );
        return false;
    }
    let work_dir = doctor_root.join(agent_os);
    let output_file = doctor_root.join(format!("{agent_os}.log"));
    let timeout_seconds = doctor_timeout_seconds();
    let smoke_label = "lightweight smoke";
    let project = PathBuf::from(&app.project_dir);
    let _ = std::fs::create_dir_all(&work_dir);
    if project.is_dir() {
        let _ = copy_dir_recursive(&project, &work_dir);
    }

    let Some(mut cmd) = build_doctor_command(app, agent_os, &work_dir, doctor_root) else {
        return false;
    };
    let started = Instant::now();
    let result = run_with_timeout(&mut cmd, Duration::from_secs(timeout_seconds));
    let elapsed = started.elapsed().as_secs();
    let (timed_out, status, output) = match result {
        Ok(r) => r,
        Err(err) => {
            ui::out(
                app,
                &format!("❌ {agent_os}: {smoke_label} failed to start ({err})"),
            );
            return false;
        }
    };
    let _ = std::fs::write(&output_file, &output);
    ui::log(
        app,
        &format!("{agent_os} doctor finished: timeout={timeout_seconds}s exit={status} elapsed={elapsed}s"),
    );
    ui::log_file_block(app, &format!("doctor {agent_os}"), &output_file);

    if timed_out || status == 124 || status == 137 {
        ui::out(app, &format!("❌ {agent_os}: {smoke_label} timed out after {timeout_seconds}s (exit {status}, elapsed {elapsed}s, log: {})", output_file.display()));
        return false;
    }
    if status != 0 {
        ui::out(
            app,
            &format!(
                "❌ {agent_os}: {smoke_label} failed (exit {status}, elapsed {elapsed}s, log: {})",
                output_file.display()
            ),
        );
        return false;
    }
    if output_has_fatal_patterns(&output) {
        ui::out(app, &format!("❌ {agent_os}: {smoke_label} reported integration errors (exit {status}, elapsed {elapsed}s, log: {})", output_file.display()));
        return false;
    }
    ui::out(
        app,
        &format!("✅ {agent_os}: {smoke_label} passed (exit {status}, elapsed {elapsed}s)"),
    );
    true
}

pub fn run_agentic_doctor(app: &mut App) {
    if !doctor_enabled(app) {
        ui::log(app, "Agentic doctor skipped");
        return;
    }
    let selected: Vec<String> = app
        .selected_agent_os
        .iter()
        .filter(|a| doctor_agent_supported(a))
        .cloned()
        .collect();
    if selected.is_empty() {
        ui::log(
            app,
            "Agentic doctor skipped: no supported real agentos selected",
        );
        return;
    }
    let doctor_root = tempfile::Builder::new()
        .prefix("agentic-doctor.")
        .tempdir_in(crate::util::tmp_dir());
    let Ok(doctor_root) = doctor_root else {
        ui::warn(app, "Could not create doctor temp directory");
        return;
    };
    let doctor_root = doctor_root.keep();
    ui::out(app, "");
    ui::out_color(app, "=== Agentic doctor ===", &app.colors.header.clone());
    ui::out(app, &format!("Doctor temp root: {}", doctor_root.display()));
    ui::out(
        app,
        &format!("Doctor timeout: {}s per agent", doctor_timeout_seconds()),
    );

    let mut failures = 0;
    for agent_os in selected {
        if !run_doctor_for_agent(app, &agent_os, &doctor_root) {
            failures += 1;
        }
    }
    let keep_tmp = std::env::var("AGENTIC_DOCTOR_KEEP_TMP")
        .map(|v| v == "1")
        .unwrap_or(false);
    if keep_tmp || failures > 0 {
        ui::out(
            app,
            &format!("Doctor temp root kept: {}", doctor_root.display()),
        );
    } else {
        let _ = std::fs::remove_dir_all(&doctor_root);
    }
    if failures > 0 {
        ui::warn(
            app,
            &format!("Agentic doctor completed with {failures} failing check(s)"),
        );
    } else {
        ui::log(app, "Agentic doctor completed successfully");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn supported_agents() {
        assert!(doctor_agent_supported("codex"));
        assert!(doctor_agent_supported("opencode"));
        assert!(doctor_agent_supported("claude"));
        assert!(doctor_agent_supported("gemini"));
        assert!(!doctor_agent_supported("cursor"));
        assert!(!doctor_agent_supported("default"));
    }

    #[test]
    fn fatal_pattern_detection() {
        assert!(output_has_fatal_patterns("MCP server error: boom"));
        assert!(output_has_fatal_patterns(
            "Traceback (most recent call last):"
        ));
        assert!(output_has_fatal_patterns("panic: something"));
        assert!(output_has_fatal_patterns("auth failed"));
        assert!(!output_has_fatal_patterns("AGENTIC_DOCTOR_OK"));
        assert!(!output_has_fatal_patterns("all good"));
    }

    #[test]
    fn timeout_parsing() {
        std::env::remove_var("AGENTIC_DOCTOR_TIMEOUT_SECONDS");
        assert_eq!(doctor_timeout_seconds(), 10);
        std::env::set_var("AGENTIC_DOCTOR_TIMEOUT_SECONDS", "3");
        assert_eq!(doctor_timeout_seconds(), 3);
        std::env::set_var("AGENTIC_DOCTOR_TIMEOUT_SECONDS", "0");
        assert_eq!(doctor_timeout_seconds(), 10);
        std::env::set_var("AGENTIC_DOCTOR_TIMEOUT_SECONDS", "junk");
        assert_eq!(doctor_timeout_seconds(), 10);
        std::env::remove_var("AGENTIC_DOCTOR_TIMEOUT_SECONDS");
    }

    #[test]
    fn doctor_disabled_by_dry_run_and_env() {
        let mut app = App::new().unwrap();
        app.doctor_enabled_env = true;
        assert!(doctor_enabled(&app));
        app.dry_run = true;
        assert!(!doctor_enabled(&app));
        app.dry_run = false;
        app.doctor_enabled_env = false;
        assert!(!doctor_enabled(&app));
    }
}
