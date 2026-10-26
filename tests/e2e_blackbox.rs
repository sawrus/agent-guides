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
    // Doctor cleans `$TMPDIR/agentic-*`, so every test gets its own temp root.
    let tmp = home.join("tmp");
    std::fs::create_dir_all(&tmp).unwrap();
    cmd.env("HOME", home)
        .env("XDG_CONFIG_HOME", home.join(".config"))
        .env("XDG_DATA_HOME", home.join(".local/share"))
        .env("XDG_CACHE_HOME", home.join(".cache"))
        .env("XDG_STATE_HOME", home.join(".local/state"))
        .env("TMPDIR", &tmp)
        .env("PATH", path)
        .env_remove("CODEX_HOME")
        .env_remove("AGENTIC_DOCTOR_OPENCODE_MODEL")
        .env_remove("npm_config_cache")
        .env_remove("NPM_CONFIG_CACHE")
        .env_remove("CLAUDE_CONFIG_DIR")
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
fn doctor_cleans_stale_agentic_tmp_dirs_and_their_sessions() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();
    write_fake_bin(fake_bin.path(), "codex", "echo AGENTIC_DOCTOR_OK");
    let mut cmd = agentic(home.path(), fake_bin.path());

    let tmp = home.path().join("tmp").canonicalize().unwrap();
    let stale = tmp.join("agentic-doctor.old/claude");
    std::fs::create_dir_all(&stale).unwrap();
    std::fs::write(tmp.join("agentic-20261026-120000.log"), "run log").unwrap();
    let encoded: String = stale
        .to_string_lossy()
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '-' })
        .collect();
    let claude_project = home.path().join(".claude/projects").join(encoded);
    std::fs::create_dir_all(&claude_project).unwrap();
    std::fs::write(claude_project.join("s1.jsonl"), "{}").unwrap();
    let other_project = home.path().join(".claude/projects/-home-u-repo");
    std::fs::create_dir_all(&other_project).unwrap();

    install_args(&mut cmd, project.path(), "codex")
        .env("AGENTIC_DOCTOR", "1")
        .env("AGENTIC_DOCTOR_TIMEOUT_SECONDS", "5")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "claude projects 1, temp directories 1",
        ));

    assert!(!tmp.join("agentic-doctor.old").exists());
    assert!(tmp.join("agentic-20261026-120000.log").exists());
    assert!(!claude_project.exists());
    assert!(other_project.exists());
}

#[cfg(target_os = "linux")]
#[test]
fn doctor_stops_processes_left_by_the_agent() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();
    let pid_file = home.path().join("child.pid");
    write_fake_bin(
        fake_bin.path(),
        "codex",
        &format!(
            "sleep 300 >/dev/null 2>&1 &\necho $! > {}\necho AGENTIC_DOCTOR_OK",
            pid_file.display()
        ),
    );

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "codex")
        .env("AGENTIC_DOCTOR", "1")
        .env("AGENTIC_DOCTOR_TIMEOUT_SECONDS", "5")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "✅ codex: lightweight smoke passed",
        ))
        .stdout(predicate::str::contains(
            "Doctor stopped 1 leftover process(es) in the temp root",
        ));

    let pid = std::fs::read_to_string(&pid_file).unwrap();
    let stat = std::fs::read_to_string(format!("/proc/{}/stat", pid.trim())).unwrap_or_default();
    // A killed child of an exited parent is reaped by init; a zombie (state Z) also counts as stopped.
    assert!(
        stat.is_empty() || stat.contains(") Z "),
        "child still running: {stat}"
    );
}

#[test]
fn opencode_doctor_uses_the_recent_model() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let fake_bin = tempfile::tempdir().unwrap();
    let args_file = home.path().join("opencode.args");
    write_fake_bin(
        fake_bin.path(),
        "opencode",
        &format!(
            "echo \"$* fetch=$OPENCODE_DISABLE_MODELS_FETCH watch=$OPENCODE_DISABLE_FILEWATCHER npm=$npm_config_cache\" > {}\necho AGENTIC_DOCTOR_OK",
            args_file.display()
        ),
    );
    let state = home.path().join(".local/state/opencode");
    std::fs::create_dir_all(&state).unwrap();
    std::fs::write(
        state.join("model.json"),
        r#"{"recent":[{"providerID":"openai","modelID":"gpt-x"}]}"#,
    )
    .unwrap();
    let cache = home.path().join(".cache/opencode");
    std::fs::create_dir_all(&cache).unwrap();
    std::fs::write(cache.join("models.json"), "{}").unwrap();

    let mut cmd = agentic(home.path(), fake_bin.path());
    install_args(&mut cmd, project.path(), "opencode")
        .env("AGENTIC_DOCTOR", "1")
        .env("AGENTIC_DOCTOR_TIMEOUT_SECONDS", "5")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "✅ opencode: lightweight smoke passed",
        ));

    let args = std::fs::read_to_string(&args_file).unwrap();
    assert!(
        args.contains("--model openai/gpt-x Reply with exactly"),
        "{args}"
    );
    assert!(args.contains("fetch=1 watch=1"), "{args}");
    assert!(
        args.contains(&format!("npm={}", home.path().join(".npm").display())),
        "{args}"
    );
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
            "Applied OpenCode profile: models: GitHub Copilot (githubcopilot) · role→model",
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

#[test]
fn upgraded_standalone_process_replaces_old_payload_with_embedded_instructions() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    let old_payload = tempfile::tempdir().unwrap();
    let standalone = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(old_payload.path().join("areas/software/general")).unwrap();
    std::fs::create_dir_all(old_payload.path().join("extensions")).unwrap();
    for name in ["AGENTS.md", "MEMORY.md", "REVIEW_PIPELINE.md"] {
        std::fs::write(old_payload.path().join(name), "# Old payload sentinel\n").unwrap();
    }
    std::fs::write(
        old_payload.path().join("areas/software/general/AGENTS.md"),
        "# Old specialization\n",
    )
    .unwrap();
    assert_cmd::Command::cargo_bin("agentic")
        .unwrap()
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--areas",
            "software",
            "--specializations",
            "software.general",
            "--no-doctor",
        ])
        .env("HOME", home.path())
        .env("AGENTIC_KB_DIR", old_payload.path())
        .env_remove("AGENTIC_FORCE_INTERACTIVE")
        .assert()
        .success();
    assert!(std::fs::read_to_string(project.path().join("AGENTS.md"))
        .unwrap()
        .contains("Old payload sentinel"));
    let executable = standalone.path().join(if cfg!(windows) {
        "agentic.exe"
    } else {
        "agentic"
    });
    std::fs::copy(env!("CARGO_BIN_EXE_agentic"), &executable).unwrap();
    assert_cmd::Command::new(&executable)
        .args(["__sync-project", "--project-dir"])
        .arg(project.path())
        .env("HOME", home.path())
        .env("AGENTIC_UPGRADED_PROCESS", "1")
        .env("AGENTIC_DOCTOR", "0")
        .env_remove("AGENTIC_KB_DIR")
        .assert()
        .success()
        .stdout(predicate::str::contains(format!(
            "embedded:v{}",
            env!("CARGO_PKG_VERSION")
        )));
    let upgraded = std::fs::read_to_string(project.path().join("AGENTS.md")).unwrap();
    assert!(!upgraded.contains("Old payload sentinel"));
    assert!(upgraded.contains("Load on demand"));
}
