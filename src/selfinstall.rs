//! self-install: copy the running binary into a bin directory and ensure PATH.

use crate::app::App;
use crate::ui;
use std::path::Path;

pub fn path_ref_for_shell_export(home: &Path, dir: &Path) -> String {
    // Match prefixes using platform-aware path semantics, then normalize the
    // relative portion for shell syntax (which conventionally uses `/`).
    if let Ok(rest) = dir.strip_prefix(home) {
        let rest = rest.to_string_lossy().replace('\\', "/");
        if rest.is_empty() {
            return "$HOME".to_string();
        }
        return format!("$HOME/{rest}");
    }

    // Fall back to normalized textual matching for synthetic or mixed-separator
    // paths (for example, values supplied by tests or environment variables).
    let home_str = home.to_string_lossy().replace('\\', "/");
    let dir_str = dir.to_string_lossy().replace('\\', "/");
    let home_str = home_str.trim_end_matches('/');
    if dir_str == home_str {
        return "$HOME".to_string();
    }
    if let Some(rest) = dir_str.strip_prefix(&format!("{home_str}/")) {
        return format!("$HOME/{rest}");
    }

    // Keep absolute paths usable in shell exports even on Windows.
    dir_str
}

pub fn self_install_profile_file(home: &Path) -> std::path::PathBuf {
    let shell = std::env::var("SHELL").unwrap_or_default();
    let shell_name = Path::new(&shell)
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();
    match shell_name.as_str() {
        "zsh" => home.join(".zshrc"),
        "bash" => home.join(".bashrc"),
        _ => home.join(".profile"),
    }
}

fn profile_has_path_export(profile_file: &Path, dir: &Path, path_ref: &str) -> bool {
    let Ok(content) = std::fs::read_to_string(profile_file) else {
        return false;
    };
    content.contains(&dir.to_string_lossy().to_string()) || content.contains(path_ref)
}

pub fn ensure_bin_dir_in_shell_path(app: &mut App, bin_dir: &Path) {
    let profile_file = self_install_profile_file(&app.home);
    let path_ref = path_ref_for_shell_export(&app.home, bin_dir);
    let export_line = format!("export PATH=\"{path_ref}:$PATH\"");

    if profile_has_path_export(&profile_file, bin_dir, &path_ref) {
        ui::log(
            app,
            &format!("PATH hint already present in {}", profile_file.display()),
        );
        return;
    }
    if app.dry_run {
        ui::log(
            app,
            &format!("DRY-RUN append PATH export to {}", profile_file.display()),
        );
        ui::log(app, &format!("DRY-RUN line: {export_line}"));
        return;
    }
    if !profile_file.exists() {
        let _ = std::fs::write(&profile_file, "");
        app.record_copied(&profile_file.to_string_lossy());
    }
    let date = chrono::Local::now().format("%Y-%m-%d");
    let block = format!(
        "\n# Added by {} self-install on {date}\n{export_line}\n",
        crate::APP_NAME
    );
    if let Ok(mut file) = std::fs::OpenOptions::new().append(true).open(&profile_file) {
        use std::io::Write;
        let _ = file.write_all(block.as_bytes());
    }
    ui::log(
        app,
        &format!("Added PATH export to {}", profile_file.display()),
    );
}

/// Used by the mempalace venv fallback to persist ~/.local/bin in PATH.
pub fn append_path_export_to_shell_rc(app: &App, local_bin: &Path) {
    let shell = std::env::var("SHELL").unwrap_or_default();
    let shell_name = Path::new(&shell)
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();
    let rc = if shell_name == "zsh" {
        app.home.join(".zshrc")
    } else {
        app.home.join(".bashrc")
    };
    let line = "export PATH=\"$HOME/.local/bin:$PATH\"";
    let already = std::fs::read_to_string(&rc)
        .map(|c| c.lines().any(|l| l == line))
        .unwrap_or(false);
    if !already {
        if let Ok(mut file) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&rc)
        {
            use std::io::Write;
            let _ = writeln!(file, "{line}");
        }
    }
    let _ = local_bin;
}

pub fn self_install(app: &mut App) -> crate::Result<()> {
    let source_path = std::env::current_exe().map_err(|e| -> crate::AnyError {
        format!("Cannot resolve installer source: {e}").into()
    })?;
    if !source_path.is_file() {
        ui::error(
            app,
            &format!(
                "Cannot read installer source at '{}'.",
                source_path.display()
            ),
        );
        return Err(crate::exit1());
    }

    let mut bin_dir = app.self_install_bin_dir.clone();
    if bin_dir == "~/.local/bin" {
        bin_dir = app.home.join(".local/bin").to_string_lossy().to_string();
    }
    let bin_dir = std::path::PathBuf::from(bin_dir);
    let target = bin_dir.join(crate::APP_NAME);

    app.ensure_dir(&bin_dir);

    if target.exists() {
        let source_real =
            std::fs::canonicalize(&source_path).unwrap_or_else(|_| source_path.clone());
        let target_real = std::fs::canonicalize(&target).unwrap_or_else(|_| target.clone());
        if source_real == target_real {
            ui::log(
                app,
                &format!(
                    "Source and target are already the same file: {}",
                    target.display()
                ),
            );
            ui::log(app, "Nothing to copy. The binary is self-contained; run 'agentic upgrade' to fetch a newer release.");
            print_self_install_report(app, &source_path, &target, &bin_dir);
            return Ok(());
        }
        if !app.self_install_force {
            ui::error(app, &format!("Target already exists: {}", target.display()));
            ui::error(app, "Use --force to overwrite");
            return Err(crate::exit1());
        }
    }

    if app.dry_run {
        ui::log(
            app,
            &format!("DRY-RUN install binary to {}", target.display()),
        );
    } else {
        std::fs::copy(&source_path, &target).map_err(|e| -> crate::AnyError {
            format!("Failed to install to {}: {e}", target.display()).into()
        })?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(&target, std::fs::Permissions::from_mode(0o755));
        }
        app.record_copied(&target.to_string_lossy());
        ui::log(app, &format!("Installed: {}", target.display()));
    }

    if app.self_install_with_fzf {
        ui::warn(
            app,
            "--install-fzf is deprecated: the Rust TUI no longer requires fzf (no-op)",
        );
    }

    let path_env = std::env::var("PATH").unwrap_or_default();
    let in_path = std::env::split_paths(&path_env).any(|p| p == bin_dir);
    if in_path {
        ui::log(app, &format!("PATH already includes {}", bin_dir.display()));
    } else {
        ui::warn(app, &format!("PATH does not include {}", bin_dir.display()));
        ensure_bin_dir_in_shell_path(app, &bin_dir);
        let path_ref = path_ref_for_shell_export(&app.home, &bin_dir);
        ui::warn(
            app,
            &format!("Open a new terminal or run: export PATH=\"{path_ref}:$PATH\""),
        );
    }

    print_self_install_report(app, &source_path, &target, &bin_dir);
    Ok(())
}

fn print_self_install_report(app: &App, source: &Path, target: &Path, _bin_dir: &Path) {
    println!();
    println!(
        "{}=== Self-install report ==={}",
        app.colors.header, app.colors.reset
    );
    println!("Source: {}", source.display());
    println!("Target binary: {}", target.display());
    println!("Config directory: {}", app.app_config_dir().display());
    println!("Knowledge base: {}", app.kb.root_label());
    println!("Install fzf requested: {}", app.self_install_with_fzf);
    println!("Dry-run: {}", app.dry_run);
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    /// Serializes tests that mutate the process-wide SHELL env var.
    static SHELL_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn path_ref_uses_home_variable() {
        let home = Path::new("/home/user");
        assert_eq!(
            path_ref_for_shell_export(home, Path::new("/home/user/.local/bin")),
            "$HOME/.local/bin"
        );
        assert_eq!(
            path_ref_for_shell_export(home, Path::new("/opt/bin")),
            "/opt/bin"
        );
        assert_eq!(
            path_ref_for_shell_export(
                Path::new(r"C:\Users\runner"),
                Path::new(r"C:\Users\runner\.local\bin"),
            ),
            "$HOME/.local/bin"
        );
    }

    #[test]
    fn profile_file_by_shell() {
        let _guard = SHELL_LOCK.lock().unwrap();
        let home = Path::new("/h");
        std::env::set_var("SHELL", "/bin/zsh");
        assert_eq!(self_install_profile_file(home), home.join(".zshrc"));
        std::env::set_var("SHELL", "/bin/bash");
        assert_eq!(self_install_profile_file(home), home.join(".bashrc"));
        std::env::set_var("SHELL", "/bin/fish");
        assert_eq!(self_install_profile_file(home), home.join(".profile"));
    }

    #[test]
    fn ensure_path_export_appends_once() {
        let _guard = SHELL_LOCK.lock().unwrap();
        let tmp = tempfile::tempdir().unwrap();
        std::env::set_var("SHELL", "/bin/bash");
        let mut app = App::new().unwrap();
        app.home = tmp.path().to_path_buf();
        let bin_dir = tmp.path().join(".local/bin");
        ensure_bin_dir_in_shell_path(&mut app, &bin_dir);
        let rc = tmp.path().join(".bashrc");
        let content = std::fs::read_to_string(&rc).unwrap();
        assert!(content.contains("export PATH=\"$HOME/.local/bin:$PATH\""));
        // second call must be a no-op
        ensure_bin_dir_in_shell_path(&mut app, &bin_dir);
        let content2 = std::fs::read_to_string(&rc).unwrap();
        assert_eq!(content, content2);
    }
}
