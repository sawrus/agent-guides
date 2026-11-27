//! GitHub star counts of the skill pack presets for the TUI "Skills" step (docs/skill-packs.md).
//! Counts come from `GET https://api.github.com/repos/<owner>/<repo>` (`stargazers_count`) and stay in
//! `~/.cache/agentic/github-stars.json` for 24 hours. All requests share one short deadline, so the TUI
//! never waits longer than [`DEADLINE`]. Offline, rate-limited, or late: the last cached count with its
//! date, else the snapshot that the preset carries. `AGENTIC_NO_GITHUB_STARS=1` turns the requests off.
//! Only the TUI asks; a non-interactive `install` never does.

use crate::app::App;
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::mpsc;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

/// The longest wait for all requests together.
pub const DEADLINE: Duration = Duration::from_secs(2);
/// A cached count newer than this is shown as live.
pub const MAX_AGE_SECS: u64 = 24 * 60 * 60;
pub const DISABLE_ENV: &str = "AGENTIC_NO_GITHUB_STARS";
const CACHE_FILE: &str = "github-stars.json";
const API: &str = "https://api.github.com/repos";

/// Star count of one repository as the TUI shows it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Stars {
    pub count: u64,
    /// Date (`YYYY-MM-DD`) of an old count; None for a count from the last 24 hours.
    pub date: Option<String>,
}

impl Stars {
    /// `★ 333.8k`, or `★ 333.8k (2026-11-27)` for an old count.
    pub fn label(&self) -> String {
        match &self.date {
            Some(date) => format!("★ {} ({date})", format_count(self.count)),
            None => format!("★ {}", format_count(self.count)),
        }
    }
}

/// `950`, `333.8k`, `1.2M`: one decimal for thousands and millions, without a trailing `.0`.
pub fn format_count(count: u64) -> String {
    let short = |value: f64, unit: &str| {
        let text = format!("{:.1}", (value * 10.0).floor() / 10.0);
        format!("{}{unit}", text.strip_suffix(".0").unwrap_or(&text))
    };
    if count >= 1_000_000 {
        short(count as f64 / 1_000_000.0, "M")
    } else if count >= 1_000 {
        short(count as f64 / 1_000.0, "k")
    } else {
        count.to_string()
    }
}

/// `~/.cache/agentic/github-stars.json` (`$XDG_CACHE_HOME/agentic/...` when set).
pub fn cache_path(app: &App) -> PathBuf {
    crate::source::cache_root(app, CACHE_FILE)
}

/// Cache entries: repository -> (count, unix time of the fetch).
pub fn read_cache(path: &Path) -> BTreeMap<String, (u64, u64)> {
    let data: Value = std::fs::read(path)
        .ok()
        .and_then(|b| serde_json::from_slice(&b).ok())
        .unwrap_or(Value::Null);
    let mut out = BTreeMap::new();
    for (repo, item) in data.as_object().into_iter().flatten() {
        if let (Some(count), Some(at)) = (item["stars"].as_u64(), item["fetched_at"].as_u64()) {
            out.insert(repo.clone(), (count, at));
        }
    }
    out
}

pub fn write_cache(path: &Path, cache: &BTreeMap<String, (u64, u64)>) {
    let data: serde_json::Map<String, Value> = cache
        .iter()
        .map(|(repo, (count, at))| (repo.clone(), json!({"stars": count, "fetched_at": at})))
        .collect();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(text) = serde_json::to_string_pretty(&Value::Object(data)) {
        let _ = std::fs::write(path, text + "\n");
    }
}

pub fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or_default()
}

fn date_of(secs: u64) -> String {
    chrono::DateTime::from_timestamp(secs as i64, 0)
        .map(|t| t.format("%Y-%m-%d").to_string())
        .unwrap_or_default()
}

/// A function that asks GitHub for the counts of `repos` within the deadline; a repository without
/// an answer is missing from the result. Tests pass their own.
pub type Fetcher<'a> = dyn Fn(&[String], Duration) -> BTreeMap<String, u64> + 'a;

/// The counts of `repos` (`owner/repo`) with their snapshots `(count, date)`: a fresh cache entry, else a
/// fetch, else the newer of the old cache entry and the snapshot, with its date. New counts go to the
/// cache file.
pub fn resolve(
    cache_file: &Path,
    repos: &[(String, u64, String)],
    now: u64,
    fetch: &Fetcher<'_>,
) -> BTreeMap<String, Stars> {
    let mut cache = read_cache(cache_file);
    let fresh = |entry: Option<&(u64, u64)>| {
        entry.is_some_and(|(_, at)| *at <= now && now - *at < MAX_AGE_SECS)
    };
    let missing: Vec<String> = repos
        .iter()
        .map(|(repo, _, _)| repo.clone())
        .filter(|repo| !fresh(cache.get(repo)))
        .collect();
    let fetched = if missing.is_empty() {
        BTreeMap::new()
    } else {
        fetch(&missing, DEADLINE)
    };
    if !fetched.is_empty() {
        for (repo, count) in &fetched {
            cache.insert(repo.clone(), (*count, now));
        }
        write_cache(cache_file, &cache);
    }
    let mut out = BTreeMap::new();
    for (repo, snapshot, snapshot_date) in repos {
        let stars = match cache.get(repo) {
            Some((count, _)) if fresh(cache.get(repo)) => Stars {
                count: *count,
                date: None,
            },
            Some((count, at)) if date_of(*at).as_str() > snapshot_date.as_str() => Stars {
                count: *count,
                date: Some(date_of(*at)),
            },
            _ => Stars {
                count: *snapshot,
                date: Some(snapshot_date.clone()),
            },
        };
        out.insert(repo.clone(), stars);
    }
    out
}

/// One request per repository, all in parallel, all within `deadline`. Unauthenticated unless
/// `GITHUB_TOKEN` or `GH_TOKEN` is set. Returns nothing when [`DISABLE_ENV`] is `1`.
pub fn fetch_live(repos: &[String], deadline: Duration) -> BTreeMap<String, u64> {
    let mut out = BTreeMap::new();
    if std::env::var(DISABLE_ENV).as_deref() == Ok("1") {
        return out;
    }
    let token = github_token(std::env::var("GH_HOST").ok().as_deref(), |k| {
        std::env::var(k).ok()
    });
    let Ok(client) = reqwest::blocking::Client::builder()
        .user_agent(format!("agentic/{}", crate::app_version()))
        .timeout(deadline)
        .connect_timeout(deadline)
        .build()
    else {
        return out;
    };
    let (tx, rx) = mpsc::channel();
    for repo in repos {
        let (tx, client, token, repo) = (tx.clone(), client.clone(), token.clone(), repo.clone());
        std::thread::spawn(move || {
            let ask = |token: Option<&str>| {
                let mut request = client
                    .get(format!("{API}/{repo}"))
                    .header("Accept", "application/vnd.github+json");
                if let Some(token) = token {
                    request = request.bearer_auth(token);
                }
                request.send()
            };
            let mut response = ask(token.as_deref());
            // A token of another installation (or an expired one): ask once more without it.
            if token.is_some()
                && response
                    .as_ref()
                    .is_ok_and(|r| retry_without_token(r.status().as_u16()))
            {
                response = ask(None);
            }
            let count = response
                .and_then(|r| r.error_for_status())
                .and_then(|r| r.json::<Value>())
                .ok()
                .and_then(|v| v["stargazers_count"].as_u64());
            let _ = tx.send((repo, count));
        });
    }
    drop(tx);
    let end = Instant::now() + deadline;
    for _ in repos {
        let left = end.saturating_duration_since(Instant::now());
        match rx.recv_timeout(left) {
            Ok((repo, Some(count))) => {
                out.insert(repo, count);
            }
            Ok((_, None)) => {}
            Err(_) => break,
        }
    }
    out
}

/// `GITHUB_TOKEN` or `GH_TOKEN` for api.github.com: only when `GH_HOST` is unset or `github.com`, since
/// otherwise the token likely belongs to another GitHub installation.
pub fn github_token(gh_host: Option<&str>, var: impl Fn(&str) -> Option<String>) -> Option<String> {
    let host = gh_host.map(str::trim).unwrap_or_default();
    if !host.is_empty() && !host.eq_ignore_ascii_case("github.com") {
        return None;
    }
    ["GITHUB_TOKEN", "GH_TOKEN"].iter().find_map(|k| {
        var(k)
            .map(|v| v.trim().to_string())
            .filter(|v| !v.is_empty())
    })
}

/// 401 and 403 with a token: the request is repeated once without it.
pub fn retry_without_token(status: u16) -> bool {
    matches!(status, 401 | 403)
}

/// The star labels of every preset, keyed by preset id, with the cache file `cache_file`.
pub fn preset_stars(cache_file: &Path, fetch: &Fetcher<'_>) -> BTreeMap<String, Stars> {
    let repos: Vec<(String, u64, String)> = crate::skill_packs::PRESETS
        .iter()
        .map(|p| (p.repo.to_string(), p.stars, p.stars_date.to_string()))
        .collect();
    let by_repo = resolve(cache_file, &repos, now_secs(), fetch);
    crate::skill_packs::PRESETS
        .iter()
        .filter_map(|p| by_repo.get(p.repo).map(|s| (p.id.to_string(), s.clone())))
        .collect()
}

/// [`preset_stars`] with [`fetch_live`], started in the background so that GitHub answers while the
/// user goes through the earlier TUI steps. [`Prefetch::wait`] waits at most [`DEADLINE`] more and
/// then shows the cached or snapshot counts.
pub struct Prefetch {
    rx: mpsc::Receiver<BTreeMap<String, Stars>>,
    fallback: BTreeMap<String, Stars>,
}

impl Prefetch {
    pub fn start(app: &App) -> Prefetch {
        let file = cache_path(app);
        let offline = |_: &[String], _: Duration| BTreeMap::new();
        let fallback = preset_stars(&file, &offline);
        let (tx, rx) = mpsc::channel();
        std::thread::spawn(move || {
            let _ = tx.send(preset_stars(&file, &fetch_live));
        });
        Prefetch { rx, fallback }
    }

    pub fn wait(self) -> BTreeMap<String, Stars> {
        self.rx
            .recv_timeout(DEADLINE + Duration::from_millis(200))
            .unwrap_or(self.fallback)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    const DAY: u64 = 24 * 60 * 60;
    // 2026-11-28T00:00:00Z
    const NOW: u64 = 1_795_824_000;

    fn repos() -> Vec<(String, u64, String)> {
        vec![
            ("mattpocock/skills".into(), 333_800, "2026-11-27".into()),
            ("obra/superpowers".into(), 327_800, "2026-11-27".into()),
        ]
    }

    #[test]
    fn formats_counts() {
        assert_eq!(format_count(0), "0");
        assert_eq!(format_count(999), "999");
        assert_eq!(format_count(1_000), "1k");
        assert_eq!(format_count(1_049), "1k");
        assert_eq!(format_count(201_211), "201.2k");
        assert_eq!(format_count(333_841), "333.8k");
        assert_eq!(format_count(999_999), "999.9k");
        assert_eq!(format_count(1_000_000), "1M");
        assert_eq!(format_count(1_250_000), "1.2M");
        let live = Stars {
            count: 333_841,
            date: None,
        };
        assert_eq!(live.label(), "★ 333.8k");
        let old = Stars {
            count: 333_800,
            date: Some("2026-11-27".into()),
        };
        assert_eq!(old.label(), "★ 333.8k (2026-11-27)");
    }

    #[test]
    fn offline_shows_the_snapshot_with_its_date() {
        let tmp = tempfile::tempdir().unwrap();
        let file = tmp.path().join("agentic/github-stars.json");
        let offline = |_: &[String], _: Duration| BTreeMap::new();
        let stars = resolve(&file, &repos(), NOW, &offline);
        assert_eq!(stars["mattpocock/skills"].label(), "★ 333.8k (2026-11-27)");
        assert_eq!(stars["obra/superpowers"].label(), "★ 327.8k (2026-11-27)");
        assert!(!file.exists(), "nothing fetched, nothing cached");
    }

    #[test]
    fn fetch_writes_the_cache_and_a_fresh_cache_skips_the_fetch() {
        let tmp = tempfile::tempdir().unwrap();
        let file = tmp.path().join("agentic/github-stars.json");
        let calls = AtomicUsize::new(0);
        let live = |repos: &[String], deadline: Duration| {
            calls.fetch_add(1, Ordering::SeqCst);
            assert_eq!(deadline, DEADLINE);
            repos.iter().map(|r| (r.clone(), 400_000)).collect()
        };
        let stars = resolve(&file, &repos(), NOW, &live);
        assert_eq!(stars["obra/superpowers"].label(), "★ 400k");
        assert_eq!(read_cache(&file)["obra/superpowers"], (400_000, NOW));
        // Within 24 hours: no request.
        let stars = resolve(&file, &repos(), NOW + DAY - 1, &live);
        assert_eq!(calls.load(Ordering::SeqCst), 1);
        assert_eq!(stars["mattpocock/skills"].label(), "★ 400k");
        // After 24 hours: a new request; offline, the old count shows with its date.
        let offline = |_: &[String], _: Duration| BTreeMap::new();
        let stars = resolve(&file, &repos(), NOW + 2 * DAY, &offline);
        assert_eq!(stars["mattpocock/skills"].label(), "★ 400k (2026-11-28)");
        let stars = resolve(&file, &repos(), NOW + 2 * DAY, &live);
        assert_eq!(calls.load(Ordering::SeqCst), 2);
        assert_eq!(stars["mattpocock/skills"].date, None);
    }

    #[test]
    fn partial_answers_and_a_broken_cache_file() {
        let tmp = tempfile::tempdir().unwrap();
        let file = tmp.path().join("github-stars.json");
        std::fs::write(&file, "not json").unwrap();
        let one = |_: &[String], _: Duration| [("obra/superpowers".to_string(), 5u64)].into();
        let stars = resolve(&file, &repos(), NOW, &one);
        assert_eq!(stars["obra/superpowers"].label(), "★ 5");
        assert_eq!(stars["mattpocock/skills"].label(), "★ 333.8k (2026-11-27)");
        // Only fetched repositories are asked for again.
        let asked = std::sync::Mutex::new(Vec::new());
        let record = |repos: &[String], _: Duration| {
            asked.lock().unwrap().extend(repos.iter().cloned());
            BTreeMap::new()
        };
        resolve(&file, &repos(), NOW + 1, &record);
        assert_eq!(
            *asked.lock().unwrap(),
            vec!["mattpocock/skills".to_string()]
        );
    }

    #[test]
    fn the_env_switch_turns_requests_off() {
        // With the switch, no request is sent.
        std::env::set_var(DISABLE_ENV, "1");
        assert!(fetch_live(&["obra/superpowers".to_string()], DEADLINE).is_empty());
    }

    #[test]
    fn token_goes_only_to_github_com() {
        let vars = |k: &str| match k {
            "GITHUB_TOKEN" => Some(" ghp_x ".to_string()),
            "GH_TOKEN" => Some("gho_y".to_string()),
            _ => None,
        };
        assert_eq!(github_token(None, vars).as_deref(), Some("ghp_x"));
        assert_eq!(github_token(Some(""), vars).as_deref(), Some("ghp_x"));
        assert_eq!(
            github_token(Some("GitHub.com"), vars).as_deref(),
            Some("ghp_x")
        );
        assert_eq!(github_token(Some("github.example.com"), vars), None);
        let gh_only = |k: &str| (k == "GH_TOKEN").then(|| "gho_y".to_string());
        assert_eq!(github_token(None, gh_only).as_deref(), Some("gho_y"));
        assert_eq!(github_token(None, |_| Some("  ".into())), None);
        assert!(retry_without_token(401) && retry_without_token(403));
        assert!(!retry_without_token(404) && !retry_without_token(200));
    }

    #[test]
    fn preset_stars_cover_every_preset() {
        let tmp = tempfile::tempdir().unwrap();
        let offline = |_: &[String], _: Duration| BTreeMap::new();
        let stars = preset_stars(&tmp.path().join("github-stars.json"), &offline);
        assert_eq!(stars["pocock"].label(), "★ 333.8k (2026-11-27)");
        assert_eq!(stars["superpowers"].label(), "★ 327.8k (2026-11-27)");
        assert_eq!(stars["anthropic"].label(), "★ 201.2k (2026-11-27)");
    }
}
