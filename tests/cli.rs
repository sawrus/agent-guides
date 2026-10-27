//! Integration tests: run the real agentic binary end-to-end
//! (port of the bash tests/e2e suite).

use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::{json, Value};
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

/// Lean + JEV: JEV hooks and the quality gate sit on the lean layout; no role team, no forced delegation.
#[test]
fn lean_jev_keeps_native_layout_on_each_host() {
    let team = ["product-owner", "developer", "qa", "team-lead"];
    for (host, agents, suffix) in [
        ("codex", ".codex/agents", "toml"),
        ("claude", ".claude/agents", "md"),
        ("opencode", ".opencode/agents", "md"),
    ] {
        let home = tempfile::tempdir().unwrap();
        let project = tempfile::tempdir().unwrap();
        let p = project.path();
        agentic(home.path())
            .env_remove("AGENTIC_ENABLE_JEV")
            .env_remove("AGENTIC_PROFILE")
            .args(["install", "--project-dir"])
            .arg(p)
            .args([
                "--agent-os",
                host,
                "--areas",
                "software",
                "--specializations",
                "software.backend,software.general",
                "--no-doctor",
                "--enable-jev",
            ])
            .assert()
            .success();
        let manifest: Value =
            serde_json::from_str(&std::fs::read_to_string(p.join(".agentic.json")).unwrap())
                .unwrap();
        assert_eq!(manifest["settings"]["profile"], "lean", "{host}");
        assert_eq!(manifest["settings"]["jev"]["enabled"], true, "{host}");
        assert!(p.join(".agent/jev/hook.py").is_file(), "{host}");
        assert!(p.join(".agent/gate/gate.py").is_file(), "{host}");
        assert!(
            p.join(agents).join(format!("explorer.{suffix}")).is_file(),
            "{host} explorer"
        );
        // Round 6 (rule H4): `reviewer` left the lean default.
        assert!(
            !p.join(agents).join(format!("reviewer.{suffix}")).exists(),
            "{host} reviewer"
        );
        for role in team {
            assert!(
                !p.join(agents).join(format!("{role}.{suffix}")).exists(),
                "{host} {role}"
            );
        }
        match host {
            "codex" => {
                let hooks = std::fs::read_to_string(p.join(".codex/hooks.json")).unwrap();
                assert!(hooks.contains("UserPromptSubmit") && hooks.contains("gate.py"));
                assert!(!p.join(".codex/AGENTS.override.md").exists());
                assert!(!p.join("AGENTS.override.md").exists());
                // Lean keeps the Codex thread default and the helpers' reasoning effort; JEV routes the model.
                let config =
                    std::fs::read_to_string(p.join(".codex/config.toml")).unwrap_or_default();
                assert!(!config.contains("max_threads"));
                let explorer =
                    std::fs::read_to_string(p.join(".codex/agents/explorer.toml")).unwrap();
                assert!(explorer.contains("\nmodel_reasoning_effort = \"low\""));
                assert!(!explorer.contains("\nmodel ="));
            }
            "claude" => {
                let settings: Value = serde_json::from_str(
                    &std::fs::read_to_string(p.join(".claude/settings.json")).unwrap(),
                )
                .unwrap();
                assert!(
                    settings.get("agent").is_none(),
                    "lean keeps the native main session"
                );
                let text = settings.to_string();
                assert!(text.contains("--host claude") && text.contains("gate.py"));
                assert!(!frontmatter(&p.join(".claude/agents/explorer.md")).contains("model:"));
            }
            _ => {
                assert!(p.join(".opencode/plugins/agentic-jev/index.ts").is_file());
                assert!(p.join(".opencode/plugins/agentic-gate.ts").is_file());
            }
        }
    }
}

#[test]
fn jev_hooks_enable_provider_replay_and_explicit_disable() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let install = |args: &[&str]| {
        agentic(home.path())
            .env_remove("AGENTIC_ENABLE_JEV")
            .env_remove("AGENTIC_JEV_PROVIDER")
            .args(["install", "--project-dir"])
            .arg(project.path())
            .args([
                "--agent-os",
                "codex,claude,gemini,opencode,cursor,kilocode,antigravity",
                "--areas",
                "software",
                "--specializations",
                "software.backend",
                "--no-doctor",
            ])
            .args(args)
            .assert()
            .success();
    };
    install(&[
        "--profile",
        "team",
        "--enable-jev",
        "--jev-api-url",
        "https://api.typesafe.ai/v1/systemone",
    ]);
    assert!(project.path().join(".agent/jev/hook.py").is_file());
    assert!(project
        .path()
        .join(".opencode/plugins/agentic-jev/index.ts")
        .is_file());
    assert!(!project.path().join(".agent/skills/jev/SKILL.md").exists());
    let hooks = project.path().join(".codex/hooks.json");
    assert!(std::fs::read_to_string(&hooks)
        .unwrap()
        .contains("UserPromptSubmit"));
    let ignore = std::fs::read_to_string(project.path().join(".gitignore")).unwrap();
    assert!(ignore.contains(".agentic*/"));
    assert!(ignore.contains(".review*/"));
    let developer_profile = project.path().join(".codex/agents/developer.toml");
    let profile = std::fs::read_to_string(&developer_profile).unwrap();
    let codex_config = project.path().join(".codex/config.toml");
    assert!(std::fs::read_to_string(&codex_config)
        .unwrap()
        .contains("max_threads = 8"));
    assert!(!profile.contains("\nmodel ="));
    let defaults: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".agent/jev/model-defaults.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(defaults["version"], 2);
    assert_eq!(defaults["roles"]["developer"], "gpt-6.1-terra");
    assert_eq!(defaults["tiers"]["frontier"], "gpt-6-astra");
    for runtime in ["questions.py", "routing.py", "adapters.py"] {
        assert!(project.path().join(".agent/jev").join(runtime).is_file());
    }
    assert!(!project.path().join(".codex/model-tiers.json").exists());
    // OpenCode reads its tier map from `.agent/jev/` only; the default profile pins no role models (QR-D2).
    let opencode_tiers = project.path().join(".agent/jev/opencode-model-tiers.json");
    // Windows checkouts embed CRLF sources while the installer writes LF; compare content only.
    assert_eq!(
        std::fs::read_to_string(&opencode_tiers)
            .unwrap()
            .replace("\r\n", "\n"),
        include_str!("../extensions/opencode/model-tiers.json").replace("\r\n", "\n")
    );
    assert!(!project.path().join(".opencode/model-tiers.json").exists());
    let profile_defaults = project
        .path()
        .join(".agent/jev/opencode-profile-defaults.json");
    assert_eq!(std::fs::read_to_string(profile_defaults).unwrap(), "{}\n");
    assert!(!profile.contains("\nmodel_reasoning_effort ="));
    assert!(profile.contains("sandbox_mode = \"workspace-write\""));
    assert!(profile.contains("You are the Software Developer"));
    let manifest = || {
        serde_json::from_str::<Value>(
            &std::fs::read_to_string(project.path().join(".agentic.json")).unwrap(),
        )
        .unwrap()
    };
    assert_eq!(
        manifest()["settings"]["jev"],
        serde_json::json!({"enabled":true,"api_url":"https://api.typesafe.ai/v1/systemone"})
    );
    install(&[]);
    assert_eq!(
        manifest()["settings"]["jev"]["api_url"],
        "https://api.typesafe.ai/v1/systemone"
    );
    install(&["--disable-jev", "--enable-jev"]);
    assert!(!project
        .path()
        .join(".agent/jev/model-defaults.json")
        .exists());
    assert!(std::fs::read_to_string(&developer_profile)
        .unwrap()
        .contains("model = \"gpt-6.1-terra\""));
    let user_profile = std::fs::read_to_string(&developer_profile)
        .unwrap()
        .replace("gpt-6.1-terra", "user-pinned-model");
    std::fs::write(&developer_profile, &user_profile).unwrap();
    let limited = std::fs::read_to_string(&codex_config)
        .unwrap()
        .replace("[agents]", "[agents] # explicit user limit")
        .replace("max_threads = 8", "max_threads = 3");
    std::fs::write(&codex_config, limited).unwrap();
    install(&["--enable-jev"]);
    assert!(std::fs::read_to_string(&codex_config)
        .unwrap()
        .contains("max_threads = 3"));
    assert_eq!(
        std::fs::read_to_string(&developer_profile).unwrap(),
        user_profile
    );
    install(&["--disable-jev"]);
    assert_eq!(manifest()["settings"]["jev"]["enabled"], false);
    assert!(!opencode_tiers.exists());
    assert!(!manifest()["settings"]["mcp_integrations"]
        .as_array()
        .unwrap()
        .contains(&serde_json::json!("jev")));
    let root = std::fs::read_to_string(project.path().join("AGENTS.md")).unwrap();
    assert!(!root.contains("Optional JEV decisions"));
    let hooks: Value = serde_json::from_str(&std::fs::read_to_string(&hooks).unwrap()).unwrap();
    assert!(hooks["hooks"]
        .get("UserPromptSubmit")
        .and_then(Value::as_array)
        .is_none_or(|groups| groups.is_empty()));
    assert!(!project
        .path()
        .join(".opencode/plugins/agentic-jev/index.ts")
        .exists());
    let codex = std::fs::read_to_string(project.path().join(".codex/config.toml")).unwrap();
    assert!(!codex.contains("mcp_servers.jev"));
    agentic(home.path())
        .env("AGENTIC_ENABLE_JEV", "1")
        .env("JEV_API_URL", "https://example.test/decide")
        .args(["__sync-project", "--project-dir"])
        .arg(project.path())
        .assert()
        .success();
    assert_eq!(manifest()["settings"]["jev"]["enabled"], false);
    assert_eq!(
        manifest()["settings"]["jev"]["api_url"],
        "https://api.typesafe.ai/v1/systemone"
    );
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
    // lean leaves Codex memories off; its agents inherit the session model
    assert!(!project.path().join(".codex/config.toml").exists());
    assert!(!project.path().join(".codex/agents/reviewer.toml").exists());
    let toml = std::fs::read_to_string(project.path().join(".codex/agents/explorer.toml")).unwrap();
    assert!(!toml.contains("\nmodel = "), "explorer pins a model");
    assert!(toml.contains("model_reasoning_effort"));
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
                "--profile",
                "team",
            ])
            .assert()
            .success();
        for specialist in ["instruction-reviewer", "memory-curator"] {
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
            std::fs::read_to_string(project.path().join(".agent/workflows/add-migration.md"))
                .unwrap();
        // Role-neutral pack workflows carry no Post-task review hook (docs/review-pipeline.md).
        assert!(workflow.contains("**Done when:**"));
        assert!(!workflow.contains("## Post-task review"));
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
    assert!(config.contains("memories = false"));
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

#[test]
fn jev_native_hook_entries_preserve_foreign_handlers_through_upgrade_and_disable() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let install = |extra: &[&str]| {
        agentic(home.path())
            .env_remove("AGENTIC_ENABLE_JEV")
            .args(["install", "--project-dir"])
            .arg(project.path())
            .args([
                "--agent-os",
                "codex,opencode",
                "--areas",
                "software",
                "--specializations",
                "software.backend",
                "--no-doctor",
            ])
            .args(extra)
            .assert()
            .success();
    };
    install(&["--enable-jev"]);
    let hook_path = project.path().join(".codex/hooks.json");
    let mut hooks: Value =
        serde_json::from_str(&std::fs::read_to_string(&hook_path).unwrap()).unwrap();
    let foreign =
        serde_json::json!({"matcher":"*","hooks":[{"type":"command","command":"echo foreign"}]});
    hooks["hooks"]["UserPromptSubmit"]
        .as_array_mut()
        .unwrap()
        .push(foreign.clone());
    std::fs::write(&hook_path, serde_json::to_string_pretty(&hooks).unwrap()).unwrap();
    install(&["--enable-jev"]);
    agentic(home.path())
        .args(["__sync-project", "--project-dir"])
        .arg(project.path())
        .assert()
        .success();
    let hooks: Value = serde_json::from_str(&std::fs::read_to_string(&hook_path).unwrap()).unwrap();
    assert_eq!(
        hooks["hooks"]["UserPromptSubmit"].as_array().unwrap().len(),
        2
    );
    assert!(hooks["hooks"]["UserPromptSubmit"]
        .as_array()
        .unwrap()
        .contains(&foreign));
    install(&["--disable-jev"]);
    let hooks: Value = serde_json::from_str(&std::fs::read_to_string(&hook_path).unwrap()).unwrap();
    assert_eq!(
        hooks["hooks"]["UserPromptSubmit"],
        serde_json::json!([foreign])
    );
    let ignore = std::fs::read_to_string(project.path().join(".gitignore")).unwrap();
    assert_eq!(ignore.matches(".agentic*/").count(), 1);
    assert_eq!(ignore.matches(".review*/").count(), 1);
}

#[test]
fn jev_user_modified_hook_is_preserved_and_disable_is_persisted() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let install = |flag: &str| {
        agentic(home.path())
            .env_remove("AGENTIC_ENABLE_JEV")
            .args(["install", "--project-dir"])
            .arg(project.path())
            .args([
                "--agent-os",
                "codex",
                "--areas",
                "software",
                "--specializations",
                "software.backend",
                "--no-doctor",
                flag,
            ])
            .assert()
            .success();
    };
    install("--enable-jev");
    let path = project.path().join(".codex/hooks.json");
    let mut data: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    data["hooks"]["UserPromptSubmit"][0]["hooks"][0]["timeout"] = serde_json::json!(99);
    std::fs::write(&path, serde_json::to_string_pretty(&data).unwrap()).unwrap();
    install("--disable-jev");
    let data: Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    assert_eq!(
        data["hooks"]["UserPromptSubmit"][0]["hooks"][0]["timeout"],
        99
    );
    let manifest: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".agentic.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(manifest["settings"]["jev"]["enabled"], false);
    assert!(project.path().join(".agent/jev/hook.py").is_file());
}

fn claude_install(home: &Path, project: &Path, extra: &[&str]) {
    agentic(home)
        .env_remove("AGENTIC_ENABLE_JEV")
        .env_remove("AGENTIC_CLAUDE_PROFILE")
        .args(["install", "--project-dir"])
        .arg(project)
        .args([
            "--agent-os",
            "claude",
            "--areas",
            "software",
            "--specializations",
            "software.backend,software.general",
            "--no-doctor",
        ])
        .args(extra)
        .assert()
        .success();
}

fn frontmatter(path: &Path) -> String {
    let text = std::fs::read_to_string(path).unwrap();
    text.split("\n---").next().unwrap().to_string()
}

#[test]
fn claude_install_writes_native_layout() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let p = project.path();
    claude_install(home.path(), p, &[]);
    assert!(p.join(".claude/skills/api-design/SKILL.md").is_file());
    // Claude auto-loads `.claude/rules`; on-demand rules stay in `.agent/rules` only.
    assert!(p.join(".claude/rules/makefile-guide.md").is_file());
    assert!(!p.join(".claude/rules/git-workflow-guide.md").exists());
    assert!(p.join(".agent/rules/git-workflow-guide.md").is_file());
    // Lean profile: the explorer helper and the native main session.
    assert!(p.join(".claude/agents/explorer.md").is_file());
    assert!(!p.join(".claude/agents/reviewer.md").exists());
    assert!(!p.join(".claude/agents/product-owner.md").exists());
    let lean: Value =
        serde_json::from_str(&std::fs::read_to_string(p.join(".claude/settings.json")).unwrap())
            .unwrap();
    assert!(lean.get("agent").is_none());
    claude_install(home.path(), p, &["--profile", "team"]);
    assert!(p.join(".agent/workflows/develop-feature.md").is_file());
    assert!(!p.join(".claude/workflows").exists());
    let command = frontmatter(&p.join(".claude/commands/develop-feature.md"));
    assert!(command.contains("argument-hint: \"[feature_request] [acceptance_criteria]\""));
    assert!(!command.contains("trigger:"));
    assert!(!command.contains("roles:"));
    let claude_md = std::fs::read_to_string(p.join(".claude/CLAUDE.md")).unwrap();
    assert!(claude_md.contains("@../AGENTS.md"));
    for role in [
        "product-owner",
        "team-lead",
        "developer",
        "qa",
        "devops-engineer",
        "analyst",
        "pm",
        "instruction-reviewer",
        "memory-curator",
    ] {
        assert!(
            p.join(format!(".claude/agents/{role}.md")).is_file(),
            "{role}"
        );
    }
    assert!(!p.join(".claude/agents/designer.md").exists());
    assert!(!p.join(".claude/profiles").exists());
    // Default anthropic profile pins aliases; reviewers are read-only.
    let developer = frontmatter(&p.join(".claude/agents/developer.md"));
    assert!(developer.contains("\nmodel: sonnet"));
    let reviewer = frontmatter(&p.join(".claude/agents/instruction-reviewer.md"));
    assert!(reviewer.contains("\ntools: Read, Grep, Glob\n"));
    assert!(reviewer.contains("\nmodel: haiku"));
    let settings: Value =
        serde_json::from_str(&std::fs::read_to_string(p.join(".claude/settings.json")).unwrap())
            .unwrap();
    assert_eq!(settings["agent"], "product-owner");
    // The quality gate is on by default: one Stop, one PreToolUse, and one SessionStart group.
    let hooks = settings["hooks"].to_string();
    assert!(hooks.contains(".agent/gate/gate.py"));
    assert_eq!(settings["hooks"]["Stop"].as_array().unwrap().len(), 1);
    assert!(settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        .as_str()
        .unwrap()
        .contains("--event start"));
    assert!(p.join(".agent/gate/gate.py").is_file());
    let manifest: Value =
        serde_json::from_str(&std::fs::read_to_string(p.join(".agentic.json")).unwrap()).unwrap();
    assert_eq!(manifest["settings"]["claude_profile"], "anthropic");

    claude_install(
        home.path(),
        p,
        &["--profile", "team", "--claude-profile", "none"],
    );
    assert!(!frontmatter(&p.join(".claude/agents/developer.md")).contains("model:"));
}

#[test]
fn claude_jev_and_telegram_hooks_are_owned_and_removable() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let p = project.path();
    let settings_path = p.join(".claude/settings.json");
    std::fs::create_dir_all(p.join(".claude")).unwrap();
    let user_hook =
        serde_json::json!({"matcher":"","hooks":[{"type":"command","command":"echo user"}]});
    std::fs::write(
        &settings_path,
        serde_json::json!({"env":{"KEEP":"1"},"hooks":{"Stop":[user_hook.clone()]}}).to_string(),
    )
    .unwrap();
    claude_install(
        home.path(),
        p,
        &[
            "--profile",
            "team",
            "--enable-jev",
            "--enable-telegram",
            "--disable-gate",
        ],
    );
    let settings: Value =
        serde_json::from_str(&std::fs::read_to_string(&settings_path).unwrap()).unwrap();
    assert_eq!(settings["env"]["KEEP"], "1");
    let text = settings.to_string();
    assert!(text.contains(".agent/jev/hook.py\\\" --host claude"));
    assert!(text.contains("--event stop"));
    assert_eq!(settings["hooks"]["PreToolUse"][0]["matcher"], "Agent|Task");
    assert_eq!(settings["hooks"]["Stop"].as_array().unwrap().len(), 2);
    assert!(p.join(".agent/jev/hook.py").is_file());
    assert!(p.join(".agent/notify/telegram.py").is_file());
    assert!(p.join(".agent/notify/telegram_turn.py").is_file());
    // JEV leaves Claude models open for routing; the pool holds aliases.
    assert!(!frontmatter(&p.join(".claude/agents/developer.md")).contains("model:"));
    let defaults: Value = serde_json::from_str(
        &std::fs::read_to_string(p.join(".agent/jev/model-defaults.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(defaults["roles"]["developer"], "sonnet");
    assert_eq!(defaults["tiers"]["fast"], "haiku");
    assert!(p.join(".agent/jev/questions.py").is_file());
    let manifest: Value =
        serde_json::from_str(&std::fs::read_to_string(p.join(".agentic.json")).unwrap()).unwrap();
    assert_eq!(
        manifest["settings"]["notifications"]["telegram"]["enabled"],
        true
    );

    // Replay keeps both enabled; explicit disables remove only owned entries.
    claude_install(home.path(), p, &[]);
    assert!(std::fs::read_to_string(&settings_path)
        .unwrap()
        .contains("telegram.py"));
    claude_install(home.path(), p, &["--disable-jev", "--disable-telegram"]);
    assert!(!p.join(".agent/gate/gate.py").exists());
    let settings: Value =
        serde_json::from_str(&std::fs::read_to_string(&settings_path).unwrap()).unwrap();
    assert_eq!(settings["hooks"], serde_json::json!({"Stop":[user_hook]}));
    assert_eq!(settings["env"]["KEEP"], "1");
    assert!(!p.join(".agent/notify/telegram.py").exists());
    assert!(!p.join(".agent/notify/telegram_turn.py").exists());
}

#[test]
fn codex_telegram_hooks_share_hooks_file_with_jev() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .env_remove("AGENTIC_ENABLE_JEV")
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--agent-os",
            "codex",
            "--areas",
            "software",
            "--specializations",
            "software.backend",
            "--no-doctor",
            "--enable-jev",
            "--enable-telegram",
        ])
        .assert()
        .success();
    let hooks: Value = serde_json::from_str(
        &std::fs::read_to_string(project.path().join(".codex/hooks.json")).unwrap(),
    )
    .unwrap();
    assert!(hooks["hooks"]["Stop"][0]["hooks"][0]["command"]
        .as_str()
        .unwrap()
        .contains("telegram.py --host codex --event stop"));
    assert_eq!(
        hooks["hooks"]["PermissionRequest"]
            .as_array()
            .unwrap()
            .len(),
        2
    );
}

#[test]
fn upgrade_migrates_renamed_role_agents() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let p = project.path();
    claude_install(home.path(), p, &["--profile", "team"]);
    // Simulate a pre-1.4 install: legacy role files tracked by the manifest.
    let manifest_path = p.join(".agentic.json");
    let mut manifest: Value =
        serde_json::from_str(&std::fs::read_to_string(&manifest_path).unwrap()).unwrap();
    for (name, content) in [
        ("designer.md", "legacy designer\n"),
        ("memory_curator.md", "legacy curator\n"),
    ] {
        let path = p.join(".claude/agents").join(name);
        std::fs::write(&path, content).unwrap();
        let hash = format!("{:x}", sha2_digest(content.as_bytes()));
        manifest["managed_files"]
            .as_array_mut()
            .unwrap()
            .push(serde_json::json!({
                "path": format!(".claude/agents/{name}"),
                "source": format!("extensions/claude/agents/{name}"),
                "content_hash": hash,
                "marker": "internal",
            }));
    }
    std::fs::write(
        &manifest_path,
        serde_json::to_string_pretty(&manifest).unwrap(),
    )
    .unwrap();
    std::fs::write(p.join(".claude/agents/memory_curator.md"), "user edited\n").unwrap();
    agentic(home.path())
        .args(["__sync-project", "--project-dir"])
        .arg(p)
        .assert()
        .success();
    assert!(!p.join(".claude/agents/designer.md").exists());
    assert!(p.join(".claude/agents/analyst.md").is_file());
    assert_eq!(
        std::fs::read_to_string(p.join(".claude/agents/memory_curator.md")).unwrap(),
        "user edited\n"
    );
}

fn sha2_digest(bytes: &[u8]) -> impl std::fmt::LowerHex {
    use sha2::Digest;
    sha2::Sha256::digest(bytes)
}

fn install_host(home: &Path, project: &Path, host: &str, profile: &str) {
    agentic(home)
        .env_remove("AGENTIC_ENABLE_JEV")
        .env_remove("AGENTIC_PROFILE")
        .env_remove("AGENTIC_OPENCODE_PROFILE")
        .env_remove("AGENTIC_CLAUDE_PROFILE")
        .args(["install", "--project-dir"])
        .arg(project)
        .args([
            "--agent-os",
            host,
            "--areas",
            "software",
            "--specializations",
            "software.general",
            "--no-doctor",
            "--profile",
            profile,
        ])
        .assert()
        .success();
}

fn host_layout(host: &str) -> (&'static str, &'static str, &'static str) {
    match host {
        "codex" => (
            ".codex/agents",
            "toml",
            ".agents/skills/agentic-profile/SKILL.md",
        ),
        "claude" => (".claude/agents", "md", ".claude/commands/profile.md"),
        _ => (".opencode/agents", "md", ".opencode/commands/profile.md"),
    }
}

/// `agentic profile use` reinstalls through the upgrade path: team -> lean removes unmodified team roles,
/// keeps edited ones, and records the profile in `.agentic.json`.
#[test]
fn profile_use_switches_team_to_lean_on_each_host() {
    for host in ["codex", "claude", "opencode"] {
        let (agents, suffix, command) = host_layout(host);
        let home = tempfile::tempdir().unwrap();
        let project = tempfile::tempdir().unwrap();
        let p = project.path();
        install_host(home.path(), p, host, "lean");
        assert!(p.join(command).is_file(), "{host}: profile command");
        agentic(home.path())
            .env_remove("AGENTIC_PROFILE")
            .args(["profile", "use", "team", "--project"])
            .arg(p)
            .assert()
            .success()
            .stdout(predicate::str::contains("Restart the agent session"));
        let role = |name: &str| p.join(format!("{agents}/{name}.{suffix}"));
        assert!(role("developer").is_file(), "{host}");
        assert!(!role("explorer").exists(), "{host}");
        std::fs::write(role("qa"), "user edit\n").unwrap();
        agentic(home.path())
            .env_remove("AGENTIC_PROFILE")
            .args(["profile", "use", "lean", "--project"])
            .arg(p)
            .assert()
            .success();
        assert!(!role("developer").exists(), "{host}");
        assert!(!role("product-owner").exists(), "{host}");
        assert!(role("explorer").is_file(), "{host}");
        assert!(role("qa").is_file(), "{host}: edited role file stays");
        let manifest: Value =
            serde_json::from_str(&std::fs::read_to_string(p.join(".agentic.json")).unwrap())
                .unwrap();
        assert_eq!(manifest["settings"]["profile"], "lean");
        assert_eq!(manifest["settings"]["profile_ids"][host], "lean");
        // The built-in seeds now exist and stay user-owned.
        assert!(home
            .path()
            .join(format!(".config/agentic/{host}/profiles/team/profile.json"))
            .is_file());
    }
}

/// A lean project of an older release has the `reviewer` helper and an unedited lean seed with it. The upgrade
/// follows the new lean default: it removes the unchanged reviewer file and keeps an edited one.
#[test]
fn upgrade_removes_the_old_lean_reviewer_unless_edited() {
    for host in ["codex", "claude", "opencode"] {
        for edited in [false, true] {
            let (agents, suffix, _) = host_layout(host);
            let home = tempfile::tempdir().unwrap();
            let project = tempfile::tempdir().unwrap();
            let p = project.path();
            let profiles = home.path().join(format!(".config/agentic/{host}/profiles"));
            let old = profiles.join("old");
            std::fs::create_dir_all(&old).unwrap();
            std::fs::write(
                old.join("profile.json"),
                r#"{"name":"old","base":"lean","agents":["explorer","reviewer"],"models":null}"#,
            )
            .unwrap();
            install_host(home.path(), p, host, "old");
            let reviewer = p.join(format!("{agents}/reviewer.{suffix}"));
            assert!(reviewer.is_file(), "{host}");
            // Turn the install into an old lean one: the manifest names `lean` and the seed lists the reviewer.
            std::fs::remove_dir_all(&old).unwrap();
            std::fs::create_dir_all(profiles.join("lean")).unwrap();
            std::fs::write(
                profiles.join("lean/profile.json"),
                r#"{"name":"lean","base":"lean","agents":["explorer","reviewer"],"models":null}"#,
            )
            .unwrap();
            let manifest_path = p.join(".agentic.json");
            let mut manifest: Value =
                serde_json::from_str(&std::fs::read_to_string(&manifest_path).unwrap()).unwrap();
            manifest["settings"]["profile_ids"][host] = json!("lean");
            if let Some(settings) = manifest["settings"].as_object_mut() {
                settings.remove("profile_defs");
            }
            std::fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
            if edited {
                std::fs::write(&reviewer, "user edit\n").unwrap();
            }
            sync_upgrade(p, home.path(), false)
                .env_remove("AGENTIC_PROFILE")
                .env_remove("AGENTIC_ENABLE_JEV")
                .env_remove("AGENTIC_OPENCODE_PROFILE")
                .env_remove("AGENTIC_CLAUDE_PROFILE")
                .assert()
                .success();
            assert_eq!(reviewer.is_file(), edited, "{host} edited={edited}");
            assert!(
                p.join(format!("{agents}/explorer.{suffix}")).is_file(),
                "{host}"
            );
            if let Ok(config) = std::fs::read_to_string(p.join(".opencode/opencode.json")) {
                let data: Value = serde_json::from_str(&config).unwrap();
                assert!(data["agent"].get("reviewer").is_none(), "{host}");
            }
        }
    }
}

/// A custom profile in `~/.config/agentic/<host>/profiles/<id>/profile.json` installs only its agents.
#[test]
fn custom_profile_installs_only_listed_agents_on_each_host() {
    for host in ["codex", "claude", "opencode"] {
        let (agents, suffix, _) = host_layout(host);
        let home = tempfile::tempdir().unwrap();
        let project = tempfile::tempdir().unwrap();
        let p = project.path();
        let dir = home
            .path()
            .join(format!(".config/agentic/{host}/profiles/my"));
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join("profile.json"),
            r#"{"name":"my","base":"team","agents":["developer","qa"],"models":null}"#,
        )
        .unwrap();
        install_host(home.path(), p, host, "my");
        let mut installed: Vec<String> = std::fs::read_dir(p.join(agents))
            .unwrap()
            .map(|e| e.unwrap().file_name().to_string_lossy().to_string())
            .collect();
        installed.sort();
        assert_eq!(
            installed,
            [format!("developer.{suffix}"), format!("qa.{suffix}")],
            "{host}"
        );
        let manifest: Value =
            serde_json::from_str(&std::fs::read_to_string(p.join(".agentic.json")).unwrap())
                .unwrap();
        assert_eq!(manifest["settings"]["profile_ids"][host], "my");
        assert_eq!(manifest["settings"]["profile"], "team");
        assert_eq!(
            manifest["settings"]["profile_defs"][host]["agents"],
            json!(["developer", "qa"])
        );
        if let Ok(config) = std::fs::read_to_string(p.join(".opencode/opencode.json")) {
            let data: Value = serde_json::from_str(&config).unwrap();
            assert!(data["agent"].get("product-owner").is_none());
        }
        // Without the user file (a teammate's machine) a sync keeps the saved roles.
        std::fs::remove_dir_all(&dir).unwrap();
        agentic(home.path())
            .env_remove("AGENTIC_PROFILE")
            .args(["__sync-project", "--project-dir"])
            .arg(p)
            .assert()
            .success();
        let mut synced: Vec<String> = std::fs::read_dir(p.join(agents))
            .unwrap()
            .map(|e| e.unwrap().file_name().to_string_lossy().to_string())
            .collect();
        synced.sort();
        assert_eq!(synced, installed, "{host} after sync");
    }
    // Unknown profiles fail before any write.
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .env_remove("AGENTIC_PROFILE")
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--agent-os",
            "claude",
            "--areas",
            "software",
            "--specializations",
            "software.general",
            "--profile",
            "ghost",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("unknown claude profile 'ghost'"));
    assert_eq!(std::fs::read_dir(project.path()).unwrap().count(), 0);
}

#[test]
fn profile_cli_list_create_show() {
    let home = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["profile", "list", "--host", "codex"])
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "codex\tlean\tlean · explorer · native main session",
        ))
        .stdout(predicate::str::contains("codex\tteam\tteam · 9 roles"));
    agentic(home.path())
        .args(["profile", "create", "mine", "--from", "lean"])
        .assert()
        .success();
    agentic(home.path())
        .args(["profile", "show", "mine", "--host", "opencode"])
        .assert()
        .success()
        .stdout(predicate::str::contains("\"base\": \"lean\""));
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["profile", "use", "team", "--project"])
        .arg(project.path())
        .assert()
        .failure()
        .stderr(predicate::str::contains("run `agentic install` first"));
}

fn git_in(dir: &Path, args: &[&str]) {
    let out = std::process::Command::new("git")
        .arg("-C")
        .arg(dir)
        .args(["-c", "user.name=t", "-c", "user.email=t@localhost"])
        .args(["-c", "commit.gpgsign=false"])
        .args(args)
        .output()
        .unwrap();
    assert!(out.status.success(), "git {args:?}");
}

/// Field case: a clone checked out on a stale local `main` while origin's default branch is
/// `master`. Install and upgrade warn without blocking; the current default branch stays silent.
#[test]
fn install_and_upgrade_warn_about_a_stale_checkout() {
    let home = tempfile::tempdir().unwrap();
    let tmp = tempfile::tempdir().unwrap();
    let seed = tmp.path().join("seed");
    let origin = tmp.path().join("origin.git");
    let clone = tmp.path().join("clone");
    std::fs::create_dir_all(&seed).unwrap();
    git_in(&seed, &["init", "-q", "-b", "master"]);
    for i in 0..4 {
        git_in(
            &seed,
            &["commit", "-q", "--allow-empty", "-m", &format!("c{i}")],
        );
        if i == 0 {
            git_in(&seed, &["branch", "main"]);
        }
    }
    let path = |p: &Path| p.to_str().unwrap().to_string();
    git_in(
        tmp.path(),
        &["clone", "-q", "--bare", &path(&seed), &path(&origin)],
    );
    git_in(tmp.path(), &["clone", "-q", &path(&origin), &path(&clone)]);
    let expected = "Stale checkout: HEAD is on branch main, not on the origin default branch master; it has no \
                    own commits and is 3 commits behind origin/master, so the code here may be outdated. \
                    Run: git switch master && git pull";
    let install = || {
        let mut cmd = agentic(home.path());
        cmd.args(["install", "--project-dir"])
            .arg(&clone)
            .args(["--agent-os", "claude", "--areas", "software"])
            .args(["--specializations", "software.general", "--no-doctor"]);
        cmd
    };

    install()
        .assert()
        .success()
        .stdout(predicate::str::contains("Stale checkout").not());
    git_in(&clone, &["switch", "-q", "-c", "main", "origin/main"]);
    install()
        .assert()
        .success()
        .stdout(predicate::str::contains(format!(
            "[agentic][warn] {expected}"
        )));
    sync_upgrade(&clone, home.path(), false)
        .assert()
        .success()
        .stdout(predicate::str::contains(expected));
}

fn copy_tree(src: &Path, dst: &Path, skip: &dyn Fn(&Path) -> bool) {
    std::fs::create_dir_all(dst).unwrap();
    for entry in std::fs::read_dir(src).unwrap() {
        let entry = entry.unwrap();
        let path = entry.path();
        if skip(&path) {
            continue;
        }
        let target = dst.join(entry.file_name());
        if entry.file_type().unwrap().is_dir() {
            copy_tree(&path, &target, skip);
        } else {
            std::fs::copy(&path, &target).unwrap();
        }
    }
}

/// A knowledge base like the repository, without `software.full-stack` and `software.platform`
/// and without any `prompts/` directory (the content cleanup release).
fn cleanup_kb() -> tempfile::TempDir {
    let repo = Path::new(env!("CARGO_MANIFEST_DIR"));
    let kb = tempfile::tempdir().unwrap();
    for file in [
        "AGENTS.md",
        "MEMORY.md",
        "REVIEW_PIPELINE.md",
        "CHANGELOG.md",
    ] {
        std::fs::copy(repo.join(file), kb.path().join(file)).unwrap();
    }
    copy_tree(
        &repo.join("extensions"),
        &kb.path().join("extensions"),
        &|p| p.ends_with("__pycache__") || p.ends_with("node_modules"),
    );
    let removed = [
        repo.join("areas/software/full-stack"),
        repo.join("areas/software/platform"),
    ];
    copy_tree(&repo.join("areas"), &kb.path().join("areas"), &|p| {
        removed.iter().any(|r| r == p) || p.file_name().is_some_and(|n| n == "prompts")
    });
    kb
}

fn manifest_json(project: &Path) -> Value {
    serde_json::from_slice(&std::fs::read(project.join(".agentic.json")).unwrap()).unwrap()
}

fn strings(value: &Value) -> Vec<String> {
    value
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap().to_string())
        .collect()
}

#[test]
fn install_does_not_copy_prompts() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--agent-os",
            "codex,opencode",
            "--areas",
            "software",
            "--specializations",
            "software.backend",
            "--no-doctor",
        ])
        .assert()
        .success();
    assert!(project.path().join(".agent/workflows").is_dir());
    assert!(!project.path().join(".agent/prompts").exists());
    let manifest = manifest_json(project.path());
    assert!(!manifest["managed_files"]
        .as_array()
        .unwrap()
        .iter()
        .any(|v| v["path"].as_str().unwrap().contains("/prompts/")));
}

#[test]
fn upgrade_removes_previously_installed_prompts_as_obsolete() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    let p = project.path();
    install_upgrade_fixture(p, home.path(), "codex");
    // An older release copied prompt files into `.agent/prompts` and recorded them in the manifest.
    let prompts = p.join(".agent/prompts");
    std::fs::create_dir_all(&prompts).unwrap();
    let original = "---\nworkflow: develop\n---\n# Prompt: /develop\n";
    let mut manifest = manifest_json(p);
    for name in ["develop.md", "custom.md"] {
        std::fs::write(prompts.join(name), original).unwrap();
        manifest["managed_files"]
            .as_array_mut()
            .unwrap()
            .push(json!({
                "path": format!(".agent/prompts/{name}"),
                "source": format!("areas/software/general/prompts/{name}"),
                "content_hash": format!("{:x}", sha2_digest(original.as_bytes())),
                "marker": "internal",
            }));
    }
    std::fs::write(
        p.join(".agentic.json"),
        serde_json::to_vec(&manifest).unwrap(),
    )
    .unwrap();
    // The user edited one prompt after install: upgrade keeps it.
    std::fs::write(prompts.join("custom.md"), "my own prompt\n").unwrap();
    sync_upgrade(p, home.path(), false)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Removed obsolete artifact: .agent/prompts/develop.md",
        ))
        .stdout(predicate::str::contains(
            "Preserved customized obsolete artifact: .agent/prompts/custom.md",
        ));
    assert!(!prompts.join("develop.md").exists());
    assert_eq!(
        std::fs::read_to_string(prompts.join("custom.md")).unwrap(),
        "my own prompt\n"
    );
    let paths: Vec<String> = manifest_json(p)["managed_files"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v["path"].as_str().unwrap().to_string())
        .collect();
    assert!(!paths.contains(&".agent/prompts/develop.md".to_string()));
}

#[test]
fn install_maps_removed_specs_and_rejects_unknown_ones() {
    let kb = cleanup_kb();
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    agentic(home.path())
        .env("AGENTIC_KB_DIR", kb.path())
        .args(["install", "--project-dir"])
        .arg(project.path())
        .args([
            "--areas",
            "software",
            "--specializations",
            "software.full-stack,software.platform",
            "--no-doctor",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "specialization 'software.full-stack' was removed; installing software.backend, software.frontend, software.general instead",
        ))
        .stdout(predicate::str::contains(
            "specialization 'software.platform' was removed; installing devops.kubernetes, devops.infrastructure, devops.ci-cd instead",
        ));
    let settings = manifest_json(project.path())["settings"].clone();
    assert_eq!(
        strings(&settings["specializations"]),
        [
            "software.backend",
            "software.frontend",
            "software.general",
            "devops.kubernetes",
            "devops.infrastructure",
            "devops.ci-cd"
        ]
    );
    assert_eq!(strings(&settings["areas"]), ["software", "devops"]);
    assert!(project.path().join(".agent/rules").is_dir());

    let other = tempfile::tempdir().unwrap();
    agentic(home.path())
        .env("AGENTIC_KB_DIR", kb.path())
        .args(["install", "--project-dir"])
        .arg(other.path())
        .args([
            "--areas",
            "software",
            "--specializations",
            "software.ghost",
            "--no-doctor",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "unknown specialization(s): software.ghost. Available:",
        ))
        .stderr(predicate::str::contains("software.backend"));
    assert!(!other.path().join(".agentic.json").exists());
}

#[test]
fn upgrade_maps_removed_specs_from_manifest_and_rejects_unknown_ones() {
    let kb = cleanup_kb();
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    let p = project.path();
    install_upgrade_fixture(p, home.path(), "default");
    let mut manifest = manifest_json(p);
    manifest["settings"]["specializations"] = json!(["software.full-stack"]);
    std::fs::write(
        p.join(".agentic.json"),
        serde_json::to_vec(&manifest).unwrap(),
    )
    .unwrap();
    sync_upgrade(p, home.path(), false)
        .env("AGENTIC_KB_DIR", kb.path())
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "specialization 'software.full-stack' was removed",
        ));
    assert_eq!(
        strings(&manifest_json(p)["settings"]["specializations"]),
        ["software.backend", "software.frontend", "software.general"]
    );

    let mut manifest = manifest_json(p);
    manifest["settings"]["specializations"] = json!(["software.ghost"]);
    let bytes = serde_json::to_vec(&manifest).unwrap();
    std::fs::write(p.join(".agentic.json"), &bytes).unwrap();
    let agents = std::fs::read(p.join("AGENTS.md")).unwrap();
    sync_upgrade(p, home.path(), false)
        .env("AGENTIC_KB_DIR", kb.path())
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "unknown specialization(s): software.ghost",
        ));
    assert_eq!(std::fs::read(p.join(".agentic.json")).unwrap(), bytes);
    assert_eq!(std::fs::read(p.join("AGENTS.md")).unwrap(), agents);
}

#[test]
fn upgrade_without_manifest_stops_unless_forced() {
    let project = tempfile::tempdir().unwrap();
    let home = tempfile::tempdir().unwrap();
    let p = project.path();
    install_upgrade_fixture(p, home.path(), "codex");
    std::fs::remove_file(p.join(".agentic.json")).unwrap();
    let rules = std::fs::read_dir(p.join(".agent/rules")).unwrap().count();
    assert!(rules > 0);
    let agents = std::fs::read(p.join("AGENTS.md")).unwrap();
    sync_upgrade(p, home.path(), false)
        .assert()
        .failure()
        .stderr(predicate::str::contains("no .agentic.json"))
        .stderr(predicate::str::contains("agentic install"))
        .stderr(predicate::str::contains("--force"));
    assert!(!p.join(".agentic.json").exists());
    assert_eq!(std::fs::read(p.join("AGENTS.md")).unwrap(), agents);
    assert_eq!(
        std::fs::read_dir(p.join(".agent/rules")).unwrap().count(),
        rules
    );
    assert!(!p.join(".agentic-backups").exists());
    // `--force` keeps the old behaviour: rebuild with default settings.
    sync_upgrade(p, home.path(), true).assert().success();
    assert_eq!(
        strings(&manifest_json(p)["settings"]["specializations"]),
        ["software.general"]
    );
}

// --- company rules (docs/company-rules.md) --------------------------------------------------------------

fn company_install(home: &Path, project: &Path, extra: &[&str]) -> assert_cmd::assert::Assert {
    agentic(home)
        .env_remove("AGENTIC_ENABLE_JEV")
        .env_remove("AGENTIC_PROFILE")
        .args(["install", "--project-dir"])
        .arg(project)
        .args([
            "--agent-os",
            "claude",
            "--areas",
            "software",
            "--specializations",
            "software.backend",
            "--no-doctor",
        ])
        .args(extra)
        .assert()
        .success()
}

fn company_sync(project: &Path, home: &Path) -> assert_cmd::assert::Assert {
    sync_upgrade(project, home, false)
        .env("XDG_CACHE_HOME", home.join(".cache"))
        .assert()
        .success()
}

fn write(path: &Path, text: &str) {
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn git(dir: &Path, args: &[&str]) {
    let status = std::process::Command::new("git")
        .current_dir(dir)
        .args(["-c", "user.name=test", "-c", "user.email=test@example.com"])
        .args(args)
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .status()
        .unwrap();
    assert!(status.success(), "git {args:?}");
}

const API_RULE: &str = "---\npaths:\n  - \"src/**\"\nreplaces: [software/backend/api-contracts]\n---\n# API\n\n- Route every public endpoint through the company gateway.\n";

#[test]
fn company_rules_from_path_exclude_pack_rules_and_add_one_agents_line() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let p = project.path();
    write(&p.join("standards/software/api.md"), API_RULE);
    write(
        &p.join("standards/software/always.md"),
        "# Always\n\n- Write commit subjects in English.\n",
    );
    write(
        &p.join("standards/software/manual.md"),
        "---\ntrigger: manual\n---\n# Manual\n\n- Read the release runbook before a release.\n",
    );
    write(&p.join("standards/README.md"), "# Standards\n");
    company_install(
        home.path(),
        p,
        &[
            "--company-rules-path",
            "standards",
            "--company-rules-exclude",
            "software/backend/testing",
        ],
    )
    .stdout(predicate::str::contains(
        "Company rule .agent/company/software/always.md has no `paths:`",
    ));
    for rel in [
        "software/api.md",
        "software/always.md",
        "software/manual.md",
    ] {
        assert!(p.join(".agent/company").join(rel).is_file(), "{rel}");
    }
    assert!(!p.join(".agent/company/README.md").exists());
    assert!(p.join(".claude/rules/company-software-api.md").is_file());
    assert!(p.join(".claude/rules/company-software-always.md").is_file());
    assert!(!p.join(".claude/rules/company-software-manual.md").exists());
    // `replaces:` and `--company-rules-exclude` drop pack rules for every host.
    for dir in [".agent/rules", ".claude/rules"] {
        assert!(!p.join(dir).join("api-contracts.md").exists(), "{dir}");
        assert!(!p.join(dir).join("testing.md").exists(), "{dir}");
        assert!(p.join(dir).join("security.md").is_file(), "{dir}");
    }
    let agents = std::fs::read_to_string(p.join("AGENTS.md")).unwrap();
    assert_eq!(
        agents
            .matches("Company rules in `.agent/company/` override agent-guides rules on conflict.")
            .count(),
        1
    );
    let manifest = manifest_json(p);
    assert_eq!(
        manifest["settings"]["company_rules"],
        json!({"sources": [{"path": "standards"}], "exclude": ["software/backend/testing"]})
    );
    let item = manifest["managed_files"]
        .as_array()
        .unwrap()
        .iter()
        .find(|i| i["path"] == ".claude/rules/company-software-api.md")
        .unwrap()
        .clone();
    assert_eq!(item["marker"], "company");
    assert_eq!(item["source"], "company:standards/software/api.md");

    // Without company rules: no AGENTS.md line and no settings key.
    let plain = tempfile::tempdir().unwrap();
    company_install(home.path(), plain.path(), &[]);
    let agents = std::fs::read_to_string(plain.path().join("AGENTS.md")).unwrap();
    assert!(!agents.contains("Company rules"));
    assert!(manifest_json(plain.path())["settings"]
        .get("company_rules")
        .is_none());
    assert!(plain.path().join(".agent/rules/api-contracts.md").is_file());
}

#[test]
fn company_rules_in_place_and_user_files_are_preserved() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let p = project.path();
    let own = "---\npaths:\n  - \"src/**\"\n---\n# Own\n\n- Log every request id.\n";
    write(&p.join(".agent/company/software/own.md"), own);
    write(&p.join("standards/software/api.md"), API_RULE);
    company_install(
        home.path(),
        p,
        &[
            "--company-rules-path",
            ".agent/company",
            "--company-rules-path",
            "standards",
        ],
    );
    // In place: the file stays as the user wrote it; Claude Code gets a copy.
    assert_eq!(
        std::fs::read_to_string(p.join(".agent/company/software/own.md")).unwrap(),
        own
    );
    assert!(p.join(".claude/rules/company-software-own.md").is_file());
    assert!(p.join(".agent/company/software/api.md").is_file());

    // A user file next to the copies survives the upgrade and stays unmanaged.
    write(&p.join(".agent/company/notes.txt"), "user notes\n");
    company_sync(p, home.path());
    assert_eq!(
        std::fs::read_to_string(p.join(".agent/company/software/own.md")).unwrap(),
        own
    );
    assert!(p.join(".agent/company/notes.txt").is_file());
    let manifest = manifest_json(p);
    let paths: Vec<&str> = manifest["managed_files"]
        .as_array()
        .unwrap()
        .iter()
        .filter_map(|i| i["path"].as_str())
        .collect();
    assert!(!paths.contains(&".agent/company/software/own.md"));
    assert!(!paths.contains(&".agent/company/notes.txt"));
    assert!(paths.contains(&".agent/company/software/api.md"));
    assert!(!p.join(".agent/rules/api-contracts.md").exists());
}

#[test]
fn company_rules_from_git_replay_on_upgrade_and_fall_back_to_cache() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let repos = tempfile::tempdir().unwrap();
    let p = project.path();
    let work = repos.path().join("work");
    let bare = repos.path().join("standards.git");
    std::fs::create_dir_all(&work).unwrap();
    git(&work, &["init", "-q", "-b", "main"]);
    write(&work.join("rules/software/api.md"), API_RULE);
    write(&work.join("other/ignored.md"), "# Not in the subdir\n");
    git(&work, &["add", "-A"]);
    git(&work, &["commit", "-q", "-m", "one"]);
    git(
        repos.path(),
        &["clone", "-q", "--bare", "work", "standards.git"],
    );
    let url = format!("file://{}", bare.display());
    company_install(
        home.path(),
        p,
        &["--company-rules-git", &format!("{url}#main:rules")],
    );
    assert!(p.join(".agent/company/software/api.md").is_file());
    assert!(!p.join(".agent/company/other").exists());
    assert!(!p.join(".agent/rules/api-contracts.md").exists());
    assert_eq!(
        manifest_json(p)["settings"]["company_rules"]["sources"],
        json!([{"git": url, "ref": "main", "subdir": "rules"}])
    );
    let agents = std::fs::read_to_string(p.join("AGENTS.md")).unwrap();
    assert!(agents.contains("Company rules in `.agent/company/`"));

    // A new commit: upgrade replays the source from the manifest and picks it up.
    std::fs::remove_file(work.join("rules/software/api.md")).unwrap();
    write(
        &work.join("rules/software/sql.md"),
        "---\npaths:\n  - \"**/*.sql\"\n---\n# SQL\n\n- Name every migration after its ticket.\n",
    );
    git(&work, &["add", "-A"]);
    git(&work, &["commit", "-q", "-m", "two"]);
    git(&work, &["push", "-q", bare.to_str().unwrap(), "main"]);
    company_sync(p, home.path());
    assert!(p.join(".agent/company/software/sql.md").is_file());
    assert!(p.join(".claude/rules/company-software-sql.md").is_file());
    assert!(!p.join(".agent/company/software/api.md").exists());
    assert!(!p.join(".claude/rules/company-software-api.md").exists());
    // The replaced pack rule comes back once no company rule replaces it.
    assert!(p.join(".agent/rules/api-contracts.md").is_file());

    // Offline: the fetch fails, the cached copy is used, nothing is removed.
    std::fs::rename(&bare, repos.path().join("moved.git")).unwrap();
    company_sync(p, home.path()).stdout(predicate::str::contains("using the cached copy"));
    assert!(p.join(".agent/company/software/sql.md").is_file());
    // No cache either: the files that the source installed before stay.
    std::fs::remove_dir_all(home.path().join(".cache/agentic/company")).unwrap();
    company_sync(p, home.path()).stdout(predicate::str::contains("no cached copy exists"));
    assert!(p.join(".agent/company/software/sql.md").is_file());
    assert!(p.join(".claude/rules/company-software-sql.md").is_file());
}

#[test]
fn company_rules_report_duplicate_pack_rules() {
    let home = tempfile::tempdir().unwrap();
    let project = tempfile::tempdir().unwrap();
    let p = project.path();
    let pack = std::fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR")).join("areas/software/backend/rules/testing.md"),
    )
    .unwrap();
    write(&p.join("standards/software/testing.md"), &pack);
    company_install(home.path(), p, &["--company-rules-path", "standards"])
        .stdout(predicate::str::contains(
            "=== Company rules vs pack rules ===",
        ))
        .stdout(predicate::str::contains(
            "--company-rules-exclude software/backend/testing",
        ));
    // The suggestion applied: the pack rule is gone and the report is clean.
    company_install(
        home.path(),
        p,
        &["--company-rules-exclude", "software/backend/testing"],
    )
    .stdout(predicate::str::contains(
        "No company rule duplicates a pack rule.",
    ));
    assert!(!p.join(".agent/rules/testing.md").exists());
    assert_eq!(
        manifest_json(p)["settings"]["company_rules"]["sources"],
        json!([{"path": "standards"}])
    );
}
