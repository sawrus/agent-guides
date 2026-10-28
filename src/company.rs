//! Company rules (docs/company-rules.md): rule files from a local directory or a git repository that
//! override pack rules. Install copies them into `.agent/company/` (every host) and, for Claude Code,
//! into `.claude/rules/company-*.md`; `exclude` and `replaces:` drop pack rules. A source can also hold
//! company skills (`skills/<name>/`) and workflows (`workflows/<id>.md`), installed like pack ones.

use crate::app::App;
use crate::{manifest, ui, util};
use serde_json::{json, Value};
use std::collections::BTreeSet;
use std::path::{Component, Path, PathBuf};
use std::process::Command;

/// Project directory that holds company rules for every host.
pub const COMPANY_DIR: &str = ".agent/company";
/// The one AGENTS.md line that company rules add.
pub const AGENTS_LINE: &str =
    "Company rules in `.agent/company/` override agent-guides rules on conflict.";
const MARKER: &str = "company";
/// Source subdirectories that hold skills and workflows instead of rules.
pub const SKILLS_DIR: &str = "skills";
pub const WORKFLOWS_DIR: &str = "workflows";

static CHECK_ARTIFACTS_PY: &str = include_str!("../scripts/check_artifacts.py");
static CONTEXT_BUDGET_PY: &str = include_str!("../scripts/context_budget.py");
static CHECK_ARTIFACTS_TOML: &str = include_str!("../scripts/check_artifacts.toml");

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

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CompanyRules {
    pub sources: Vec<Source>,
    /// Pack rule ids `<area>/<spec>/<rule>` that the install skips.
    pub exclude: Vec<String>,
}

impl CompanyRules {
    pub fn is_empty(&self) -> bool {
        self.sources.is_empty() && self.exclude.is_empty()
    }
}

/// True when the project has at least one company rules source.
pub fn configured(app: &App) -> bool {
    app.company_rules
        .as_ref()
        .is_some_and(|c| !c.sources.is_empty())
}

/// `<url>[#ref][:subdir]`. A subdir needs the `#`: `<url>#:<subdir>` keeps the default ref.
pub fn parse_git_spec(spec: &str) -> Result<Source, String> {
    let spec = spec.trim();
    let (url, rest) = match spec.rsplit_once('#') {
        Some((url, rest)) => (url, rest),
        None => (spec, ""),
    };
    let (git_ref, subdir) = rest.split_once(':').unwrap_or((rest, ""));
    if url.is_empty() {
        return Err(format!("--company-rules-git: missing URL in '{spec}'"));
    }
    let subdir = subdir.trim_matches('/').to_string();
    if !subdir.is_empty() && !is_relative_clean(&subdir) {
        return Err(format!(
            "--company-rules-git: subdir must be a relative path: '{subdir}'"
        ));
    }
    Ok(Source::Git {
        url: url.to_string(),
        git_ref: git_ref.to_string(),
        subdir,
    })
}

/// `area/spec/rule` from `area/spec/rule`, `area/spec/rule.md`, or `areas/area/spec/rules/rule.md`.
pub fn normalize_rule_id(raw: &str) -> String {
    let id = raw.trim().trim_matches('/').trim_end_matches(".md");
    let id = id.strip_prefix("areas/").unwrap_or(id);
    let parts: Vec<&str> = id.split('/').collect();
    match parts.as_slice() {
        [area, spec, "rules", rule] => format!("{area}/{spec}/{rule}"),
        _ => id.to_string(),
    }
}

fn is_relative_clean(path: &str) -> bool {
    let p = Path::new(path);
    !path.is_empty() && p.components().all(|c| matches!(c, Component::Normal(_)))
}

pub fn to_settings(rules: &CompanyRules) -> Value {
    let sources: Vec<Value> = rules
        .sources
        .iter()
        .map(|s| match s {
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
        })
        .collect();
    json!({ "sources": sources, "exclude": rules.exclude })
}

pub fn from_settings(value: &Value) -> Option<CompanyRules> {
    let obj = value.as_object()?;
    let mut rules = CompanyRules::default();
    for item in obj
        .get("sources")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
    {
        let text = |key: &str| item[key].as_str().unwrap_or_default().to_string();
        if let Some(path) = item["path"].as_str().filter(|p| !p.is_empty()) {
            rules.sources.push(Source::Path(path.to_string()));
        } else if let Some(url) = item["git"].as_str().filter(|u| !u.is_empty()) {
            let subdir = text("subdir").trim_matches('/').to_string();
            if !subdir.is_empty() && !is_relative_clean(&subdir) {
                continue;
            }
            rules.sources.push(Source::Git {
                url: url.to_string(),
                git_ref: text("ref"),
                subdir,
            });
        }
    }
    for id in obj
        .get("exclude")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
    {
        util::unique_append(&mut rules.exclude, &normalize_rule_id(id));
    }
    Some(rules)
}

/// Replay: CLI sources replace the saved ones; CLI excludes add to the saved ones.
pub fn merge_saved(app: &mut App, saved: CompanyRules) {
    let rules = app.company_rules.get_or_insert_with(Default::default);
    if rules.sources.is_empty() {
        rules.sources = saved.sources;
    }
    for id in saved.exclude {
        util::unique_append(&mut rules.exclude, &id);
    }
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

fn source_id(source: &Source) -> String {
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

/// One rule file of a source.
#[derive(Debug, Clone)]
pub struct RuleFile {
    pub source_id: String,
    /// Path below the source root, `/`-separated (`software/api.md`).
    pub rel: String,
    pub content: String,
    /// The source is `.agent/company` itself: the file stays where it is.
    pub in_place: bool,
}

#[derive(Debug, Default)]
pub struct Prepared {
    pub files: Vec<RuleFile>,
    /// Skill files; `rel` is `<name>/<path>` below the source's `skills/`.
    pub skills: Vec<RuleFile>,
    /// Workflow files; `rel` is `<id>.md` below the source's `workflows/`.
    pub workflows: Vec<RuleFile>,
    /// Files (`path`, `source`) that a source which cannot be read installed before; they stay.
    pub kept: Vec<(String, String)>,
}

fn front(content: &str) -> &str {
    content
        .strip_prefix("---\n")
        .or_else(|| content.strip_prefix("---\r\n"))
        .and_then(|rest| rest.split_once("\n---"))
        .map(|(meta, _)| meta)
        .unwrap_or("")
}

/// Values of a frontmatter key: `key: a`, `key: [a, b]`, or a block list.
pub fn front_list(content: &str, key: &str) -> Vec<String> {
    let clean = |v: &str| v.trim().trim_matches(['"', '\'']).trim().to_string();
    let mut out = Vec::new();
    let mut lines = front(content).lines().peekable();
    while let Some(line) = lines.next() {
        let Some(value) = line.strip_prefix(&format!("{key}:")) else {
            continue;
        };
        let value = value.trim();
        if let Some(inner) = value.strip_prefix('[').and_then(|v| v.strip_suffix(']')) {
            out.extend(inner.split(',').map(clean).filter(|v| !v.is_empty()));
        } else if !value.is_empty() {
            out.push(clean(value));
        } else {
            while let Some(next) = lines.peek() {
                let Some(item) = next.trim_start().strip_prefix("- ") else {
                    break;
                };
                if !next.starts_with([' ', '-']) {
                    break;
                }
                out.push(clean(item));
                lines.next();
            }
        }
    }
    out
}

fn has_key(content: &str, key: &str) -> bool {
    front(content)
        .lines()
        .any(|line| line.starts_with(&format!("{key}:")))
}

fn is_manual(content: &str) -> bool {
    front(content)
        .lines()
        .any(|line| line.trim() == "trigger: manual")
}

/// True for a file that agentic wrote (marker in the frontmatter), e.g. a copy from another source.
fn is_agentic_copy(content: &str) -> bool {
    front(content)
        .lines()
        .any(|line| line.trim() == "generated_by: agentic")
}

fn collect_md(root: &Path, dir: &Path, out: &mut Vec<(String, String)>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    let mut entries: Vec<_> = entries.filter_map(|e| e.ok()).collect();
    entries.sort_by_key(|e| e.file_name());
    for entry in entries {
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with('.') {
            continue;
        }
        let path = entry.path();
        let Ok(kind) = entry.file_type() else {
            continue;
        };
        if kind.is_dir() && dir == root && (name == SKILLS_DIR || name == WORKFLOWS_DIR) {
            continue;
        }
        if kind.is_dir() {
            collect_md(root, &path, out);
        } else if kind.is_file() && name.ends_with(".md") && !name.eq_ignore_ascii_case("README.md")
        {
            if let (Ok(rel), Ok(text)) = (path.strip_prefix(root), std::fs::read_to_string(&path)) {
                out.push((rel.to_string_lossy().replace('\\', "/"), text));
            }
        }
    }
}

/// Every file below `dir` (skills carry scripts and templates); dot entries are skipped.
fn collect_all(root: &Path, dir: &Path, out: &mut Vec<(String, Option<String>)>) {
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

/// Skills (`skills/<name>/**`) and workflows (`workflows/<id>.md`) of one source root.
fn collect_assets(
    app: &mut App,
    root: &Path,
    id: &str,
    seen: &mut BTreeSet<String>,
    prepared: &mut Prepared,
) {
    let mut skills = Vec::new();
    collect_all(&root.join(SKILLS_DIR), &root.join(SKILLS_DIR), &mut skills);
    for (rel, content) in skills {
        if !rel.contains('/') {
            ui::warn(
                app,
                &format!("Company skills: {SKILLS_DIR}/{rel} from {id} is not inside a skill directory; skipped"),
            );
            continue;
        }
        push_asset(
            app,
            id,
            SKILLS_DIR,
            rel,
            content,
            seen,
            &mut prepared.skills,
        );
    }
    let mut workflows = Vec::new();
    collect_md(
        &root.join(WORKFLOWS_DIR),
        &root.join(WORKFLOWS_DIR),
        &mut workflows,
    );
    for (rel, content) in workflows {
        if rel.contains('/') {
            continue;
        }
        push_asset(
            app,
            id,
            WORKFLOWS_DIR,
            rel,
            Some(content),
            seen,
            &mut prepared.workflows,
        );
    }
}

fn push_asset(
    app: &mut App,
    id: &str,
    kind: &str,
    rel: String,
    content: Option<String>,
    seen: &mut BTreeSet<String>,
    out: &mut Vec<RuleFile>,
) {
    let Some(content) = content else {
        ui::warn(
            app,
            &format!("Company {kind}: {kind}/{rel} from {id} is not UTF-8 text; skipped"),
        );
        return;
    };
    if !seen.insert(format!("{kind}/{rel}")) {
        ui::warn(
            app,
            &format!("Company {kind}: {kind}/{rel} from {id} repeats an earlier source; skipped"),
        );
        return;
    }
    out.push(RuleFile {
        source_id: id.to_string(),
        rel,
        content,
        in_place: false,
    });
}

pub fn cache_root(app: &App) -> PathBuf {
    let base = std::env::var("XDG_CACHE_HOME")
        .ok()
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(|| app.home.join(".cache"));
    base.join("agentic/company")
}

fn git(dir: &Path, args: &[&str]) -> bool {
    let mut cmd = Command::new("git");
    cmd.arg("-C")
        .arg(dir)
        .args(args)
        .env("GIT_TERMINAL_PROMPT", "0")
        .env("GCM_INTERACTIVE", "never")
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null());
    if std::env::var_os("GIT_SSH_COMMAND").is_none() {
        cmd.env("GIT_SSH_COMMAND", "ssh -o BatchMode=yes");
    }
    cmd.status().is_ok_and(|s| s.success())
}

/// Fetch `url` at `git_ref` into the cache. Returns the checkout, the cached copy when the fetch fails,
/// or None when there is no copy at all.
fn fetch_git(app: &mut App, url: &str, git_ref: &str) -> Option<PathBuf> {
    let dir = cache_root(app).join(util::sha256_hex(url.as_bytes()));
    let shown = redact_url(url);
    let has_checkout = |dir: &Path| git(dir, &["rev-parse", "--verify", "--quiet", "HEAD"]);
    if !dir.join(".git").is_dir()
        && (std::fs::create_dir_all(&dir).is_err()
            || !git(&dir, &["init", "--quiet"])
            || !git(&dir, &["remote", "add", "origin", url]))
    {
        ui::warn(
            app,
            &format!("Company rules: cannot prepare the git cache for {shown}"),
        );
        let _ = std::fs::remove_dir_all(&dir);
        return None;
    }
    let wanted = if git_ref.is_empty() { "HEAD" } else { git_ref };
    let fetched = git(
        &dir,
        &["fetch", "--quiet", "--depth", "1", "origin", wanted],
    ) && git(&dir, &["checkout", "--quiet", "--force", "FETCH_HEAD"])
        && git(&dir, &["clean", "--quiet", "-fdx"]);
    if fetched {
        ui::log(app, &format!("Company rules: fetched {shown} ({wanted})"));
        return Some(dir);
    }
    if has_checkout(&dir) {
        ui::warn(
            app,
            &format!(
                "Company rules: cannot fetch {shown} ({wanted}); using the cached copy in {}",
                dir.display()
            ),
        );
        return Some(dir);
    }
    ui::warn(
        app,
        &format!("Company rules: cannot fetch {shown} ({wanted}) and no cached copy exists"),
    );
    let _ = std::fs::remove_dir_all(&dir);
    None
}

fn base_dir(app: &App) -> PathBuf {
    app.company_base_dir
        .clone()
        .unwrap_or_else(|| PathBuf::from(&app.project_dir))
}

fn same_dir(a: &Path, b: &Path) -> bool {
    match (a.canonicalize(), b.canonicalize()) {
        (Ok(a), Ok(b)) => a == b,
        _ => a == b,
    }
}

/// Read every source, then fill `app.excluded_pack_rules` from `exclude` and `replaces:`.
pub fn prepare(app: &mut App) -> crate::Result<Prepared> {
    app.excluded_pack_rules.clear();
    let Some(rules) = app.company_rules.clone() else {
        return Ok(Prepared::default());
    };
    let mut prepared = Prepared::default();
    let mut seen: BTreeSet<String> = BTreeSet::new();
    let base = base_dir(app);
    let project = PathBuf::from(&app.project_dir);
    for source in &rules.sources {
        let id = source_id(source);
        if app.dry_run {
            ui::log(app, &format!("DRY-RUN read company rules from {id}"));
            continue;
        }
        let (root, in_place) = match source {
            Source::Path(path) => {
                let abs = if Path::new(path).is_absolute() {
                    PathBuf::from(path)
                } else {
                    base.join(path)
                };
                if same_dir(&abs, &base.join(COMPANY_DIR)) {
                    (Some(project.join(COMPANY_DIR)), true)
                } else if abs.is_dir() {
                    (Some(abs), false)
                } else {
                    ui::warn(
                        app,
                        &format!("Company rules: directory not found: {}", abs.display()),
                    );
                    (None, false)
                }
            }
            Source::Git {
                url,
                git_ref,
                subdir,
            } => match fetch_git(app, url, git_ref) {
                Some(dir) => {
                    let root = if subdir.is_empty() {
                        dir
                    } else {
                        dir.join(subdir)
                    };
                    if root.is_dir() {
                        (Some(root), false)
                    } else {
                        ui::warn(
                            app,
                            &format!("Company rules: '{subdir}' not found in {}", redact_url(url)),
                        );
                        (None, false)
                    }
                }
                None => (None, false),
            },
        };
        let Some(root) = root else {
            prepared.kept.extend(previous_files(&project, &id));
            continue;
        };
        collect_assets(app, &root, &id, &mut seen, &mut prepared);
        let mut found = Vec::new();
        collect_md(&root, &root, &mut found);
        for (rel, content) in found {
            // In place, the copies of other sources sit next to the company's own files.
            if in_place && is_agentic_copy(&content) {
                continue;
            }
            if !seen.insert(rel.clone()) {
                ui::warn(
                    app,
                    &format!("Company rules: {rel} from {id} repeats an earlier source; skipped"),
                );
                continue;
            }
            prepared.files.push(RuleFile {
                source_id: id.clone(),
                rel,
                content,
                in_place,
            });
        }
    }
    for id in &rules.exclude {
        add_exclusion(app, id, "company_rules.exclude");
    }
    let mut replacing: Vec<(String, String)> = prepared
        .files
        .iter()
        .map(|f| (format!("{COMPANY_DIR}/{}", f.rel), f.content.clone()))
        .collect();
    for (path, _) in &prepared.kept {
        if path.starts_with(&format!("{COMPANY_DIR}/")) {
            let text = std::fs::read_to_string(project.join(path)).unwrap_or_default();
            replacing.push((path.clone(), text));
        }
    }
    for (path, content) in replacing {
        for id in front_list(&content, "replaces") {
            add_exclusion(
                app,
                &normalize_rule_id(&id),
                &format!("replaces: in {path}"),
            );
        }
    }
    Ok(prepared)
}

fn add_exclusion(app: &mut App, id: &str, why: &str) {
    let exists = id.split('/').count() == 3 && {
        let (area, rest) = id.split_once('/').unwrap();
        let (spec, rule) = rest.split_once('/').unwrap();
        app.kb
            .read_file(&format!("areas/{area}/{spec}/rules/{rule}.md"))
            .is_some()
    };
    if !exists {
        ui::warn(
            app,
            &format!("Company rules: `{id}` ({why}) names no pack rule"),
        );
        return;
    }
    if app.excluded_pack_rules.insert(id.to_string()) {
        ui::log(app, &format!("Company rules: skip pack rule {id} ({why})"));
    }
}

/// `area/spec/rule` when `src_rel`/`rel` is a pack rule file (`areas/<area>/<spec>/rules` + `<rule>.md`).
pub fn pack_rule_id(src_rel: &str, rel: &str) -> Option<String> {
    let parts: Vec<&str> = src_rel.split('/').collect();
    let ["areas", area, spec, "rules"] = parts.as_slice() else {
        return None;
    };
    let rule = rel.strip_suffix(".md").filter(|r| !r.contains('/'))?;
    Some(format!("{area}/{spec}/{rule}"))
}

/// Claude Code copy name: `.claude/rules/company-<area>-<name>.md`.
pub fn claude_name(rel: &str) -> String {
    format!("company-{}", rel.replace('/', "-"))
}

/// Write the prepared files: `.agent/company/<rel>` (unless in place) and the Claude Code copies.
pub fn install(app: &mut App, project_dir: &Path, prepared: &Prepared) -> crate::Result<()> {
    if app.company_rules.is_none() || app.dry_run {
        return Ok(());
    }
    let claude = app.selected_agent_os_contains("claude");
    for file in &prepared.files {
        let source_ref = format!("company:{}/{}", file.source_id, file.rel);
        if !file.in_place {
            let dest = project_dir.join(COMPANY_DIR).join(&file.rel);
            write(app, &file.content, &dest, &source_ref)?;
        }
        if !claude {
            continue;
        }
        if is_manual(&file.content) {
            continue;
        }
        if !has_key(&file.content, "paths") {
            ui::warn(
                app,
                &format!(
                    "Company rule {COMPANY_DIR}/{} has no `paths:`; Claude Code loads it in every session",
                    file.rel
                ),
            );
        }
        let dest = project_dir
            .join(".claude/rules")
            .join(claude_name(&file.rel));
        write(app, &file.content, &dest, &source_ref)?;
    }
    install_assets(app, project_dir, prepared)?;
    for (path, source) in &prepared.kept {
        if !app.managed_records.iter().any(|r| &r.path == path) {
            manifest::register_managed_file(app, &project_dir.join(path), source, MARKER, false);
        }
    }
    if !app.upgrade_mode {
        remove_excluded(app, project_dir)?;
    }
    Ok(())
}

/// Destination directories of `bucket` (skills, workflows) for the selected hosts plus `.agent/`.
fn asset_dirs(app: &App, bucket: &str) -> Vec<String> {
    let mut dirs = Vec::new();
    for target in app
        .selected_agent_os
        .iter()
        .map(String::as_str)
        .chain(["agents"])
    {
        let dir = crate::agentsmd::get_dest_dir(target, bucket);
        if dir != "-" {
            util::unique_append(&mut dirs, &dir);
        }
    }
    dirs
}

/// Company skills and workflows go where pack ones go; written after the pack, a company file with the
/// same name replaces the pack file. Claude Code gets a `.claude/commands/<id>.md` wrapper per workflow.
fn install_assets(app: &mut App, project_dir: &Path, prepared: &Prepared) -> crate::Result<()> {
    for (bucket, files) in [
        (SKILLS_DIR, &prepared.skills),
        (WORKFLOWS_DIR, &prepared.workflows),
    ] {
        for dir in asset_dirs(app, bucket) {
            for file in files {
                let source_ref = format!("company:{}/{bucket}/{}", file.source_id, file.rel);
                write(
                    app,
                    &file.content,
                    &project_dir.join(&dir).join(&file.rel),
                    &source_ref,
                )?;
            }
        }
    }
    if app.selected_agent_os_contains("claude") {
        let team = crate::profile::is_team_for(app, "claude");
        for file in &prepared.workflows {
            let id = file.rel.trim_end_matches(".md");
            let source_ref = format!("company:{}/{WORKFLOWS_DIR}/{}", file.source_id, file.rel);
            let content = crate::claude::workflow_command(id, &file.content, team);
            write(
                app,
                &content,
                &project_dir.join(format!(".claude/commands/{id}.md")),
                &source_ref,
            )?;
        }
    }
    Ok(())
}

/// The managed-file rules protect user files once a manifest exists; before the first install a file
/// without the agentic marker belongs to the user as well.
fn write(app: &mut App, content: &str, dest: &Path, source_ref: &str) -> crate::Result<()> {
    let first_install = !app.upgrade_mode && !app.project_manifest_path().is_file();
    if first_install && std::fs::read_to_string(dest).is_ok_and(|text| !is_agentic_copy(&text)) {
        let rel = app.project_rel_path(dest);
        ui::warn(
            app,
            &format!("Company rules: kept the existing user file {rel}"),
        );
        app.record_skipped(&rel);
        return Ok(());
    }
    manifest::write_managed_file(app, content, dest, source_ref, MARKER)
}

/// A repeated `agentic install` removes the excluded pack rules that an earlier install wrote and the
/// user did not edit (`agentic upgrade` removes them as obsolete artifacts).
fn remove_excluded(app: &mut App, project_dir: &Path) -> crate::Result<()> {
    let manifest: Value = std::fs::read(project_dir.join(crate::PROJECT_MANIFEST_NAME))
        .ok()
        .and_then(|b| serde_json::from_slice(&b).ok())
        .unwrap_or(Value::Null);
    for item in manifest["managed_files"].as_array().into_iter().flatten() {
        let (Some(path), Some(source)) = (item["path"].as_str(), item["source"].as_str()) else {
            continue;
        };
        let Some((src_rel, rel)) = source.rsplit_once('/') else {
            continue;
        };
        if !pack_rule_id(src_rel, rel).is_some_and(|id| app.excluded_pack_rules.contains(&id)) {
            continue;
        }
        let Ok(dest) = crate::project_inventory::safe_path(project_dir, path) else {
            continue;
        };
        if !dest.is_file() {
            continue;
        }
        if item["content_hash"].as_str() == util::hash_file(&dest).ok().as_deref() {
            std::fs::remove_file(&dest)?;
            let baseline = crate::project_update::baseline_path(project_dir, path);
            if baseline.is_file() {
                std::fs::remove_file(baseline)?;
            }
            ui::log(app, &format!("Removed excluded pack rule: {path}"));
        } else {
            ui::warn(
                app,
                &format!("Kept excluded pack rule with local edits: {path}"),
            );
        }
    }
    Ok(())
}

/// The files that source `id` installed before (from the manifest), so that an offline upgrade
/// keeps them instead of removing them as obsolete.
fn previous_files(project_dir: &Path, id: &str) -> Vec<(String, String)> {
    let manifest: Value = std::fs::read(project_dir.join(crate::PROJECT_MANIFEST_NAME))
        .ok()
        .and_then(|b| serde_json::from_slice(&b).ok())
        .unwrap_or(Value::Null);
    manifest["managed_files"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|item| Some((item["path"].as_str()?, item["source"].as_str()?)))
        .filter(|(path, source)| {
            source.starts_with(&format!("company:{id}/")) && project_dir.join(path).is_file()
        })
        .map(|(path, source)| (path.to_string(), source.to_string()))
        .collect()
}

/// Run `scripts/check_artifacts.py --project <dir> --json` and print the pack rules that company
/// rules duplicate (ART-K1, ART-K2). Never fails the install.
pub fn report_duplicates(app: &mut App, project_dir: &Path) {
    if !configured(app) || app.dry_run || !project_dir.join(COMPANY_DIR).is_dir() {
        return;
    }
    let report = match run_check(app, project_dir) {
        Ok(report) => report,
        Err(note) => {
            ui::log(
                app,
                &format!("Company rules duplicate check skipped: {note}"),
            );
            return;
        }
    };
    let lines = duplicate_lines(app, &report);
    ui::out(app, "");
    ui::out_color(
        app,
        "=== Company rules vs pack rules ===",
        &app.colors.header.clone(),
    );
    if lines.is_empty() {
        ui::out(app, "No company rule duplicates a pack rule.");
        return;
    }
    for line in lines {
        ui::out(app, &line);
    }
}

fn run_check(app: &App, project_dir: &Path) -> Result<Value, String> {
    let tmp = tempfile::tempdir().map_err(|e| e.to_string())?;
    let root = tmp.path();
    let write = |rel: &str, text: &str| -> Result<(), String> {
        let path = root.join(rel);
        std::fs::create_dir_all(path.parent().unwrap()).map_err(|e| e.to_string())?;
        std::fs::write(path, text).map_err(|e| e.to_string())
    };
    write("scripts/check_artifacts.py", CHECK_ARTIFACTS_PY)?;
    write("scripts/context_budget.py", CONTEXT_BUDGET_PY)?;
    write("scripts/check_artifacts.toml", CHECK_ARTIFACTS_TOML)?;
    write(
        "AGENTS.md",
        &app.kb.read_file("AGENTS.md").unwrap_or_default(),
    )?;
    for (rel, text) in app.kb.walk_files("areas") {
        let parts: Vec<&str> = rel.split('/').collect();
        if parts.len() == 4 && parts[2] == "rules" && rel.ends_with(".md") {
            write(&format!("areas/{rel}"), &text)?;
        }
    }
    let output = Command::new("python3")
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .arg("-I")
        .arg(root.join("scripts/check_artifacts.py"))
        .arg("--root")
        .arg(root)
        .arg("--project")
        .arg(project_dir)
        .arg("--no-baseline")
        .arg("--json")
        .output()
        .map_err(|_| "python3 not found".to_string())?;
    serde_json::from_slice(&output.stdout).map_err(|_| {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let last = stderr.lines().last().unwrap_or("no output").trim();
        format!("python3 check failed ({last}); Python 3.11+ is required")
    })
}

/// Pack rule ids of a pack file name (`.agent/rules/<name>.md`) among the selected specializations.
fn pack_ids(app: &App, pack_rel: &str) -> Vec<String> {
    let name = pack_rel.rsplit('/').next().unwrap_or(pack_rel);
    app.selected_specs
        .iter()
        .filter_map(|key| key.split_once('.'))
        .filter(|(area, spec)| {
            app.kb
                .read_file(&format!("areas/{area}/{spec}/rules/{name}"))
                .is_some()
        })
        .map(|(area, spec)| format!("{area}/{spec}/{}", name.trim_end_matches(".md")))
        .collect()
}

pub fn duplicate_lines(app: &App, report: &Value) -> Vec<String> {
    let mut lines = Vec::new();
    for item in report["replace_suggestions"]
        .as_array()
        .into_iter()
        .flatten()
    {
        let company = item["company"].as_str().unwrap_or_default();
        let pack = item["pack"].as_str().unwrap_or_default();
        let ids: Vec<&str> = item["replaces"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .collect();
        let id = ids.first().copied().unwrap_or_default();
        lines.push(format!(
            "- {company} covers pack rule {pack}: add `replaces: [{id}]` to it, or install with --company-rules-exclude {id}"
        ));
    }
    let restate = regex::Regex::new(r"restate pack rule (\S+)$").unwrap();
    for finding in report["findings"].as_array().into_iter().flatten() {
        let message = finding["message"].as_str().unwrap_or_default();
        let path = finding["path"].as_str().unwrap_or_default();
        match finding["id"].as_str() {
            Some("ART-K2") => {
                let pack = restate
                    .captures(message)
                    .map(|c| c[1].to_string())
                    .unwrap_or_default();
                let hint = pack_ids(app, &pack)
                    .first()
                    .map(|id| {
                        format!("; if it replaces that rule, use --company-rules-exclude {id}")
                    })
                    .unwrap_or_default();
                lines.push(format!("- {path}: {message}{hint}"));
            }
            Some("ART-K1") if !message.starts_with("covers the topic") => {
                lines.push(format!("- {path}: {message}"));
            }
            _ => {}
        }
    }
    lines
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_git_specs() {
        assert_eq!(
            parse_git_spec("git@gitlab.example.com:group/standards.git#main:rules").unwrap(),
            Source::Git {
                url: "git@gitlab.example.com:group/standards.git".into(),
                git_ref: "main".into(),
                subdir: "rules".into()
            }
        );
        assert_eq!(
            parse_git_spec("https://gitlab.example.com/group/standards.git").unwrap(),
            Source::Git {
                url: "https://gitlab.example.com/group/standards.git".into(),
                git_ref: String::new(),
                subdir: String::new()
            }
        );
        assert_eq!(
            parse_git_spec("file:///tmp/x.git#:rules/").unwrap(),
            Source::Git {
                url: "file:///tmp/x.git".into(),
                git_ref: String::new(),
                subdir: "rules".into()
            }
        );
        assert!(parse_git_spec("file:///tmp/x.git#main:../up").is_err());
        assert!(parse_git_spec("#main").is_err());
    }

    #[test]
    fn settings_roundtrip_and_merge() {
        let rules = CompanyRules {
            sources: vec![
                Source::Path(".agent/company".into()),
                parse_git_spec("<url>#main:rules").unwrap(),
            ],
            exclude: vec!["software/backend/api-contracts".into()],
        };
        let value = to_settings(&rules);
        assert_eq!(value["sources"][1]["ref"], "main");
        assert_eq!(from_settings(&value).unwrap(), rules);
        assert!(from_settings(&Value::Null).is_none());

        let mut app = App::new().unwrap();
        app.company_rules = Some(CompanyRules {
            sources: vec![],
            exclude: vec!["a/b/c".into()],
        });
        merge_saved(&mut app, rules.clone());
        let merged = app.company_rules.clone().unwrap();
        assert_eq!(merged.sources, rules.sources);
        assert_eq!(
            merged.exclude,
            vec!["a/b/c", "software/backend/api-contracts"]
        );
    }

    #[test]
    fn normalizes_ids_and_reads_frontmatter() {
        assert_eq!(normalize_rule_id("a/b/c.md"), "a/b/c");
        assert_eq!(normalize_rule_id("areas/a/b/rules/c.md"), "a/b/c");
        let inline = "---\nreplaces: [a/b/c, \"d/e/f\"]\npaths:\n  - \"src/**\"\n---\nbody";
        assert_eq!(front_list(inline, "replaces"), vec!["a/b/c", "d/e/f"]);
        assert_eq!(front_list(inline, "paths"), vec!["src/**"]);
        let block = "---\nreplaces:\n  - a/b/c\n- d/e/f\nname: x\n---\n";
        assert_eq!(front_list(block, "replaces"), vec!["a/b/c", "d/e/f"]);
        assert!(front_list("no front", "replaces").is_empty());
        assert!(has_key(inline, "paths") && !has_key(block, "paths"));
        assert!(is_manual("---\ntrigger: manual\n---\n"));
        assert_eq!(
            pack_rule_id("areas/software/backend/rules", "api.md").as_deref(),
            Some("software/backend/api")
        );
        assert!(pack_rule_id("areas/software/backend/skills", "x.md").is_none());
        assert_eq!(claude_name("software/x.md"), "company-software-x.md");
    }

    #[test]
    fn redacts_credentials() {
        assert_eq!(
            redact_url("https://user:secret@gitlab.example.com/group/standards.git"),
            "https://***@gitlab.example.com/group/standards.git"
        );
        assert_eq!(
            redact_url("git@gitlab.example.com:group/standards.git"),
            "git@gitlab.example.com:group/standards.git"
        );
    }

    #[test]
    fn path_source_copies_rules_and_skips_excluded_pack_rules() {
        let tmp = tempfile::tempdir().unwrap();
        let src = tmp.path().join("standards");
        std::fs::create_dir_all(src.join("software")).unwrap();
        std::fs::write(
            src.join("software/api.md"),
            "---\npaths:\n  - \"src/**\"\nreplaces: [software/backend/api-contracts]\n---\nUse v2.\n",
        )
        .unwrap();
        std::fs::write(src.join("README.md"), "# docs\n").unwrap();
        let mut app = App::new().unwrap();
        app.project_dir = tmp.path().join("p").to_string_lossy().into();
        app.selected_agent_os = vec!["claude".into()];
        app.company_rules = Some(CompanyRules {
            sources: vec![Source::Path(src.to_string_lossy().into())],
            exclude: vec!["software/ghost/none".into()],
        });
        let prepared = prepare(&mut app).unwrap();
        assert_eq!(prepared.files.len(), 1);
        assert!(app
            .excluded_pack_rules
            .contains("software/backend/api-contracts"));
        assert!(app
            .warnings
            .iter()
            .any(|w| w.contains("software/ghost/none")));
        let project = PathBuf::from(&app.project_dir);
        // Before the first install, a same-name file without the agentic marker belongs to the user.
        let mine = project.join(".claude/rules/company-software-api.md");
        std::fs::create_dir_all(mine.parent().unwrap()).unwrap();
        std::fs::write(&mine, "mine\n").unwrap();
        install(&mut app, &project, &prepared).unwrap();
        assert!(project.join(".agent/company/software/api.md").is_file());
        assert_eq!(std::fs::read_to_string(&mine).unwrap(), "mine\n");
        assert_eq!(app.managed_records.len(), 1);
        assert!(app.managed_records.iter().all(|r| r.marker == "company"));
    }
}
