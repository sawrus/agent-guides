//! Back up and apply a validated project delta, restoring on filesystem failures.
use crate::{app::App, project_inventory::safe_path, ui};
use serde_json::json;
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

type Files = BTreeMap<String, Vec<u8>>;
/// Execute bits (`0o111` mask) by path; a missing path has none.
pub type ExecBits = BTreeMap<String, u32>;

/// The execute bits of `rels` below `root` (empty outside Unix).
pub fn exec_bits<'a>(root: &Path, rels: impl IntoIterator<Item = &'a String>) -> ExecBits {
    rels.into_iter()
        .filter_map(|rel| {
            let bits = crate::util::exec_bits(&safe_path(root, rel).ok()?);
            (bits != 0).then(|| (rel.clone(), bits))
        })
        .collect()
}

fn private_dir(path: &Path) -> crate::Result<()> {
    std::fs::create_dir_all(path)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o700))?;
    }
    #[cfg(windows)]
    {
        let identity = std::process::Command::new("whoami").output()?;
        if !identity.status.success() {
            return Err("Cannot determine backup owner".into());
        }
        let owner = String::from_utf8(identity.stdout)?.trim().to_owned();
        let status = std::process::Command::new("icacls")
            .arg(path)
            .args(["/inheritance:r", "/grant:r", &format!("{owner}:(OI)(CI)F")])
            .stdout(std::process::Stdio::null())
            .status()?;
        if !status.success() {
            return Err("Cannot restrict backup access".into());
        }
    }
    Ok(())
}

/// Write `bytes` atomically. An existing file keeps its permissions; a new file gets the umask mode
/// of a normal file (`0o666 & !umask`). `exec` (when given) sets the execute bits exactly: they come
/// from the staging copy, where the install already applied the umask.
fn write_file(path: &Path, bytes: &[u8], exec: Option<u32>) -> crate::Result<()> {
    std::fs::create_dir_all(path.parent().ok_or("Missing parent directory")?)?;
    // Atomic replacement avoids exposing partially written configurations.
    let mut tmp = tempfile::NamedTempFile::new_in(path.parent().unwrap())?;
    use std::io::Write;
    tmp.write_all(bytes)?;
    tmp.as_file().sync_all()?;
    let existing = std::fs::metadata(path).ok().map(|m| m.permissions());
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let allowed = crate::util::umask_allowed();
        let base = existing
            .as_ref()
            .map_or(0o666 & allowed, |p| p.mode() & 0o7777);
        let mode = match exec {
            Some(bits) => (base & 0o666) | (bits & 0o111),
            None => base,
        };
        tmp.as_file()
            .set_permissions(std::fs::Permissions::from_mode(mode))?;
    }
    #[cfg(not(unix))]
    {
        let _ = exec;
        if let Some(permissions) = existing {
            tmp.as_file().set_permissions(permissions)?;
        }
    }
    tmp.persist(path).map_err(|e| e.error)?;
    Ok(())
}

fn restore(
    root: &Path,
    changed: &[String],
    before: &Files,
    dirs: &[PathBuf],
    permissions: &BTreeMap<String, std::fs::Permissions>,
) -> crate::Result<()> {
    for rel in changed.iter().rev() {
        let path = safe_path(root, rel)?;
        if let Some(bytes) = before.get(rel) {
            write_file(&path, bytes, None)?;
            if let Some(mode) = permissions.get(rel) {
                std::fs::set_permissions(&path, mode.clone())?;
            }
        } else if path.is_file() {
            std::fs::remove_file(path)?;
        }
    }
    for dir in dirs.iter().rev() {
        if dir.is_dir() && std::fs::read_dir(dir)?.next().is_none() {
            std::fs::remove_dir(dir)?;
        }
    }
    Ok(())
}

/// Apply `after` to `root`. `exec` holds the execute bits of the `after` files: a file whose bits
/// differ from the project file is written too, so scripts stay executable.
pub fn apply(
    app: &App,
    root: &Path,
    before: &Files,
    after: &Files,
    exec: &ExecBits,
) -> crate::Result<()> {
    apply_with(app, root, before, after, exec, |_, _| Ok(()))
}

fn apply_with<F: Fn(usize, &Path) -> crate::Result<()>>(
    app: &App,
    root: &Path,
    before: &Files,
    after: &Files,
    exec: &ExecBits,
    check: F,
) -> crate::Result<()> {
    let all: BTreeSet<_> = before.keys().chain(after.keys()).cloned().collect();
    let current = exec_bits(root, before.keys());
    let changed: Vec<_> = all
        .into_iter()
        .filter(|p| {
            before.get(p) != after.get(p)
                || (after.contains_key(p) && current.get(p) != exec.get(p))
        })
        .collect();
    for rel in &changed {
        let path = safe_path(root, rel)?;
        if path.exists() && !path.is_file() {
            return Err(format!("Expected a file: {rel}").into());
        }
        // Refuse to overwrite edits made while the staging plan was being prepared.
        if std::fs::read(&path).ok().as_ref() != before.get(rel) {
            return Err(format!("Project changed while preparing upgrade: {rel}").into());
        }
        let action = if !after.contains_key(rel) {
            "Remove"
        } else if before.contains_key(rel) {
            "Update"
        } else {
            "Create"
        };
        ui::log(
            app,
            &format!(
                "{}{action}: {rel}",
                if app.dry_run { "DRY-RUN " } else { "" }
            ),
        );
    }
    if app.dry_run || changed.is_empty() {
        ui::log(
            app,
            if changed.is_empty() {
                "Project instructions already up to date"
            } else {
                "DRY-RUN backup and apply planned changes"
            },
        );
        return Ok(());
    }
    let stamp = chrono::Utc::now().format("%Y%m%d-%H%M%S-%f");
    let backup_rel = format!(".agentic-backups/{stamp}-{}", std::process::id());
    let backup = safe_path(root, &backup_rel)?;
    private_dir(&root.join(".agentic-backups"))?;
    private_dir(&backup)?;
    let mut dirs = BTreeSet::new();
    let mut permissions = BTreeMap::new();
    for rel in &changed {
        let target = safe_path(root, rel)?;
        let mut parent = target.parent();
        while let Some(dir) = parent.filter(|p| p.starts_with(root)) {
            if !dir.exists() {
                dirs.insert(dir.to_path_buf());
            }
            parent = dir.parent();
        }
        if let Some(bytes) = before.get(rel) {
            permissions.insert(rel.clone(), std::fs::metadata(&target)?.permissions());
            let path = backup.join("files").join(rel);
            private_dir(path.parent().unwrap())?;
            std::fs::write(&path, bytes)?;
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600))?;
            }
        }
    }
    let journal = backup.join("journal.json");
    let records: Vec<_> = changed
        .iter()
        .map(|rel| {
            let mut record = json!({"path": rel, "existed": before.contains_key(rel)});
            if let Some(mode) = permissions.get(rel) {
                record["readonly"] = json!(mode.readonly());
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    record["mode"] = json!(mode.mode());
                }
            }
            record
        })
        .collect();
    std::fs::write(
        &journal,
        crate::markers::to_pretty_json(&json!({"status": "prepared", "files": records})),
    )?;
    let dirs: Vec<_> = dirs.into_iter().collect();
    let result: crate::Result<()> = (|| {
        for (index, rel) in changed.iter().enumerate() {
            let path = safe_path(root, rel)?;
            check(index, &path)?;
            if let Some(bytes) = after.get(rel) {
                write_file(&path, bytes, Some(exec.get(rel).copied().unwrap_or(0)))?;
            } else {
                std::fs::remove_file(&path)?;
            }
        }
        std::fs::write(
            &journal,
            crate::markers::to_pretty_json(&json!({"status": "committed", "files": records})),
        )?;
        Ok(())
    })();
    match result {
        Ok(()) => {
            ui::log(app, &format!("Backup: {}", backup.display()));
            Ok(())
        }
        Err(error) => {
            restore(root, &changed, before, &dirs, &permissions).map_err(
                |restore_error| -> crate::AnyError {
                    format!(
                        "Upgrade failed: {error}; restoration failed: {restore_error}; backup: {}",
                        backup.display()
                    )
                    .into()
                },
            )?;
            std::fs::write(
                journal,
                crate::markers::to_pretty_json(&json!({"status": "rolled_back", "files": records})),
            )?;
            Err(format!(
                "Upgrade failed and project restored: {error}; backup: {}",
                backup.display()
            )
            .into())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn restores_old_and_removes_new_files_after_partial_failure() {
        let root = tempfile::tempdir().unwrap();
        std::fs::write(root.path().join("old.md"), "old").unwrap();
        std::fs::write(root.path().join("updated.md"), "original").unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(
                root.path().join("old.md"),
                std::fs::Permissions::from_mode(0o750),
            )
            .unwrap();
        }
        let before = BTreeMap::from([
            ("old.md".into(), b"old".to_vec()),
            ("updated.md".into(), b"original".to_vec()),
        ]);
        let after = BTreeMap::from([
            ("updated.md".into(), b"changed".to_vec()),
            ("z-trigger.md".into(), b"unwritten".to_vec()),
            ("nested/new.md".into(), b"created".to_vec()),
        ]);
        let app = App::new().unwrap();
        let result = apply_with(
            &app,
            root.path(),
            &before,
            &after,
            &ExecBits::new(),
            |index, _| {
                if index == 3 {
                    Err("injected failure".into())
                } else {
                    Ok(())
                }
            },
        );
        assert!(result.unwrap_err().to_string().contains("project restored"));
        assert_eq!(
            std::fs::read_to_string(root.path().join("old.md")).unwrap(),
            "old"
        );
        assert!(!root.path().join("nested").exists());
        assert!(!root.path().join("z-trigger.md").exists());
        assert_eq!(
            std::fs::read_to_string(root.path().join("updated.md")).unwrap(),
            "original"
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                std::fs::metadata(root.path().join("old.md"))
                    .unwrap()
                    .permissions()
                    .mode()
                    & 0o777,
                0o750
            );
        }
    }

    #[cfg(unix)]
    #[test]
    fn new_files_get_the_umask_mode_and_the_given_execute_bits() {
        use std::os::unix::fs::PermissionsExt;
        let mode = |p: &Path| std::fs::metadata(p).unwrap().permissions().mode() & 0o7777;
        let allowed = crate::util::umask_allowed();
        let root = tempfile::tempdir().unwrap();
        let old = root.path().join("old.sh");
        std::fs::write(&old, "x").unwrap();
        std::fs::set_permissions(&old, std::fs::Permissions::from_mode(0o640)).unwrap();
        let before = BTreeMap::from([("old.sh".to_string(), b"x".to_vec())]);
        let after = BTreeMap::from([
            ("old.sh".to_string(), b"x".to_vec()),
            ("new.md".to_string(), b"doc".to_vec()),
            ("bin/run".to_string(), b"#!/bin/sh\n".to_vec()),
        ]);
        let exec = ExecBits::from([
            ("old.sh".to_string(), 0o100),
            ("bin/run".to_string(), 0o111),
        ]);
        let app = App::new().unwrap();
        apply(&app, root.path(), &before, &after, &exec).unwrap();
        assert_eq!(mode(&root.path().join("new.md")), 0o666 & allowed);
        assert_eq!(
            mode(&root.path().join("bin/run")),
            (0o666 & allowed) | 0o111
        );
        // Same bytes, new bits: the mode changes and the rest of the mode stays.
        assert_eq!(mode(&old), 0o740);
    }
}
