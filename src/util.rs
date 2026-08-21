//! Small shared utilities: string helpers, hashing, path normalization.

use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

pub fn split_csv(raw: &str) -> Vec<String> {
    raw.split(',')
        .map(|p| p.trim().to_string())
        .filter(|p| !p.is_empty())
        .collect()
}

pub fn unique_append(list: &mut Vec<String>, value: &str) {
    if !list.iter().any(|item| item == value) {
        list.push(value.to_string());
    }
}

pub fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

pub fn hash_file(path: &Path) -> std::io::Result<String> {
    let bytes = std::fs::read(path)?;
    Ok(sha256_hex(&bytes))
}

/// Mirror of bash `normalize_project_dir_path`: resolve to a physical path when
/// the directory (or its parent) exists; otherwise return the raw value.
pub fn normalize_project_dir_path(raw: &str) -> String {
    if raw.is_empty() {
        return raw.to_string();
    }
    let path = Path::new(raw);
    if path.is_dir() {
        if let Ok(real) = std::fs::canonicalize(path) {
            return real.to_string_lossy().to_string();
        }
        return raw.to_string();
    }
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    let base = path
        .file_name()
        .map(|b| b.to_string_lossy().to_string())
        .unwrap_or_default();
    if parent.as_os_str().is_empty() {
        return raw.to_string();
    }
    if parent.is_dir() {
        if let Ok(parent_real) = std::fs::canonicalize(parent) {
            return parent_real.join(base).to_string_lossy().to_string();
        }
    }
    raw.to_string()
}

pub fn home_dir() -> PathBuf {
    if let Ok(home) = std::env::var("HOME") {
        if !home.is_empty() {
            return PathBuf::from(home);
        }
    }
    if let Ok(profile) = std::env::var("USERPROFILE") {
        if !profile.is_empty() {
            return PathBuf::from(profile);
        }
    }
    PathBuf::from("/")
}

pub fn tmp_dir() -> PathBuf {
    std::env::var("TMPDIR")
        .ok()
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(std::env::temp_dir)
}

/// Sanitize a MemPalace wing name: lowercase, non-alnum -> `_`, collapse and
/// trim underscores; empty -> `project`.
pub fn mempalace_sanitize_wing_name(raw: &str) -> String {
    let lowered = raw.to_lowercase();
    let mut out = String::new();
    let mut last_underscore = false;
    for ch in lowered.chars() {
        if ch.is_ascii_alphanumeric() {
            out.push(ch);
            last_underscore = false;
        } else if !last_underscore {
            out.push('_');
            last_underscore = true;
        }
    }
    let trimmed = out.trim_matches('_').to_string();
    if trimmed.is_empty() {
        "project".to_string()
    } else {
        trimmed
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn split_csv_trims_and_filters() {
        assert_eq!(split_csv(" a, b ,,c "), vec!["a", "b", "c"]);
        assert!(split_csv("").is_empty());
        assert!(split_csv(" , ,").is_empty());
    }

    #[test]
    fn unique_append_dedupes() {
        let mut v = vec!["a".to_string()];
        unique_append(&mut v, "a");
        unique_append(&mut v, "b");
        assert_eq!(v, vec!["a", "b"]);
    }

    #[test]
    fn sha256_matches_known_vector() {
        assert_eq!(
            sha256_hex(b"hello"),
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        );
    }

    #[test]
    fn wing_name_sanitization() {
        assert_eq!(
            mempalace_sanitize_wing_name("My-Project 2!"),
            "my_project_2"
        );
        assert_eq!(mempalace_sanitize_wing_name("___"), "project");
        assert_eq!(mempalace_sanitize_wing_name(""), "project");
        assert_eq!(mempalace_sanitize_wing_name("a__b"), "a_b");
    }

    #[test]
    fn normalize_missing_dir_uses_parent() {
        let tmp = tempfile::tempdir().unwrap();
        let raw = tmp.path().join("newdir");
        let normalized = normalize_project_dir_path(raw.to_str().unwrap());
        assert!(normalized.ends_with("newdir"));
        let normalized_existing = normalize_project_dir_path(tmp.path().to_str().unwrap());
        assert!(!normalized_existing.is_empty());
    }
}
