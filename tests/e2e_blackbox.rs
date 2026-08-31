//! Real-run blackbox e2e tests: exercise the agentic binary with fake agent
//! binaries on PATH (doctor smoke checks, MemPalace setup, upgrade re-sync).

#![cfg(unix)]

use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::Value;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

fn write_fake_bin(dir: &Path, name: &str, script: &str) {
    let path = dir.join(name);
    std::fs::write(&path, format!("#!/bin/sh\n{script}\n")).unwrap();
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).unwrap();
}

fn agentic(home: &Path, fake_bin: &Path) -> Command {
    let mut cmd = Command::cargo_bin("agentic").unwrap();
    let path = format!("{}:/usr/bin:/bin", fake_bin.display());
    cmd.env("HOME", home)
        .env("XDG_CONFIG_HOME", home.join(".config"))
        .env("XDG_DATA_HOME", home.join(".local/share"))
        .env("XDG_CACHE_HOME", home.join(".cache"))
        .env("PATH", path)
        .env_remove("AGENTIC_ENABLE_MCPS")
        .env_remove("AGENTIC_ENABLE_CONTEXT7")
        .env_remove("AGENTIC_ENABLE_MEMPALACE")
        .env_remove("CONTEXT7_API_KEY");
    cmd
}

fn install_args<'a>(cmd: &'a mut Command, project: &Path, agent_os: &str) -> &'a mut Command {
    cmd.args(["install", "--project-dir"]).arg(project).args([
        "--agent-os",
        agent_os,
        "--areas",
        "software",
        "--specializations",
        "software.backend",
    ])
}

#[test]
fn doctor_passes_with_healthy_fake_codex() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();
    write_fake_bin(fake_bin.path(), "codex", "echo AGENTIC_DOCTOR_OK");

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "codex")
        .env("AGENTIC_DOCTOR", "1")
        .env("AGENTIC_DOCTOR_TIMEOUT_SECONDS", "5")
        .assert()
        .success()
        .stdout(predicate::str::contains("=== Agentic doctor ==="))
        .stdout(predicate::str::contains(
            "✅ codex: lightweight smoke passed",
        ))
        .stdout(predicate::str::contains(
            "Agentic doctor completed successfully",
        ));
}

#[test]
fn doctor_reports_timeout_failure_and_fatal_output() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();
    // gemini times out, claude exits non-zero, opencode reports MCP failure
    write_fake_bin(fake_bin.path(), "gemini", "sleep 30");
    write_fake_bin(fake_bin.path(), "claude", "echo boom; exit 3");
    write_fake_bin(
        fake_bin.path(),
        "opencode",
        "echo 'MCP server startup failed'",
    );

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "opencode,claude,gemini")
        .env("AGENTIC_DOCTOR", "1")
        .env("AGENTIC_DOCTOR_TIMEOUT_SECONDS", "1")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "❌ gemini: lightweight smoke timed out after 1s",
        ))
        .stdout(predicate::str::contains(
            "❌ claude: lightweight smoke failed (exit 3",
        ))
        .stdout(predicate::str::contains(
            "❌ opencode: lightweight smoke reported integration errors",
        ))
        .stdout(predicate::str::contains("Doctor temp root kept:"))
        .stdout(predicate::str::contains(
            "Agentic doctor completed with 3 failing check(s)",
        ));
}

#[test]
fn doctor_reports_missing_binary() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "codex")
        .env("AGENTIC_DOCTOR", "1")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "❌ codex: binary 'codex' is not installed",
        ))
        .stdout(predicate::str::contains(
            "=== Agent binary setup recommendations ===",
        ))
        .stdout(predicate::str::contains("https://github.com/openai/codex"));
}

#[test]
fn mempalace_setup_with_fake_binaries() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();
    write_fake_bin(fake_bin.path(), "python3", "echo Python 3.12.0");
    write_fake_bin(fake_bin.path(), "mempalace", "echo ok");
    write_fake_bin(fake_bin.path(), "mempalace-mcp", "echo ok");

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "opencode,codex")
        .env("AGENTIC_DOCTOR", "0")
        .env("AGENTIC_ENABLE_MEMPALACE", "y")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "MemPalace binaries already available",
        ))
        .stdout(predicate::str::contains("MemPalace init completed"))
        .stdout(predicate::str::contains(
            "MemPalace mine project wing completed",
        ))
        .stdout(predicate::str::contains(
            "MemPalace MCP binary found: mempalace-mcp",
        ));

    // ignore file + configs
    assert!(project.path().join(".mempalaceignore").is_file());
    let opencode: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join("opencode.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(opencode["mcp"]["mempalace"]["command"][0], "mempalace-mcp");
    let toml = std::fs::read_to_string(project.path().join(".codex/config.toml")).unwrap();
    assert!(toml.contains("[mcp_servers.mempalace]"));
    // manifest carries the selection
    let manifest: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".agentic.json")).unwrap(),
    )
    .unwrap();
    assert!(manifest["settings"]["mcp_integrations"]
        .as_array()
        .unwrap()
        .iter()
        .any(|v| v == "mempalace"));
}

#[test]
fn mempalace_init_timeout_prints_manual_instructions() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();
    write_fake_bin(fake_bin.path(), "python3", "echo Python 3.12.0");
    write_fake_bin(fake_bin.path(), "mempalace", "sleep 30");
    write_fake_bin(fake_bin.path(), "mempalace-mcp", "echo ok");

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "claude")
        .env("AGENTIC_DOCTOR", "0")
        .env("AGENTIC_ENABLE_MEMPALACE", "y")
        .env("AGENTIC_MEMPALACE_TIMEOUT_SECONDS", "1")
        .assert()
        .success()
        .stdout(predicate::str::contains("Timed out after 1s"))
        .stdout(predicate::str::contains("pip install mempalace"));
    // configs still written even after failed init
    let claude: Value =
        serde_json::from_str(&std::fs::read_to_string(project.path().join(".mcp.json")).unwrap())
            .unwrap();
    assert_eq!(
        claude["mcpServers"]["mempalace"]["command"],
        "mempalace-mcp"
    );
}

#[test]
fn mempalace_setup_skip_env() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();
    write_fake_bin(fake_bin.path(), "mempalace-mcp", "echo ok");

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "cursor")
        .env("AGENTIC_DOCTOR", "0")
        .env("AGENTIC_ENABLE_MEMPALACE", "y")
        .env("AGENTIC_MEMPALACE_SETUP", "skip")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "skipped by AGENTIC_MEMPALACE_SETUP=skip",
        ));
    let cursor: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".cursor/mcp.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(
        cursor["mcpServers"]["mempalace"]["command"],
        "mempalace-mcp"
    );
}

#[test]
fn kubernetes_mcp_warns_without_kubectl() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "opencode")
        .env("AGENTIC_DOCTOR", "0")
        .env("AGENTIC_ENABLE_MCPS", "kubernetes")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Kubernetes MCP selected, but 'kubectl version'",
        ));
}

#[test]
fn upgrade_resyncs_managed_project() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "opencode")
        .env("AGENTIC_DOCTOR", "0")
        .assert()
        .success();

    // upgrade --dry-run from inside the managed project replays settings
    agentic(home.path(), fake_bin.path())
        .args(["upgrade", "--dry-run"])
        .current_dir(project.path())
        .env("AGENTIC_DOCTOR", "0")
        .assert()
        .success()
        .stdout(predicate::str::contains("Detected managed project"))
        .stdout(predicate::str::contains("Agent OS targets: opencode"));
}

#[test]
fn telegram_plugin_replay_from_manifest() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();

    // First install non-interactively: plugins default to disabled
    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "opencode")
        .env("AGENTIC_DOCTOR", "0")
        .assert()
        .success();
    let plugin_config = home.path().join(".config/agentic/opencode-plugins.json");
    let data: Value =
        serde_json::from_str(&std::fs::read_to_string(&plugin_config).unwrap()).unwrap();
    assert_eq!(data["telegram"]["enabled"], false);
    assert_eq!(data["agentModelMapper"]["enabled"], false);

    // Seed manifest with enabled telegram and replay: credentials go global
    let manifest_path = project.path().join(".agentic.json");
    let mut manifest: Value =
        serde_json::from_str(&std::fs::read_to_string(&manifest_path).unwrap()).unwrap();
    manifest["settings"]["opencode_plugins"] = serde_json::json!({
        "telegram": {"enabled": true, "botToken": "tok", "chatId": "chat"},
        "agentModelMapper": {"enabled": false},
    });
    std::fs::write(
        &manifest_path,
        serde_json::to_string_pretty(&manifest).unwrap(),
    )
    .unwrap();

    agentic(home.path(), fake_bin.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .env("AGENTIC_DOCTOR", "0")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "OpenCode plugin settings loaded from .agentic.json",
        ));
    let global: Value = serde_json::from_str(
        &std::fs::read_to_string(home.path().join(".config/agentic/config.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(global["opencode"]["plugins"]["telegram"]["botToken"], "tok");
}

#[test]
fn opencode_profile_env_applied() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "opencode")
        .env("AGENTIC_DOCTOR", "0")
        .env("AGENTIC_OPENCODE_PROFILE", "githubcopilot")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Applied OpenCode profile: GitHub Copilot Model Profile",
        ));
    let config: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".opencode/opencode.json")).unwrap(),
    )
    .unwrap();
    assert!(
        config.get("model").is_some()
            || config.get("provider").is_some()
            || config.get("agent").is_some()
    );
    let manifest: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".agentic.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(manifest["settings"]["opencode_profile"], "githubcopilot");
}

#[test]
fn unknown_opencode_profile_warns() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "opencode")
        .env("AGENTIC_DOCTOR", "0")
        .env("AGENTIC_OPENCODE_PROFILE", "ghost-profile")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Ignoring unknown OpenCode profile 'ghost-profile'",
        ));
}

#[test]
fn generated_markers_and_manifest_hashes_consistent() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "default")
        .env("AGENTIC_DOCTOR", "0")
        .assert()
        .success();
    let manifest: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".agentic.json")).unwrap(),
    )
    .unwrap();
    // every managed file exists and its recorded hash matches its content
    for item in manifest["managed_files"].as_array().unwrap() {
        let rel = item["path"].as_str().unwrap();
        let expected = item["content_hash"].as_str().unwrap();
        let full = project.path().join(rel);
        assert!(full.is_file(), "missing managed file {rel}");
        let bytes = std::fs::read(&full).unwrap();
        let mut hasher = <sha2::Sha256 as sha2::Digest>::new();
        sha2::Digest::update(&mut hasher, &bytes);
        let digest = format!("{:x}", sha2::Digest::finalize(hasher));
        assert_eq!(digest, expected, "hash mismatch for {rel}");
    }
    // markdown payloads carry the frontmatter marker
    let rules_dir = project.path().join(".agent/rules");
    let some_rule: PathBuf = std::fs::read_dir(&rules_dir)
        .unwrap()
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .find(|p| p.extension().map(|e| e == "md").unwrap_or(false))
        .unwrap();
    let content = std::fs::read_to_string(&some_rule).unwrap();
    assert!(content.contains("agentic:"));
    assert!(content.contains("generated_by: agentic"));
}
