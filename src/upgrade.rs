//! Self-upgrade from GitHub Releases and post-upgrade project re-sync.

use crate::app::App;
use crate::ui;
use serde_json::Value;

pub const RELEASES_LATEST_API: &str =
    "https://api.github.com/repos/sawrus/agent-guides/releases/latest";

pub fn release_asset_name() -> String {
    let os = match std::env::consts::OS {
        "macos" => "apple-darwin",
        "windows" => "pc-windows-msvc",
        _ => "unknown-linux-musl",
    };
    let arch = match std::env::consts::ARCH {
        "aarch64" => "aarch64",
        _ => "x86_64",
    };
    let ext = if std::env::consts::OS == "windows" {
        "zip"
    } else {
        "tar.gz"
    };
    format!("agentic-{arch}-{os}.{ext}")
}

/// Compare "1.2.3"-style versions; returns true when `remote` is newer.
pub fn is_newer_version(current: &str, remote: &str) -> bool {
    let parse = |v: &str| -> Vec<u64> {
        v.trim_start_matches('v')
            .split('.')
            .map(|p| {
                p.chars()
                    .take_while(|c| c.is_ascii_digit())
                    .collect::<String>()
            })
            .map(|p| p.parse::<u64>().unwrap_or(0))
            .collect()
    };
    let cur = parse(current);
    let rem = parse(remote);
    for i in 0..cur.len().max(rem.len()) {
        let c = cur.get(i).copied().unwrap_or(0);
        let r = rem.get(i).copied().unwrap_or(0);
        if r != c {
            return r > c;
        }
    }
    false
}

fn extract_binary_from_tar_gz(bytes: &[u8]) -> crate::Result<Vec<u8>> {
    let tmp = tempfile::tempdir()?;
    let archive = tmp.path().join("asset.tar.gz");
    std::fs::write(&archive, bytes)?;
    let listing = std::process::Command::new("tar")
        .arg("-tzf")
        .arg(&archive)
        .output()?;
    let names = String::from_utf8(listing.stdout)?;
    let names: Vec<_> = names.lines().collect();
    if !listing.status.success() || names.len() != 1 || !matches!(names[0], "agentic" | "./agentic")
    {
        return Err("release archive must contain exactly the agentic executable".into());
    }
    // Stream the member: archive paths and links cannot write outside a temp directory.
    let output = std::process::Command::new("tar")
        .arg("-xOzf")
        .arg(&archive)
        .arg(names[0])
        .output()?;
    if !output.status.success() || output.stdout.is_empty() {
        return Err("failed to extract release executable".into());
    }
    Ok(output.stdout)
}

fn extract_binary_from_zip(bytes: &[u8]) -> crate::Result<Vec<u8>> {
    use std::io::Read;
    let mut archive = zip::ZipArchive::new(std::io::Cursor::new(bytes))?;
    if archive.len() != 1 {
        return Err("release ZIP must contain exactly agentic.exe".into());
    }
    let mut entry = archive.by_index(0)?;
    if entry.name() != "agentic.exe" || entry.is_dir() || entry.size() > 256 * 1024 * 1024 {
        return Err("invalid release ZIP executable".into());
    }
    let mut binary = Vec::new();
    entry.read_to_end(&mut binary)?;
    Ok(binary)
}

fn validate_binary(binary: &[u8]) -> crate::Result<()> {
    let valid = binary.len() >= 64
        && match std::env::consts::OS {
            "windows" => binary.starts_with(b"MZ"),
            "macos" => binary.get(..4).is_some_and(|magic| {
                matches!(
                    magic,
                    [0xcf, 0xfa, 0xed, 0xfe]
                        | [0xfe, 0xed, 0xfa, 0xcf]
                        | [0xca, 0xfe, 0xba, 0xbe]
                        | [0xca, 0xfe, 0xba, 0xbf]
                )
            }),
            _ => binary.starts_with(b"\x7fELF"),
        };
    if !valid {
        return Err("release asset is not a platform executable".into());
    }
    Ok(())
}

pub fn upgrade_binary(app: &mut App) -> crate::Result<Option<std::path::PathBuf>> {
    ui::log(
        app,
        &format!("Current version: {}", crate::app_version_label()),
    );
    ui::log(app, "Checking latest release on GitHub...");

    if app.dry_run {
        ui::log(app, &format!("DRY-RUN query {RELEASES_LATEST_API}"));
        ui::log(
            app,
            &format!("DRY-RUN download asset {}", release_asset_name()),
        );
        return Ok(None);
    }

    let client = reqwest::blocking::Client::builder()
        .user_agent(format!("agentic/{}", crate::app_version()))
        .build()?;
    let release: Value = client
        .get(RELEASES_LATEST_API)
        .send()
        .and_then(|r| r.error_for_status())
        .map_err(|e| -> crate::AnyError { format!("Failed to query GitHub releases: {e}").into() })?
        .json()?;

    let tag = release
        .get("tag_name")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    if tag.is_empty() {
        ui::warn(app, "No release tag found; skipping binary upgrade");
        return Ok(None);
    }
    if !is_newer_version(&crate::app_version(), &tag) {
        ui::log(app, &format!("Already up to date ({tag})"));
        return Ok(None);
    }

    let asset_name = release_asset_name();
    let asset_url = release
        .get("assets")
        .and_then(|v| v.as_array())
        .and_then(|assets| {
            assets
                .iter()
                .find(|a| a.get("name").and_then(|n| n.as_str()) == Some(asset_name.as_str()))
        })
        .and_then(|a| a.get("browser_download_url"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let Some(asset_url) = asset_url else {
        ui::warn(
            app,
            &format!("Release {tag} has no asset '{asset_name}'; skipping binary upgrade"),
        );
        return Ok(None);
    };

    ui::log(app, &format!("Downloading {asset_url}"));
    let bytes = client
        .get(&asset_url)
        .send()
        .and_then(|r| r.error_for_status())
        .map_err(|e| -> crate::AnyError {
            format!("Failed to download release asset: {e}").into()
        })?
        .bytes()?;

    let binary = if asset_name.ends_with(".tar.gz") {
        extract_binary_from_tar_gz(&bytes)?
    } else {
        extract_binary_from_zip(&bytes)?
    };

    validate_binary(&binary)?;
    let tmp = tempfile::Builder::new()
        .suffix(if cfg!(windows) { ".exe" } else { "" })
        .tempfile_in(crate::util::tmp_dir())?;
    std::fs::write(tmp.path(), &binary)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(tmp.path(), std::fs::Permissions::from_mode(0o755))?;
    }
    let tmp = tmp.into_temp_path();
    let executable: &std::path::Path = tmp.as_ref();
    let version = std::process::Command::new(executable)
        .arg("--version")
        .output()
        .map_err(|e| -> crate::AnyError {
            format!("Downloaded executable cannot run: {e}").into()
        })?;
    if !version.status.success()
        || String::from_utf8_lossy(&version.stdout)
            .trim()
            .trim_start_matches('v')
            != tag.trim_start_matches('v')
    {
        return Err("Downloaded executable version does not match release tag".into());
    }
    let installed = std::env::current_exe()?;
    self_replace::self_replace(executable)
        .map_err(|e| -> crate::AnyError { format!("Failed to replace binary: {e}").into() })?;
    ui::log(app, &format!("Updated installed binary to {tag}"));
    Ok(Some(installed))
}

pub fn sync_current_project_after_upgrade(app: &mut App) -> crate::Result<()> {
    crate::project_update::synchronize(app)
}

#[derive(Debug)]
pub struct ChildExit(pub i32);
impl std::fmt::Display for ChildExit {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "project synchronization exited with {}", self.0)
    }
}
impl std::error::Error for ChildExit {}

fn run_sync_binary(app: &App, executable: &std::path::Path) -> crate::Result<()> {
    let mut command = std::process::Command::new(executable);
    command.arg("__sync-project");
    if !app.project_dir.is_empty() {
        command.args(["--project-dir", &app.project_dir]);
    }
    if app.upgrade_force {
        command.arg("--force");
    }
    if app.dry_run {
        command.arg("--dry-run");
    }
    // Avoid accidentally selecting an adjacent old development checkout after replacement.
    command.env("AGENTIC_UPGRADED_PROCESS", "1");
    let status = command.status()?;
    if !status.success() {
        return Err(Box::new(ChildExit(status.code().unwrap_or(1))));
    }
    Ok(())
}

pub fn sync_with_new_binary(app: &App, executable: &std::path::Path) -> crate::Result<()> {
    run_sync_binary(app, executable)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn zip_extraction_and_executable_validation() {
        use std::io::Write;
        let mut writer = zip::ZipWriter::new(std::io::Cursor::new(Vec::new()));
        writer
            .start_file("agentic.exe", zip::write::SimpleFileOptions::default())
            .unwrap();
        writer.write_all(b"MZfake-executable").unwrap();
        let bytes = writer.finish().unwrap().into_inner();
        assert_eq!(
            extract_binary_from_zip(&bytes).unwrap(),
            b"MZfake-executable"
        );
        assert!(extract_binary_from_zip(b"not a zip").is_err());
        assert!(validate_binary(b"not executable").is_err());
        assert!(validate_binary(&std::fs::read(std::env::current_exe().unwrap()).unwrap()).is_ok());
        let mut writer = zip::ZipWriter::new(std::io::Cursor::new(Vec::new()));
        writer
            .start_file("../agentic.exe", zip::write::SimpleFileOptions::default())
            .unwrap();
        writer.write_all(b"MZbad").unwrap();
        assert!(extract_binary_from_zip(&writer.finish().unwrap().into_inner()).is_err());
    }

    #[cfg(unix)]
    #[test]
    fn synchronization_uses_the_new_executable_and_propagates_status() {
        use std::os::unix::fs::PermissionsExt;
        let root = tempfile::tempdir().unwrap();
        let executable = root.path().join("new-agentic");
        std::fs::write(
            &executable,
            r#"#!/bin/sh
[ "$1" = __sync-project ] || exit 8
[ "$AGENTIC_UPGRADED_PROCESS" = 1 ] || exit 9
printf 'new embedded instructions' > "$3/AGENTS.md"
exit 7
"#,
        )
        .unwrap();
        std::fs::set_permissions(&executable, std::fs::Permissions::from_mode(0o755)).unwrap();
        let mut app = App::new().unwrap();
        app.project_dir = root.path().to_string_lossy().into();
        app.upgrade_force = true;
        let error = run_sync_binary(&app, &executable).unwrap_err();
        assert_eq!(error.downcast_ref::<ChildExit>().unwrap().0, 7);
        assert_eq!(
            std::fs::read_to_string(root.path().join("AGENTS.md")).unwrap(),
            "new embedded instructions"
        );
    }

    #[test]
    fn version_comparison() {
        assert!(is_newer_version("0.6.3", "v0.7.0"));
        assert!(is_newer_version("0.7.0", "0.7.1"));
        assert!(!is_newer_version("0.7.0", "v0.7.0"));
        assert!(!is_newer_version("0.7.1", "0.7.0"));
        assert!(is_newer_version("0.9.9", "1.0.0"));
        assert!(!is_newer_version("1.0.0", "0.9.9"));
        assert!(is_newer_version("1.0", "1.0.1"));
    }

    #[test]
    fn tar_gz_extraction_roundtrip() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(tmp.path().join("agentic"), b"fake-binary-content").unwrap();
        let archive = tmp.path().join("asset.tar.gz");
        let status = std::process::Command::new("tar")
            .arg("-czf")
            .arg(&archive)
            .arg("-C")
            .arg(tmp.path())
            .arg("agentic")
            .status()
            .unwrap();
        assert!(status.success());
        let bytes = std::fs::read(&archive).unwrap();
        let extracted = extract_binary_from_tar_gz(&bytes).unwrap();
        assert_eq!(extracted, b"fake-binary-content");
        assert!(extract_binary_from_tar_gz(b"not an archive").is_err());
    }

    #[test]
    fn asset_name_matches_platform() {
        let name = release_asset_name();
        assert!(name.starts_with("agentic-"));
        assert!(name.ends_with(".tar.gz") || name.ends_with(".zip"));
    }
}
