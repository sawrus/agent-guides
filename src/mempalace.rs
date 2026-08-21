//! Optional MemPalace integration. Requires python3/pip at runtime only when
//! the user enables it; the agentic binary itself stays self-contained.

use crate::app::App;
use crate::manifest::{write_json_config_file, write_text_config_file};
use crate::mcp::migrate_opencode_legacy_servers;
use crate::tomledit;
use crate::ui;
use serde_json::json;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

pub const MEMPALACE_IGNORE_CONTENT: &str = "node_modules/\n.venv/\nvenv/\ndist/\nlogs/\nbuild/\ntarget/\ncoverage/\n.ai/\n.git/\n.github/\n.cursor/\n.agent/\n.opencode/\n.claude/\n.gemini/\n.codex/\n.idea/\n*.csv\n*.parquet\n*.log\n*.jsonl\n\ndata/\ndumps/\ntmp/\n";

pub fn mempalace_project_wing(app: &App) -> String {
    let base = Path::new(&app.project_dir)
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();
    crate::util::mempalace_sanitize_wing_name(&base)
}

pub fn mempalace_shared_docs_wing() -> &'static str {
    "shared_docs"
}

pub fn mempalace_timeout_seconds() -> u64 {
    std::env::var("AGENTIC_MEMPALACE_TIMEOUT_SECONDS")
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
        .filter(|v| *v > 0)
        .unwrap_or(60)
}

fn command_available(name: &str) -> bool {
    Command::new(name)
        .arg("--version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .is_ok()
}

pub fn write_mempalace_ignore_file(app: &mut App) -> crate::Result<()> {
    let dest = PathBuf::from(&app.project_dir).join(".mempalaceignore");
    if dest.exists() {
        ui::log(
            app,
            &format!("MemPalace ignore file already exists: {}", dest.display()),
        );
        return Ok(());
    }
    write_text_config_file(
        app,
        &dest,
        "generated:mempalace-ignore",
        MEMPALACE_IGNORE_CONTENT,
    )
}

pub fn write_mempalace_opencode_config(app: &mut App, dest: &Path) -> crate::Result<()> {
    write_json_config_file(
        app,
        dest,
        "generated:mempalace-opencode-config",
        |data, _key| {
            migrate_opencode_legacy_servers(data);
            data.get_mut("mcp")
                .unwrap()
                .as_object_mut()
                .unwrap()
                .insert(
                    "mempalace".to_string(),
                    json!({"type": "local", "command": ["mempalace-mcp"]}),
                );
        },
    )
}

pub fn write_mempalace_codex_config(app: &mut App) -> crate::Result<()> {
    let dest = PathBuf::from(&app.project_dir).join(".codex/config.toml");
    let text = std::fs::read_to_string(&dest).unwrap_or_default();
    let text = tomledit::remove_server_block(&text, "mempalace");
    let block = "[mcp_servers.mempalace]\ncommand = \"mempalace-mcp\"\nstartup_timeout_sec = 30\n";
    let body = if text.is_empty() {
        block.to_string()
    } else {
        format!("{}\n\n{block}", text.trim_end())
    };
    write_text_config_file(app, &dest, "generated:mempalace-codex-config", &body)
}

pub fn write_mempalace_generic_json_config(
    app: &mut App,
    dest: &Path,
    marker: &str,
) -> crate::Result<()> {
    write_json_config_file(app, dest, marker, |data, _key| {
        if !data.contains_key("mcpServers") {
            data.insert("mcpServers".to_string(), json!({}));
        }
        data.get_mut("mcpServers")
            .unwrap()
            .as_object_mut()
            .unwrap()
            .insert("mempalace".to_string(), json!({"command": "mempalace-mcp"}));
    })
}

fn print_setup_instructions(app: &mut App) {
    let project_wing = mempalace_project_wing(app);
    let project_dir = app.project_dir.clone();
    ui::log(
        app,
        &format!(
            "Optional MemPalace project indexing instructions for target project: {project_dir}"
        ),
    );
    ui::out(app, "1) Ensure Python is installed and available in PATH.");
    ui::out(app, "2) Install MemPalace:");
    ui::out(app, "   pip install mempalace");
    ui::out(
        app,
        "3) Initialize the project memory taxonomy without LLM calls:",
    );
    ui::out(
        app,
        &format!("   echo \"N\" | mempalace init \"{project_dir}\" --yes --no-llm"),
    );
    ui::out(app, "4) Mine project knowledge into its isolated wing:");
    ui::out(
        app,
        &format!("   mempalace mine \"{project_dir}\" --wing \"{project_wing}\""),
    );
    if Path::new(&project_dir).join("docs").is_dir() {
        ui::out(
            app,
            "5) Mine shared project docs into the cross-project docs wing:",
        );
        ui::out(
            app,
            &format!("   mempalace mine \"{project_dir}/docs\" --wing shared_docs"),
        );
        ui::out(
            app,
            "6) Verify in your IDE/agent that MemPalace MCP tools are connected.",
        );
    } else {
        ui::out(
            app,
            "5) Verify in your IDE/agent that MemPalace MCP tools are connected.",
        );
    }
    ui::out(
        app,
        "Note: agentic uses --no-llm by default to keep MemPalace setup low-cost.",
    );
}

/// Run a command with the MemPalace timeout, capturing output to a temp file.
pub fn run_with_timeout(
    cmd: &mut Command,
    timeout: Duration,
) -> std::io::Result<(bool, i32, String)> {
    cmd.stdout(Stdio::piped()).stderr(Stdio::piped());
    let mut child = cmd.spawn()?;
    let start = Instant::now();
    loop {
        match child.try_wait()? {
            Some(status) => {
                let mut output = String::new();
                if let Some(mut stdout) = child.stdout.take() {
                    use std::io::Read;
                    let _ = stdout.read_to_string(&mut output);
                }
                if let Some(mut stderr) = child.stderr.take() {
                    use std::io::Read;
                    let _ = stderr.read_to_string(&mut output);
                }
                return Ok((false, status.code().unwrap_or(-1), output));
            }
            None => {
                if start.elapsed() >= timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Ok((true, 124, String::new()));
                }
                std::thread::sleep(Duration::from_millis(100));
            }
        }
    }
}

fn run_mempalace_command(app: &mut App, label: &str, cmd: &mut Command) -> bool {
    let timeout = Duration::from_secs(mempalace_timeout_seconds());
    match run_with_timeout(cmd, timeout) {
        Ok((true, _, _)) => {
            ui::warn(
                app,
                &format!("Timed out after {}s: {label}", timeout.as_secs()),
            );
            false
        }
        Ok((false, 0, _)) => {
            ui::log(app, &format!("{label} completed"));
            true
        }
        Ok((false, status, output)) => {
            ui::warn(app, &format!("Failed: {label} (exit {status})"));
            if output.contains("incompatible architecture") && output.contains("numpy") {
                ui::warn(app, "MemPalace failed because Python/NumPy architecture is inconsistent. Reinstall MemPalace dependencies with the same architecture as the Python running 'mempalace'.");
            } else if output.contains("No LLM provider reachable") {
                ui::warn(app, "MemPalace could not reach an LLM provider and continued heuristics-only; this is non-fatal unless a later dependency error appears.");
            }
            false
        }
        Err(err) => {
            ui::warn(app, &format!("Failed to run {label}: {err}"));
            false
        }
    }
}

fn pip_command() -> Option<Vec<String>> {
    for candidate in ["pip", "pip3"] {
        if command_available(candidate) {
            return Some(vec![candidate.to_string()]);
        }
    }
    if command_available("python3") {
        let ok = Command::new("python3")
            .args(["-m", "pip", "--version"])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false);
        if ok {
            return Some(vec![
                "python3".to_string(),
                "-m".to_string(),
                "pip".to_string(),
            ]);
        }
    }
    None
}

fn python_available() -> bool {
    command_available("python3") || command_available("python")
}

fn install_mempalace_with_pip(app: &mut App, pip: &[String]) -> bool {
    let mut cmd = Command::new(&pip[0]);
    cmd.args(&pip[1..]).args(["install", "mempalace"]);
    let output = cmd.output();
    match output {
        Ok(out) if out.status.success() => {
            ui::log(
                app,
                &format!(
                    "MemPalace package installed via '{} install mempalace'",
                    pip.join(" ")
                ),
            );
            true
        }
        Ok(out) => {
            let combined = format!(
                "{}{}",
                String::from_utf8_lossy(&out.stdout),
                String::from_utf8_lossy(&out.stderr)
            );
            if combined
                .to_lowercase()
                .contains("externally-managed-environment")
            {
                ui::log(app, "Detected PEP 668 externally-managed Python environment; retrying inside isolated venv");
                return install_mempalace_in_venv(app);
            }
            ui::warn(app, "Unable to auto-install mempalace via pip; continuing with manual setup instructions");
            let reason = combined
                .lines()
                .find(|l| !l.trim().is_empty())
                .unwrap_or("");
            if !reason.is_empty() {
                ui::warn(app, &format!("pip failure reason: {reason}"));
            }
            false
        }
        Err(err) => {
            ui::warn(app, &format!("Unable to run pip: {err}"));
            false
        }
    }
}

fn install_mempalace_in_venv(app: &mut App) -> bool {
    let py_bin = if command_available("python3") {
        "python3"
    } else if command_available("python") {
        "python"
    } else {
        ui::warn(app, "python3/python executable not found");
        return false;
    };
    let venv_dir = app.home.join(".agentic/mempalace-venv");
    if !venv_dir.is_dir() {
        if let Some(parent) = venv_dir.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let ok = Command::new(py_bin)
            .args(["-m", "venv"])
            .arg(&venv_dir)
            .status()
            .map(|s| s.success())
            .unwrap_or(false);
        if !ok {
            ui::warn(
                app,
                &format!(
                    "Unable to create virtual environment at {}",
                    venv_dir.display()
                ),
            );
            return false;
        }
    }
    let venv_python = venv_dir.join("bin/python");
    let steps: [&[&str]; 2] = [
        &[
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ],
        &[
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--upgrade",
            "mempalace",
        ],
    ];
    for step in steps {
        let ok = Command::new(&venv_python)
            .args(step)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false);
        if !ok {
            ui::warn(
                app,
                "Unable to install mempalace inside virtual environment",
            );
            return false;
        }
    }
    let local_bin = app.home.join(".local/bin");
    let _ = std::fs::create_dir_all(&local_bin);
    #[cfg(unix)]
    {
        let _ = std::fs::remove_file(local_bin.join("mempalace"));
        let _ =
            std::os::unix::fs::symlink(venv_dir.join("bin/mempalace"), local_bin.join("mempalace"));
        if venv_dir.join("bin/mempalace-mcp").exists() {
            let _ = std::fs::remove_file(local_bin.join("mempalace-mcp"));
            let _ = std::os::unix::fs::symlink(
                venv_dir.join("bin/mempalace-mcp"),
                local_bin.join("mempalace-mcp"),
            );
        }
    }
    let current_path = std::env::var("PATH").unwrap_or_default();
    std::env::set_var(
        "PATH",
        format!(
            "{}:{}:{current_path}",
            local_bin.display(),
            venv_dir.join("bin").display()
        ),
    );
    crate::selfinstall::append_path_export_to_shell_rc(app, &local_bin);
    ui::log(
        app,
        &format!(
            "MemPalace installed successfully inside virtual environment: {}",
            venv_dir.display()
        ),
    );
    true
}

fn initialize_mempalace_project(app: &mut App, step_prefix: &str) -> bool {
    let project_wing = mempalace_project_wing(app);
    let project_dir = app.project_dir.clone();
    ui::log(
        app,
        &format!("{step_prefix} [4/4] Initializing project memory at {project_dir} (wing: {project_wing})"),
    );
    if !command_available("mempalace") {
        ui::warn(
            app,
            "mempalace command is unavailable after install; please run setup manually",
        );
        print_setup_instructions(app);
        return false;
    }
    let mut init_cmd = Command::new("mempalace");
    init_cmd
        .args(["init", &project_dir, "--yes", "--no-llm"])
        .stdin(Stdio::null());
    if !run_mempalace_command(app, "MemPalace init", &mut init_cmd) {
        print_setup_instructions(app);
        return false;
    }
    let mut mine_cmd = Command::new("mempalace");
    mine_cmd.args(["mine", &project_dir, "--wing", &project_wing]);
    if !run_mempalace_command(app, "MemPalace mine project wing", &mut mine_cmd) {
        print_setup_instructions(app);
        return false;
    }
    if Path::new(&project_dir).join("docs").is_dir() {
        let docs = format!("{project_dir}/docs");
        let mut docs_cmd = Command::new("mempalace");
        docs_cmd.args(["mine", &docs, "--wing", mempalace_shared_docs_wing()]);
        if !run_mempalace_command(app, "MemPalace mine shared docs wing", &mut docs_cmd) {
            print_setup_instructions(app);
            return false;
        }
    }
    ui::log(
        app,
        &format!("{step_prefix} [4/4] Initialization step finished"),
    );
    true
}

fn setup_mempalace_for_agentic(app: &mut App, initialize_project: bool) -> bool {
    let step_prefix = "MemPalace setup";
    if std::env::var("AGENTIC_MEMPALACE_SETUP")
        .map(|v| v == "skip")
        .unwrap_or(false)
    {
        ui::log(
            app,
            &format!("{step_prefix} skipped by AGENTIC_MEMPALACE_SETUP=skip"),
        );
        return command_available("mempalace-mcp");
    }

    ui::log(
        app,
        &format!("{step_prefix} [1/4] Checking Python availability"),
    );
    if !python_available() {
        ui::warn(
            app,
            "Python is not installed. Install Python 3 first, then run: pip install mempalace",
        );
        ui::warn(app, "Install help: https://www.python.org/downloads/");
        print_setup_instructions(app);
        return false;
    }
    ui::log(app, &format!("{step_prefix} [1/4] Python check passed"));

    if command_available("mempalace-mcp") && (!initialize_project || command_available("mempalace"))
    {
        ui::log(
            app,
            &format!(
                "{step_prefix} [2/4] MemPalace binaries already available; skipping pip install"
            ),
        );
        if !initialize_project {
            ui::log(app, &format!("{step_prefix} [4/4] Project memory initialization skipped for selected agent target(s)"));
            return true;
        }
        return initialize_mempalace_project(app, step_prefix);
    }

    ui::log(
        app,
        &format!("{step_prefix} [2/4] Checking pip availability"),
    );
    let Some(pip) = pip_command() else {
        ui::warn(
            app,
            "pip is not available. Install pip for Python 3, then run: pip install mempalace",
        );
        print_setup_instructions(app);
        return false;
    };
    ui::log(app, &format!("{step_prefix} [2/4] pip check passed"));

    ui::log(
        app,
        &format!("{step_prefix} [3/4] Installing mempalace package"),
    );
    if !install_mempalace_with_pip(app, &pip) {
        print_setup_instructions(app);
        return false;
    }
    if !initialize_project {
        ui::log(app, &format!("{step_prefix} [4/4] Project memory initialization skipped for selected agent target(s)"));
        return true;
    }
    initialize_mempalace_project(app, step_prefix)
}

pub fn configure_mempalace_if_needed(app: &mut App) -> crate::Result<()> {
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

    let mut enable = "N".to_string();
    if let Some(env) = &app.enable_mempalace_env {
        enable = env.trim().to_string();
    } else if app.is_interactive_terminal() {
        enable =
            crate::prompt::read_line_prompt("Enable MemPalace MCP memory integration? [y/N]: ");
        if enable.is_empty() {
            enable = "n".to_string();
        }
    }
    if enable.eq_ignore_ascii_case("n") {
        ui::log(app, "Skipped MemPalace MCP configuration");
        return Ok(());
    }

    write_mempalace_ignore_file(app)?;

    let setup_ok = setup_mempalace_for_agentic(app, true);
    if !setup_ok {
        if !command_available("mempalace-mcp") {
            ui::warn(
                app,
                "mempalace-mcp is unavailable; install/repair MemPalace and re-run setup",
            );
        }
    } else {
        ui::log(app, "MemPalace MCP binary found: mempalace-mcp");
    }

    let project = PathBuf::from(&app.project_dir);
    if app.selected_agent_os_contains("opencode") {
        write_mempalace_opencode_config(app, &project.join("opencode.json"))?;
        write_mempalace_opencode_config(app, &project.join(".opencode/opencode.json"))?;
    }
    if app.selected_agent_os_contains("codex") {
        write_mempalace_codex_config(app)?;
    }
    if app.selected_agent_os_contains("claude") {
        write_mempalace_generic_json_config(
            app,
            &project.join(".mcp.json"),
            "generated:mempalace-claude-config",
        )?;
    }
    if app.selected_agent_os_contains("cursor") {
        write_mempalace_generic_json_config(
            app,
            &project.join(".cursor/mcp.json"),
            "generated:mempalace-cursor-config",
        )?;
    }
    if app.selected_agent_os_contains("gemini") {
        write_mempalace_generic_json_config(
            app,
            &project.join(".gemini/settings.json"),
            "generated:mempalace-gemini-config",
        )?;
    }
    if app.selected_agent_os_contains("kilocode") {
        write_mempalace_generic_json_config(
            app,
            &project.join(".kilocode/mcp.json"),
            "generated:mempalace-kilocode-config",
        )?;
    }
    if app.selected_agent_os_contains("antigravity") {
        let dest = app.home.join(".gemini/antigravity/mcp_config.json");
        write_mempalace_generic_json_config(app, &dest, "generated:mempalace-antigravity-config")?;
    }
    Ok(())
}

pub fn upgrade_mempalace_graph(app: &mut App) {
    let enabled = app
        .enable_mempalace_env
        .as_deref()
        .map(|v| v.to_lowercase().starts_with('y'))
        .unwrap_or(false);
    if !enabled || !command_available("mempalace") {
        return;
    }
    let project_wing = mempalace_project_wing(app);
    let project_dir = app.project_dir.clone();
    if app.dry_run {
        ui::log(
            app,
            &format!("DRY-RUN mempalace mine \"{project_dir}\" --wing \"{project_wing}\""),
        );
        if Path::new(&project_dir).join("docs").is_dir() {
            ui::log(
                app,
                &format!("DRY-RUN mempalace mine \"{project_dir}/docs\" --wing \"shared_docs\""),
            );
        }
        return;
    }
    ui::log(
        app,
        &format!("Refreshing MemPalace knowledge graph for {project_dir} (wing: {project_wing})"),
    );
    let ok = Command::new("mempalace")
        .args(["mine", &project_dir, "--wing", &project_wing])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false);
    if ok {
        ui::log(app, "MemPalace graph updated");
    } else {
        ui::warn(app, &format!("mempalace mine failed; graph may be stale — run manually: mempalace mine \"{project_dir}\" --wing \"{project_wing}\""));
    }
    if Path::new(&project_dir).join("docs").is_dir() {
        let docs = format!("{project_dir}/docs");
        ui::log(
            app,
            &format!("Refreshing shared MemPalace docs wing from {docs}"),
        );
        let ok = Command::new("mempalace")
            .args(["mine", &docs, "--wing", mempalace_shared_docs_wing()])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false);
        if ok {
            ui::log(app, "MemPalace shared docs wing updated");
        } else {
            ui::warn(app, &format!("mempalace docs mine failed; shared docs may be stale — run manually: mempalace mine \"{docs}\" --wing \"shared_docs\""));
        }
    }
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
    fn ignore_file_written_once() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        write_mempalace_ignore_file(&mut app).unwrap();
        let dest = tmp.path().join(".mempalaceignore");
        assert_eq!(
            std::fs::read_to_string(&dest).unwrap(),
            MEMPALACE_IGNORE_CONTENT
        );
        std::fs::write(&dest, "custom").unwrap();
        let mut app2 = test_app(tmp.path());
        write_mempalace_ignore_file(&mut app2).unwrap();
        assert_eq!(std::fs::read_to_string(&dest).unwrap(), "custom");
    }

    #[test]
    fn opencode_config_gets_mempalace() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        let dest = tmp.path().join("opencode.json");
        write_mempalace_opencode_config(&mut app, &dest).unwrap();
        let data: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(&dest).unwrap()).unwrap();
        assert_eq!(
            data["mcp"]["mempalace"]["command"],
            json!(["mempalace-mcp"])
        );
    }

    #[test]
    fn codex_config_gets_mempalace_block() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        write_mempalace_codex_config(&mut app).unwrap();
        let text = std::fs::read_to_string(tmp.path().join(".codex/config.toml")).unwrap();
        assert!(text.contains("[mcp_servers.mempalace]"));
        assert!(text.contains("startup_timeout_sec = 30"));
    }

    #[test]
    fn generic_config_gets_mempalace() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        let dest = tmp.path().join(".mcp.json");
        write_mempalace_generic_json_config(&mut app, &dest, "generated:test").unwrap();
        let data: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(&dest).unwrap()).unwrap();
        assert_eq!(
            data["mcpServers"]["mempalace"]["command"],
            json!("mempalace-mcp")
        );
    }

    #[test]
    fn wing_names() {
        let mut app = App::new().unwrap();
        app.project_dir = "/tmp/My Cool-Project".to_string();
        assert_eq!(mempalace_project_wing(&app), "my_cool_project");
        assert_eq!(mempalace_shared_docs_wing(), "shared_docs");
    }

    #[test]
    fn timeout_parsing() {
        std::env::remove_var("AGENTIC_MEMPALACE_TIMEOUT_SECONDS");
        assert_eq!(mempalace_timeout_seconds(), 60);
        std::env::set_var("AGENTIC_MEMPALACE_TIMEOUT_SECONDS", "5");
        assert_eq!(mempalace_timeout_seconds(), 5);
        std::env::set_var("AGENTIC_MEMPALACE_TIMEOUT_SECONDS", "0");
        assert_eq!(mempalace_timeout_seconds(), 60);
        std::env::remove_var("AGENTIC_MEMPALACE_TIMEOUT_SECONDS");
    }

    #[test]
    fn interactive_decline_skips_configuration() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["claude".to_string()];
        app.interactive_override = Some(true);
        crate::prompt::set_test_answers(&[""]);
        configure_mempalace_if_needed(&mut app).unwrap();
        assert!(!tmp.path().join(".mempalaceignore").exists());
        assert!(!tmp.path().join(".mcp.json").exists());
    }

    #[test]
    fn skipped_for_default_target() {
        let tmp = tempfile::tempdir().unwrap();
        let mut app = test_app(tmp.path());
        app.selected_agent_os = vec!["default".to_string()];
        app.enable_mempalace_env = Some("y".to_string());
        configure_mempalace_if_needed(&mut app).unwrap();
        assert!(!tmp.path().join(".mempalaceignore").exists());
    }

    #[test]
    fn run_with_timeout_kills_slow_process() {
        let mut cmd = Command::new("sleep");
        cmd.arg("5");
        let (timed_out, code, _) = run_with_timeout(&mut cmd, Duration::from_millis(200)).unwrap();
        assert!(timed_out);
        assert_eq!(code, 124);
        let mut ok_cmd = Command::new("true");
        let (timed_out, code, _) = run_with_timeout(&mut ok_cmd, Duration::from_secs(5)).unwrap();
        assert!(!timed_out);
        assert_eq!(code, 0);
    }
}
