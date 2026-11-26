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
            preset: self.id.to_string(),
            ..SkillPack::default()
        }
    }
}

/// The built-in preset `id`.
pub fn preset(id: &str) -> Option<&'static Preset> {
    PRESETS.iter().find(|p| p.id == id)
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
    /// Id of the built-in preset this pack comes from; empty for a pack from a URL or a directory.
    /// `.agentic.json` keeps only the preset id, the user overrides, and the lock, so a newer agentic
    /// brings the newer pin and `select` list of the preset.
    pub preset: String,
    /// The user set `ref` (`<preset>#<ref>`): the pin of the preset no longer moves the lock.
    pub own_ref: bool,
    /// The user set `select` (`--select`); otherwise the saved or preset list stays.
    pub own_select: bool,
    /// The user set `exclude` (`--exclude`); otherwise the saved list stays.
    pub own_exclude: bool,
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
            preset: String::new(),
            own_ref: false,
            own_select: false,
            own_exclude: false,
        }
    }
}

impl SkillPack {
    fn same_origin(&self, other: &SkillPack) -> bool {
        if !self.preset.is_empty() || !other.preset.is_empty() {
            return self.preset == other.preset;
        }
        self.source == other.source && self.skills_root == other.skills_root
    }

    /// True when the preset pin moved away from the lock in this agentic version.
    fn preset_pin_moved(&self) -> bool {
        !self.preset.is_empty()
            && !self.own_ref
            && !self.commit.is_empty()
            && self.commit != self.git_ref()
    }

    fn git_ref(&self) -> &str {
        match &self.source {
            Source::Git { git_ref, .. } => git_ref,
            Source::Path(_) => "",
        }
    }

    fn set_ref(&mut self, value: &str) {
        if let Source::Git { git_ref, .. } = &mut self.source {
            *git_ref = value.to_string();
        }
    }
}

fn is_git_spec(spec: &str) -> bool {
    let url = spec.rsplit_once('#').map_or(spec, |(url, _)| url);
    url.contains("://") || url.starts_with("git@") || url.ends_with(".git")
}

/// A preset id (`<preset>[#ref]`), a git spec `<url>[#ref][:skills_root]`, or a directory.
pub fn parse_spec(spec: &str) -> Result<SkillPack, String> {
    let spec = spec.trim();
    if spec.is_empty() {
        return Err("--skill-pack: empty value".into());
    }
    let (name, git_ref) = spec.split_once('#').unwrap_or((spec, ""));
    if let Some(preset) = preset(name) {
        let mut pack = preset.pack();
        if !git_ref.is_empty() {
            pack.set_ref(git_ref);
            pack.own_ref = true;
        }
        return Ok(pack);
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
                if !pack.preset.is_empty() {
                    return preset_settings(pack);
                }
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

/// A preset pack in `.agentic.json`: the preset id, the user overrides, and the lock. The URL, the pin,
/// `skills_root`, and the `select` list come from [`PRESETS`] of the running agentic.
fn preset_settings(pack: &SkillPack) -> Value {
    let mut v = json!({"preset": pack.preset, "id": pack.id});
    if pack.own_ref {
        v["ref"] = json!(pack.git_ref());
    }
    if pack.own_select {
        v["select"] = json!(pack.select);
    }
    if pack.own_exclude {
        v["exclude"] = json!(pack.exclude);
    }
    if !pack.commit.is_empty() {
        v["commit"] = json!(pack.commit);
    }
    v
}

/// A saved preset pack with its fields resolved from [`PRESETS`]. An unknown preset id keeps the
/// entry; `prepare` reports it.
fn preset_from_settings(name: &str, item: &Value, list: impl Fn(&str) -> Vec<String>) -> SkillPack {
    let mut pack = match preset(name) {
        Some(preset) => preset.pack(),
        None => SkillPack {
            id: name.to_string(),
            source: Source::Git {
                url: String::new(),
                git_ref: String::new(),
                subdir: String::new(),
            },
            preset: name.to_string(),
            ..SkillPack::default()
        },
    };
    if let Some(id) = item["id"].as_str().filter(|id| !id.is_empty()) {
        pack.id = id.to_string();
    }
    if let Some(git_ref) = item["ref"].as_str().filter(|r| !r.is_empty()) {
        pack.set_ref(git_ref);
        pack.own_ref = true;
    }
    if item["select"].is_array() {
        pack.select = list("select");
        pack.own_select = true;
    }
    if item["exclude"].is_array() {
        pack.exclude = list("exclude");
        pack.own_exclude = true;
    }
    pack.commit = item["commit"].as_str().unwrap_or_default().to_string();
    pack
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
        if let Some(name) = item["preset"].as_str().filter(|n| !n.is_empty()) {
            packs.push(preset_from_settings(name, item, |key| list(item, key)));
            continue;
        }
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
            ..SkillPack::default()
        });
    }
    Some(packs)
}

/// Add or replace `pack` by id. For the same source, what the new entry does not set stays as saved:
/// `select`, `exclude`, the own ref of a preset, and the locked commit of the same ref. So
/// `skills add pocock --issue-tracker github` changes only the tracker.
pub fn upsert(packs: &mut Vec<SkillPack>, mut pack: SkillPack) {
    match packs.iter_mut().find(|p| p.id == pack.id) {
        Some(old) => {
            if old.same_origin(&pack) {
                if !pack.own_select {
                    pack.select = old.select.clone();
                    pack.own_select = old.own_select;
                }
                if !pack.own_exclude {
                    pack.exclude = old.exclude.clone();
                    pack.own_exclude = old.own_exclude;
                }
                if !pack.preset.is_empty() && !pack.own_ref && old.own_ref {
                    pack.set_ref(old.git_ref());
                    pack.own_ref = true;
                }
                if pack.commit.is_empty() && pack.git_ref() == old.git_ref() {
                    pack.commit = old.commit.clone();
                }
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
            // A newer agentic pins the preset to another commit: move the lock there, unless the
            // user set the ref. Offline, the lock and the installed files stay.
            let pin_moved = pack.preset_pin_moved();
            if pin_moved {
                ui::log(
                    app,
                    &format!(
                        "Skill pack {id}: preset {} pins {git_ref}; moving the lock from {}",
                        pack.preset, pack.commit
                    ),
                );
            }
            let fetched = if pack.commit.is_empty() || refresh || pin_moved {
                source::fetch_ref(app, CACHE_KIND, LABEL, url, git_ref)
            } else {
                None
            };
            let dir = if let Some(dir) = fetched {
                dir
            } else if pin_moved && !refresh {
                ui::warn(
                    app,
                    &format!(
                        "Skill pack {id}: cannot fetch the new preset pin {git_ref}; the lock stays at {}",
                        pack.commit
                    ),
                );
                match source::checkout_commit(app, CACHE_KIND, LABEL, url, &pack.commit) {
                    Some(dir) => dir,
                    None => return Ok(None),
                }
            } else if pack.commit.is_empty() {
                return Err(format!(
                    "Skill pack {id}: cannot fetch {shown}; nothing was installed or saved"
                )
                .into());
            } else if refresh {
                return Err(format!(
                    "Skill pack {id}: cannot fetch {shown}; the lock stays at {}",
                    pack.commit
                )
                .into());
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
    // The preset `pocock` installs agentic's own `setup-matt-pocock-skills` in place of the upstream
    // one; no other skill may take that name.
    if let Some(setup_id) = crate::pocock_setup::pack_id(app).map(str::to_string) {
        let name = crate::pocock_setup::SETUP_SKILL;
        if let Some(owner) = owners.get(name) {
            return Err(format!(
                "Skill pack {setup_id}: the preset installs the agentic skill `{name}`, but {owner} has \
                 that name; rename or remove that skill"
            )
            .into());
        }
        owners.insert(
            name.to_string(),
            format!("the agentic setup skill of preset pocock (pack {setup_id})"),
        );
    }
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
        if !pack.preset.is_empty() && preset(&pack.preset).is_none() {
            return Err(format!(
                "Skill pack {id}: unknown preset `{}`; this agentic version has {}",
                pack.preset,
                PRESETS.iter().map(|p| p.id).collect::<Vec<_>>().join(", ")
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
            // The preset always gets agentic's stand-in, never the upstream setup skill.
            if pack.preset == crate::pocock_setup::PACK_ID
                && name == crate::pocock_setup::SETUP_SKILL
            {
                ui::log(
                    app,
                    &format!(
                        "Skill pack {id}: upstream `{name}` skipped; agentic installs its own"
                    ),
                );
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
/// Every host gets the upstream text unchanged: Claude Code and OpenCode read
/// `disable-model-invocation` themselves, and Codex ignores unknown frontmatter keys. The files that a
/// host needs in addition come from [`host_entry_files`].
pub fn adapt_for_host(_host: &str, _skill: &str, _rel: &str, content: &str) -> String {
    content.to_string()
}

/// Path of the Codex skill metadata file below a skill directory.
pub const CODEX_METADATA: &str = "agents/openai.yaml";
const CODEX_POLICY: &str = "policy:\n  allow_implicit_invocation: false\n";

/// A user-invoked skill: the top-level frontmatter of its `SKILL.md` has
/// `disable-model-invocation: true` (the Claude Code key that upstream packs use).
pub fn user_invoked(skill: &PackSkill) -> bool {
    let Some((_, text)) = skill.files.iter().find(|(rel, _)| rel == "SKILL.md") else {
        return false;
    };
    top_level_frontmatter(text)
        .iter()
        .any(|(key, value)| key == "disable-model-invocation" && value.eq_ignore_ascii_case("true"))
}

/// `key: value` pairs of the unindented lines of the leading frontmatter block.
fn top_level_frontmatter(text: &str) -> Vec<(String, String)> {
    let text = text.strip_prefix('\u{feff}').unwrap_or(text);
    let Some(rest) = text
        .strip_prefix("---\n")
        .or_else(|| text.strip_prefix("---\r\n"))
    else {
        return Vec::new();
    };
    let mut out = Vec::new();
    for line in rest.lines() {
        if line.trim_end() == "---" {
            break;
        }
        if line.starts_with([' ', '\t']) {
            continue;
        }
        if let Some((key, value)) = line.split_once(':') {
            let value = value.trim().trim_matches(|c| c == '\'' || c == '"');
            out.push((key.trim().to_string(), value.to_string()));
        }
    }
    out
}

/// The OpenCode command text that starts user-invoked skill `name`.
fn opencode_command(name: &str, skill: &PackSkill) -> String {
    let description = skill
        .files
        .iter()
        .find(|(rel, _)| rel == "SKILL.md")
        .and_then(|(_, text)| {
            top_level_frontmatter(text)
                .into_iter()
                .find(|(key, _)| key == "description")
                .map(|(_, value)| value)
        })
        .filter(|value| !value.is_empty() && !value.starts_with(['>', '|']))
        .unwrap_or_else(|| format!("Run the {name} skill"));
    format!(
        "---\ndescription: {}\n---\n\nLoad the skill `{name}` with the skill tool and follow its instructions.\n\nArguments: $ARGUMENTS\n",
        serde_json::to_string(&description).unwrap_or_default()
    )
}

/// One file that a host needs besides the upstream skill files.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EntryFile {
    /// Path relative to the project.
    pub path: String,
    pub content: String,
    /// `<skill>/@<host>/<file>`: the manifest source below `skill-pack:<id>/`.
    pub source: String,
}

/// The user entry point of a user-invoked skill on `host`, whose skills directory is `dir`:
/// - Claude Code: none; the skill is the `/<name>` command, and Claude reads the frontmatter key.
/// - OpenCode: `.opencode/commands/<name>.md`, the `/<name>` command that loads the skill.
/// - Codex: `agents/openai.yaml` with `allow_implicit_invocation: false`; the user starts the skill
///   with `$<name>` or `/skills`. A skill that ships its own `agents/openai.yaml` keeps it.
pub fn host_entry_files(host: &str, dir: &str, skill: &PackSkill) -> Vec<EntryFile> {
    if !user_invoked(skill) {
        return Vec::new();
    }
    let name = &skill.name;
    match host {
        "opencode" => vec![EntryFile {
            path: format!(
                "{}/{name}.md",
                crate::agentsmd::get_dest_dir("opencode", "workflows")
            ),
            content: opencode_command(name, skill),
            source: format!("{name}/@opencode/command.md"),
        }],
        "codex" if !skill.files.iter().any(|(rel, _)| rel == CODEX_METADATA) => {
            vec![EntryFile {
                path: format!("{dir}/{name}/{CODEX_METADATA}"),
                content: CODEX_POLICY.to_string(),
                source: format!("{name}/@codex/{CODEX_METADATA}"),
            }]
        }
        _ => Vec::new(),
    }
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
            if host == "codex" && user_invoked(skill) {
                warn_own_codex_metadata(app, skill);
            }
            for entry in host_entry_files(host, dir, skill) {
                let dest = project_dir.join(&entry.path);
                desired.insert(app.project_rel_path(&dest));
                write(
                    app,
                    &entry.content,
                    &dest,
                    &source_ref(&skill.pack, &entry.source),
                )?;
            }
        }
    }
    if let Some(setup_id) = crate::pocock_setup::pack_id(app).map(str::to_string) {
        let skill = crate::pocock_setup::SETUP_SKILL;
        // The stand-in skill is user-invoked, so it gets the same host entry points as pack skills.
        let stub = PackSkill {
            pack: setup_id.clone(),
            name: skill.to_string(),
            files: vec![(
                "SKILL.md".to_string(),
                crate::pocock_setup::SETUP_SKILL_TEXT.to_string(),
            )],
        };
        for (host, dir) in &dirs {
            let text = adapt_for_host(
                host,
                skill,
                "SKILL.md",
                crate::pocock_setup::SETUP_SKILL_TEXT,
            );
            let dest = project_dir.join(dir).join(skill).join("SKILL.md");
            desired.insert(app.project_rel_path(&dest));
            let source = source_ref(&setup_id, &format!("{skill}/SKILL.md"));
            write(app, &text, &dest, &source)?;
            for entry in host_entry_files(host, dir, &stub) {
                let dest = project_dir.join(&entry.path);
                desired.insert(app.project_rel_path(&dest));
                write(
                    app,
                    &entry.content,
                    &dest,
                    &source_ref(&stub.pack, &entry.source),
                )?;
            }
        }
    }
    let setup_id = crate::pocock_setup::pack_id(app)
        .unwrap_or_default()
        .to_string();
    for (rel, text, name) in crate::pocock_setup::files(app) {
        let dest = project_dir.join(rel);
        desired.insert(app.project_rel_path(&dest));
        write(app, &text, &dest, &source_ref(&setup_id, name))?;
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

/// An upstream `agents/openai.yaml` stays unchanged; say so when it does not turn implicit
/// invocation off.
fn warn_own_codex_metadata(app: &mut App, skill: &PackSkill) {
    let own = skill
        .files
        .iter()
        .find(|(rel, _)| rel == CODEX_METADATA)
        .map(|(_, text)| text);
    if own.is_some_and(|text| !text.contains("allow_implicit_invocation")) {
        ui::warn(
            app,
            &format!(
                "Skill pack {}: {}/{CODEX_METADATA} is the pack's own file; Codex may start the skill without `${}`",
                skill.pack, skill.name, skill.name
            ),
        );
    }
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
                if !pack.preset.is_empty() {
                    return Err(format!(
                        "skills add: preset `{}` sets its own skills_root; --skills-root is for a URL or a directory",
                        pack.preset
                    )
                    .into());
                }
                pack.skills_root = root;
            }
            if let Some(select) = select {
                pack.select = select;
                pack.own_select = true;
            }
            if let Some(exclude) = exclude {
                pack.exclude = exclude;
                pack.own_exclude = true;
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
        if !pack.preset.is_empty() {
            line.push_str(&format!("  preset={}", pack.preset));
        }
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
        app.skill_packs = vec![again.clone()];
        merge_saved(&mut app, packs.clone());
        assert_eq!(app.skill_packs.len(), 2);
        assert_eq!(app.skill_packs[0].commit, "abc");
        // Without an explicit `select` the saved list stays; an explicit one replaces it.
        assert_eq!(app.skill_packs[0].select, vec!["tdd"]);
        again.own_select = true;
        app.skill_packs = vec![again];
        merge_saved(&mut app, packs.clone());
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

    const USER_SKILL: &str = "---\nname: to-spec\ndescription: Turn the talk into a \"spec\".\ndisable-model-invocation: true\n---\n\n# To spec\n\nUse $ARGUMENTS as the topic.\n";

    fn skill_names(dir: &Path) -> Vec<String> {
        find_skills(dir).into_iter().map(|(name, _)| name).collect()
    }

    /// The text below the frontmatter block.
    fn body(text: &str) -> &str {
        let rest = text.strip_prefix("---\n").unwrap();
        &rest[rest.find("\n---\n").unwrap() + 5..]
    }

    #[test]
    fn hosts_get_the_same_skills_and_a_user_entry_point() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = tmp.path().join("pack");
        write(&dir.join("skills/engineering/tdd/SKILL.md"), SKILL);
        write(&dir.join("skills/planning/to-spec/SKILL.md"), USER_SKILL);
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &dir);
        run_install(&mut app, &project).unwrap();

        let hosts = [
            ("claude", ".claude/skills"),
            ("codex", ".agents/skills"),
            ("opencode", ".opencode/skills"),
        ];
        for (host, skills_dir) in hosts {
            assert_eq!(
                skill_names(&project.join(skills_dir)),
                vec!["tdd", "to-spec"],
                "{host}"
            );
            for (name, upstream) in [("tdd", SKILL), ("to-spec", USER_SKILL)] {
                let text =
                    std::fs::read_to_string(project.join(skills_dir).join(name).join("SKILL.md"))
                        .unwrap();
                assert_eq!(body(&text), body(upstream), "{host} {name}");
                for line in upstream.lines().skip(1).take_while(|l| *l != "---") {
                    assert!(text.lines().any(|l| l == line), "{host} {name}: {line}");
                }
            }
        }
        // Claude Code: the skill itself is `/to-spec`, and Claude reads the frontmatter key.
        // OpenCode: a `/to-spec` command loads the skill.
        let command =
            std::fs::read_to_string(project.join(".opencode/commands/to-spec.md")).unwrap();
        assert!(command.contains("description: \"Turn the talk into a \\\"spec\\\".\""));
        assert!(command.contains("Load the skill `to-spec` with the skill tool"));
        assert!(command.contains("Arguments: $ARGUMENTS"));
        // Codex: implicit invocation off; the user starts it with `$to-spec`.
        let policy =
            std::fs::read_to_string(project.join(".agents/skills/to-spec/agents/openai.yaml"))
                .unwrap();
        assert!(policy.contains("policy:\n  allow_implicit_invocation: false\n"));
        // A model-invoked skill gets no extra file.
        assert!(!project.join(".opencode/commands/tdd.md").exists());
        assert!(!project.join(".agents/skills/tdd/agents").exists());
        assert!(!project.join(".claude/skills/to-spec/agents").exists());
        assert!(!project.join(".opencode/skills/to-spec/agents").exists());
        let manifest = read_manifest(&project);
        assert_eq!(installed_skills(&manifest, "demo"), vec!["tdd", "to-spec"]);
        let sources: Vec<String> = manifest_files(&manifest, None)
            .into_iter()
            .map(|(path, source, _)| format!("{path} {source}"))
            .collect();
        assert!(sources.contains(
            &".opencode/commands/to-spec.md skill-pack:demo/to-spec/@opencode/command.md".into()
        ));
        assert!(sources.contains(
            &".agents/skills/to-spec/agents/openai.yaml skill-pack:demo/to-spec/@codex/agents/openai.yaml"
                .into()
        ));

        // Remove: nothing of the pack stays on any host.
        let mut app = app_for(&project, &dir);
        app.skill_packs.clear();
        run_install(&mut app, &project).unwrap();
        for (_, skills_dir) in hosts {
            assert!(skill_names(&project.join(skills_dir)).is_empty());
        }
        assert!(!project.join(".opencode/commands/to-spec.md").exists());
        assert!(manifest_files(&read_manifest(&project), None).is_empty());
    }

    #[test]
    fn user_invoked_reads_only_the_top_level_key() {
        let skill = |text: &str| PackSkill {
            pack: "demo".into(),
            name: "x".into(),
            files: vec![("SKILL.md".into(), text.into())],
        };
        assert!(user_invoked(&skill(USER_SKILL)));
        assert!(user_invoked(&skill(
            "---\r\nname: x\r\ndisable-model-invocation: \"True\"\r\n---\r\n"
        )));
        assert!(!user_invoked(&skill(SKILL)));
        assert!(!user_invoked(&skill(
            "---\nmetadata:\n  disable-model-invocation: true\n---\n"
        )));
        assert!(!user_invoked(&skill(
            "---\nname: x\n---\ndisable-model-invocation: true\n"
        )));
        assert!(!user_invoked(&skill("disable-model-invocation: true\n")));
        let folded = skill("---\ndescription: >\n  long\ndisable-model-invocation: true\n---\n");
        assert!(opencode_command("x", &folded).contains("description: \"Run the x skill\""));
    }

    #[test]
    fn codex_keeps_the_pack_metadata_file() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = tmp.path().join("pack");
        write(&dir.join("skills/to-spec/SKILL.md"), USER_SKILL);
        write(
            &dir.join("skills/to-spec/agents/openai.yaml"),
            "interface:\n  display_name: \"To spec\"\n",
        );
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &dir);
        run_install(&mut app, &project).unwrap();
        let text =
            std::fs::read_to_string(project.join(".agents/skills/to-spec/agents/openai.yaml"))
                .unwrap();
        assert!(text.contains("display_name") && !text.contains("allow_implicit_invocation"));
        assert!(app
            .warnings
            .iter()
            .any(|w| w.contains("to-spec/agents/openai.yaml is the pack's own file")));
        assert!(project.join(".opencode/commands/to-spec.md").is_file());
    }

    #[test]
    fn a_command_name_taken_by_agentic_is_an_error() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = tmp.path().join("pack");
        write(&dir.join("skills/profile/SKILL.md"), USER_SKILL);
        let project = tmp.path().join("p");
        let mut app = app_for(&project, &dir);
        manifest::register_managed_file(
            &mut app,
            &project.join(".opencode/commands/profile.md"),
            "extensions/opencode/commands/profile.md",
            "extension",
            false,
        );
        let err = run_install(&mut app, &project).unwrap_err();
        assert!(
            err.to_string()
                .contains(".opencode/commands/profile.md clashes with"),
            "{err}"
        );
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
        // The stand-in skill is user-invoked: it gets the OpenCode command and the Codex policy.
        let command =
            std::fs::read_to_string(project.join(".opencode/commands/setup-matt-pocock-skills.md"))
                .unwrap();
        assert!(command.contains("Load the skill `setup-matt-pocock-skills`"));
        assert!(command.contains("agentic:"), "marker");
        let policy = std::fs::read_to_string(
            project.join(".agents/skills/setup-matt-pocock-skills/agents/openai.yaml"),
        )
        .unwrap();
        assert_eq!(policy, "policy:\n  allow_implicit_invocation: false\n");
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
            assert!(section_text.starts_with(&format!(
                "{}\n## Agent skills\n",
                crate::pocock_setup::SECTION_BEGIN
            )));
            assert!(section_text.contains(section), "{section_text}");
            assert!(section_text.len() < 900);
        }
    }

    /// A full install (no packs) of `project`, then `skills add`-like synchronization with `packs`.
    fn full_install(project: &Path, home: &Path) {
        let mut app = App::new().unwrap();
        app.project_dir = project.to_string_lossy().to_string();
        app.config_home_override = Some(home.to_path_buf());
        app.home = home.to_path_buf();
        app.doctor_enabled_env = false;
        app.selected_agent_os = vec!["claude".into(), "codex".into(), "opencode".into()];
        app.selected_areas = vec!["software".into()];
        app.selected_specs = vec!["software.backend".into()];
        crate::install::run_install(&mut app).unwrap();
    }

    fn synchronize_with(
        project: &Path,
        home: &Path,
        packs: Vec<SkillPack>,
        tracker: Option<&str>,
    ) -> (crate::Result<()>, App) {
        let mut app = App::new().unwrap();
        app.project_dir = project.to_string_lossy().to_string();
        app.config_home_override = Some(home.to_path_buf());
        app.home = home.to_path_buf();
        app.doctor_enabled_env = false;
        app.skill_packs = packs;
        app.skill_packs_replace = true;
        app.issue_tracker = tracker.map(str::to_string);
        let result = crate::project_update::synchronize(&mut app);
        (result, app)
    }

    #[test]
    fn pocock_setup_keeps_a_user_file_in_docs_agents_on_upgrade() {
        // docs/agents was not in the project inventory: a user file there (for example from the
        // upstream /setup-matt-pocock-skills) made `skills add pocock` and every upgrade fail.
        let tmp = tempfile::tempdir().unwrap();
        let dir = pocock_fixture(tmp.path());
        let project = tmp.path().join("p");
        let home = tmp.path().join("home");
        full_install(&project, &home);
        let user = "# Domain\n\nOur own domain notes.\n";
        write(&project.join("docs/agents/domain.md"), user);
        let packs = pocock_app(&project, &dir, None).skill_packs;
        let (result, app) = synchronize_with(&project, &home, packs.clone(), None);
        result.unwrap();
        assert_eq!(
            std::fs::read_to_string(project.join("docs/agents/domain.md")).unwrap(),
            user
        );
        assert!(app
            .upgrade_actions
            .iter()
            .any(|a| a.contains("Preserved user file") && a.contains("docs/agents/domain.md")));
        assert!(project.join("docs/agents/issue-tracker.md").is_file());
        // The next upgrade works as well and still keeps the file.
        let (result, _) = synchronize_with(&project, &home, packs, None);
        result.unwrap();
        assert_eq!(
            std::fs::read_to_string(project.join("docs/agents/domain.md")).unwrap(),
            user
        );
    }

    #[test]
    fn pocock_agents_section_merges_with_user_edits_at_the_end() {
        // The section was appended at the end of AGENTS.md: with a user edit there the merge
        // conflicted and the whole file was replaced (the edit only in the backup).
        let tmp = tempfile::tempdir().unwrap();
        let dir = pocock_fixture(tmp.path());
        let project = tmp.path().join("p");
        let home = tmp.path().join("home");
        full_install(&project, &home);
        let agents = project.join("AGENTS.md");
        let mut text = std::fs::read_to_string(&agents).unwrap();
        text.push_str("\n## Our team\n\nAlways run make check.\n");
        std::fs::write(&agents, &text).unwrap();
        let packs = pocock_app(&project, &dir, None).skill_packs;
        for tracker in ["local", "github"] {
            let (result, app) = synchronize_with(&project, &home, packs.clone(), Some(tracker));
            result.unwrap();
            let text = std::fs::read_to_string(&agents).unwrap();
            assert!(text.contains("Always run make check."), "{tracker}");
            assert_eq!(text.matches("## Agent skills").count(), 1, "{tracker}");
            assert_eq!(
                text.matches(crate::pocock_setup::SECTION_BEGIN).count(),
                1,
                "{tracker}"
            );
            assert!(
                !app.upgrade_actions
                    .iter()
                    .any(|a| a.contains("Replaced conflict")),
                "{tracker}: {:?}",
                app.upgrade_actions
            );
        }
        assert!(std::fs::read_to_string(&agents)
            .unwrap()
            .contains("GitHub Issues"));
    }

    #[test]
    fn pocock_agents_section_is_not_added_next_to_the_users_own() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pocock_fixture(tmp.path());
        let project = tmp.path().join("p");
        let home = tmp.path().join("home");
        full_install(&project, &home);
        let agents = project.join("AGENTS.md");
        let mut text = std::fs::read_to_string(&agents).unwrap();
        text.push_str("\n## Agent skills\n\nIssues live in Jira.\n");
        std::fs::write(&agents, &text).unwrap();
        let packs = pocock_app(&project, &dir, None).skill_packs;
        let (result, app) = synchronize_with(&project, &home, packs, None);
        result.unwrap();
        let text = std::fs::read_to_string(&agents).unwrap();
        assert_eq!(text.matches("## Agent skills").count(), 1);
        assert!(text.contains("Issues live in Jira."));
        assert!(!text.contains(crate::pocock_setup::SECTION_BEGIN));
        assert!(app
            .warnings
            .iter()
            .any(|w| w.contains("has its own `## Agent skills` section")));
        assert!(crate::pocock_setup::has_own_section(&text));
        assert!(!crate::pocock_setup::has_own_section(&format!(
            "{}\n## Agent skills\n{}\n",
            crate::pocock_setup::SECTION_BEGIN,
            crate::pocock_setup::SECTION_END
        )));
    }

    #[test]
    fn preset_settings_keep_only_the_preset_id_overrides_and_lock() {
        // The pin and the select list were saved in full, so a newer agentic never reached them.
        let mut pack = parse_spec("pocock").unwrap();
        pack.commit = "a".repeat(40);
        let saved = to_settings(std::slice::from_ref(&pack));
        assert_eq!(
            saved,
            json!([{"preset": "pocock", "id": "pocock", "commit": "a".repeat(40)}])
        );
        let back = from_settings(&saved).unwrap();
        assert_eq!(back, vec![pack.clone()]);
        assert_eq!(back[0].select.len(), pocock_preset().select.len());
        assert_eq!(back[0].git_ref(), pocock_preset().git_ref);

        // User overrides stay; everything else comes from the preset.
        let mut custom = parse_spec("pocock#v2").unwrap();
        custom.id = "mp".into();
        custom.select = vec!["tdd".into()];
        custom.own_select = true;
        custom.exclude = vec!["pr".into()];
        custom.own_exclude = true;
        let saved = to_settings(std::slice::from_ref(&custom));
        assert_eq!(
            saved,
            json!([{"preset": "pocock", "id": "mp", "ref": "v2", "select": ["tdd"], "exclude": ["pr"]}])
        );
        assert_eq!(from_settings(&saved).unwrap(), vec![custom]);

        // An unknown preset is an error, not a silent removal of its files.
        let mut app = app_for(Path::new("/nonexistent"), Path::new("/nonexistent"));
        app.skill_packs =
            from_settings(&json!([{"preset": "gone", "commit": "b".repeat(40)}])).unwrap();
        let err = prepare(&mut app, &crate::company::Prepared::default()).unwrap_err();
        assert!(err.to_string().contains("unknown preset `gone`"), "{err}");
    }

    #[test]
    fn a_new_preset_pin_moves_the_lock_unless_the_user_set_the_ref() {
        if std::env::var_os("XDG_CACHE_HOME").is_some() {
            return;
        }
        let tmp = tempfile::tempdir().unwrap();
        let work = pack_dir(tmp.path());
        let git = init_repo(&work);
        git(&["init", "-q", "-b", "main"]);
        git(&["add", "-A"]);
        git(&["commit", "-qm", "one"]);
        let old = source::head_commit(&work).unwrap();
        write(&work.join("skills/new-skill/SKILL.md"), SKILL);
        git(&["add", "-A"]);
        git(&["commit", "-qm", "two"]);
        let pin = source::head_commit(&work).unwrap();
        let project = tmp.path().join("p");
        // A preset whose pin (`ref`) is `pin` while the saved lock is still `old`.
        let preset_app = |own_ref: bool| {
            let mut app = app_for(&project, &work);
            app.home = tmp.path().join("home");
            let mut pack = parse_spec("pocock").unwrap();
            pack.source = Source::Git {
                url: work.to_string_lossy().to_string(),
                git_ref: pin.clone(),
                subdir: String::new(),
            };
            pack.select.clear();
            pack.commit = old.clone();
            pack.own_ref = own_ref;
            app.skill_packs = vec![pack];
            app
        };
        let mut app = preset_app(true);
        prepare(&mut app, &crate::company::Prepared::default()).unwrap();
        assert_eq!(app.skill_packs[0].commit, old, "an own ref keeps the lock");
        let mut app = preset_app(false);
        let prepared = prepare(&mut app, &crate::company::Prepared::default()).unwrap();
        assert_eq!(app.skill_packs[0].commit, pin);
        assert!(prepared.skills.iter().any(|s| s.name == "new-skill"));
    }

    #[test]
    fn adding_a_pack_again_keeps_the_saved_select_exclude_and_ref() {
        // `skills add pocock --issue-tracker X` (what the stand-in skill recommends) reset them.
        let mut saved = parse_spec("pocock#v2").unwrap();
        saved.select = vec!["tdd".into()];
        saved.own_select = true;
        saved.exclude = vec!["pr".into()];
        saved.own_exclude = true;
        saved.commit = "c".repeat(40);
        let mut packs = vec![saved.clone()];
        upsert(&mut packs, parse_spec("pocock").unwrap());
        assert_eq!(packs, vec![saved.clone()]);
        // Explicit flags replace the saved values; a new ref drops the old lock.
        let mut again = parse_spec("pocock#v3").unwrap();
        again.select = vec!["grill-me".into()];
        again.own_select = true;
        upsert(&mut packs, again);
        assert_eq!(packs[0].select, vec!["grill-me"]);
        assert_eq!(packs[0].exclude, vec!["pr"]);
        assert_eq!(packs[0].git_ref(), "v3");
        assert!(packs[0].commit.is_empty());
        // The same for a URL pack.
        let mut url = parse_spec("https://example.com/team/skills.git#main").unwrap();
        url.exclude = vec!["draft".into()];
        let mut packs = vec![url.clone()];
        upsert(
            &mut packs,
            parse_spec("https://example.com/team/skills.git#main").unwrap(),
        );
        assert_eq!(packs[0].exclude, vec!["draft"]);
    }

    #[test]
    fn pocock_setup_follows_the_preset_not_the_id() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pocock_fixture(tmp.path());
        // A pack from a directory with the id `pocock` is not the preset: no setup, no stand-in.
        let project = tmp.path().join("p1");
        let mut app = app_for(&project, &dir);
        app.skill_packs[0].id = "pocock".into();
        app.skill_packs[0].select = vec!["tdd".into()];
        run_install(&mut app, &project).unwrap();
        assert!(!crate::pocock_setup::active(&app));
        assert!(!project.join("docs/agents").exists());
        assert!(!project
            .join(".claude/skills/setup-matt-pocock-skills")
            .exists());
        // The preset under another id gets the setup, with sources of that id.
        let project = tmp.path().join("p2");
        let mut app = pocock_app(&project, &dir, None);
        app.skill_packs[0].id = "mp".into();
        run_install(&mut app, &project).unwrap();
        assert!(project.join("docs/agents/domain.md").is_file());
        let manifest = read_manifest(&project);
        assert!(installed_skills(&manifest, "mp").contains(&"setup-matt-pocock-skills".to_string()));
        assert!(manifest_files(&manifest, Some("pocock")).is_empty());
    }

    #[test]
    fn the_upstream_setup_skill_never_replaces_the_stand_in() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pocock_fixture(tmp.path());
        write(
            &dir.join("skills/misc/setup-matt-pocock-skills/refs/questions.md"),
            "# upstream\n",
        );
        let project = tmp.path().join("p");
        let mut app = pocock_app(&project, &dir, None);
        app.skill_packs[0]
            .select
            .push("setup-matt-pocock-skills".into());
        app.skill_packs[0].own_select = true;
        run_install(&mut app, &project).unwrap();
        for dir in [".claude/skills", ".agents/skills", ".opencode/skills"] {
            let skill = project.join(dir).join("setup-matt-pocock-skills");
            assert!(std::fs::read_to_string(skill.join("SKILL.md"))
                .unwrap()
                .contains("managed by agentic"));
            assert!(!skill.join("refs").exists(), "{dir}");
        }
    }

    #[test]
    fn another_skill_named_like_the_stand_in_is_a_clear_error() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = pocock_fixture(tmp.path());
        let other = tmp.path().join("other");
        write(
            &other.join("skills/setup-matt-pocock-skills/SKILL.md"),
            SKILL,
        );
        write(&other.join("skills/notes/SKILL.md"), SKILL);
        let project = tmp.path().join("p");
        let mut app = pocock_app(&project, &dir, None);
        let mut pack = parse_spec(&other.to_string_lossy()).unwrap();
        pack.id = "other".into();
        app.skill_packs.push(pack);
        let err = prepare(&mut app, &crate::company::Prepared::default()).unwrap_err();
        let err = err.to_string();
        assert!(
            err.contains("Skill pack other: skill `setup-matt-pocock-skills`"),
            "{err}"
        );
        assert!(
            err.contains("agentic setup skill of preset pocock"),
            "{err}"
        );
        assert!(err.contains("add it to the pack's `exclude`"), "{err}");
        // The advice works.
        app.skill_packs[1].exclude = vec!["setup-matt-pocock-skills".into()];
        run_install(&mut app, &project).unwrap();
        assert!(project.join(".claude/skills/notes/SKILL.md").is_file());

        // A company skill with that name cannot be excluded from the preset: rename it.
        let company = crate::company::Prepared {
            skills: vec![crate::company::RuleFile {
                source_id: "standards".into(),
                rel: "setup-matt-pocock-skills/SKILL.md".into(),
                content: SKILL.into(),
                in_place: false,
            }],
            ..crate::company::Prepared::default()
        };
        let mut app = pocock_app(&project, &dir, None);
        let err = prepare(&mut app, &company).unwrap_err().to_string();
        assert!(err.contains("the company skill from standards"), "{err}");
        assert!(err.contains("rename or remove that skill"), "{err}");
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
        assert!(!project
            .join(".opencode/commands/setup-matt-pocock-skills.md")
            .exists());
        assert!(!project
            .join(".agents/skills/setup-matt-pocock-skills")
            .exists());
        assert!(manifest_files(&read_manifest(&project), None).is_empty());
        assert!(read_manifest(&project)["settings"]
            .get("issue_tracker")
            .is_none());
    }
}
