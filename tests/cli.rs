//! Integration tests: run the real agentic binary end-to-end
//! (port of the bash tests/e2e suite).

use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::Value;
use std::path::Path;

fn agentic(home: &Path) -> Command {
    let mut cmd = Command::cargo_bin("agentic").unwrap();
    cmd.env("HOME", home)
        .env("XDG_CONFIG_HOME", home.join(".config"))
        .env("XDG_DATA_HOME", home.join(".local/share"))
        .env("XDG_CACHE_HOME", home.join(".cache"))
        .env("AGENTIC_DOCTOR", "0")
        .env_remove("AGENTIC_ENABLE_MCPS")
        .env_remove("AGENTIC_ENABLE_CONTEXT7")
        .env_remove("AGENTIC_ENABLE_MEMPALACE")
        .env_remove("AGENTIC_FORCE_INTERACTIVE")
        .env_remove("CONTEXT7_API_KEY");
    cmd
}

#[test]
fn version_output() {
    let home = tempfile::tempdir().unwrap();
    agentic(home.path())
        .arg("--version")
        .assert()
        .success()
        .stdout(predicate::str::starts_with("v"));
    agentic(home.path())
        .arg("version")
        .assert()
        .success()
        .stdout(predicate::str::contains(env!("CARGO_PKG_VERSION")));
}

#[test]
fn help_output() {
    let home = tempfile::tempdir().unwrap();
    agentic(home.path())
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("Agentic Installer"))
        .stdout(predicate::str::contains("self-install"));
}

#[test]
fn no_args_non_interactive_exits_1_with_usage() {
    let home = tempfile::tempdir().unwrap();
    agentic(home.path())
        .assert()
        .failure()
        .code(1)
        .stdout(predicate::str::contains("Usage:"));
}

#[test]
fn unknown_command_exits_1() {
    let home = tempfile::tempdir().unwrap();
    agentic(home.path()).arg("bogus").assert().failure().code(1);
}

#[test]
fn list_agentos_areas_specs() {
    let home = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["list", "agentos"])
        .assert()
        .success()
        .stdout(predicate::str::contains("opencode"))
        .stdout(predicate::str::contains("codex"))
        .stdout(predicate::str::contains("gemini"));
    agentic(home.path())
        .args(["list", "areas"])
        .assert()
        .success()
        .stdout(predicate::str::contains("software"))
        .stdout(predicate::str::contains("devops"))
        .stdout(predicate::str::contains("template").not());
    agentic(home.path())
        .args(["list", "specs", "--area", "software"])
        .assert()
        .success()
        .stdout(predicate::str::contains("backend"));
    agentic(home.path())
        .args(["list", "specs"])
        .assert()
        .failure()
        .code(1);
    agentic(home.path())
        .args(["list", "nothing"])
        .assert()
        .failure()
        .code(1);
}

#[test]
fn install_requires_args() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .assert()
        .failure()
        .code(1)
        .stderr(predicate::str::contains("--areas is required"));
    agentic(home.path())
        .args(["install", "--areas", "software"])
        .assert()
        .failure()
        .code(1)
        .stderr(predicate::str::contains("--project-dir is required"));
}

#[test]
fn install_validation_errors() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args(["--areas", "ghost", "--specializations", "ghost.x"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("unknown area 'ghost'"));
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args(["--areas", "software", "--specializations", "nodot"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("area.spec format"));
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--agent-os",
            "ghostos",
            "--areas",
            "software",
            "--specializations",
            "software.backend",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("unknown agent OS 'ghostos'"));
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args(["--theme", "neon"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("Invalid --theme value"));
}

#[test]
fn full_install_default_target() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--areas",
            "software",
            "--specializations",
            "software.backend",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("=== Installation report ==="));

    assert!(project.path().join("AGENTS.md").is_file());
    assert!(project.path().join("MEMORY.md").is_file());
    assert!(project.path().join(".agent/rules").is_dir());
    assert!(project.path().join(".agentic.json").is_file());

    let agents = std::fs::read_to_string(project.path().join("AGENTS.md")).unwrap();
    assert!(agents.contains("# Agentic Project Guidelines"));
    assert!(agents.starts_with("---\nagentic:\n"));

    let manifest: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".agentic.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(manifest["version"], 1);
    assert_eq!(manifest["settings"]["areas"][0], "software");
    assert_eq!(
        manifest["settings"]["specializations"][0],
        "software.backend"
    );
    assert!(manifest["managed_files"].as_array().unwrap().len() > 3);
}

#[test]
fn opencode_codex_install_layout() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--agent-os",
            "opencode,codex",
            "--areas",
            "software",
            "--specializations",
            "software.backend",
        ])
        .assert()
        .success();

    assert!(project.path().join(".opencode/rules").is_dir());
    assert!(project.path().join(".opencode/AGENTS.md").is_file());
    assert!(project.path().join(".opencode/MEMORY.md").is_file());
    assert!(project.path().join(".codex").is_dir());
    assert!(project.path().join("MEMORY.md").is_file());
    // codex memories feature enabled
    let toml = std::fs::read_to_string(project.path().join(".codex/config.toml")).unwrap();
    assert!(toml.contains("[features]\nmemories = true"));
    // opencode prompts are skipped, workflows land in commands
    assert!(!project.path().join(".opencode/prompts").exists());
}

#[test]
fn install_is_idempotent() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let run = || {
        agentic(home.path())
            .args(["install", "--project-dir"])
            .arg(project.path())
            .args([
                "--areas",
                "software",
                "--specializations",
                "software.backend",
            ])
            .assert()
            .success();
    };
    run();
    let manifest_before = std::fs::read_to_string(project.path().join(".agentic.json")).unwrap();
    let agents_before = std::fs::read_to_string(project.path().join("AGENTS.md")).unwrap();
    run();
    let manifest_after = std::fs::read_to_string(project.path().join(".agentic.json")).unwrap();
    let agents_after = std::fs::read_to_string(project.path().join("AGENTS.md")).unwrap();
    assert_eq!(manifest_before, manifest_after);
    assert_eq!(agents_before, agents_after);
}

#[test]
fn rerun_preserves_user_modified_files() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--areas",
            "software",
            "--specializations",
            "software.backend",
        ])
        .assert()
        .success();
    let agents_md = project.path().join("AGENTS.md");
    std::fs::write(&agents_md, "user content").unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--areas",
            "software",
            "--specializations",
            "software.backend",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Skipping user-modified managed file: AGENTS.md",
        ));
    assert_eq!(std::fs::read_to_string(&agents_md).unwrap(), "user content");
}

#[test]
fn replay_install_from_manifest() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--agent-os",
            "opencode",
            "--areas",
            "software",
            "--specializations",
            "software.backend",
        ])
        .assert()
        .success();
    // Replay without areas/specs: settings come from .agentic.json
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .assert()
        .success()
        .stdout(predicate::str::contains("Agent OS targets: opencode"));
}

#[test]
fn dry_run_writes_nothing() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--areas",
            "software",
            "--specializations",
            "software.backend",
            "--dry-run",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("DRY-RUN"));
    assert!(!project.path().join("AGENTS.md").exists());
    assert!(!project.path().join(".agentic.json").exists());
}

#[test]
fn mcp_env_selection_writes_configs() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--agent-os",
            "opencode,claude",
            "--areas",
            "software",
            "--specializations",
            "software.backend",
        ])
        .env("AGENTIC_ENABLE_MCPS", "playwright,anydb")
        .assert()
        .success();
    let opencode: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join("opencode.json")).unwrap(),
    )
    .unwrap();
    assert!(opencode["mcp"]["playwright"].is_object());
    assert!(opencode["mcp"]["anydb"].is_object());
    let claude: Value =
        serde_json::from_str(&std::fs::read_to_string(project.path().join(".mcp.json")).unwrap())
            .unwrap();
    assert_eq!(claude["mcpServers"]["playwright"]["command"], "npx");
    // manifest records selections
    let manifest: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".agentic.json")).unwrap(),
    )
    .unwrap();
    let mcps: Vec<String> = manifest["settings"]["mcp_integrations"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap().to_string())
        .collect();
    assert!(mcps.contains(&"playwright".to_string()));
    assert!(mcps.contains(&"anydb".to_string()));
}

#[test]
fn context7_env_enable_non_interactive() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--agent-os",
            "codex",
            "--areas",
            "software",
            "--specializations",
            "software.backend",
        ])
        .env("AGENTIC_ENABLE_CONTEXT7", "y")
        .env("CONTEXT7_API_KEY", "test-key")
        .assert()
        .success();
    let toml = std::fs::read_to_string(project.path().join(".codex/config.toml")).unwrap();
    assert!(toml.contains("[mcp_servers.context7]"));
    assert!(toml.contains("url = \"https://mcp.context7.com/mcp\""));
    assert!(toml.contains("CONTEXT7_API_KEY"));
    assert!(toml.contains("[sandbox_workspace_write]"));
}

#[test]
fn theme_option_saved_to_config() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--areas",
            "software",
            "--specializations",
            "software.backend",
            "--theme",
            "light",
        ])
        .assert()
        .success();
    let config = std::fs::read_to_string(home.path().join(".config/agentic/config")).unwrap();
    assert!(config.contains("theme=light"));
}

#[test]
fn self_install_and_force() {
    let home = tempfile::tempdir().unwrap();
    let bin_dir = home.path().join("bin");
    agentic(home.path())
        .args(["self-install", "--bin-dir"])
        .arg(&bin_dir)
        .assert()
        .success()
        .stdout(predicate::str::contains("=== Self-install report ==="));
    assert!(bin_dir.join("agentic").is_file());
    // second run without --force fails
    agentic(home.path())
        .args(["self-install", "--bin-dir"])
        .arg(&bin_dir)
        .assert()
        .failure()
        .code(1)
        .stderr(predicate::str::contains("Use --force to overwrite"));
    // --force succeeds
    agentic(home.path())
        .args(["self-install", "--force", "--bin-dir"])
        .arg(&bin_dir)
        .assert()
        .success();
    // installed binary works
    let mut installed = Command::new(bin_dir.join("agentic"));
    installed
        .env("HOME", home.path())
        .arg("--version")
        .assert()
        .success();
}

#[test]
fn tui_non_interactive_fails() {
    let home = tempfile::tempdir().unwrap();
    agentic(home.path())
        .arg("tui")
        .assert()
        .failure()
        .code(1)
        .stderr(predicate::str::contains("interactive terminal"));
}

#[test]
fn upgrade_dry_run() {
    let home = tempfile::tempdir().unwrap();
    let work = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["upgrade", "--dry-run"])
        .current_dir(work.path())
        .assert()
        .success()
        .stdout(predicate::str::contains("DRY-RUN"));
}

#[test]
fn kilocode_and_cursor_layout() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--agent-os",
            "kilocode,cursor",
            "--areas",
            "devops",
            "--specializations",
            "devops.sre",
        ])
        .assert()
        .success();
    assert!(project.path().join(".kilocode/rules").is_dir());
    assert!(project.path().join(".cursor/rules").is_dir());
    assert!(project.path().join(".agent/rules").is_dir());
}
