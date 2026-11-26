//! External sources shared by company rules (docs/company-rules.md) and skill packs
//! (docs/skill-packs.md): a local directory or a git repository, the git cache below
//! `~/.cache/agentic/<kind>/`, and the file walk of a source directory.

use crate::app::App;
use crate::{ui, util};
use serde_json::{json, Value};
use std::path::{Component, Path, PathBuf};
use std::process::{Command, Stdio};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Source {
    /// A directory, relative to the project or absolute.
    Path(String),
    /// A git repository; empty `git_ref` means the remote HEAD, empty `subdir` the repository root.
    Git {
        url: String,
        git_ref: String,
        subdir: String,
    },
}

/// `<url>[#ref][:subdir]`. A subdir needs the `#`: `<url>#:<subdir>` keeps the default ref.
/// `flag` names the option in error messages (`--company-rules-git`, `--skill-pack`).
pub fn parse_git_spec(spec: &str, flag: &str) -> Result<Source, String> {
    let spec = spec.trim();
    let (url, rest) = match spec.rsplit_once('#') {
        Some((url, rest)) => (url, rest),
        None => (spec, ""),
    };
    let (git_ref, subdir) = rest.split_once(':').unwrap_or((rest, ""));
    if url.is_empty() {
        return Err(format!("{flag}: missing URL in '{spec}'"));
    }
    if !valid_url(url) {
        return Err(format!("{flag}: invalid URL '{url}'"));
    }
    if !valid_ref(git_ref) {
        return Err(format!("{flag}: invalid ref '{git_ref}'"));
    }
    let subdir = subdir.trim_matches('/').to_string();
    if !subdir.is_empty() && !is_relative_clean(&subdir) {
        return Err(format!(
            "{flag}: subdir must be a relative path: '{subdir}'"
        ));
    }
    Ok(Source::Git {
        url: url.to_string(),
        git_ref: git_ref.to_string(),
        subdir,
    })
}

/// A non-empty relative path without `..`, `.`, or a root.
pub fn is_relative_clean(path: &str) -> bool {
    let p = Path::new(path);
    !path.is_empty() && p.components().all(|c| matches!(c, Component::Normal(_)))
}

/// Hide the user part of `https://user:token@host/...` in messages and in the manifest source ids.
pub fn redact_url(url: &str) -> String {
    if let Some((scheme, rest)) = url.split_once("://") {
        let host_end = rest.find('/').unwrap_or(rest.len());
        if let Some(at) = rest[..host_end].rfind('@') {
            return format!("{scheme}://***@{}", &rest[at + 1..]);
        }
    }
    url.to_string()
}

/// The path as configured, or the redacted git URL with `#ref` and `:subdir`.
pub fn source_id(source: &Source) -> String {
    match source {
        Source::Path(path) => path.trim_end_matches('/').to_string(),
        Source::Git {
            url,
            git_ref,
            subdir,
        } => {
            let mut id = redact_url(url);
            if !git_ref.is_empty() {
                id.push('#');
                id.push_str(git_ref);
            }
            if !subdir.is_empty() {
                id.push(':');
                id.push_str(subdir);
            }
            id
        }
    }
}

/// `{"path": ...}` or `{"git": ..., "ref"?: ..., "subdir"?: ...}`.
pub fn to_json(source: &Source) -> Value {
    match source {
        Source::Path(path) => json!({ "path": path }),
        Source::Git {
            url,
            git_ref,
            subdir,
        } => {
            let mut v = json!({ "git": url });
            if !git_ref.is_empty() {
                v["ref"] = json!(git_ref);
            }
            if !subdir.is_empty() {
                v["subdir"] = json!(subdir);
            }
            v
        }
    }
}

/// Inverse of [`to_json`]; None for an entry without a usable `path` or `git`.
pub fn from_json(item: &Value) -> Option<Source> {
    let text = |key: &str| item[key].as_str().unwrap_or_default().to_string();
    if let Some(path) = item["path"].as_str().filter(|p| !p.is_empty()) {
        return Some(Source::Path(path.to_string()));
    }
    let url = item["git"].as_str().filter(|u| !u.is_empty())?;
    let subdir = text("subdir").trim_matches('/').to_string();
    if !subdir.is_empty() && !is_relative_clean(&subdir) {
        return None;
    }
    Some(Source::Git {
        url: url.to_string(),
        git_ref: text("ref"),
        subdir,
    })
}

/// `~/.cache/agentic/<kind>` (`$XDG_CACHE_HOME/agentic/<kind>` when set).
pub fn cache_root(app: &App, kind: &str) -> PathBuf {
    let base = std::env::var("XDG_CACHE_HOME")
        .ok()
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(|| app.home.join(".cache"));
    base.join("agentic").join(kind)
}

/// A branch, tag, or commit for `git fetch`: empty (the remote HEAD) or a value that git cannot read
/// as an option (no leading `-`, no whitespace or control characters).
pub fn valid_ref(git_ref: &str) -> bool {
    !git_ref.starts_with('-') && !git_ref.chars().any(|c| c.is_whitespace() || c.is_control())
}

/// A full commit id: 40 (SHA-1) or 64 (SHA-256) hex digits.
pub fn valid_commit(commit: &str) -> bool {
    matches!(commit.len(), 40 | 64) && commit.chars().all(|c| c.is_ascii_hexdigit())
}

/// A git URL or path that git cannot read as an option.
pub fn valid_url(url: &str) -> bool {
    !url.is_empty() && !url.starts_with('-') && !url.chars().any(char::is_control)
}

/// Each component of `rel` below `root` is a real directory or file, not a symbolic link, so the
/// path stays inside `root`.
pub fn no_symlink_below(root: &Path, rel: &str) -> bool {
    let mut path = root.to_path_buf();
    for part in Path::new(rel).components() {
        path.push(part);
        match std::fs::symlink_metadata(&path) {
            Ok(meta) if meta.file_type().is_symlink() => return false,
            Ok(_) => {}
            Err(_) => return false,
        }
    }
    true
}

/// A regular file (not a symbolic link).
pub fn is_plain_file(path: &Path) -> bool {
    std::fs::symlink_metadata(path).is_ok_and(|m| m.file_type().is_file())
}

fn git_command(dir: &Path, args: &[&str]) -> Command {
    let mut cmd = Command::new("git");
    // Keep upstream line endings (frontmatter detection) and never run `ext::` transports.
    cmd.arg("-C")
        .arg(dir)
        .args([
            "-c",
            "core.autocrlf=false",
            "-c",
            "protocol.ext.allow=never",
        ])
        .args(args)
        .env("GIT_TERMINAL_PROMPT", "0")
        .env("GCM_INTERACTIVE", "never")
        .stdin(Stdio::null())
        .stderr(Stdio::null());
    if std::env::var_os("GIT_SSH_COMMAND").is_none() {
        cmd.env("GIT_SSH_COMMAND", "ssh -o BatchMode=yes");
    }
    cmd
}

/// Run git without prompts; true on success.
pub fn git(dir: &Path, args: &[&str]) -> bool {
    git_command(dir, args)
        .stdout(Stdio::null())
        .status()
        .is_ok_and(|s| s.success())
}

/// Trimmed stdout of a successful git command.
pub fn git_stdout(dir: &Path, args: &[&str]) -> Option<String> {
    let output = git_command(dir, args).output().ok()?;
    output
        .status
        .success()
        .then(|| String::from_utf8_lossy(&output.stdout).trim().to_string())
        .filter(|s| !s.is_empty())
}

/// The commit of the checkout in `dir`.
pub fn head_commit(dir: &Path) -> Option<String> {
    git_stdout(dir, &["rev-parse", "--verify", "--quiet", "HEAD"])
}

/// The cache repository of `url` below `cache_root(kind)`, created on first use.
fn cache_repo(app: &mut App, kind: &str, label: &str, url: &str) -> Option<PathBuf> {
    if !valid_url(url) {
        ui::warn(
            app,
            &format!("{label}: invalid git URL `{}`", redact_url(url)),
        );
        return None;
    }
    let dir = cache_root(app, kind).join(util::sha256_hex(url.as_bytes()));
    if !dir.join(".git").is_dir()
        && (std::fs::create_dir_all(&dir).is_err()
            || !git(&dir, &["init", "--quiet"])
            || !git(&dir, &["remote", "add", "--", "origin", url]))
    {
        ui::warn(
            app,
            &format!(
                "{label}: cannot prepare the git cache for {}",
                redact_url(url)
            ),
        );
        let _ = std::fs::remove_dir_all(&dir);
        return None;
    }
    Some(dir)
}

fn checkout(dir: &Path, what: &str) -> bool {
    git(dir, &["checkout", "--quiet", "--force", what, "--"])
        && git(dir, &["clean", "--quiet", "-fdx"])
}

/// `git fetch --depth 1 -- origin <wanted>` and a checkout of `FETCH_HEAD`. `--` keeps a value from
/// being read as an option.
fn fetch_into(dir: &Path, wanted: &str) -> bool {
    git(
        dir,
        &["fetch", "--quiet", "--depth", "1", "--", "origin", wanted],
    ) && checkout(dir, "FETCH_HEAD")
}

fn checked_ref<'a>(app: &mut App, label: &str, git_ref: &'a str) -> Option<&'a str> {
    if valid_ref(git_ref) {
        return Some(if git_ref.is_empty() { "HEAD" } else { git_ref });
    }
    ui::warn(
        app,
        &format!("{label}: invalid git ref `{}`", git_ref.escape_debug()),
    );
    None
}

/// Fetch `url` at `git_ref` into the cache. None when the fetch fails: no fallback to the cache.
pub fn fetch_ref(
    app: &mut App,
    kind: &str,
    label: &str,
    url: &str,
    git_ref: &str,
) -> Option<PathBuf> {
    let wanted = checked_ref(app, label, git_ref)?;
    let dir = cache_repo(app, kind, label, url)?;
    let shown = redact_url(url);
    if fetch_into(&dir, wanted) {
        ui::log(app, &format!("{label}: fetched {shown} ({wanted})"));
        return Some(dir);
    }
    ui::warn(app, &format!("{label}: cannot fetch {shown} ({wanted})"));
    None
}

/// Fetch `url` at `git_ref` into the cache. Returns the checkout, the cached copy when the fetch fails,
/// or None when there is no copy at all.
pub fn fetch_git(
    app: &mut App,
    kind: &str,
    label: &str,
    url: &str,
    git_ref: &str,
) -> Option<PathBuf> {
    let wanted = checked_ref(app, label, git_ref)?;
    let dir = cache_repo(app, kind, label, url)?;
    let shown = redact_url(url);
    if fetch_into(&dir, wanted) {
        ui::log(app, &format!("{label}: fetched {shown} ({wanted})"));
        return Some(dir);
    }
    if head_commit(&dir).is_some() {
        ui::warn(
            app,
            &format!(
                "{label}: cannot fetch {shown} ({wanted}); using the cached copy in {}",
                dir.display()
            ),
        );
        return Some(dir);
    }
    ui::warn(
        app,
        &format!("{label}: cannot fetch {shown} ({wanted}) and no cached copy exists"),
    );
    let _ = std::fs::remove_dir_all(&dir);
    None
}

/// Check out the exact `commit` of `url`: from the cache when it has the commit, else by a shallow
/// fetch of that commit. None when neither works (offline and not cached) or `commit` is not a full
/// commit id.
pub fn checkout_commit(
    app: &mut App,
    kind: &str,
    label: &str,
    url: &str,
    commit: &str,
) -> Option<PathBuf> {
    if !valid_commit(commit) {
        ui::warn(
            app,
            &format!("{label}: invalid locked commit `{}`", commit.escape_debug()),
        );
        return None;
    }
    let dir = cache_repo(app, kind, label, url)?;
    let object = format!("{commit}^{{commit}}");
    let cached = git(&dir, &["cat-file", "-e", &object]);
    let ok = if cached {
        checkout(&dir, commit)
    } else {
        fetch_into(&dir, commit)
    };
    let shown = redact_url(url);
    if ok && head_commit(&dir).as_deref() == Some(commit) {
        ui::log(app, &format!("{label}: checked out {shown} at {commit}"));
        return Some(dir);
    }
    ui::warn(
        app,
        &format!("{label}: cannot check out {shown} at the locked commit {commit}"),
    );
    None
}

/// The real project root (an upgrade installs into a staging copy), for relative path sources.
pub fn base_dir(app: &App) -> PathBuf {
    app.company_base_dir
        .clone()
        .unwrap_or_else(|| PathBuf::from(&app.project_dir))
}

/// A path source as an absolute directory.
pub fn resolve_path(app: &App, path: &str) -> PathBuf {
    if Path::new(path).is_absolute() {
        PathBuf::from(path)
    } else {
        base_dir(app).join(path)
    }
}

/// Every file below `dir` as (`/`-separated path below `root`, UTF-8 text or None); dot entries are
/// skipped. Skills carry scripts and templates, so this is not limited to Markdown.
pub fn collect_all(root: &Path, dir: &Path, out: &mut Vec<(String, Option<String>)>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    let mut entries: Vec<_> = entries.filter_map(|e| e.ok()).collect();
    entries.sort_by_key(|e| e.file_name());
    for entry in entries {
        if entry.file_name().to_string_lossy().starts_with('.') {
            continue;
        }
        let path = entry.path();
        match entry.file_type() {
            Ok(kind) if kind.is_dir() => collect_all(root, &path, out),
            Ok(kind) if kind.is_file() => {
                if let Ok(rel) = path.strip_prefix(root) {
                    let rel = rel.to_string_lossy().replace('\\', "/");
                    out.push((rel, std::fs::read_to_string(&path).ok()));
                }
            }
            _ => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn json_roundtrip_and_flag_in_errors() {
        let git = parse_git_spec("<url>#main:rules", "--x").unwrap();
        assert_eq!(from_json(&to_json(&git)), Some(git.clone()));
        let path = Source::Path("dir".into());
        assert_eq!(from_json(&to_json(&path)), Some(path));
        assert!(from_json(&json!({"git": "<url>", "subdir": "../up"})).is_none());
        assert!(from_json(&json!({})).is_none());
        assert!(parse_git_spec("#main", "--skill-pack")
            .unwrap_err()
            .starts_with("--skill-pack:"));
        assert_eq!(source_id(&git), "<url>#main:rules");
    }

    #[test]
    fn rejects_refs_commits_and_urls_that_git_could_read_as_options() {
        assert!(valid_ref("") && valid_ref("main") && valid_ref("v1.2/x"));
        for bad in ["--upload-pack=touch X;", "-x", "a b", "a\nb"] {
            assert!(!valid_ref(bad), "{bad}");
        }
        assert!(valid_commit(&"a".repeat(40)) && valid_commit(&"0".repeat(64)));
        assert!(!valid_commit("--upload-pack=touch X;") && !valid_commit(&"g".repeat(40)));
        assert!(!valid_url("--upload-pack=x") && valid_url("/tmp/a b.git"));
        assert!(parse_git_spec("<url>#--upload-pack=x", "--f").is_err());
        assert!(parse_git_spec("--upload-pack=x#main", "--f").is_err());
    }

    #[test]
    fn option_like_lock_or_ref_never_runs_a_command() {
        if std::env::var_os("XDG_CACHE_HOME").is_some() {
            return;
        }
        let tmp = tempfile::tempdir().unwrap();
        let mut app = App::new().unwrap();
        app.home = tmp.path().join("home");
        let flag = tmp.path().join("pwned");
        let evil = format!("--upload-pack=touch {};", flag.display());
        let url = tmp.path().join("none").to_string_lossy().to_string();
        assert!(checkout_commit(&mut app, "test", "T", &url, &evil).is_none());
        assert!(fetch_git(&mut app, "test", "T", &url, &evil).is_none());
        assert!(fetch_ref(&mut app, "test", "T", &url, &evil).is_none());
        assert!(fetch_git(&mut app, "test", "T", &evil, "main").is_none());
        assert!(!flag.exists());
    }

    #[cfg(unix)]
    #[test]
    fn symlink_components_are_detected() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(tmp.path().join("real/skills")).unwrap();
        std::fs::write(tmp.path().join("real/LICENSE"), "x").unwrap();
        std::os::unix::fs::symlink(tmp.path().join("real"), tmp.path().join("link")).unwrap();
        assert!(no_symlink_below(tmp.path(), "real/skills"));
        assert!(!no_symlink_below(tmp.path(), "link/skills"));
        assert!(!no_symlink_below(tmp.path(), "missing"));
        assert!(is_plain_file(&tmp.path().join("real/LICENSE")));
        std::os::unix::fs::symlink(tmp.path().join("real/LICENSE"), tmp.path().join("L")).unwrap();
        assert!(!is_plain_file(&tmp.path().join("L")));
    }

    #[test]
    fn checks_out_a_locked_commit_from_a_local_repository() {
        // The cache follows XDG_CACHE_HOME when set; do not write test repositories there.
        if std::env::var_os("XDG_CACHE_HOME").is_some() {
            return;
        }
        let tmp = tempfile::tempdir().unwrap();
        let work = tmp.path().join("work");
        std::fs::create_dir_all(&work).unwrap();
        let run = |args: &[&str]| {
            assert!(std::process::Command::new("git")
                .current_dir(&work)
                .args(["-c", "user.name=t", "-c", "user.email=t@example.com"])
                .args(args)
                .env("GIT_CONFIG_NOSYSTEM", "1")
                .env("GIT_CONFIG_GLOBAL", "/dev/null")
                .status()
                .unwrap()
                .success());
        };
        run(&["init", "-q", "-b", "main"]);
        std::fs::write(work.join("a.txt"), "one\n").unwrap();
        run(&["add", "."]);
        run(&["commit", "-qm", "one"]);
        let first = head_commit(&work).unwrap();
        std::fs::write(work.join("a.txt"), "two\n").unwrap();
        run(&["commit", "-qam", "two"]);
        let mut app = App::new().unwrap();
        app.home = tmp.path().join("home");
        let url = work.to_string_lossy().to_string();
        let dir = fetch_git(&mut app, "test", "T", &url, "main").unwrap();
        assert_ne!(head_commit(&dir).unwrap(), first);
        // The shallow cache lacks the first commit; a fetch by commit id gets it.
        let dir = checkout_commit(&mut app, "test", "T", &url, &first).unwrap();
        assert_eq!(std::fs::read_to_string(dir.join("a.txt")).unwrap(), "one\n");
        assert!(checkout_commit(&mut app, "test", "T", &url, &"0".repeat(40)).is_none());
    }
}
