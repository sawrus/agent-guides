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
    assert!(project.path().join("REVIEW_PIPELINE.md").is_file());
    assert!(project.path().join(".agent/rules").is_dir());
    assert!(project.path().join(".agentic.json").is_file());

    let agents = std::fs::read_to_string(project.path().join("AGENTS.md")).unwrap();
    assert!(agents.contains("# Agentic Project Guidelines"));
    assert!(agents.starts_with("---\nagentic:\n"));

    let manifest: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".agentic.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(manifest["version"], 2);
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
    let review_before = std::fs::read_to_string(project.path().join("REVIEW_PIPELINE.md")).unwrap();
    run();
    let manifest_after = std::fs::read_to_string(project.path().join(".agentic.json")).unwrap();
    let agents_after = std::fs::read_to_string(project.path().join("AGENTS.md")).unwrap();
    assert_eq!(manifest_before, manifest_after);
    assert_eq!(agents_before, agents_after);
    assert_eq!(
        review_before,
        std::fs::read_to_string(project.path().join("REVIEW_PIPELINE.md")).unwrap()
    );
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
    let review_md = project.path().join("REVIEW_PIPELINE.md");
    std::fs::write(&review_md, "user review policy").unwrap();
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
    assert_eq!(
        std::fs::read_to_string(&review_md).unwrap(),
        "user review policy"
    );
}

#[test]
fn review_profiles_install_for_each_environment() {
    for environment in ["claude", "codex", "opencode", "gemini"] {
        let home = tempfile::tempdir().unwrap();
        let project = tempfile::tempdir().unwrap();
        agentic(home.path())
            .args(["install", "--project-dir"])
            .arg(project.path())
            .args([
                "--agent-os",
                environment,
                "--areas",
                "software",
                "--specializations",
                "software.backend",
            ])
            .assert()
            .success();
        for specialist in ["instruction_reviewer", "memory_curator"] {
            let extension = if environment == "codex" { "toml" } else { "md" };
            let path = project
                .path()
                .join(format!(".{environment}/agents/{specialist}.{extension}"));
            let profile = std::fs::read_to_string(path).unwrap();
            assert!(profile.contains("read-only"));
            assert!(profile.contains("500 words"));
        }
        let protocol = std::fs::read_to_string(project.path().join("REVIEW_PIPELINE.md")).unwrap();
        assert!(protocol.contains("summary.md"));
        let workflow =
            std::fs::read_to_string(project.path().join(".agent/workflows/develop-feature.md"))
                .unwrap();
        assert!(workflow.contains("## Post-task review"));
        assert!(workflow.contains("outside SDLC `roles`"));
    }
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
    assert!(!project.path().join("REVIEW_PIPELINE.md").exists());
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

// Internal sync exercises the project transaction without a GitHub network request.
fn sync_upgrade(
    project: &std::path::Path,
    home: &std::path::Path,
    force: bool,
) -> assert_cmd::Command {
    let mut cmd = assert_cmd::Command::cargo_bin("agentic").unwrap();
    cmd.args(["__sync-project", "--project-dir"])
        .arg(project)
        .env("HOME", home)
        .env("XDG_CONFIG_HOME", home.join(".config"))
        .env("AGENTIC_DOCTOR", "0")
        .env("AGENTIC_FORCE_INTERACTIVE", "1")
        .env_remove("AGENTIC_ENABLE_MCPS")
        .env_remove("AGENTIC_KB_DIR");
    if force {
        cmd.arg("--force");
    }
    cmd
}

fn install_upgrade_fixture(project: &std::path::Path, home: &std::path::Path, agents: &str) {
    let mut cmd = assert_cmd::Command::cargo_bin("agentic").unwrap();
    cmd.args(["install", "--project-dir"])
        .arg(project)
        .args([
            "--agent-os",
            agents,
            "--areas",
            "software",
            "--specializations",
            "software.general",
            "--no-doctor",
        ])
        .env("HOME", home)
        .env("XDG_CONFIG_HOME", home.join(".config"))
        .env("AGENTIC_ENABLE_CONTEXT7", "n")
        .env("AGENTIC_ENABLE_MEMPALACE", "n")
        .env_remove("AGENTIC_FORCE_INTERACTIVE")
        .env_remove("AGENTIC_ENABLE_MCPS")
        .assert()
        .success();
}

#[test]
fn smart_upgrade_merges_edits_and_is_idempotent() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    install_upgrade_fixture(project.path(), home.path(), "default");
    let path = project.path().join("AGENTS.md");
    let mut local = std::fs::read_to_string(&path).unwrap();
    local.push_str("\n## Project convention\nUse our local API.\n");
    std::fs::write(&path, local).unwrap();
    sync_upgrade(project.path(), home.path(), false)
        .assert()
        .success()
        .stdout(predicate::str::contains("Merged: AGENTS.md"));
    assert!(std::fs::read_to_string(&path)
        .unwrap()
        .contains("Use our local API."));
    let manifest = std::fs::read(project.path().join(".agentic.json")).unwrap();
    sync_upgrade(project.path(), home.path(), false)
        .assert()
        .success()
        .stdout(predicate::str::contains("already up to date"));
    assert_eq!(
        std::fs::read(project.path().join(".agentic.json")).unwrap(),
        manifest
    );
}

#[test]
fn force_replays_and_removes_only_agentic_artifacts() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    install_upgrade_fixture(project.path(), home.path(), "codex");
    let obsolete = project.path().join(".agent/obsolete.md");
    std::fs::write(
        &obsolete,
        std::fs::read(project.path().join("MEMORY.md")).unwrap(),
    )
    .unwrap();
    std::fs::write(
        project.path().join("AGENTS.md"),
        "customized managed instructions",
    )
    .unwrap();
    std::fs::write(project.path().join(".agent/custom.md"), "user owned").unwrap();
    let config = project.path().join(".codex/config.toml");
    std::fs::write(&config, "model = \"mine\"\n[features]\nmemories = false\nother = true\n[mcp_servers.custom]\ncommand = \"custom\"\n").unwrap();
    sync_upgrade(project.path(), home.path(), true)
        .assert()
        .success();
    assert!(!obsolete.exists());
    assert_eq!(
        std::fs::read_to_string(project.path().join(".agent/custom.md")).unwrap(),
        "user owned"
    );
    let config = std::fs::read_to_string(config).unwrap();
    assert!(config.contains("model = \"mine\""));
    assert!(config.contains("other = true"));
    assert!(config.contains("[mcp_servers.custom]"));
    assert!(config.contains("memories = true"));
    let manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(project.path().join(".agentic.json")).unwrap())
            .unwrap();
    assert_eq!(manifest["settings"]["agent_os"][0], "codex");
    assert!(project.path().join(".agentic-backups").is_dir());
}

#[test]
fn legacy_adoption_missing_base_and_user_owned_agents() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    install_upgrade_fixture(project.path(), home.path(), "default");
    let manifest_path = project.path().join(".agentic.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    manifest["version"] = serde_json::json!(1);
    let entries = manifest["managed_files"].as_array_mut().unwrap();
    entries.retain(|v| v["path"] != "MEMORY.md");
    for entry in entries {
        entry.as_object_mut().unwrap().remove("generated_hash");
    }
    std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
    std::fs::remove_dir_all(project.path().join(".agentic/baselines")).unwrap();
    std::fs::write(
        project.path().join("AGENTS.md"),
        "locally edited managed file",
    )
    .unwrap();
    sync_upgrade(project.path(), home.path(), false)
        .assert()
        .success()
        .stdout(predicate::str::contains("Replaced without baseline"));
    let updated: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    assert!(updated["managed_files"]
        .as_array()
        .unwrap()
        .iter()
        .any(|v| v["path"] == "MEMORY.md"));
    std::fs::remove_file(&manifest_path).unwrap();
    std::fs::write(
        project.path().join("AGENTS.md"),
        "entirely user instructions",
    )
    .unwrap();
    sync_upgrade(project.path(), home.path(), true)
        .assert()
        .success()
        .stdout(predicate::str::contains("manual integration required"));
    assert_eq!(
        std::fs::read_to_string(project.path().join("AGENTS.md")).unwrap(),
        "entirely user instructions"
    );
}

#[test]
fn force_defaults_and_dry_run_do_not_touch_project_or_home() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    sync_upgrade(project.path(), home.path(), true)
        .arg("--dry-run")
        .assert()
        .success()
        .stdout(predicate::str::contains("DRY-RUN Create: AGENTS.md"));
    assert_eq!(std::fs::read_dir(project.path()).unwrap().count(), 0);
    assert_eq!(std::fs::read_dir(home.path()).unwrap().count(), 0);
    sync_upgrade(project.path(), home.path(), true)
        .assert()
        .success();
    let manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(project.path().join(".agentic.json")).unwrap())
            .unwrap();
    assert_eq!(
        manifest["settings"]["specializations"][0],
        "software.general"
    );
    assert!(manifest["settings"]["mcp_integrations"]
        .as_array()
        .unwrap()
        .is_empty());
    assert_eq!(std::fs::read_dir(home.path()).unwrap().count(), 0);
}

#[test]
fn upgrade_rejects_escaping_manifest_before_writes() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    let bytes = br#"{"managed_files":[{"path":"../escaped.md"}]}"#;
    std::fs::write(project.path().join(".agentic.json"), bytes).unwrap();
    sync_upgrade(project.path(), home.path(), true)
        .assert()
        .failure()
        .stderr(predicate::str::contains("Unsafe project path"));
    assert_eq!(
        std::fs::read(project.path().join(".agentic.json")).unwrap(),
        bytes
    );
    assert!(!project.path().join(".agentic-backups").exists());
}

#[cfg(unix)]
#[test]
fn upgrade_rejects_symlink_targets() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    std::os::unix::fs::symlink(home.path(), project.path().join(".agent")).unwrap();
    sync_upgrade(project.path(), home.path(), true)
        .assert()
        .failure()
        .stderr(predicate::str::contains("Symlink project path"));
    assert_eq!(std::fs::read_dir(home.path()).unwrap().count(), 0);
}

#[test]
fn invalid_shared_json_aborts_before_project_changes() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    install_upgrade_fixture(project.path(), home.path(), "opencode");
    let manifest_path = project.path().join(".agentic.json");
    let mut data: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    data["settings"]["mcp_integrations"] = serde_json::json!(["playwright"]);
    std::fs::write(&manifest_path, serde_json::to_vec(&data).unwrap()).unwrap();
    std::fs::write(project.path().join("opencode.json"), "invalid json").unwrap();
    let before = std::fs::read(project.path().join("AGENTS.md")).unwrap();
    sync_upgrade(project.path(), home.path(), false)
        .assert()
        .failure()
        .stderr(predicate::str::contains("Invalid shared JSON"));
    assert_eq!(
        std::fs::read(project.path().join("AGENTS.md")).unwrap(),
        before
    );
    assert_eq!(
        std::fs::read_to_string(project.path().join("opencode.json")).unwrap(),
        "invalid json"
    );
    assert!(!project.path().join(".agentic-backups").exists());
}

#[test]
fn corrupt_manifest_force_uses_defaults_and_preserves_global_configuration() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    std::fs::write(project.path().join(".agentic.json"), "broken manifest").unwrap();
    let global_dir = home.path().join(".config/agentic");
    std::fs::create_dir_all(&global_dir).unwrap();
    let credentials = global_dir.join("config.json");
    std::fs::write(&credentials, "{\"private\":\"must remain unchanged\"}").unwrap();
    sync_upgrade(project.path(), home.path(), true)
        .assert()
        .success();
    let data: serde_json::Value =
        serde_json::from_slice(&std::fs::read(project.path().join(".agentic.json")).unwrap())
            .unwrap();
    assert_eq!(data["version"], 2);
    assert_eq!(data["settings"]["specializations"][0], "software.general");
    assert_eq!(
        std::fs::read_to_string(credentials).unwrap(),
        "{\"private\":\"must remain unchanged\"}"
    );
}

#[test]
fn public_upgrade_project_dir_force_dry_run_accepts_new_flags() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    let mut cmd = assert_cmd::Command::cargo_bin("agentic").unwrap();
    cmd.args(["upgrade", "--project-dir"])
        .arg(project.path())
        .args(["--force", "--dry-run"])
        .env("HOME", home.path())
        .env("AGENTIC_DOCTOR", "0")
        .assert()
        .success()
        .stdout(predicate::str::contains("DRY-RUN Create: AGENTS.md"));
    assert_eq!(std::fs::read_dir(project.path()).unwrap().count(), 0);
}

#[test]
fn force_preserves_unavailable_context7_key_and_updates_other_mcps() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    install_upgrade_fixture(project.path(), home.path(), "opencode");
    let manifest_path = project.path().join(".agentic.json");
    let mut data: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).unwrap()).unwrap();
    data["settings"]["mcp_integrations"] = serde_json::json!(["context7", "playwright"]);
    data["settings"]["context7"]["api_key_mode"] = serde_json::json!("api_key");
    data["managed_files"].as_array_mut().unwrap().push(serde_json::json!({"path":"opencode.json","marker":"config","source":"generated:mcp-config"}));
    std::fs::write(&manifest_path, serde_json::to_vec(&data).unwrap()).unwrap();
    std::fs::write(project.path().join("opencode.json"), r#"{"mcp":{"context7":{"type":"remote","url":"https://mcp.context7.com/mcp","headers":{"CONTEXT7_API_KEY":"preserve-me"}},"playwright":{"command":["old"]},"custom":{"command":["mine"]}}}"#).unwrap();
    sync_upgrade(project.path(), home.path(), true)
        .env_remove("CONTEXT7_API_KEY")
        .assert()
        .success();
    let result: serde_json::Value =
        serde_json::from_slice(&std::fs::read(project.path().join("opencode.json")).unwrap())
            .unwrap();
    assert_eq!(
        result["mcp"]["context7"]["headers"]["CONTEXT7_API_KEY"],
        "preserve-me"
    );
    assert_eq!(
        result["mcp"]["custom"]["command"],
        serde_json::json!(["mine"])
    );
    assert_eq!(
        result["mcp"]["playwright"]["command"],
        serde_json::json!(["npx", "-y", "@playwright/mcp@latest"])
    );
}
