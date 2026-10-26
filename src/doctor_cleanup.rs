//! Cleanup of leftover `agentic-*` temp directories before a doctor run.
//!
//! Agents remember every directory they ran in, so the temp directory is not removed alone: first each agent
//! forgets its sessions there (Codex threads, OpenCode sessions, Claude Code project transcripts).

use crate::app::App;
use crate::mempalace::run_with_timeout;
use crate::ui;
use rusqlite::{Connection, OpenFlags};
use std::path::{Component, Path, PathBuf};
use std::process::Command;
use std::time::Duration;

const TMP_DIR_PREFIX: &str = "agentic-";
const SESSION_DELETE_TIMEOUT: Duration = Duration::from_secs(30);

/// Decides which paths belong to leftover agentic temp directories.
pub struct TmpScope {
    roots: Vec<PathBuf>,
    protected: Option<PathBuf>,
}

impl TmpScope {
    /// `protected` (the project being installed) and the temp directory holding it are never touched.
    pub fn new(tmp: &Path, protected: Option<&Path>) -> Self {
        let mut roots = vec![tmp.to_path_buf()];
        if let Ok(canonical) = tmp.canonicalize() {
            if !roots.contains(&canonical) {
                roots.push(canonical);
            }
        }
        let protected = protected
            .filter(|p| !p.as_os_str().is_empty())
            .map(|p| p.canonicalize().unwrap_or_else(|_| p.to_path_buf()));
        Self { roots, protected }
    }

    /// The top-level `<tmp>/agentic-*` directory that contains `path`, if any.
    fn top_dir(&self, path: &Path) -> Option<PathBuf> {
        self.roots.iter().find_map(|root| {
            let rest = path.strip_prefix(root).ok()?;
            match rest.components().next()? {
                Component::Normal(name) if name.to_string_lossy().starts_with(TMP_DIR_PREFIX) => {
                    Some(root.join(name))
                }
                _ => None,
            }
        })
    }

    pub fn contains(&self, path: &Path) -> bool {
        let Some(top) = self.top_dir(path) else {
            return false;
        };
        match &self.protected {
            Some(protected) => self.top_dir(protected).is_none_or(|p| p != top),
            None => true,
        }
    }

    /// Claude Code names a project directory after its path with every non-alphanumeric char replaced by `-`.
    fn claude_project_prefixes(&self) -> Vec<String> {
        self.roots
            .iter()
            .map(|root| {
                format!(
                    "{}-{}",
                    claude_encode(root),
                    claude_encode(Path::new(TMP_DIR_PREFIX))
                )
            })
            .collect()
    }
}

fn claude_encode(path: &Path) -> String {
    path.to_string_lossy()
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '-' })
        .collect()
}

fn env_dir(var: &str) -> Option<PathBuf> {
    std::env::var(var)
        .ok()
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
}

fn open_read_only(db: &Path) -> Option<Connection> {
    if !db.is_file() {
        return None;
    }
    Connection::open_with_flags(db, OpenFlags::SQLITE_OPEN_READ_ONLY).ok()
}

fn query_ids(conn: &Connection, sql: &str, scope: &TmpScope) -> Vec<String> {
    let Ok(mut stmt) = conn.prepare(sql) else {
        return Vec::new();
    };
    let Ok(rows) = stmt.query_map([], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
    }) else {
        return Vec::new();
    };
    rows.flatten()
        .filter(|(_, dir)| scope.contains(Path::new(dir)))
        .map(|(id, _)| id)
        .collect()
}

/// Newest `state_<N>.sqlite` in the Codex home: Codex bumps N when the schema changes.
fn codex_state_db(codex_home: &Path) -> Option<PathBuf> {
    std::fs::read_dir(codex_home)
        .ok()?
        .flatten()
        .filter_map(|entry| {
            let name = entry.file_name().to_string_lossy().to_string();
            let version = name
                .strip_prefix("state_")?
                .strip_suffix(".sqlite")?
                .parse::<u32>()
                .ok()?;
            Some((version, entry.path()))
        })
        .max_by_key(|(version, _)| *version)
        .map(|(_, path)| path)
}

pub fn codex_session_ids(codex_home: &Path, scope: &TmpScope) -> Vec<String> {
    let Some(conn) = codex_state_db(codex_home).and_then(|db| open_read_only(&db)) else {
        return Vec::new();
    };
    query_ids(&conn, "SELECT id, cwd FROM threads", scope)
}

/// Only top-level sessions: `opencode session delete` removes the child sessions too.
pub fn opencode_session_ids(data_home: &Path, scope: &TmpScope) -> Vec<String> {
    let Some(conn) = open_read_only(&data_home.join("opencode/opencode.db")) else {
        return Vec::new();
    };
    query_ids(
        &conn,
        "SELECT id, directory FROM session_v2 WHERE parent_id IS NULL",
        scope,
    )
}

pub fn claude_project_dirs(claude_home: &Path, scope: &TmpScope) -> Vec<PathBuf> {
    let prefixes = scope.claude_project_prefixes();
    // The encoding is lossy, so anything that may be inside the protected temp directory is kept.
    let protected = scope
        .protected
        .as_deref()
        .and_then(|p| scope.top_dir(p))
        .map(|top| claude_encode(&top));
    let Ok(entries) = std::fs::read_dir(claude_home.join("projects")) else {
        return Vec::new();
    };
    entries
        .flatten()
        .filter(|entry| entry.file_type().is_ok_and(|t| t.is_dir()))
        .filter(|entry| {
            let name = entry.file_name().to_string_lossy().to_string();
            prefixes.iter().any(|p| name.starts_with(p.as_str()))
                && protected
                    .as_deref()
                    .is_none_or(|p| !(name == p || name.starts_with(&format!("{p}-"))))
        })
        .map(|entry| entry.path())
        .collect()
}

/// Removes a Claude Code project directory and the per-session state stored next to `projects/`.
fn remove_claude_project(claude_home: &Path, project: &Path) -> bool {
    if let Ok(entries) = std::fs::read_dir(project) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().is_some_and(|e| e == "jsonl") {
                if let Some(session) = path.file_stem() {
                    for side in ["file-history", "session-env"] {
                        let _ = std::fs::remove_dir_all(claude_home.join(side).join(session));
                    }
                }
            }
        }
    }
    std::fs::remove_dir_all(project).is_ok()
}

/// Top-level `<tmp>/agentic-*` directories; symlinks and files (the run log) are left alone.
pub fn stale_tmp_dirs(tmp: &Path, scope: &TmpScope) -> Vec<PathBuf> {
    let Ok(entries) = std::fs::read_dir(tmp) else {
        return Vec::new();
    };
    entries
        .flatten()
        .filter(|entry| entry.file_type().is_ok_and(|t| t.is_dir()))
        .map(|entry| entry.path())
        .filter(|path| scope.contains(path))
        .collect()
}

fn parent_pid(pid: u32) -> Option<u32> {
    let stat = std::fs::read_to_string(format!("/proc/{pid}/stat")).ok()?;
    // The command name may contain spaces, so fields are counted after its closing parenthesis.
    stat.rsplit_once(')')?
        .1
        .split_whitespace()
        .nth(1)?
        .parse()
        .ok()
}

/// This process and its ancestors (the user's shell may sit in such a directory) are never stopped.
fn own_process_chain() -> Vec<u32> {
    let mut chain = vec![std::process::id()];
    while let Some(parent) = chain.last().and_then(|pid| parent_pid(*pid)) {
        if parent <= 1 || chain.contains(&parent) {
            break;
        }
        chain.push(parent);
    }
    chain
}

/// Processes whose working directory matches `inside`. Linux only (`/proc`); elsewhere none are found.
fn processes_in(inside: impl Fn(&Path) -> bool) -> Vec<u32> {
    let own = own_process_chain();
    let Ok(entries) = std::fs::read_dir("/proc") else {
        return Vec::new();
    };
    entries
        .flatten()
        .filter_map(|entry| entry.file_name().to_str()?.parse::<u32>().ok())
        .filter(|pid| !own.contains(pid))
        .filter(|pid| {
            std::fs::read_link(format!("/proc/{pid}/cwd")).is_ok_and(|cwd| {
                let cwd = cwd.to_string_lossy();
                inside(Path::new(cwd.strip_suffix(" (deleted)").unwrap_or(&cwd)))
            })
        })
        .collect()
}

fn signal(pids: &[u32], name: &str) {
    if pids.is_empty() {
        return;
    }
    let _ = Command::new("kill")
        .arg(format!("-{name}"))
        .args(pids.iter().map(u32::to_string))
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status();
}

/// Stops leftover processes in the given directories, such as MCP servers that outlived the agent which
/// started them and keep writing logs there: TERM first, KILL after a short grace period.
pub fn stop_processes_in(inside: impl Fn(&Path) -> bool) -> usize {
    let pids = processes_in(&inside);
    signal(&pids, "TERM");
    let deadline = std::time::Instant::now() + Duration::from_secs(2);
    let alive = |pid: &&u32| Path::new(&format!("/proc/{pid}")).exists();
    while pids.iter().any(|pid| alive(&pid)) && std::time::Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(100));
    }
    let left: Vec<u32> = pids.iter().filter(alive).copied().collect();
    signal(&left, "KILL");
    pids.len()
}

fn binary_available(name: &str) -> bool {
    let Ok(path_var) = std::env::var("PATH") else {
        return false;
    };
    std::env::split_paths(&path_var).any(|dir| dir.join(name).is_file())
}

/// `listed` re-reads the agent database: deleting a parent session also deletes its subagent sessions, and a
/// later delete of such a child fails although the session is gone.
fn delete_sessions(
    app: &App,
    agent: &str,
    ids: &[String],
    args: &[&str],
    listed: impl Fn() -> Vec<String>,
) -> usize {
    if ids.is_empty() {
        return 0;
    }
    if !binary_available(agent) {
        ui::log(
            app,
            &format!(
                "Doctor cleanup: {agent} is not installed, {} session(s) left",
                ids.len()
            ),
        );
        return 0;
    }
    let mut deleted = 0;
    for id in ids {
        let mut cmd = Command::new(agent);
        cmd.args(args).arg(id).stdin(std::process::Stdio::null());
        match run_with_timeout(&mut cmd, SESSION_DELETE_TIMEOUT) {
            Ok((false, 0, _)) => deleted += 1,
            _ if !listed().contains(id) => deleted += 1,
            Ok((_, status, output)) => ui::log(
                app,
                &format!(
                    "Doctor cleanup: {agent} could not delete session {id} (exit {status}): {}",
                    output.trim()
                ),
            ),
            Err(err) => ui::log(
                app,
                &format!("Doctor cleanup: {agent} could not delete session {id}: {err}"),
            ),
        }
    }
    deleted
}

/// Deletes agent sessions that ran in `<tmp>/agentic-*` directories, then the directories themselves.
pub fn clean_agentic_tmp(app: &App) {
    let tmp = crate::util::tmp_dir();
    let project = PathBuf::from(&app.project_dir);
    let scope = TmpScope::new(&tmp, Some(&project));

    let processes_stopped = stop_processes_in(|cwd| scope.contains(cwd));

    let codex_home = env_dir("CODEX_HOME").unwrap_or_else(|| app.home.join(".codex"));
    let codex_ids = codex_session_ids(&codex_home, &scope);
    let codex_deleted = delete_sessions(app, "codex", &codex_ids, &["delete", "--force"], || {
        codex_session_ids(&codex_home, &scope)
    });

    let data_home = env_dir("XDG_DATA_HOME").unwrap_or_else(|| app.home.join(".local/share"));
    let opencode_ids = opencode_session_ids(&data_home, &scope);
    let opencode_deleted = delete_sessions(
        app,
        "opencode",
        &opencode_ids,
        &["session", "delete"],
        || opencode_session_ids(&data_home, &scope),
    );

    let claude_home = env_dir("CLAUDE_CONFIG_DIR").unwrap_or_else(|| app.home.join(".claude"));
    let claude_deleted = claude_project_dirs(&claude_home, &scope)
        .iter()
        .filter(|project| remove_claude_project(&claude_home, project))
        .count();

    let dirs_deleted = stale_tmp_dirs(&tmp, &scope)
        .iter()
        .filter(|dir| std::fs::remove_dir_all(dir).is_ok())
        .count();

    ui::log(
        app,
        &format!(
            "Doctor cleanup: processes stopped {processes_stopped}, codex sessions {codex_deleted}/{}, opencode sessions {opencode_deleted}/{}, claude projects {claude_deleted}, temp directories {dirs_deleted}",
            codex_ids.len(),
            opencode_ids.len()
        ),
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scope_matches_only_agentic_dirs_outside_the_project() {
        let tmp = Path::new("/tmpx");
        let scope = TmpScope::new(tmp, Some(Path::new("/tmpx/agentic-project/app")));
        assert!(scope.contains(Path::new("/tmpx/agentic-doctor.ab12/opencode")));
        assert!(scope.contains(Path::new("/tmpx/agentic-bench")));
        assert!(!scope.contains(Path::new("/tmpx/agentic-project")));
        assert!(!scope.contains(Path::new("/tmpx/agentic-project/other")));
        assert!(!scope.contains(Path::new("/tmpx/other/agentic-x")));
        assert!(!scope.contains(Path::new("/home/u/agentic-x")));
        assert!(!scope.contains(Path::new("/tmpx")));
    }

    #[test]
    fn stale_tmp_dirs_skip_files_and_protected_project() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        std::fs::create_dir_all(root.join("agentic-doctor.x/claude")).unwrap();
        std::fs::create_dir_all(root.join("agentic-project")).unwrap();
        std::fs::create_dir_all(root.join("other")).unwrap();
        std::fs::write(root.join("agentic-20261026-120000.abc"), "run log").unwrap();
        let scope = TmpScope::new(root, Some(&root.join("agentic-project")));
        let dirs = stale_tmp_dirs(root, &scope);
        let names: Vec<_> = dirs
            .iter()
            .map(|d| d.file_name().unwrap().to_string_lossy().to_string())
            .collect();
        assert_eq!(names, vec!["agentic-doctor.x"]);
    }

    #[test]
    fn finds_codex_and_opencode_sessions_by_directory() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        let scope = TmpScope::new(Path::new("/tmpx"), None);

        let codex_home = root.join("codex");
        std::fs::create_dir_all(&codex_home).unwrap();
        std::fs::write(codex_home.join("state_4.sqlite"), "").unwrap();
        let conn = Connection::open(codex_home.join("state_5.sqlite")).unwrap();
        conn.execute_batch(
            "CREATE TABLE threads (id TEXT, cwd TEXT);
             INSERT INTO threads VALUES ('t1', '/tmpx/agentic-doctor.a/codex'), ('t2', '/home/u/repo');",
        )
        .unwrap();
        drop(conn);
        assert_eq!(codex_session_ids(&codex_home, &scope), vec!["t1"]);

        let data_home = root.join("share");
        std::fs::create_dir_all(data_home.join("opencode")).unwrap();
        let conn = Connection::open(data_home.join("opencode/opencode.db")).unwrap();
        conn.execute_batch(
            "CREATE TABLE session_v2 (id TEXT, directory TEXT, parent_id TEXT);
             INSERT INTO session_v2 VALUES
               ('s1', '/tmpx/agentic-jev-x', NULL),
               ('s2', '/tmpx/agentic-jev-x', 's1'),
               ('s3', '/home/u/repo', NULL);",
        )
        .unwrap();
        drop(conn);
        assert_eq!(opencode_session_ids(&data_home, &scope), vec!["s1"]);
    }

    #[test]
    fn claude_project_dirs_match_encoded_tmp_paths() {
        let tmp = tempfile::tempdir().unwrap();
        let claude_home = tmp.path();
        for name in [
            "-tmpx-agentic-bench-claude",
            "-tmpx-agentic-project",
            "-tmpx-agentic-project-app",
            "-home-u-repo",
        ] {
            std::fs::create_dir_all(claude_home.join("projects").join(name)).unwrap();
        }
        let scope = TmpScope::new(Path::new("/tmpx"), Some(Path::new("/tmpx/agentic-project")));
        let dirs = claude_project_dirs(claude_home, &scope);
        let names: Vec<_> = dirs
            .iter()
            .map(|d| d.file_name().unwrap().to_string_lossy().to_string())
            .collect();
        assert_eq!(names, vec!["-tmpx-agentic-bench-claude"]);

        let project = claude_home.join("projects/-tmpx-agentic-bench-claude");
        std::fs::write(project.join("abc.jsonl"), "{}").unwrap();
        std::fs::create_dir_all(claude_home.join("file-history/abc")).unwrap();
        assert!(remove_claude_project(claude_home, &project));
        assert!(!project.exists());
        assert!(!claude_home.join("file-history/abc").exists());
    }
}
