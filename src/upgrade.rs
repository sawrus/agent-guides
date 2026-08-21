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
    // Minimal .tar.gz extraction: gzip decode via flate2-free approach is not
    // available; store the raw binary as the only asset payload instead.
    // Release assets are built as plain gzip-compressed tarballs by CI, so we
    // shell out to tar which is universally available on unix.
    let tmp = tempfile::tempdir()?;
    let archive_path = tmp.path().join("asset.tar.gz");
    std::fs::write(&archive_path, bytes)?;
    let status = std::process::Command::new("tar")
        .arg("-xzf")
        .arg(&archive_path)
        .arg("-C")
        .arg(tmp.path())
        .status()?;
    if !status.success() {
        return Err("failed to extract release archive".into());
    }
    let binary = tmp.path().join("agentic");
    Ok(std::fs::read(&binary)?)
}

pub fn upgrade_binary(app: &mut App) -> crate::Result<()> {
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
        return Ok(());
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
        return Ok(());
    }
    if !is_newer_version(&crate::app_version(), &tag) {
        ui::log(app, &format!("Already up to date ({tag})"));
        return Ok(());
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
        return Ok(());
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
        bytes.to_vec()
    };

    let tmp = tempfile::NamedTempFile::new_in(crate::util::tmp_dir())?;
    std::fs::write(tmp.path(), &binary)?;
    self_replace::self_replace(tmp.path())
        .map_err(|e| -> crate::AnyError { format!("Failed to replace binary: {e}").into() })?;
    ui::log(app, &format!("Updated installed binary to {tag}"));
    Ok(())
}

pub fn sync_current_project_after_upgrade(app: &mut App) -> crate::Result<()> {
    let cwd = std::env::current_dir()?;
    let manifest = cwd.join(crate::PROJECT_MANIFEST_NAME);
    if !manifest.is_file() {
        ui::log(
            app,
            &format!(
                "No {} in current directory; knowledge base upgrade complete",
                crate::PROJECT_MANIFEST_NAME
            ),
        );
        return Ok(());
    }
    ui::log(
        app,
        &format!(
            "Detected managed project in {}; syncing from upgraded knowledge base",
            cwd.display()
        ),
    );
    app.project_dir = std::fs::canonicalize(&cwd)
        .unwrap_or(cwd)
        .to_string_lossy()
        .to_string();
    crate::manifest::load_install_settings_from_manifest(app, &manifest)?;
    crate::install::run_install(app)?;
    crate::mempalace::upgrade_mempalace_graph(app);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

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
