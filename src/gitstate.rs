//! Stale-checkout warning. Reads local git refs only (no fetch, no network) and warns when the
//! checked-out code is older than the origin default branch, so the agent does not analyse
//! outdated code. The gate runtime (`gate.py --event start`) applies the same rule and text.
//!
//! Rule (`origin/<default>` comes from `refs/remotes/origin/HEAD`):
//! - HEAD is not on `<default>` (another branch or detached): warn when HEAD has no commits of its
//!   own (`ahead == 0`) and is behind `origin/<default>` (`behind >= 1`). HEAD is then a strict
//!   ancestor of the default branch; a feature branch with its own commits never warns.
//! - HEAD is on `<default>`: warn when it is behind `origin/<default>` by `STALE_BEHIND` or more.
//!
//! A directory outside git, a repository without `origin/HEAD`, or any git error gives no warning.

use std::path::Path;
use std::process::Command;

/// Commits behind `origin/<default>` before a checkout of the default branch counts as stale.
pub const STALE_BEHIND: u64 = 20;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitState {
    /// Current branch; `None` for a detached HEAD.
    pub branch: Option<String>,
    /// Origin default branch without the `origin/` prefix.
    pub default: String,
    pub ahead: u64,
    pub behind: u64,
}

fn git(project: &Path, args: &[&str]) -> Option<String> {
    let out = Command::new("git")
        .arg("-C")
        .arg(project)
        .args(args)
        .output()
        .ok()?;
    if !out.status.success() {
        return None;
    }
    Some(String::from_utf8_lossy(&out.stdout).trim().to_string())
}

/// Local repository state; `None` outside git or without `origin/HEAD`.
pub fn read(project: &Path) -> Option<GitState> {
    let head = git(project, &["rev-parse", "--abbrev-ref", "HEAD"])?;
    let origin_head = git(
        project,
        &["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
    )?;
    let default = origin_head.strip_prefix("origin/")?.to_string();
    if default.is_empty() {
        return None;
    }
    let counts = git(
        project,
        &[
            "rev-list",
            "--left-right",
            "--count",
            &format!("HEAD...origin/{default}"),
        ],
    )?;
    let mut parts = counts.split_whitespace().map(str::parse::<u64>);
    let ahead = parts.next()?.ok()?;
    let behind = parts.next()?.ok()?;
    Some(GitState {
        branch: (head != "HEAD").then_some(head),
        default,
        ahead,
        behind,
    })
}

fn commits(n: u64) -> String {
    if n == 1 {
        "1 commit".to_string()
    } else {
        format!("{n} commits")
    }
}

/// One-line warning, or `None` when the checkout is current enough.
pub fn warning(state: &GitState) -> Option<String> {
    let default = &state.default;
    let hint = format!("Run: git switch {default} && git pull");
    let behind = commits(state.behind);
    if state.branch.as_deref() == Some(default.as_str()) {
        if state.behind < STALE_BEHIND {
            return None;
        }
        return Some(format!(
            "Stale checkout: {default} is {behind} behind origin/{default} (local refs may be older still); \
             the code here may be outdated. {hint}"
        ));
    }
    if state.ahead > 0 || state.behind == 0 {
        return None;
    }
    let place = match &state.branch {
        Some(branch) => format!("branch {branch}"),
        None => "a detached HEAD".to_string(),
    };
    Some(format!(
        "Stale checkout: HEAD is on {place}, not on the origin default branch {default}; it has no own commits \
         and is {behind} behind origin/{default}, so the code here may be outdated. {hint}"
    ))
}

/// Warning for the project checkout, if any.
pub fn check(project: &Path) -> Option<String> {
    warning(&read(project)?)
}

/// Print the warning in install and upgrade output; never blocks.
pub fn report(app: &mut crate::app::App, project: &Path) {
    if let Some(message) = check(project) {
        crate::ui::warn(app, &message);
    }
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;

    pub(crate) fn run(dir: &Path, args: &[&str]) {
        let out = Command::new("git")
            .arg("-C")
            .arg(dir)
            .args([
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@localhost",
                "-c",
                "init.defaultBranch=master",
                "-c",
                "commit.gpgsign=false",
            ])
            .args(args)
            .output()
            .unwrap();
        assert!(
            out.status.success(),
            "git {args:?}: {}",
            String::from_utf8_lossy(&out.stderr)
        );
    }

    /// A clone of a bare origin whose default branch `master` has `upstream` commits; the clone
    /// also has a local `main` at the first commit. Returns (tempdir, clone path).
    pub(crate) fn stale_clone(upstream: usize) -> (tempfile::TempDir, std::path::PathBuf) {
        let tmp = tempfile::tempdir().unwrap();
        let seed = tmp.path().join("seed");
        let origin = tmp.path().join("origin.git");
        let clone = tmp.path().join("clone");
        std::fs::create_dir_all(&seed).unwrap();
        run(&seed, &["init", "-q", "-b", "master"]);
        for i in 0..upstream {
            run(
                &seed,
                &["commit", "-q", "--allow-empty", "-m", &format!("c{i}")],
            );
            if i == 0 {
                run(&seed, &["branch", "main"]);
            }
        }
        run(
            tmp.path(),
            &[
                "clone",
                "-q",
                "--bare",
                seed.to_str().unwrap(),
                origin.to_str().unwrap(),
            ],
        );
        run(
            tmp.path(),
            &[
                "clone",
                "-q",
                origin.to_str().unwrap(),
                clone.to_str().unwrap(),
            ],
        );
        run(&clone, &["branch", "main", "origin/main"]);
        (tmp, clone)
    }

    fn state(branch: Option<&str>, ahead: u64, behind: u64) -> GitState {
        GitState {
            branch: branch.map(str::to_string),
            default: "master".into(),
            ahead,
            behind,
        }
    }

    #[test]
    fn rule_covers_branch_kinds() {
        // Another long-lived branch that is a strict ancestor of origin/master.
        let text = warning(&state(Some("main"), 0, 281)).unwrap();
        assert_eq!(
            text,
            "Stale checkout: HEAD is on branch main, not on the origin default branch master; it has no own \
             commits and is 281 commits behind origin/master, so the code here may be outdated. \
             Run: git switch master && git pull"
        );
        assert!(warning(&state(None, 0, 1))
            .unwrap()
            .contains("a detached HEAD"));
        assert!(warning(&state(None, 0, 1)).unwrap().contains("1 commit "));
        // Feature branches with own commits, and current branches, stay silent.
        assert_eq!(warning(&state(Some("feat/x"), 2, 50)), None);
        assert_eq!(warning(&state(Some("main"), 0, 0)), None);
        // On the default branch only a large lag warns.
        assert_eq!(warning(&state(Some("master"), 0, STALE_BEHIND - 1)), None);
        let text = warning(&state(Some("master"), 0, STALE_BEHIND)).unwrap();
        assert!(text.starts_with("Stale checkout: master is 20 commits behind origin/master"));
        assert!(text.ends_with("Run: git switch master && git pull"));
    }

    #[test]
    fn reads_local_refs_of_a_clone() {
        let (_tmp, clone) = stale_clone(4);
        let fresh = read(&clone).unwrap();
        assert_eq!(fresh, state(Some("master"), 0, 0));
        assert_eq!(check(&clone), None);
        run(&clone, &["switch", "-q", "main"]);
        assert_eq!(read(&clone).unwrap(), state(Some("main"), 0, 3));
        assert!(check(&clone).unwrap().contains("branch main"));
        run(&clone, &["commit", "-q", "--allow-empty", "-m", "own"]);
        assert_eq!(check(&clone), None);
        run(&clone, &["switch", "-q", "--detach", "origin/master~1"]);
        assert!(check(&clone).unwrap().contains("a detached HEAD"));
    }

    #[test]
    fn default_branch_behind_threshold_warns() {
        let (_tmp, clone) = stale_clone(STALE_BEHIND as usize + 2);
        run(&clone, &["reset", "-q", "--hard", "origin/master~21"]);
        let text = check(&clone).unwrap();
        assert!(text.contains("master is 21 commits behind origin/master"));
    }

    #[test]
    fn non_git_and_no_origin_are_silent() {
        let tmp = tempfile::tempdir().unwrap();
        assert_eq!(read(tmp.path()), None);
        run(tmp.path(), &["init", "-q"]);
        run(tmp.path(), &["commit", "-q", "--allow-empty", "-m", "x"]);
        assert_eq!(read(tmp.path()), None);
    }

    /// The gate runtime (`gate.py --event start`) gives the same text as Rust for the same repo.
    #[test]
    fn gate_runtime_text_matches() {
        let runtime =
            Path::new(env!("CARGO_MANIFEST_DIR")).join("extensions/codex/hooks/gate/gate.py");
        let start = |clone: &Path| -> Option<String> {
            let out = Command::new(crate::hookmerge::python())
                .arg(&runtime)
                .args(["--event", "start", "--project-dir"])
                .arg(clone)
                .env("PYTHONDONTWRITEBYTECODE", "1")
                .output()
                .unwrap();
            assert!(out.status.success());
            let text = String::from_utf8_lossy(&out.stdout);
            if text.trim().is_empty() {
                return None;
            }
            let value: serde_json::Value = serde_json::from_str(&text).unwrap();
            assert_eq!(value["hookSpecificOutput"]["hookEventName"], "SessionStart");
            Some(
                value["hookSpecificOutput"]["additionalContext"]
                    .as_str()
                    .unwrap()
                    .to_string(),
            )
        };
        let (_tmp, clone) = stale_clone(STALE_BEHIND as usize + 2);
        assert_eq!(start(&clone), None);
        for target in ["main", "--detach origin/master~1"] {
            let mut args = vec!["switch", "-q"];
            args.extend(target.split(' '));
            run(&clone, &args);
            let rust = check(&clone);
            assert!(rust.is_some());
            assert_eq!(start(&clone), rust);
        }
        run(&clone, &["switch", "-q", "master"]);
        run(&clone, &["reset", "-q", "--hard", "origin/master~20"]);
        let rust = check(&clone);
        assert!(rust.is_some());
        assert_eq!(start(&clone), rust);
    }
}
