//! Upgrade reminder. The session-start hook of the quality gate (`gate.py --event start`) calls the hidden
//! command `agentic __update-check --format claude|codex|opencode`. At most once per interval (default 7
//! days, machine-wide) it asks GitHub for the latest release and, when it is newer than this binary, prints
//! one JSON object with the reminder text. It only offers the upgrade; it never upgrades. Every failure is
//! silent: the hook must never block or fail a session. See `docs/upgrade-reminder.md`.

use crate::app::App;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::time::Duration;

pub const DEFAULT_INTERVAL_DAYS: u64 = 7;
/// Total time for the release lookup, so a slow network cannot hold up a session start.
const FETCH_TIMEOUT: Duration = Duration::from_secs(2);
const DAY: i64 = 86_400;

/// A newer release the user has not been told about in this interval.
#[derive(Debug, PartialEq, Eq)]
pub struct Notice {
    pub latest: String,
    pub installed: String,
    pub interval_days: u64,
}

#[derive(Debug, Default, PartialEq, Eq)]
struct State {
    last_check_at: Option<i64>,
    last_notified_at: Option<i64>,
    latest_seen: Option<String>,
}

fn read_state(path: &Path) -> State {
    let data: Value = std::fs::read_to_string(path)
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or(Value::Null);
    State {
        last_check_at: data.get("last_check_at").and_then(Value::as_i64),
        last_notified_at: data.get("last_notified_at").and_then(Value::as_i64),
        latest_seen: data
            .get("latest_seen")
            .and_then(Value::as_str)
            .map(str::to_string),
    }
}

/// Atomic write (temp file in the same directory, then rename) so concurrent sessions never read half a file.
/// Returns false when the state cannot be saved.
fn write_state(path: &Path, state: &State) -> bool {
    let body = json!({
        "last_check_at": state.last_check_at,
        "last_notified_at": state.last_notified_at,
        "latest_seen": state.latest_seen,
    });
    let Some(parent) = path.parent() else {
        return false;
    };
    if std::fs::create_dir_all(parent).is_err() {
        return false;
    }
    let tmp = parent.join(format!(".update-check.{}.tmp", std::process::id()));
    let saved =
        std::fs::write(&tmp, body.to_string()).is_ok() && std::fs::rename(&tmp, path).is_ok();
    if !saved {
        let _ = std::fs::remove_file(&tmp);
    }
    saved
}

/// `~/.cache/agentic/update-check.json`, or under `$XDG_CACHE_HOME`.
pub fn state_file(app: &App) -> PathBuf {
    std::env::var("XDG_CACHE_HOME")
        .ok()
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(|| app.home.join(".cache"))
        .join(crate::APP_NAME)
        .join("update-check.json")
}

/// Interval in days from `update_check.interval_days` of `config.json`; `0` means off. The env value
/// `AGENTIC_UPDATE_CHECK=0` (or `off`/`false`/`no`) turns the reminder off whatever the file says.
pub fn interval_days(config_json: &Path, env: Option<&str>) -> u64 {
    if matches!(
        env.map(|v| v.trim().to_ascii_lowercase()).as_deref(),
        Some("0" | "off" | "false" | "no")
    ) {
        return 0;
    }
    std::fs::read_to_string(config_json)
        .ok()
        .and_then(|t| serde_json::from_str::<Value>(&t).ok())
        .and_then(|v| v.get("update_check")?.get("interval_days")?.as_u64())
        .unwrap_or(DEFAULT_INTERVAL_DAYS)
}

/// Strict `X.Y.Z` with an optional `v`; `None` for pre-releases (`-rc.1`), build metadata, or junk.
fn release_version(tag: &str) -> Option<String> {
    let v = tag.trim().trim_start_matches('v');
    let parts: Vec<&str> = v.split('.').collect();
    let ok = parts.len() == 3
        && parts
            .iter()
            .all(|p| !p.is_empty() && p.chars().all(|c| c.is_ascii_digit()));
    ok.then(|| v.to_string())
}

/// Latest stable version from a GitHub `releases/latest` body; drafts and pre-releases give `None`.
pub fn latest_from_release(release: &Value) -> Option<String> {
    if release.get("draft").and_then(Value::as_bool) == Some(true)
        || release.get("prerelease").and_then(Value::as_bool) == Some(true)
    {
        return None;
    }
    release_version(release.get("tag_name")?.as_str()?)
}

/// Core rule with an injected clock and fetcher. The attempt is recorded before the lookup, so a failing
/// or slow lookup is not retried until the next interval.
pub fn check(
    state_path: &Path,
    installed: &str,
    now: i64,
    interval_days: u64,
    fetch: &dyn Fn() -> Option<String>,
) -> Option<Notice> {
    if interval_days == 0 {
        return None;
    }
    let mut state = read_state(state_path);
    let span = (interval_days as i64).saturating_mul(DAY);
    // A clock set back (last check in the future) counts as elapsed.
    if let Some(last) = state.last_check_at {
        if last <= now && now - last < span {
            return None;
        }
    }
    state.last_check_at = Some(now);
    // Without a saved attempt the next session would query again: stay offline and silent.
    if !write_state(state_path, &state) {
        return None;
    }
    let latest = release_version(&fetch()?)?;
    state.latest_seen = Some(latest.clone());
    let newer = crate::upgrade::is_newer_version(installed, &latest);
    if newer {
        state.last_notified_at = Some(now);
    }
    let _ = write_state(state_path, &state);
    newer.then(|| Notice {
        latest,
        installed: installed.to_string(),
        interval_days,
    })
}

fn release_fetcher() -> Option<String> {
    // Test and offline hook: a fixed tag, no network.
    if let Ok(tag) = std::env::var("AGENTIC_UPDATE_CHECK_LATEST") {
        return Some(tag);
    }
    let client = reqwest::blocking::Client::builder()
        .user_agent(format!("agentic/{}", crate::app_version()))
        .timeout(FETCH_TIMEOUT)
        .connect_timeout(FETCH_TIMEOUT)
        .build()
        .ok()?;
    // Optional auth against the API rate limit; the value is never printed or stored. It goes only to
    // github.com (not with another GH_HOST), and a 401/403 with a token retries once without it.
    let host_ok = std::env::var("GH_HOST")
        .map(|h| h.is_empty() || h == "github.com")
        .unwrap_or(true);
    let token = ["GITHUB_TOKEN", "GH_TOKEN"]
        .iter()
        .find_map(|k| std::env::var(k).ok().filter(|v| !v.is_empty()))
        .filter(|_| host_ok);
    let get = |token: Option<&String>| {
        let mut request = client.get(crate::upgrade::RELEASES_LATEST_API);
        if let Some(token) = token {
            request = request.bearer_auth(token);
        }
        request.send().ok()
    };
    let mut response = get(token.as_ref())?;
    if token.is_some() && matches!(response.status().as_u16(), 401 | 403) {
        response = get(None)?;
    }
    let release: Value = response.error_for_status().ok()?.json().ok()?;
    latest_from_release(&release).map(|v| format!("v{v}"))
}

fn message(notice: &Notice) -> String {
    format!(
        "agentic v{} is available (installed v{}). Run `agentic upgrade` to update the binary and this \
         project's agentic files. The next reminder comes in {} days.",
        notice.latest, notice.installed, notice.interval_days
    )
}

/// Hook output. Claude Code and Codex show `systemMessage` to the user and also get the agent line; OpenCode
/// has no user-visible channel for a server plugin, so the agent line asks the agent to say it.
pub fn render(notice: &Notice, format: &str) -> Value {
    let text = message(notice);
    let seen = matches!(format, "claude" | "codex");
    let context = if seen {
        format!(
            "Agentic update: {text} Claude Code and Codex may have shown this to the user. If the user did not \
             see it, mention it briefly in your first reply. Run `agentic upgrade` only after the user agrees \
             (for example, answers \"yes\"); never upgrade on your own. If the user declines, drop it."
        )
    } else {
        format!(
            "Agentic update: {text} At the start of your first reply, tell the user this in one sentence and \
             offer to run `agentic upgrade`. Run it only after the user agrees; never upgrade on your own. If \
             the user declines, drop it."
        )
    };
    let mut out = json!({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}});
    if seen {
        out["systemMessage"] = json!(text);
    }
    out
}

/// `agentic __update-check [--format claude|codex|opencode]`. Prints nothing when there is no reminder; never
/// returns an error.
pub fn run_hook(rest: &[String]) {
    let format = rest
        .windows(2)
        .find(|w| w[0] == "--format")
        .map(|w| w[1].as_str())
        .unwrap_or("claude");
    let Ok(app) = App::new() else { return };
    let days = interval_days(
        &app.app_config_json_file(),
        std::env::var("AGENTIC_UPDATE_CHECK").ok().as_deref(),
    );
    let now = chrono::Utc::now().timestamp();
    if let Some(notice) = check(
        &state_file(&app),
        &crate::app_version(),
        now,
        days,
        &release_fetcher,
    ) {
        println!("{}", render(&notice, format));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::Cell;

    fn fixed(tag: &'static str) -> impl Fn() -> Option<String> {
        move || Some(tag.to_string())
    }

    #[test]
    fn newer_release_notifies_then_snoozes_for_the_interval() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("c/update-check.json");
        let n = check(&path, "14.0.1", 1_000, 7, &fixed("v15.0.0")).unwrap();
        assert_eq!(n.latest, "15.0.0");
        assert_eq!(n.installed, "14.0.1");
        let state = read_state(&path);
        assert_eq!(state.last_check_at, Some(1_000));
        assert_eq!(state.last_notified_at, Some(1_000));
        assert_eq!(state.latest_seen.as_deref(), Some("15.0.0"));
        // Inside the interval: silent, and no lookup.
        let calls = Cell::new(0);
        let counting = || {
            calls.set(calls.get() + 1);
            Some("v15.0.0".to_string())
        };
        assert!(check(&path, "14.0.1", 1_000 + 7 * DAY - 1, 7, &counting).is_none());
        assert_eq!(calls.get(), 0);
        // After the interval: the reminder comes again.
        assert!(check(&path, "14.0.1", 1_000 + 7 * DAY, 7, &counting).is_some());
        assert_eq!(calls.get(), 1);
    }

    #[test]
    fn current_or_older_release_is_silent_but_recorded() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("u.json");
        assert!(check(&path, "14.0.1", 5, 7, &fixed("v14.0.1")).is_none());
        let state = read_state(&path);
        assert_eq!(state.last_check_at, Some(5));
        assert_eq!(state.last_notified_at, None);
        assert_eq!(state.latest_seen.as_deref(), Some("14.0.1"));
        assert!(check(&path, "14.0.1", 5 + 8 * DAY, 7, &fixed("v13.0.0")).is_none());
    }

    #[test]
    fn disabled_interval_never_looks_up() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("u.json");
        let panics = || -> Option<String> { panic!("no lookup when off") };
        assert!(check(&path, "1.0.0", 1, 0, &panics).is_none());
        assert!(!path.exists());
    }

    #[test]
    fn failed_lookup_is_silent_and_not_retried_early() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("u.json");
        assert!(check(&path, "1.0.0", 100, 7, &|| None).is_none());
        assert_eq!(read_state(&path).last_check_at, Some(100));
        let calls = Cell::new(0);
        let counting = || {
            calls.set(calls.get() + 1);
            Some("v9.0.0".to_string())
        };
        assert!(check(&path, "1.0.0", 200, 7, &counting).is_none());
        assert_eq!(calls.get(), 0);
        // Junk from the server is a failure too.
        assert!(check(&path, "1.0.0", 100 + 8 * DAY, 7, &fixed("not-a-version")).is_none());
    }

    #[test]
    fn corrupt_state_and_clock_skew_count_as_due() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("u.json");
        std::fs::write(&path, "{broken").unwrap();
        assert!(check(&path, "1.0.0", 10, 7, &fixed("v2.0.0")).is_some());
        // The last check lies in the future (clock set back).
        assert!(check(&path, "1.0.0", 5, 7, &fixed("v2.0.0")).is_some());
    }

    #[test]
    fn versions_compare_as_numbers_and_skip_prereleases() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("u.json");
        assert!(check(&path, "9.0.0", 1, 1, &fixed("v10.0.0")).is_some());
        assert!(check(&path, "14.9.0", 1 + 2 * DAY, 1, &fixed("v14.10.0")).is_some());
        assert_eq!(release_version("v15.0.0-rc.1"), None);
        assert_eq!(release_version("15.0.0+build"), None);
        assert_eq!(release_version("v15.0"), None);
        assert_eq!(release_version("v15.0.0").as_deref(), Some("15.0.0"));
        assert!(latest_from_release(&json!({"tag_name": "v15.0.0", "prerelease": true})).is_none());
        assert!(latest_from_release(&json!({"tag_name": "v15.0.0", "draft": true})).is_none());
        assert_eq!(
            latest_from_release(&json!({"tag_name": "v15.0.0"})).as_deref(),
            Some("15.0.0")
        );
    }

    #[test]
    fn unwritable_state_means_no_lookup() {
        let dir = tempfile::tempdir().unwrap();
        // The state path lies below a regular file, so it cannot be created.
        let blocker = dir.path().join("file");
        std::fs::write(&blocker, "x").unwrap();
        let path = blocker.join("sub/u.json");
        let panics = || -> Option<String> { panic!("no lookup without a saved attempt") };
        assert!(check(&path, "1.0.0", 1, 7, &panics).is_none());
    }

    #[test]
    fn state_write_leaves_no_temp_files() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("u.json");
        assert!(check(&path, "1.0.0", 1, 7, &fixed("v2.0.0")).is_some());
        let names: Vec<_> = std::fs::read_dir(dir.path())
            .unwrap()
            .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
            .collect();
        assert_eq!(names, ["u.json"]);
    }

    #[test]
    fn interval_comes_from_config_and_env() {
        let dir = tempfile::tempdir().unwrap();
        let cfg = dir.path().join("config.json");
        assert_eq!(interval_days(&cfg, None), 7);
        std::fs::write(
            &cfg,
            r#"{"update_check": {"interval_days": 30}, "opencode": {}}"#,
        )
        .unwrap();
        assert_eq!(interval_days(&cfg, None), 30);
        assert_eq!(interval_days(&cfg, Some("1")), 30);
        for off in ["0", "off", "False", " no "] {
            assert_eq!(interval_days(&cfg, Some(off)), 0, "{off}");
        }
        std::fs::write(&cfg, r#"{"update_check": {"interval_days": 0}}"#).unwrap();
        assert_eq!(interval_days(&cfg, None), 0);
        std::fs::write(&cfg, "garbage").unwrap();
        assert_eq!(interval_days(&cfg, None), 7);
    }

    #[test]
    fn output_per_host() {
        let n = Notice {
            latest: "15.0.0".into(),
            installed: "14.0.1".into(),
            interval_days: 7,
        };
        for host in ["claude", "codex"] {
            let v = render(&n, host);
            let message = v["systemMessage"].as_str().unwrap();
            assert!(message.contains("v15.0.0") && message.contains("v14.0.1"));
            assert!(message.contains("agentic upgrade"));
            let ctx = v["hookSpecificOutput"]["additionalContext"]
                .as_str()
                .unwrap();
            assert!(
                ctx.contains("only after the user agrees")
                    && ctx.contains("never upgrade on your own")
            );
            assert!(!ctx.contains("already saw"));
            assert_eq!(v["hookSpecificOutput"]["hookEventName"], "SessionStart");
        }
        let v = render(&n, "opencode");
        assert!(v.get("systemMessage").is_none());
        let ctx = v["hookSpecificOutput"]["additionalContext"]
            .as_str()
            .unwrap();
        assert!(
            ctx.contains("start of your first reply") && ctx.contains("never upgrade on your own")
        );
    }
}
