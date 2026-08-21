//! Knowledge base access. The payload (areas/, extensions/, AGENTS.md,
//! MEMORY.md, CHANGELOG.md) is embedded into the binary at build time.
//! A development checkout next to the executable (or AGENTIC_KB_DIR) takes
//! priority so contributors can iterate without rebuilding.

use include_dir::{include_dir, Dir};
use std::path::{Path, PathBuf};

static AREAS: Dir = include_dir!("$CARGO_MANIFEST_DIR/areas");
static EXTENSIONS: Dir = include_dir!("$CARGO_MANIFEST_DIR/extensions");
static ROOT_AGENTS_MD: &str = include_str!("../AGENTS.md");
static ROOT_MEMORY_MD: &str = include_str!("../MEMORY.md");
static ROOT_CHANGELOG_MD: &str = include_str!("../CHANGELOG.md");

pub const STATIC_AGENT_OS: [&str; 6] = [
    "opencode",
    "codex",
    "claude",
    "antigravity",
    "cursor",
    "kilocode",
];

#[derive(Debug, Clone)]
pub enum Kb {
    Embedded,
    Checkout(PathBuf),
}

fn is_repo_root(dir: &Path) -> bool {
    dir.join("areas").is_dir() && dir.join("extensions").is_dir() && dir.join("AGENTS.md").is_file()
}

impl Kb {
    pub fn resolve() -> Kb {
        if let Ok(override_dir) = std::env::var("AGENTIC_KB_DIR") {
            let path = PathBuf::from(&override_dir);
            if is_repo_root(&path) {
                return Kb::Checkout(path);
            }
        }
        if let Ok(exe) = std::env::current_exe() {
            let mut candidates: Vec<PathBuf> = Vec::new();
            if let Some(dir) = exe.parent() {
                candidates.push(dir.to_path_buf());
                if let Some(parent) = dir.parent() {
                    candidates.push(parent.to_path_buf());
                    // target/{debug,release}/agentic -> repo root two levels up
                    if let Some(grand) = parent.parent() {
                        candidates.push(grand.to_path_buf());
                    }
                }
            }
            for candidate in candidates {
                if is_repo_root(&candidate) {
                    return Kb::Checkout(candidate);
                }
            }
        }
        Kb::Embedded
    }

    pub fn root_label(&self) -> String {
        match self {
            Kb::Embedded => format!("embedded:{}", crate::app_version_label()),
            Kb::Checkout(path) => path.to_string_lossy().to_string(),
        }
    }

    fn list_dir_names(&self, rel: &str) -> Vec<String> {
        let mut names: Vec<String> = match self {
            Kb::Embedded => {
                let (root, sub) = if let Some(rest) = rel.strip_prefix("areas") {
                    (&AREAS, rest.trim_start_matches('/'))
                } else if let Some(rest) = rel.strip_prefix("extensions") {
                    (&EXTENSIONS, rest.trim_start_matches('/'))
                } else {
                    return Vec::new();
                };
                let dir = if sub.is_empty() {
                    Some(root)
                } else {
                    root.get_dir(sub)
                };
                dir.map(|d| {
                    d.dirs()
                        .filter_map(|sd| {
                            sd.path()
                                .file_name()
                                .map(|n| n.to_string_lossy().to_string())
                        })
                        .collect()
                })
                .unwrap_or_default()
            }
            Kb::Checkout(root) => {
                let dir = root.join(rel);
                std::fs::read_dir(&dir)
                    .map(|entries| {
                        entries
                            .filter_map(|e| e.ok())
                            .filter(|e| e.path().is_dir())
                            .map(|e| e.file_name().to_string_lossy().to_string())
                            .collect()
                    })
                    .unwrap_or_default()
            }
        };
        names.sort();
        names
    }

    pub fn list_areas(&self) -> Vec<String> {
        self.list_dir_names("areas")
            .into_iter()
            .filter(|name| name != "template")
            .collect()
    }

    pub fn list_specs(&self, area: &str) -> Vec<String> {
        self.list_dir_names(&format!("areas/{area}"))
    }

    pub fn dynamic_agentos(&self) -> Vec<String> {
        self.list_dir_names("extensions")
    }

    pub fn agentos_choices(&self) -> Vec<String> {
        let mut seen: Vec<String> = Vec::new();
        for name in STATIC_AGENT_OS {
            crate::util::unique_append(&mut seen, name);
        }
        for name in self.dynamic_agentos() {
            crate::util::unique_append(&mut seen, &name);
        }
        seen
    }

    pub fn dir_exists(&self, rel: &str) -> bool {
        match self {
            Kb::Embedded => {
                if let Some(rest) = rel.strip_prefix("areas/") {
                    AREAS.get_dir(rest).is_some()
                } else if let Some(rest) = rel.strip_prefix("extensions/") {
                    EXTENSIONS.get_dir(rest).is_some()
                } else {
                    rel == "areas" || rel == "extensions"
                }
            }
            Kb::Checkout(root) => root.join(rel).is_dir(),
        }
    }

    pub fn read_file(&self, rel: &str) -> Option<String> {
        match self {
            Kb::Embedded => match rel {
                "AGENTS.md" => Some(ROOT_AGENTS_MD.to_string()),
                "MEMORY.md" => Some(ROOT_MEMORY_MD.to_string()),
                "CHANGELOG.md" => Some(ROOT_CHANGELOG_MD.to_string()),
                _ => {
                    if let Some(rest) = rel.strip_prefix("areas/") {
                        AREAS
                            .get_file(rest)
                            .and_then(|f| f.contents_utf8())
                            .map(|s| s.to_string())
                    } else if let Some(rest) = rel.strip_prefix("extensions/") {
                        EXTENSIONS
                            .get_file(rest)
                            .and_then(|f| f.contents_utf8())
                            .map(|s| s.to_string())
                    } else {
                        None
                    }
                }
            },
            Kb::Checkout(root) => std::fs::read_to_string(root.join(rel)).ok(),
        }
    }

    /// Recursively collect files under a knowledge-base relative directory.
    /// Returns (path relative to `rel`, file content) sorted by path.
    pub fn walk_files(&self, rel: &str) -> Vec<(String, String)> {
        let mut files: Vec<(String, String)> = Vec::new();
        match self {
            Kb::Embedded => {
                let (root, sub) = if let Some(rest) = rel.strip_prefix("areas") {
                    (&AREAS, rest.trim_start_matches('/'))
                } else if let Some(rest) = rel.strip_prefix("extensions") {
                    (&EXTENSIONS, rest.trim_start_matches('/'))
                } else {
                    return files;
                };
                let dir = if sub.is_empty() {
                    Some(root)
                } else {
                    root.get_dir(sub)
                };
                if let Some(dir) = dir {
                    collect_embedded(dir, sub, &mut files);
                }
            }
            Kb::Checkout(root) => {
                let base = root.join(rel);
                collect_fs(&base, &base, &mut files);
            }
        }
        files.sort_by(|a, b| a.0.cmp(&b.0));
        files
    }
}

fn collect_embedded(dir: &Dir, base: &str, out: &mut Vec<(String, String)>) {
    for file in dir.files() {
        let full = file.path().to_string_lossy().to_string();
        let rel = if base.is_empty() {
            full
        } else {
            full.strip_prefix(&format!("{base}/"))
                .map(|s| s.to_string())
                .unwrap_or(full)
        };
        if let Some(content) = file.contents_utf8() {
            out.push((rel, content.to_string()));
        }
    }
    for sub in dir.dirs() {
        collect_embedded(sub, base, out);
    }
}

fn collect_fs(base: &Path, dir: &Path, out: &mut Vec<(String, String)>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.filter_map(|e| e.ok()) {
        let path = entry.path();
        if path.is_dir() {
            collect_fs(base, &path, out);
        } else if path.is_file() {
            if let Ok(content) = std::fs::read_to_string(&path) {
                let rel = path
                    .strip_prefix(base)
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_default();
                out.push((rel, content));
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedded_lists_areas_without_template() {
        let kb = Kb::Embedded;
        let areas = kb.list_areas();
        assert!(areas.contains(&"software".to_string()));
        assert!(areas.contains(&"devops".to_string()));
        assert!(!areas.contains(&"template".to_string()));
    }

    #[test]
    fn embedded_lists_specs_sorted() {
        let kb = Kb::Embedded;
        let specs = kb.list_specs("software");
        assert!(specs.contains(&"backend".to_string()));
        let mut sorted = specs.clone();
        sorted.sort();
        assert_eq!(specs, sorted);
    }

    #[test]
    fn agentos_choices_include_static_and_dynamic() {
        let kb = Kb::Embedded;
        let choices = kb.agentos_choices();
        assert!(choices.contains(&"opencode".to_string()));
        assert!(choices.contains(&"codex".to_string()));
        assert!(choices.contains(&"gemini".to_string()));
        // static order preserved first
        assert_eq!(choices[0], "opencode");
    }

    #[test]
    fn embedded_reads_root_files() {
        let kb = Kb::Embedded;
        assert!(kb.read_file("AGENTS.md").is_some());
        assert!(kb.read_file("MEMORY.md").is_some());
        assert!(kb.read_file("CHANGELOG.md").is_some());
        assert!(kb.read_file("nope.md").is_none());
    }

    #[test]
    fn walk_files_returns_relative_paths() {
        let kb = Kb::Embedded;
        let files = kb.walk_files("extensions/opencode");
        assert!(!files.is_empty());
        assert!(files.iter().all(|(rel, _)| !rel.starts_with("extensions")));
        assert!(files.iter().any(|(rel, _)| rel == "opencode.json"));
    }

    #[test]
    fn dir_exists_checks() {
        let kb = Kb::Embedded;
        assert!(kb.dir_exists("areas/software/backend"));
        assert!(!kb.dir_exists("areas/software/nonexistent"));
    }
}
