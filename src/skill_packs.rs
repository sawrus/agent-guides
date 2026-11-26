//! Skill packs (docs/skill-packs.md): ready-made skills from an external git repository or a local
//! directory, installed unchanged into the skills directory of every selected host. A skill is any
//! directory with a `SKILL.md` below the pack's `skills_root`; nested layouts
//! (`skills/<category>/<name>/SKILL.md`) are flattened to `<skills dir>/<name>/`. The manifest locks the
//! commit of a git pack; `agentic skills update` resolves the ref again.

use crate::app::App;
use crate::source::{self, Source};
use crate::{manifest, ui, util};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

/// Manifest marker of every file that a skill pack installs.
pub const MARKER: &str = "skill-pack";
/// `<LICENSE_DIR>/<id>/LICENSE`: the license of a pack, outside every host skills directory.
pub const LICENSE_DIR: &str = ".agent/skill-packs";
pub const DEFAULT_SKILLS_ROOT: &str = "skills";
const CACHE_KIND: &str = "skill-packs";
const LABEL: &str = "Skill pack";
const LICENSE_NAMES: [&str; 6] = [
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "LICENCE",
    "LICENCE.md",
    "COPYING",
];
/// Skills that agentic writes outside the specialization skill buckets.
const RESERVED_SKILLS: [&str; 1] = ["agentic-profile"];

/// A built-in pack that `agentic skills add <id>` and `--skill-pack <id>` accept by name.
pub struct Preset {
    pub id: &'static str,
    pub url: &'static str,
    pub git_ref: &'static str,
    pub skills_root: &'static str,
    /// Skills to install; empty installs every skill.
    pub select: &'static [&'static str],
}

/// Built-in presets. Add an entry here to make a pack available by its id.
pub const PRESETS: &[Preset] = &[Preset {
    id: "pocock",
    url: "https://github.com/mattpocock/skills.git",
    git_ref: "6f7f7831a625f040a8e06a0e7954826b87ce775a",
    skills_root: "skills",
    select: &[
        "grilling",
        "grill-me",
        "grill-with-docs",
        "to-spec",
        "to-tickets",
        "domain-modeling",
        "tdd",
        "implement",
        "implement-spec",
        "code-review",
        "diagnosing-bugs",
        "codebase-design",
        "improve-codebase-architecture",
        "prototype",
        "research",
        "handoff",
        "wayfinder",
        "retro",
        "wizard",
        "pr",
        "writing-for-agents",
    ],
}];

impl Preset {
    fn pack(&self) -> SkillPack {
        SkillPack {
            id: self.id.to_string(),
            source: Source::Git {
                url: self.url.to_string(),
                git_ref: self.git_ref.to_string(),
                subdir: String::new(),
            },
            skills_root: self.skills_root.to_string(),
            select: self.select.iter().map(|s| s.to_string()).collect(),
            ..SkillPack::default()
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SkillPack {
    pub id: String,
    /// `Source::Git` never has a `subdir` here: `skills_root` takes its place.
    pub source: Source,
    /// Directory below the source root that holds the skills; `.` is the source root.
    pub skills_root: String,
    /// Skill names to install; empty installs every skill.
    pub select: Vec<String>,
    /// Skill names to skip.
    pub exclude: Vec<String>,
    /// Lock: the resolved commit of a git pack; empty until the first fetch.
    pub commit: String,
}

impl Default for SkillPack {
    fn default() -> Self {
        SkillPack {
            id: String::new(),
            source: Source::Path(String::new()),
            skills_root: DEFAULT_SKILLS_ROOT.to_string(),
            select: Vec::new(),
            exclude: Vec::new(),
            commit: String::new(),
        }
    }
}

impl SkillPack {
    fn same_origin(&self, other: &SkillPack) -> bool {
        self.source == other.source && self.skills_root == other.skills_root
    }

    fn git_ref(&self) -> &str {
        match &self.source {
            Source::Git { git_ref, .. } => git_ref,
            Source::Path(_) => "",
        }
    }
}

fn is_git_spec(spec: &str) -> bool {
    let url = spec.rsplit_once('#').map_or(spec, |(url, _)| url);
    url.contains("://") || url.starts_with("git@") || url.ends_with(".git")
}

/// A preset id, a git spec `<url>[#ref][:skills_root]`, or a directory.
pub fn parse_spec(spec: &str) -> Result<SkillPack, String> {
    let spec = spec.trim();
    if spec.is_empty() {
        return Err("--skill-pack: empty value".into());
    }
    if let Some(preset) = PRESETS.iter().find(|p| p.id == spec) {
        return Ok(preset.pack());
    }
    let (source, skills_root) = if is_git_spec(spec) {
        match source::parse_git_spec(spec, "--skill-pack")? {
            Source::Git {
                url,
                git_ref,
                subdir,
            } => (
                Source::Git {
                    url,
                    git_ref,
                    subdir: String::new(),
                },
                subdir,
            ),
            path => (path, String::new()),
        }
    } else {
        (Source::Path(spec.to_string()), String::new())
    };
    Ok(SkillPack {
        id: derive_id(&source),
        source,
        skills_root: if skills_root.is_empty() {
            DEFAULT_SKILLS_ROOT.to_string()
        } else {
            skills_root
        },
        ..SkillPack::default()
    })
}

/// `<owner>-<repo>` of a git URL, the directory name of a path.
pub fn derive_id(source: &Source) -> String {
    let (raw, git) = match source {
        Source::Path(path) => (path.as_str(), false),
        Source::Git { url, .. } => (url.as_str(), true),
    };
    let trimmed = raw.trim_end_matches(['/', '\\']);
    let trimmed = trimmed.strip_suffix(".git").unwrap_or(trimmed);
    let parts: Vec<&str> = trimmed
        .split(['/', '\\', ':'])
        .filter(|s| !s.is_empty() && *s != "." && *s != "..")
        .collect();
    let name = match parts.as_slice() {
        [.., owner, repo] if git => format!("{owner}-{repo}"),
        [.., last] => last.to_string(),
        [] => String::new(),
    };
    let clean: String = name
        .to_lowercase()
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-') {
                c
            } else {
                '-'
            }
        })
        .collect();
    let clean = clean.trim_matches(['-', '.', '_']).to_string();
    if clean.is_empty() {
        "pack".into()
    } else {
        clean
    }
}

pub fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && !id.starts_with(['.', '_', '-'])
        && id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-'))
}

fn valid_root(root: &str) -> bool {
    root == "." || source::is_relative_clean(root)
}

pub fn to_settings(packs: &[SkillPack]) -> Value {
    Value::Array(
        packs
            .iter()
            .map(|pack| {
                let mut v = source::to_json(&pack.source);
                v["id"] = json!(pack.id);
                v["skills_root"] = json!(pack.skills_root);
                v["select"] = json!(pack.select);
                v["exclude"] = json!(pack.exclude);
                if !pack.commit.is_empty() {
                    v["commit"] = json!(pack.commit);
                }
                v
            })
            .collect(),
    )
}

/// `settings.skill_packs`; None when the key is not a list.
pub fn from_settings(value: &Value) -> Option<Vec<SkillPack>> {
    let items = value.as_array()?;
    let list = |item: &Value, key: &str| -> Vec<String> {
        let mut out = Vec::new();
        for name in item[key]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
        {
            util::unique_append(&mut out, name.trim());
        }
        out
    };
    let mut packs = Vec::new();
    for item in items {
        let Some(mut source) = source::from_json(item) else {
            continue;
        };
        let mut skills_root = item["skills_root"].as_str().unwrap_or_default().to_string();
        if let Source::Git { subdir, .. } = &mut source {
            if skills_root.is_empty() {
                skills_root = std::mem::take(subdir);
            }
            subdir.clear();
        }
        let skills_root = skills_root.trim_matches('/').to_string();
        packs.push(SkillPack {
            id: item["id"]
                .as_str()
                .filter(|id| !id.is_empty())
                .map(str::to_string)
                .unwrap_or_else(|| derive_id(&source)),
            source,
            skills_root: if skills_root.is_empty() {
                DEFAULT_SKILLS_ROOT.to_string()
            } else {
                skills_root
            },
            select: list(item, "select"),
            exclude: list(item, "exclude"),
            commit: item["commit"].as_str().unwrap_or_default().to_string(),
        });
    }
    Some(packs)
}

/// Add or replace `pack` by id. The same source keeps its locked commit.
pub fn upsert(packs: &mut Vec<SkillPack>, mut pack: SkillPack) {
    match packs.iter_mut().find(|p| p.id == pack.id) {
        Some(old) => {
            if old.same_origin(&pack) && pack.commit.is_empty() {
                pack.commit = old.commit.clone();
            }
            *old = pack;
        }
        None => packs.push(pack),
    }
}

/// Replay: packs from `--skill-pack` add to (or replace by id) the saved packs. The `skills`
/// subcommands set `skill_packs_replace` and pass the complete list.
pub fn merge_saved(app: &mut App, saved: Vec<SkillPack>) {
    if app.skill_packs_replace {
        return;
    }
    let cli = std::mem::take(&mut app.skill_packs);
    app.skill_packs = saved;
    for pack in cli {
        upsert(&mut app.skill_packs, pack);
    }
}

/// One skill of a pack: files as (`/`-separated path below the skill directory, text).
#[derive(Debug, Clone)]
pub struct PackSkill {
    pub pack: String,
    pub name: String,
    pub files: Vec<(String, String)>,
}

#[derive(Debug, Default)]
pub struct Prepared {
    pub skills: Vec<PackSkill>,
    /// (pack id, file name, text) of each pack license.
    pub licenses: Vec<(String, String, String)>,
    /// Files (`path`, `source`) of a pack whose source cannot be read now; they stay.
    pub kept: Vec<(String, String)>,
}

/// Every directory with a `SKILL.md` below `root` as (name, directory). The files of a skill are not
/// searched for further skills. Dot directories, `node_modules`, and symlinks are skipped.
pub fn find_skills(root: &Path) -> Vec<(String, PathBuf)> {
    fn walk(dir: &Path, out: &mut Vec<(String, PathBuf)>) {
        let Ok(entries) = std::fs::read_dir(dir) else {
            return;
        };
        let mut entries: Vec<_> = entries.filter_map(|e| e.ok()).collect();
        entries.sort_by_key(|e| e.file_name());
        for entry in entries {
            let name = entry.file_name().to_string_lossy().to_string();
            if name.starts_with('.') || name == "node_modules" {
                continue;
            }
            if !entry.file_type().is_ok_and(|t| t.is_dir()) {
                continue;
            }
            let path = entry.path();
            if source::is_plain_file(&path.join("SKILL.md")) {
                out.push((name, path));
            } else {
                walk(&path, out);
            }
        }
    }
    let mut out = Vec::new();
    walk(root, &mut out);
    out
}

/// Skill names that a pack must not reuse, with their owner for the error message.
fn taken_names(app: &App, company: &crate::company::Prepared) -> BTreeMap<String, String> {
    let mut owners = BTreeMap::new();
    for spec_key in &app.selected_specs {
        let (area, spec) = spec_key.split_once('.').unwrap_or((spec_key, ""));
        for (rel, _) in app.kb.walk_files(&format!("areas/{area}/{spec}/skills")) {
            if let Some((name, _)) = rel.split_once('/') {
                owners
                    .entry(name.to_string())
                    .or_insert_with(|| format!("the agentic skill of {spec_key}"));
            }
        }
    }
    for name in RESERVED_SKILLS {
        owners.insert(name.to_string(), "an agentic skill".to_string());
    }
    for file in &company.skills {
        if let Some((name, _)) = file.rel.split_once('/') {
            owners
                .entry(name.to_string())
                .or_insert_with(|| format!("the company skill from {}", file.source_id));
        }
    }
    owners
}

fn refresh_requested(app: &App, id: &str) -> bool {
    app.skill_packs_update
        .as_ref()
        .is_some_and(|ids| ids.is_empty() || ids.iter().any(|i| i == id))
}

/// The pack root and the resolved commit of a git pack. `Ok(None)` when the source cannot be read now
/// and the pack has installed files to keep. A failed fetch never changes the lock: `skills update`
/// and a pack without a lock (`skills add`, first install) fail instead.
fn open_source(
    app: &mut App,
    project: &Path,
    pack: &SkillPack,
) -> crate::Result<Option<(PathBuf, Option<String>)>> {
    let id = &pack.id;
    let shown = source::source_id(&pack.source);
    match &pack.source {
        Source::Path(path) => {
            let abs = source::resolve_path(app, path);
            if abs.is_dir() {
                return Ok(Some((abs, None)));
            }
            if previous_files(project, id).is_empty() {
                return Err(
                    format!("Skill pack {id}: directory not found: {}", abs.display()).into(),
                );
            }
            ui::warn(
                app,
                &format!("Skill pack {id}: directory not found: {}", abs.display()),
            );
            Ok(None)
        }
        Source::Git { url, git_ref, .. } => {
            let refresh = refresh_requested(app, id);
            let dir = if pack.commit.is_empty() || refresh {
                match source::fetch_ref(app, CACHE_KIND, LABEL, url, git_ref) {
                    Some(dir) => dir,
                    None if pack.commit.is_empty() => {
                        return Err(format!(
                            "Skill pack {id}: cannot fetch {shown}; nothing was installed or saved"
                        )
                        .into())
                    }
                    None => {
                        return Err(format!(
                            "Skill pack {id}: cannot fetch {shown}; the lock stays at {}",
                            pack.commit
                        )
                        .into())
                    }
                }
            } else {
                match source::checkout_commit(app, CACHE_KIND, LABEL, url, &pack.commit) {
                    Some(dir) => dir,
                    None => return Ok(None),
                }
            };
            let commit = source::head_commit(&dir)
                .ok_or_else(|| format!("Skill pack {id}: no commit in the checkout of {shown}"))?;
            if !pack.commit.is_empty() && pack.commit != commit {
                ui::log(
                    app,
                    &format!("Skill pack {id}: {} -> {commit}", pack.commit),
                );
            }
            Ok(Some((dir, Some(commit))))
        }
    }
}

/// A skill directory name that every host accepts: letters, digits, `.`, `_`, `-`; not `.` or `..`.
pub fn valid_skill_name(name: &str) -> bool {
    !name.is_empty()
        && name != "."
        && name != ".."
        && name
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-'))
}

/// Read every pack, check names, and record the resolved commits in `app.skill_packs`.
pub fn prepare(app: &mut App, company: &crate::company::Prepared) -> crate::Result<Prepared> {
    let mut prepared = Prepared::default();
    if app.skill_packs.is_empty() {
        return Ok(prepared);
    }
    let project = PathBuf::from(&app.project_dir);
    let mut owners = taken_names(app, company);
    let mut ids = BTreeSet::new();
    for index in 0..app.skill_packs.len() {
        let pack = app.skill_packs[index].clone();
        let id = pack.id.as_str();
        if !valid_id(id) {
            return Err(format!(
                "Skill pack id `{id}` is invalid: use letters, digits, `.`, `_`, `-`"
            )
            .into());
        }
        if !ids.insert(id.to_string()) {
            return Err(format!("Skill pack id `{id}` is configured twice").into());
        }
        if !valid_root(&pack.skills_root) {
            return Err(format!(
                "Skill pack {id}: skills_root must be a relative path: `{}`",
                pack.skills_root
            )
            .into());
        }
        let shown = source::source_id(&pack.source);
        if app.dry_run {
            ui::log(app, &format!("DRY-RUN read skill pack {id} from {shown}"));
            continue;
        }
        if !pack.commit.is_empty() && !source::valid_commit(&pack.commit) {
            return Err(format!(
                "Skill pack {id}: invalid locked commit `{}`",
                pack.commit.escape_debug()
            )
            .into());
        }
        let Some((root, commit)) = open_source(app, &project, &pack)? else {
            prepared.kept.extend(previous_files(&project, id));
            continue;
        };
        if let Some(commit) = commit {
            app.skill_packs[index].commit = commit;
        }
        let skills_dir = if pack.skills_root == "." {
            root.clone()
        } else {
            root.join(&pack.skills_root)
        };
        if !skills_dir.is_dir() {
            return Err(format!(
                "Skill pack {id}: no `{}` directory in {shown}",
                pack.skills_root
            )
            .into());
        }
        // A symlinked skills_root would copy files from outside the source into the project.
        if pack.skills_root != "." && !source::no_symlink_below(&root, &pack.skills_root) {
            return Err(format!(
                "Skill pack {id}: `{}` in {shown} is a symbolic link",
                pack.skills_root
            )
            .into());
        }
        let mut found = find_skills(&skills_dir);
        for (name, _) in found.iter().filter(|(name, _)| !valid_skill_name(name)) {
            ui::warn(
                app,
                &format!(
                    "Skill pack {id}: skill directory `{}` has an invalid name; skipped",
                    name.escape_debug()
                ),
            );
        }
        found.retain(|(name, _)| valid_skill_name(name));
        let known: BTreeSet<&str> = found.iter().map(|(name, _)| name.as_str()).collect();
        for name in &pack.select {
            if !known.contains(name.as_str()) {
                return Err(format!(
                    "Skill pack {id}: `select` names `{name}`, but {shown} has no such skill"
                )
                .into());
            }
        }
        for name in &pack.exclude {
            if !known.contains(name.as_str()) {
                ui::warn(
                    app,
                    &format!("Skill pack {id}: `exclude` names `{name}`, which is not in the pack"),
                );
            }
        }
        let rel_of = |dir: &Path| {
            dir.strip_prefix(&root)
                .unwrap_or(dir)
                .to_string_lossy()
                .replace('\\', "/")
        };
        let mut chosen: BTreeMap<String, PathBuf> = BTreeMap::new();
        for (name, dir) in found {
            if (!pack.select.is_empty() && !pack.select.contains(&name))
                || pack.exclude.contains(&name)
            {
                continue;
            }
            if let Some(first) = chosen.get(&name) {
                return Err(format!(
                    "Skill pack {id}: two skills are named `{name}`: {} and {}; add one to `exclude`",
                    rel_of(first),
                    rel_of(&dir)
                )
                .into());
            }
            if let Some(owner) = owners.get(&name) {
                return Err(format!(
                    "Skill pack {id}: skill `{name}` ({}) has the name of {owner}; add it to the pack's `exclude`",
                    rel_of(&dir)
                )
                .into());
            }
            chosen.insert(name, dir);
        }
        if chosen.is_empty() {
            ui::warn(app, &format!("Skill pack {id}: no skill to install"));
        }
        for (name, dir) in chosen {
            owners.insert(name.clone(), format!("a skill of pack {id}"));
            let mut all = Vec::new();
            source::collect_all(&dir, &dir, &mut all);
            let mut files = Vec::new();
            for (rel, text) in all {
                match text {
                    Some(text) => files.push((rel, text)),
                    None => ui::warn(
                        app,
                        &format!("Skill pack {id}: {name}/{rel} is not UTF-8 text; skipped"),
                    ),
                }
            }
            prepared.skills.push(PackSkill {
                pack: id.to_string(),
                name,
                files,
            });
        }
        if let Some(name) = LICENSE_NAMES
            .iter()
            .find(|n| source::is_plain_file(&root.join(n)))
        {
            if let Ok(text) = std::fs::read_to_string(root.join(name)) {
                prepared
                    .licenses
                    .push((id.to_string(), name.to_string(), text));
            }
        }
    }
    Ok(prepared)
}

/// (host, skills directory) of the selected hosts plus `.agent/skills`, one entry per directory.
pub fn host_skill_dirs(app: &App) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    for target in app
        .selected_agent_os
        .iter()
        .map(String::as_str)
        .chain(["agents"])
    {
        let dir = crate::agentsmd::get_dest_dir(target, "skills");
        if dir != "-" && !out.iter().any(|(_, d)| *d == dir) {
            out.push((target.to_string(), dir));
        }
    }
    out
}

/// Per-host adaptation of one pack skill file before it is written to that host's skills directory.
/// Hook point for host-specific frontmatter (for example `disable-model-invocation`); today every
/// host gets the upstream text unchanged.
pub fn adapt_for_host(_host: &str, _skill: &str, _rel: &str, content: &str) -> String {
    content.to_string()
}

fn source_ref(pack: &str, rel: &str) -> String {
    format!("{MARKER}:{pack}/{rel}")
}

/// Write the prepared skills into every host skills directory and the licenses into
/// `.agent/skill-packs/<id>/`. A repeated `agentic install` removes the files of packs and skills
/// that are no longer configured (upgrade and `agentic skills` remove them as obsolete artifacts).
pub fn install(app: &mut App, project_dir: &Path, prepared: &Prepared) -> crate::Result<()> {
    if app.dry_run {
        return Ok(());
    }
    let mut desired: BTreeSet<String> = BTreeSet::new();
    let dirs = host_skill_dirs(app);
    for skill in &prepared.skills {
        for (host, dir) in &dirs {
            for (rel, content) in &skill.files {
                let text = adapt_for_host(host, &skill.name, rel, content);
                let dest = project_dir.join(dir).join(&skill.name).join(rel);
                desired.insert(app.project_rel_path(&dest));
                let source = source_ref(&skill.pack, &format!("{}/{rel}", skill.name));
                write(app, &text, &dest, &source)?;
            }
        }
    }
    if crate::pocock_setup::active(app) {
        let skill = crate::pocock_setup::SETUP_SKILL;
        for (host, dir) in &dirs {
            let text = adapt_for_host(
                host,
                skill,
                "SKILL.md",
                crate::pocock_setup::SETUP_SKILL_TEXT,
            );
            let dest = project_dir.join(dir).join(skill).join("SKILL.md");
            desired.insert(app.project_rel_path(&dest));
            let source = source_ref(crate::pocock_setup::PACK_ID, &format!("{skill}/SKILL.md"));
            write(app, &text, &dest, &source)?;
        }
    }
    for (rel, text, name) in crate::pocock_setup::files(app) {
        let dest = project_dir.join(rel);
        desired.insert(app.project_rel_path(&dest));
        write(
            app,
            &text,
            &dest,
            &source_ref(crate::pocock_setup::PACK_ID, name),
        )?;
    }
    for (pack, name, text) in &prepared.licenses {
        let dest = project_dir.join(LICENSE_DIR).join(pack).join(name);
        desired.insert(app.project_rel_path(&dest));
        write(app, text, &dest, &source_ref(pack, name))?;
    }
    for (path, source) in &prepared.kept {
        desired.insert(path.clone());
        if !app.managed_records.iter().any(|r| &r.path == path) {
            manifest::register_managed_file(app, &project_dir.join(path), source, MARKER, false);
        }
    }
    if !app.upgrade_mode {
        remove_stale(app, project_dir, &desired)?;
    }
    Ok(())
}

/// Never overwrite a file that another installer step wrote in this run; before the first install a
/// file without the agentic marker belongs to the user.
fn write(app: &mut App, content: &str, dest: &Path, source_ref: &str) -> crate::Result<()> {
    let rel = app.project_rel_path(dest);
    if let Some(other) = app
        .managed_records
        .iter()
        .find(|r| r.path == rel && r.marker != MARKER)
    {
        return Err(format!(
            "Skill pack file {rel} clashes with {} ({}); add the skill to the pack's `exclude`",
            other.source, other.marker
        )
        .into());
    }
    let first_install = !app.upgrade_mode && !app.project_manifest_path().is_file();
    if first_install
        && std::fs::read_to_string(dest)
            .is_ok_and(|text| !crate::project_inventory::recognized(&text))
    {
        ui::warn(
            app,
            &format!("Skill pack: kept the existing user file {rel}"),
        );
        app.record_skipped(&rel);
        return Ok(());
    }
    // Only Markdown gets the in-file marker (frontmatter); a comment line would break JSON, SVG, CSV,
    // or a shebang-less script. The manifest hash tracks the other files.
    let markdown = dest
        .extension()
        .is_some_and(|ext| ext.eq_ignore_ascii_case("md"));
    if markdown {
        manifest::write_managed_file(app, content, dest, source_ref, MARKER)
    } else {
        manifest::write_managed_file_unmarked(app, content, dest, source_ref, MARKER)
    }
}

fn read_manifest(project_dir: &Path) -> Value {
    std::fs::read(project_dir.join(crate::PROJECT_MANIFEST_NAME))
        .ok()
        .and_then(|b| serde_json::from_slice(&b).ok())
        .unwrap_or(Value::Null)
}

/// Manifest paths with the skill pack marker (and the source, when `id` is given, of that pack).
fn manifest_files(manifest: &Value, id: Option<&str>) -> Vec<(String, String, String)> {
    manifest["managed_files"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|item| item["marker"] == MARKER)
        .filter_map(|item| {
            Some((
                item["path"].as_str()?.to_string(),
                item["source"].as_str()?.to_string(),
                item["content_hash"]
                    .as_str()
                    .unwrap_or_default()
                    .to_string(),
            ))
        })
        .filter(|(_, source, _)| id.is_none_or(|id| source.starts_with(&source_ref(id, ""))))
        .collect()
}

/// The files that pack `id` installed before, so that an offline run keeps them.
fn previous_files(project_dir: &Path, id: &str) -> Vec<(String, String)> {
    manifest_files(&read_manifest(project_dir), Some(id))
        .into_iter()
        .filter(|(path, _, _)| project_dir.join(path).is_file())
        .map(|(path, source, _)| (path, source))
        .collect()
}

fn remove_stale(
    app: &mut App,
    project_dir: &Path,
    desired: &BTreeSet<String>,
) -> crate::Result<()> {
    for (path, _, hash) in manifest_files(&read_manifest(project_dir), None) {
        if desired.contains(&path) {
            continue;
        }
        let Ok(dest) = crate::project_inventory::safe_path(project_dir, &path) else {
            continue;
        };
        if !dest.is_file() {
            app.dropped_records.push(path);
            continue;
        }
        if util::hash_file(&dest).ok().as_deref() != Some(hash.as_str()) {
            ui::warn(
                app,
                &format!("Kept skill pack file with local edits: {path}"),
            );
            continue;
        }
        std::fs::remove_file(&dest)?;
        let baseline = crate::project_update::baseline_path(project_dir, &path);
        if baseline.is_file() {
            std::fs::remove_file(baseline)?;
        }
        prune_empty_dirs(project_dir, &path);
        ui::log(app, &format!("Removed skill pack file: {path}"));
        app.dropped_records.push(path);
    }
    Ok(())
}

/// Remove the empty directories above a removed file, but keep the host directories themselves
/// (`.claude/skills`, `.agent/skill-packs`).
pub fn prune_empty_dirs(project_dir: &Path, rel: &str) {
    let mut parts: Vec<&str> = rel.split('/').collect();
    parts.pop();
    // Host directories (`.claude/skills`) stay; `docs/agents` and `docs` go when empty.
    let keep = if parts.first().is_some_and(|p| p.starts_with('.')) {
        2
    } else {
        0
    };
    while parts.len() > keep {
        let dir = project_dir.join(parts.join("/"));
        if !dir.is_dir() || std::fs::remove_dir(&dir).is_err() {
            break;
        }
        parts.pop();
    }
}

// --- `agentic skills` --------------------------------------------------------------------------

pub fn usage() -> String {
    let name = crate::APP_NAME;
    format!(
        "Usage:
  {name} skills add <git-url[#ref][:skills_root]|dir|preset> [--id <id>] [--select a,b] [--exclude x,y] [--skills-root <dir>] [--issue-tracker local|github|gitlab]
  {name} skills list
  {name} skills remove <id>
  {name} skills update [<id>]

Common options: --project-dir <dir> (default: current directory), --dry-run, --no-doctor.
add, remove, and update change settings.skill_packs in .agentic.json and synchronize the project like
`{name} upgrade`. See docs/skill-packs.md.
"
    )
}

fn csv_list(value: &str) -> Vec<String> {
    let mut out = Vec::new();
    for item in util::split_csv(value) {
        util::unique_append(&mut out, &item);
    }
    out
}

pub fn run_cli(app: &mut App, args: &[String]) -> crate::Result<()> {
    let mut positional: Vec<String> = Vec::new();
    let mut id: Option<String> = None;
    let mut select: Option<Vec<String>> = None;
    let mut exclude: Option<Vec<String>> = None;
    let mut skills_root: Option<String> = None;
    let mut i = 0;
    while i < args.len() {
        let arg = args[i].as_str();
        let value = || -> crate::Result<String> {
            args.get(i + 1)
                .filter(|v| !v.starts_with("--"))
                .cloned()
                .ok_or_else(|| format!("{arg} requires a value").into())
        };
        match arg {
            "-h" | "--help" => {
                print!("{}", usage());
                return Ok(());
            }
            "--dry-run" => app.dry_run = true,
            "--no-doctor" => app.doctor_enabled_env = false,
            "--project-dir" => {
                app.project_dir = value()?;
                i += 1;
            }
            "--id" => {
                id = Some(value()?);
                i += 1;
            }
            "--select" => {
                select = Some(csv_list(&value()?));
                i += 1;
            }
            "--exclude" => {
                exclude = Some(csv_list(&value()?));
                i += 1;
            }
            "--issue-tracker" => {
                app.issue_tracker = Some(crate::pocock_setup::parse_tracker(&value()?)?);
                i += 1;
            }
            "--skills-root" => {
                skills_root = Some(value()?.trim_matches('/').to_string());
                i += 1;
            }
            other if other.starts_with("--") => {
                return Err(format!("skills: unknown option {other}\n{}", usage()).into());
            }
            other => positional.push(other.to_string()),
        }
        i += 1;
    }
    let Some(command) = positional.first().cloned() else {
        return Err(usage().into());
    };
    let root = if app.project_dir.is_empty() {
        std::env::current_dir()?
    } else {
        PathBuf::from(util::normalize_project_dir_path(&app.project_dir))
    };
    let manifest = read_manifest(&root);
    let mut packs = from_settings(&manifest["settings"]["skill_packs"]).unwrap_or_default();
    let arg = positional.get(1).cloned();
    if positional.len() > 2 {
        return Err(format!("skills {command}: too many arguments\n{}", usage()).into());
    }
    match command.as_str() {
        "list" => {
            print_list(app, &packs, &manifest);
            return Ok(());
        }
        "add" => {
            let spec = arg.ok_or_else(|| format!("skills add: missing source\n{}", usage()))?;
            let mut pack = parse_spec(&spec)?;
            if let Some(id) = id {
                pack.id = id;
            }
            if !valid_id(&pack.id) {
                return Err(format!(
                    "skills add: invalid id `{}`: use letters, digits, `.`, `_`, `-`",
                    pack.id
                )
                .into());
            }
            if let Some(root) = skills_root.filter(|r| !r.is_empty()) {
                pack.skills_root = root;
            }
            if let Some(select) = select {
                pack.select = select;
            }
            if let Some(exclude) = exclude {
                pack.exclude = exclude;
            }
            ui::out(
                app,
                &format!(
                    "Skill pack {}: {}",
                    pack.id,
                    source::source_id(&pack.source)
                ),
            );
            upsert(&mut packs, pack);
        }
        "remove" => {
            let id = arg.ok_or_else(|| format!("skills remove: missing id\n{}", usage()))?;
            if !packs.iter().any(|p| p.id == id) {
                return Err(format!("skills remove: no skill pack `{id}`").into());
            }
            packs.retain(|p| p.id != id);
        }
        "update" => {
            if let Some(id) = &arg {
                if !packs.iter().any(|p| &p.id == id) {
                    return Err(format!("skills update: no skill pack `{id}`").into());
                }
            } else if packs.is_empty() {
                ui::out(app, "No skill packs configured.");
                return Ok(());
            }
            app.skill_packs_update = Some(arg.into_iter().collect());
        }
        other => return Err(format!("skills: unknown command {other}\n{}", usage()).into()),
    }
    if !root.join(crate::PROJECT_MANIFEST_NAME).is_file() {
        return Err(format!(
            "No {} in {}. Run `{} install --project-dir {} ... --skill-pack <spec>` first",
            crate::PROJECT_MANIFEST_NAME,
            root.display(),
            crate::APP_NAME,
            root.display()
        )
        .into());
    }
    let before = manifest_files(&manifest, None);
    app.project_dir = root.to_string_lossy().to_string();
    app.skill_packs = packs;
    app.skill_packs_replace = true;
    crate::project_update::synchronize(app)?;
    if app.dry_run {
        return Ok(());
    }
    for (path, _, _) in before {
        if !root.join(&path).exists() {
            prune_empty_dirs(&root, &path);
        }
    }
    let after = read_manifest(&root);
    let packs = from_settings(&after["settings"]["skill_packs"]).unwrap_or_default();
    print_list(app, &packs, &after);
    Ok(())
}

/// Installed skill names per pack, from the manifest sources `skill-pack:<id>/<name>/<path>`.
fn installed_skills(manifest: &Value, id: &str) -> Vec<String> {
    let mut names = Vec::new();
    for (_, source, _) in manifest_files(manifest, Some(id)) {
        let rest = &source[source_ref(id, "").len()..];
        if let Some((name, _)) = rest.split_once('/') {
            util::unique_append(&mut names, name);
        }
    }
    names
}

fn print_list(app: &mut App, packs: &[SkillPack], manifest: &Value) {
    if packs.is_empty() {
        ui::out(app, "No skill packs configured.");
        return;
    }
    for pack in packs {
        let mut line = format!("{}  {}", pack.id, source::source_id(&pack.source));
        if pack.skills_root != DEFAULT_SKILLS_ROOT {
            line.push_str(&format!("  skills_root={}", pack.skills_root));
        }
        if !pack.git_ref().is_empty() {
            line.push_str(&format!("  ref={}", pack.git_ref()));
        }
        if !pack.commit.is_empty() {
            line.push_str(&format!(
                "  commit={}",
                &pack.commit[..pack.commit.len().min(12)]
            ));
        }
        if !pack.select.is_empty() {
            line.push_str(&format!("  select={}", pack.select.join(",")));
        }
        if !pack.exclude.is_empty() {
            line.push_str(&format!("  exclude={}", pack.exclude.join(",")));
        }
        ui::out(app, &line);
        let skills = installed_skills(manifest, &pack.id);
        let shown = if skills.is_empty() {
            "(none installed)".to_string()
        } else {
            skills.join(", ")
        };
        ui::out(app, &format!("  skills: {shown}"));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write(path: &Path, text: &str) {
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(path, text).unwrap();
    }

    const SKILL: &str = "---\nname: x\ndescription: A test skill.\n---\nBody.\n";

    /// A pack directory in the upstream layout `skills/<category>/<name>/SKILL.md`.
    fn pack_dir(root: &Path) -> PathBuf {
        let dir = root.join("pack");
        write(&dir.join("skills/engineering/tdd/SKILL.md"), SKILL);
        write(
            &dir.join("skills/engineering/tdd/scripts/run.sh"),
            "#!/bin/sh\necho ok\n",
        );
        write(&dir.join("skills/writing/grill-me/SKILL.md"), SKILL);
        write(&dir.join("skills/writing/README.md"), "# not a skill\n");
        write(&dir.join("skills/.hidden/secret/SKILL.md"), SKILL);
        write(&dir.join("LICENSE"), "MIT License\n");
        dir
    }

    fn app_for(project: &Path, dir: &Path) -> App {
        let mut app = App::new().unwrap();
        app.project_dir = project.to_string_lossy().to_string();
        app.selected_agent_os = vec!["claude".into(), "codex".into(), "opencode".into()];
        app.selected_specs = vec!["software.backend".into()];
        app.skill_packs = vec![SkillPack {
            id: "demo".into(),
            source: Source::Path(dir.to_string_lossy().to_string()),
            ..SkillPack::default()
        }];
        app
    }

    fn run_install(app: &mut App, project: &Path) -> crate::Result<()> {
        let prepared = prepare(app, &crate::company::Prepared::default())?;
        install(app, project, &prepared)?;
        manifest::write_agentic_manifest(app, project)
    }

    #[test]
    fn parses_specs_and_derives_ids() {
        let pack = parse_spec("https://github.com/mattpocock/skills").unwrap();
        assert_eq!(pack.id, "mattpocock-skills");
        assert_eq!(pack.skills_root, "skills");
        let pack =
            parse_spec("git@gitlab.example.com:group/team-skills.git#v1:pack/skills").unwrap();
        assert_eq!(pack.id, "group-team-skills");
        assert_eq!(pack.skills_root, "pack/skills");
        assert_eq!(pack.git_ref(), "v1");
        assert!(matches!(&pack.source, Source::Git { subdir, .. } if subdir.is_empty()));
        let pack = parse_spec("./vendor/My Skills/").unwrap();
        assert_eq!(pack.source, Source::Path("./vendor/My Skills/".into()));
        assert_eq!(pack.id, "my-skills");
        assert!(parse_spec(" ").is_err());
        assert!(parse_spec("https://x.example.com/a.git#main:../up").is_err());
        assert!(valid_id("a.b_c-1") && !valid_id(".x") && !valid_id("a/b") && !valid_id(""));
    }

    #[test]
    fn settings_roundtrip_and_replay_merge() {
        let packs = vec![
            SkillPack {
                id: "pocock".into(),
                source: Source::Git {
                    url: "https://github.com/mattpocock/skills".into(),
                    git_ref: "main".into(),
                    subdir: String::new(),
                },
                select: vec!["tdd".into()],
                exclude: vec!["grill-me".into()],
                commit: "abc".into(),
                ..SkillPack::default()
            },
            SkillPack {
                id: "local".into(),
                source: Source::Path("vendor/skills".into()),
                skills_root: ".".into(),
                ..SkillPack::default()
            },
        ];
        let value = to_settings(&packs);
        assert_eq!(value[0]["git"], "https://github.com/mattpocock/skills");
        assert_eq!(value[0]["commit"], "abc");
        assert!(value[1].get("commit").is_none());
        assert_eq!(from_settings(&value).unwrap(), packs);
        assert!(from_settings(&Value::Null).is_none());

        // `--skill-pack` with the same source keeps the lock; other packs stay.
        let mut app = App::new().unwrap();
        let mut again = packs[0].clone();
        again.commit.clear();
        again.select.clear();
        app.skill_packs = vec![again];
        merge_saved(&mut app, packs.clone());
        assert_eq!(app.skill_packs.len(), 2);
        assert_eq!(app.skill_packs[0].commit, "abc");
        assert!(app.skill_packs[0].select.is_empty());
        // The `skills` subcommands pass the full list.
        app.skill_packs = vec![];
        app.skill_packs_replace = true;
        merge_saved(&mut app, packs);
        assert!(app.skill_packs.is_empty());
    }

    #[test]
    fn flattens_nested_layout_for_every_host_and_copies_the_license() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pack_dir(tmp.path());
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &dir);
        run_install(&mut app, &project).unwrap();
        for host_dir in [
            ".claude/skills",
            ".agents/skills",
            ".opencode/skills",
            ".agent/skills",
        ] {
            let skill = project.join(host_dir).join("tdd/SKILL.md");
            let text = std::fs::read_to_string(&skill).unwrap();
            assert!(text.contains("description: A test skill.") && text.contains("Body."));
            assert!(project.join(host_dir).join("tdd/scripts/run.sh").is_file());
            assert!(project.join(host_dir).join("grill-me/SKILL.md").is_file());
            assert!(!project.join(host_dir).join("engineering").exists());
            assert!(!project.join(host_dir).join("secret").exists());
        }
        let license = project.join(LICENSE_DIR).join("demo/LICENSE");
        assert!(std::fs::read_to_string(license)
            .unwrap()
            .contains("MIT License"));
        let manifest = read_manifest(&project);
        assert_eq!(installed_skills(&manifest, "demo"), vec!["grill-me", "tdd"]);
        assert!(manifest_files(&manifest, None)
            .iter()
            .any(|(path, source, _)| path == ".claude/skills/tdd/SKILL.md"
                && source == "skill-pack:demo/tdd/SKILL.md"));
    }

    #[test]
    fn select_and_exclude_filter_skills() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pack_dir(tmp.path());
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &dir);
        app.skill_packs[0].select = vec!["tdd".into(), "grill-me".into()];
        app.skill_packs[0].exclude = vec!["grill-me".into(), "ghost".into()];
        let prepared = prepare(&mut app, &crate::company::Prepared::default()).unwrap();
        let names: Vec<&str> = prepared.skills.iter().map(|s| s.name.as_str()).collect();
        assert_eq!(names, vec!["tdd"]);
        assert!(app.warnings.iter().any(|w| w.contains("`ghost`")));
        app.skill_packs[0].select = vec!["ghost".into()];
        let err = prepare(&mut app, &crate::company::Prepared::default()).unwrap_err();
        assert!(err.to_string().contains("no such skill"), "{err}");
    }

    #[test]
    fn name_conflicts_are_errors() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pack_dir(tmp.path());
        let project = tmp.path().join("p");
        // Two skills with one name inside a pack.
        write(&dir.join("skills/other/tdd/SKILL.md"), SKILL);
        let mut app = app_for(&project, &dir);
        let err = prepare(&mut app, &crate::company::Prepared::default()).unwrap_err();
        assert!(
            err.to_string().contains("two skills are named `tdd`"),
            "{err}"
        );
        std::fs::remove_dir_all(dir.join("skills/other")).unwrap();

        // The name of an agentic pack skill of the selected specializations.
        write(&dir.join("skills/api-design/SKILL.md"), SKILL);
        let err = prepare(&mut app, &crate::company::Prepared::default()).unwrap_err();
        assert!(
            err.to_string()
                .contains("agentic skill of software.backend"),
            "{err}"
        );
        app.skill_packs[0].exclude = vec!["api-design".into()];
        assert!(prepare(&mut app, &crate::company::Prepared::default()).is_ok());

        // The name of a company skill.
        let company = crate::company::Prepared {
            skills: vec![crate::company::RuleFile {
                source_id: "standards".into(),
                rel: "tdd/SKILL.md".into(),
                content: SKILL.into(),
                in_place: false,
            }],
            ..Default::default()
        };
        let err = prepare(&mut app, &company).unwrap_err();
        assert!(
            err.to_string().contains("company skill from standards"),
            "{err}"
        );

        // The same skill name in two packs.
        let mut second = app.skill_packs[0].clone();
        second.id = "second".into();
        app.skill_packs.push(second);
        let err = prepare(&mut app, &crate::company::Prepared::default()).unwrap_err();
        assert!(err.to_string().contains("a skill of pack demo"), "{err}");
    }

    #[test]
    fn reinstall_removes_only_the_files_a_pack_no_longer_has() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pack_dir(tmp.path());
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &dir);
        run_install(&mut app, &project).unwrap();
        let mine = project.join(".claude/skills/mine/SKILL.md");
        write(&mine, "my own skill\n");

        // The pack drops grill-me and a script.
        std::fs::remove_dir_all(dir.join("skills/writing/grill-me")).unwrap();
        std::fs::remove_file(dir.join("skills/engineering/tdd/scripts/run.sh")).unwrap();
        let mut app = app_for(&project, &dir);
        run_install(&mut app, &project).unwrap();
        assert!(project.join(".claude/skills/tdd/SKILL.md").is_file());
        assert!(!project.join(".claude/skills/grill-me").exists());
        assert!(!project.join(".agents/skills/tdd/scripts").exists());
        assert!(project.join(".claude/skills").is_dir());
        assert!(mine.is_file());
        let manifest = read_manifest(&project);
        assert!(!manifest_files(&manifest, None)
            .iter()
            .any(|(path, _, _)| path.contains("grill-me") || path.ends_with("run.sh")));

        // No packs at all: every pack file goes, the user skill stays.
        let mut app = app_for(&project, &dir);
        app.skill_packs.clear();
        run_install(&mut app, &project).unwrap();
        assert!(!project.join(".claude/skills/tdd").exists());
        assert!(!project.join(LICENSE_DIR).join("demo").exists());
        assert!(mine.is_file());
        assert!(manifest_files(&read_manifest(&project), None).is_empty());
    }

    #[test]
    fn unreadable_source_keeps_previous_files() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pack_dir(tmp.path());
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &dir);
        run_install(&mut app, &project).unwrap();
        std::fs::rename(&dir, tmp.path().join("moved")).unwrap();
        let mut app = app_for(&project, &dir);
        run_install(&mut app, &project).unwrap();
        assert!(app
            .warnings
            .iter()
            .any(|w| w.contains("directory not found")));
        assert!(project.join(".claude/skills/tdd/SKILL.md").is_file());
        assert_eq!(installed_skills(&read_manifest(&project), "demo").len(), 2);
    }

    #[test]
    fn git_pack_locks_the_commit_until_update() {
        if std::env::var_os("XDG_CACHE_HOME").is_some() {
            return;
        }
        let tmp = tempfile::tempdir().unwrap();
        let work = pack_dir(tmp.path());
        let git = |args: &[&str]| {
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
        git(&["init", "-q", "-b", "main"]);
        git(&["add", "-A"]);
        git(&["commit", "-qm", "one"]);
        let first = source::head_commit(&work).unwrap();
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &work);
        app.home = tmp.path().join("home");
        app.skill_packs[0].source = Source::Git {
            url: work.to_string_lossy().to_string(),
            git_ref: "main".into(),
            subdir: String::new(),
        };
        let packs = app.skill_packs.clone();
        run_install(&mut app, &project).unwrap();
        let saved = from_settings(&read_manifest(&project)["settings"]["skill_packs"]).unwrap();
        assert_eq!(saved[0].commit, first);

        // Upstream moves on; a plain reinstall stays on the locked commit.
        write(&work.join("skills/new-skill/SKILL.md"), SKILL);
        git(&["add", "-A"]);
        git(&["commit", "-qm", "two"]);
        let replay = |update: Option<Vec<String>>| {
            let mut app = app_for(&project, &work);
            app.home = tmp.path().join("home");
            app.skill_packs = packs.clone();
            app.skill_packs_update = update;
            crate::manifest::load_install_settings_from_manifest(
                &mut app,
                &project.join(crate::PROJECT_MANIFEST_NAME),
            )
            .unwrap();
            run_install(&mut app, &project).unwrap();
        };
        replay(None);
        assert!(!project.join(".claude/skills/new-skill").exists());
        replay(Some(vec![]));
        assert!(project.join(".claude/skills/new-skill/SKILL.md").is_file());
        let saved = from_settings(&read_manifest(&project)["settings"]["skill_packs"]).unwrap();
        assert_eq!(saved[0].commit, source::head_commit(&work).unwrap());
        assert_ne!(saved[0].commit, first);
    }

    fn init_repo(work: &Path) -> impl Fn(&[&str]) + '_ {
        move |args: &[&str]| {
            assert!(std::process::Command::new("git")
                .current_dir(work)
                .args(["-c", "user.name=t", "-c", "user.email=t@example.com"])
                .args(args)
                .env("GIT_CONFIG_NOSYSTEM", "1")
                .env("GIT_CONFIG_GLOBAL", "/dev/null")
                .status()
                .unwrap()
                .success());
        }
    }

    #[test]
    fn option_like_locked_commit_is_rejected_before_git_runs() {
        let tmp = tempfile::tempdir().unwrap();
        let project = tmp.path().join("p");
        let flag = tmp.path().join("pwned");
        let mut app = app_for(&project, tmp.path());
        app.home = tmp.path().join("home");
        app.skill_packs[0].source = Source::Git {
            url: tmp.path().join("none").to_string_lossy().to_string(),
            git_ref: String::new(),
            subdir: String::new(),
        };
        app.skill_packs[0].commit = format!("--upload-pack=touch {};", flag.display());
        let err = prepare(&mut app, &crate::company::Prepared::default()).unwrap_err();
        assert!(err.to_string().contains("invalid locked commit"), "{err}");
        // An option-like ref is refused as well.
        app.skill_packs[0].commit.clear();
        app.skill_packs[0].source = Source::Git {
            url: tmp.path().join("none").to_string_lossy().to_string(),
            git_ref: format!("--upload-pack=touch {};", flag.display()),
            subdir: String::new(),
        };
        assert!(prepare(&mut app, &crate::company::Prepared::default()).is_err());
        assert!(!flag.exists());
    }

    #[cfg(unix)]
    #[test]
    fn symlinks_in_the_pack_are_not_followed() {
        let tmp = tempfile::tempdir().unwrap();
        let outside = tmp.path().join("outside");
        write(&outside.join("secret/SKILL.md"), SKILL);
        write(&outside.join("id_rsa"), "PRIVATE KEY\n");
        let dir = tmp.path().join("pack");
        write(&dir.join("skills/ok/SKILL.md"), SKILL);
        std::os::unix::fs::symlink(outside.join("id_rsa"), dir.join("LICENSE")).unwrap();
        std::os::unix::fs::symlink(&outside, dir.join("skills/linked")).unwrap();
        std::fs::create_dir_all(dir.join("skills/fake")).unwrap();
        std::os::unix::fs::symlink(
            outside.join("secret/SKILL.md"),
            dir.join("skills/fake/SKILL.md"),
        )
        .unwrap();
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &dir);
        run_install(&mut app, &project).unwrap();
        assert!(project.join(".claude/skills/ok/SKILL.md").is_file());
        assert!(!project.join(".claude/skills/secret").exists());
        assert!(!project.join(".claude/skills/fake").exists());
        assert!(!project.join(LICENSE_DIR).join("demo").exists());

        // A symlinked skills_root is an error.
        let other = tmp.path().join("pack2");
        std::fs::create_dir_all(&other).unwrap();
        std::os::unix::fs::symlink(&outside, other.join("skills")).unwrap();
        let mut app = app_for(&project, &other);
        let err = prepare(&mut app, &crate::company::Prepared::default()).unwrap_err();
        assert!(err.to_string().contains("symbolic link"), "{err}");
    }

    #[test]
    fn only_markdown_gets_the_marker() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = tmp.path().join("pack");
        write(&dir.join("skills/tdd/SKILL.md"), SKILL);
        let files = [
            ("data.json", "[1, 2]\n"),
            ("icon.svg", "<svg xmlns=\"http://www.w3.org/2000/svg\"/>\n"),
            ("rows.csv", "a,b\n1,2\n"),
            ("run.mjs", "export const x = 1;\n"),
        ];
        for (name, text) in files {
            write(&dir.join("skills/tdd").join(name), text);
        }
        write(&dir.join("LICENSE"), "MIT License\n");
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &dir);
        run_install(&mut app, &project).unwrap();
        for (name, text) in files {
            let path = project.join(".claude/skills/tdd").join(name);
            assert_eq!(std::fs::read_to_string(path).unwrap(), text, "{name}");
        }
        assert_eq!(
            std::fs::read_to_string(project.join(LICENSE_DIR).join("demo/LICENSE")).unwrap(),
            "MIT License\n"
        );
        let skill = std::fs::read_to_string(project.join(".claude/skills/tdd/SKILL.md")).unwrap();
        assert!(skill.contains("generated_by: agentic"));
        // Unmarked files are still owned: an unchanged reinstall and removal work by hash.
        let mut app = app_for(&project, &dir);
        run_install(&mut app, &project).unwrap();
        assert!(
            app.skipped_managed_paths.is_empty(),
            "{:?}",
            app.skipped_managed_paths
        );
        let mut app = app_for(&project, &dir);
        app.skill_packs.clear();
        run_install(&mut app, &project).unwrap();
        assert!(!project.join(".claude/skills/tdd").exists());
    }

    #[test]
    fn invalid_skill_names_are_skipped() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = tmp.path().join("pack");
        write(&dir.join("skills/ok/SKILL.md"), SKILL);
        write(&dir.join("skills/bad name/SKILL.md"), SKILL);
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &dir);
        let prepared = prepare(&mut app, &crate::company::Prepared::default()).unwrap();
        let names: Vec<&str> = prepared.skills.iter().map(|s| s.name.as_str()).collect();
        assert_eq!(names, vec!["ok"]);
        assert!(app.warnings.iter().any(|w| w.contains("invalid name")));
        assert!(valid_skill_name("a.b_c-1") && !valid_skill_name("..") && !valid_skill_name("a/b"));
    }

    #[test]
    fn missing_new_source_is_an_error() {
        let tmp = tempfile::tempdir().unwrap();
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &tmp.path().join("missing"));
        let err = prepare(&mut app, &crate::company::Prepared::default()).unwrap_err();
        assert!(err.to_string().contains("directory not found"), "{err}");
    }

    #[test]
    fn failed_fetch_never_moves_the_lock() {
        if std::env::var_os("XDG_CACHE_HOME").is_some() {
            return;
        }
        let tmp = tempfile::tempdir().unwrap();
        let work = pack_dir(tmp.path());
        let git = init_repo(&work);
        git(&["init", "-q", "-b", "main"]);
        git(&["add", "-A"]);
        git(&["commit", "-qm", "one"]);
        let first = source::head_commit(&work).unwrap();
        let project = tmp.path().join("p");
        let pack_app = |update: Option<Vec<String>>| {
            let mut app = app_for(&project, &work);
            app.home = tmp.path().join("home");
            app.skill_packs[0].source = Source::Git {
                url: work.to_string_lossy().to_string(),
                git_ref: "main".into(),
                subdir: String::new(),
            };
            app.skill_packs_update = update;
            crate::manifest::load_install_settings_from_manifest(
                &mut app,
                &project.join(crate::PROJECT_MANIFEST_NAME),
            )
            .unwrap();
            app
        };
        let mut app = pack_app(None);
        run_install(&mut app, &project).unwrap();
        // A second commit lands in the shared cache through another pack id, then the remote goes away.
        write(&work.join("skills/new-skill/SKILL.md"), SKILL);
        git(&["add", "-A"]);
        git(&["commit", "-qm", "two"]);
        let mut other = pack_app(None);
        other.skill_packs[0].id = "other".into();
        other.skill_packs[0].commit.clear();
        other.skill_packs[0].exclude = vec!["tdd".into(), "grill-me".into(), "new-skill".into()];
        let prepared = prepare(&mut other, &crate::company::Prepared::default()).unwrap();
        assert!(prepared.skills.is_empty());
        std::fs::rename(&work, tmp.path().join("gone")).unwrap();

        // `skills update` fails clearly and keeps the lock.
        let mut app = pack_app(Some(vec![]));
        let err = run_install(&mut app, &project).unwrap_err();
        assert!(err.to_string().contains("the lock stays at"), "{err}");
        let lock = |p: &Path| {
            from_settings(&read_manifest(p)["settings"]["skill_packs"]).unwrap()[0]
                .commit
                .clone()
        };
        assert_eq!(lock(&project), first);
        // A plain reinstall checks out the locked commit from the cache, not the cache HEAD.
        let mut app = pack_app(None);
        run_install(&mut app, &project).unwrap();
        assert_eq!(lock(&project), first);
        assert!(!project.join(".claude/skills/new-skill").exists());
        assert!(project.join(".claude/skills/tdd/SKILL.md").is_file());
        // A new pack without a lock cannot be added offline.
        let mut app = pack_app(None);
        app.skill_packs[0].id = "fresh".into();
        app.skill_packs[0].commit.clear();
        let err = prepare(&mut app, &crate::company::Prepared::default()).unwrap_err();
        assert!(
            err.to_string().contains("nothing was installed or saved"),
            "{err}"
        );
    }

    // --- preset `pocock` and its project setup ---------------------------------------------------

    fn pocock_preset() -> &'static Preset {
        PRESETS.iter().find(|p| p.id == "pocock").unwrap()
    }

    /// A fixture with the preset's skills, plus skills that the preset must not select.
    fn pocock_fixture(root: &Path) -> PathBuf {
        let dir = root.join("pocock-src");
        for name in pocock_preset().select {
            write(
                &dir.join(format!("skills/engineering/{name}/SKILL.md")),
                SKILL,
            );
        }
        for name in ["setup-matt-pocock-skills", "triage", "ask-matt", "teach"] {
            write(&dir.join(format!("skills/misc/{name}/SKILL.md")), SKILL);
        }
        write(&dir.join("LICENSE"), "MIT License\n");
        dir
    }

    fn pocock_app(project: &Path, dir: &Path, tracker: Option<&str>) -> App {
        let mut app = app_for(project, dir);
        let mut pack = parse_spec("pocock").unwrap();
        pack.source = Source::Path(dir.to_string_lossy().to_string());
        app.skill_packs = vec![pack];
        app.issue_tracker = tracker.map(str::to_string);
        app
    }

    #[test]
    fn pocock_preset_resolves_and_pins_a_commit() {
        let pack = parse_spec("pocock").unwrap();
        assert_eq!(pack.id, "pocock");
        assert_eq!(pack.skills_root, "skills");
        assert_eq!(pack.select.len(), 21);
        assert!(matches!(&pack.source, Source::Git { url, git_ref, .. }
            if url == "https://github.com/mattpocock/skills.git"
                && git_ref.len() == 40
                && git_ref.chars().all(|c| c.is_ascii_hexdigit())));
        for banned in [
            "setup-matt-pocock-skills",
            "triage",
            "ask-matt",
            "teach",
            "wait-what",
        ] {
            assert!(!pack.select.iter().any(|n| n == banned), "{banned}");
        }
    }

    #[test]
    fn pocock_select_list_is_valid_against_the_fixture() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pocock_fixture(tmp.path());
        let project = tmp.path().join("p");
        let mut app = pocock_app(&project, &dir, None);
        run_install(&mut app, &project).unwrap();
        for name in pocock_preset().select {
            assert!(
                project
                    .join(".claude/skills")
                    .join(name)
                    .join("SKILL.md")
                    .is_file(),
                "{name}"
            );
        }
        assert!(!project.join(".claude/skills/triage").exists());
        // The fixture's upstream setup skill is not selected; the installed one is agentic's own.
        let own = std::fs::read_to_string(
            project.join(".claude/skills/setup-matt-pocock-skills/SKILL.md"),
        )
        .unwrap();
        assert!(own.contains("managed by agentic"));
        // The setup files are not skills.
        let packs = from_settings(&read_manifest(&project)["settings"]["skill_packs"]).unwrap();
        let skills = installed_skills(&read_manifest(&project), &packs[0].id);
        assert_eq!(skills.len(), 22, "{skills:?}");
        assert!(skills.contains(&"setup-matt-pocock-skills".to_string()));
        for dir in [".claude/skills", ".agents/skills", ".agent/skills"] {
            let text = std::fs::read_to_string(
                project.join(dir).join("setup-matt-pocock-skills/SKILL.md"),
            )
            .unwrap();
            assert!(text.contains("disable-model-invocation: true"));
            assert!(text.contains("agentic:"), "marker");
        }
    }

    #[test]
    fn pocock_setup_files_follow_the_tracker_choice() {
        for (tracker, needle, section) in [
            (
                None,
                ".scratch/<feature-slug>/",
                "markdown files under `.scratch",
            ),
            (
                Some("local"),
                ".scratch/<feature-slug>/",
                "markdown files under `.scratch",
            ),
            (Some("github"), "`gh` CLI", "GitHub Issues"),
            (Some("gitlab"), "glab issue create", "GitLab Issues"),
        ] {
            let tmp = tempfile::tempdir().unwrap();
            let dir = pocock_fixture(tmp.path());
            let project = tmp.path().join("p");
            let mut app = pocock_app(&project, &dir, tracker);
            run_install(&mut app, &project).unwrap();
            let doc =
                std::fs::read_to_string(project.join("docs/agents/issue-tracker.md")).unwrap();
            assert!(doc.contains(needle), "{tracker:?}");
            assert!(doc.contains("agentic:"), "marker");
            assert!(!doc.contains("company"), "no company data");
            for f in ["triage-labels.md", "domain.md"] {
                assert!(project.join("docs/agents").join(f).is_file(), "{f}");
            }
            let manifest = read_manifest(&project);
            assert_eq!(
                manifest["settings"]["issue_tracker"],
                tracker.unwrap_or("local")
            );
            let setup = manifest_files(&manifest, Some("pocock"))
                .into_iter()
                .filter(|(path, _, _)| path.starts_with("docs/agents/"))
                .count();
            assert_eq!(setup, 3);
            let section_text = crate::pocock_setup::agents_section(&app).unwrap();
            assert!(section_text.starts_with("## Agent skills\n"));
            assert!(section_text.contains(section), "{section_text}");
            assert!(section_text.len() < 900);
        }
    }

    #[test]
    fn pocock_setup_is_idempotent_keeps_user_edits_and_cleans_up() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pocock_fixture(tmp.path());
        let project = tmp.path().join("p");
        let mut app = pocock_app(&project, &dir, Some("github"));
        run_install(&mut app, &project).unwrap();
        let doc = project.join("docs/agents/issue-tracker.md");
        let first = std::fs::read_to_string(&doc).unwrap();
        let mut app = pocock_app(&project, &dir, Some("github"));
        run_install(&mut app, &project).unwrap();
        assert_eq!(std::fs::read_to_string(&doc).unwrap(), first);

        // A user edit survives a switch of the tracker.
        std::fs::write(&doc, format!("{first}\nMy own rule.\n")).unwrap();
        let mut app = pocock_app(&project, &dir, Some("gitlab"));
        run_install(&mut app, &project).unwrap();
        assert!(std::fs::read_to_string(&doc)
            .unwrap()
            .contains("My own rule."));
        std::fs::write(&doc, &first).unwrap();

        // Removing the preset removes the setup files too.
        let mut app = pocock_app(&project, &dir, None);
        app.skill_packs.clear();
        run_install(&mut app, &project).unwrap();
        assert!(!project.join("docs/agents/issue-tracker.md").exists());
        assert!(!project.join("docs/agents/domain.md").exists());
        assert!(!project.join("docs/agents").exists());
        assert!(!project
            .join(".claude/skills/setup-matt-pocock-skills")
            .exists());
        assert!(manifest_files(&read_manifest(&project), None).is_empty());
        assert!(read_manifest(&project)["settings"]
            .get("issue_tracker")
            .is_none());
    }
}
