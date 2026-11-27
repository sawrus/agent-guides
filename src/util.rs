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

/// Run a command with a timeout, capturing stdout and stderr.
///
/// Returns `(timed_out, exit_code, output)`. A timed-out process is killed and
/// reports exit code 124.
pub fn run_with_timeout(
    cmd: &mut std::process::Command,
    timeout: std::time::Duration,
) -> std::io::Result<(bool, i32, String)> {
    use std::process::Stdio;
    use std::time::{Duration, Instant};
    cmd.stdout(Stdio::piped()).stderr(Stdio::piped());
    let mut child = cmd.spawn()?;
    let start = Instant::now();
    loop {
        match child.try_wait()? {
            Some(status) => {
                let mut output = String::new();
                if let Some(mut stdout) = child.stdout.take() {
                    use std::io::Read;
                    let _ = stdout.read_to_string(&mut output);
                }
                if let Some(mut stderr) = child.stderr.take() {
                    use std::io::Read;
                    let _ = stderr.read_to_string(&mut output);
                }
                return Ok((false, status.code().unwrap_or(-1), output));
            }
            None => {
                if start.elapsed() >= timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Ok((true, 124, String::new()));
                }
                std::thread::sleep(Duration::from_millis(100));
            }
        }
    }
}

/// The permission bits that the process umask allows (`0o777 & !umask`), probed once with a file in
/// the temp directory; `0o755` when the probe fails. Always `0o777` outside Unix.
pub fn umask_allowed() -> u32 {
    static ALLOWED: std::sync::OnceLock<u32> = std::sync::OnceLock::new();
    *ALLOWED.get_or_init(|| {
        #[cfg(unix)]
        {
            use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
            let probe = std::env::temp_dir().join(format!(
                ".agentic-umask-{}-{:?}",
                std::process::id(),
                std::thread::current().id()
            ));
            let _ = std::fs::remove_file(&probe);
            let mode = std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o777)
                .open(&probe)
                .and_then(|f| f.metadata())
                .map(|m| m.permissions().mode() & 0o777);
            let _ = std::fs::remove_file(&probe);
            mode.unwrap_or(0o755)
        }
        #[cfg(not(unix))]
        {
            0o777
        }
    })
}

/// The execute bits (`0o111` mask) of a file; 0 for a missing file and outside Unix.
pub fn exec_bits(path: &Path) -> u32 {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::metadata(path).map_or(0, |m| m.permissions().mode() & 0o111)
    }
    #[cfg(not(unix))]
    {
        let _ = path;
        0
    }
}

/// Set the execute bits of an existing file to exactly `bits & 0o111`, limited by the umask. Read and
/// write bits stay; setuid, setgid, and sticky bits are cleared.
pub fn set_exec_bits(path: &Path, bits: u32) -> std::io::Result<()> {
    copy_exec_bits(path, bits & umask_allowed())
}

/// Set the execute bits of an existing file to exactly `bits & 0o111` (no umask limit): a copy of
/// the bits of another file.
pub fn copy_exec_bits(path: &Path, bits: u32) -> std::io::Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mode = std::fs::metadata(path)?.permissions().mode() & 0o7777;
        let wanted = (mode & 0o666) | (bits & 0o111);
        if wanted != mode {
            std::fs::set_permissions(path, std::fs::Permissions::from_mode(wanted))?;
        }
    }
    #[cfg(not(unix))]
    let _ = (path, bits);
    Ok(())
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
    fn run_with_timeout_kills_slow_process() {
        use std::process::Command;
        use std::time::Duration;
        let mut cmd = Command::new("sleep");
        cmd.arg("5");
        let (timed_out, code, _) = run_with_timeout(&mut cmd, Duration::from_millis(200)).unwrap();
        assert!(timed_out);
        assert_eq!(code, 124);
        let mut ok_cmd = Command::new("true");
        let (timed_out, code, _) = run_with_timeout(&mut ok_cmd, Duration::from_secs(5)).unwrap();
        assert!(!timed_out);
        assert_eq!(code, 0);
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
