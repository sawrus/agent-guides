//! Logging helpers mirroring the bash `log`/`warn`/`error`/`out` functions,
//! including the persistent run log file.

use crate::app::App;
use chrono::Local;
use std::io::Write;

pub fn timestamp_now() -> String {
    Local::now().format("%Y-%m-%d %H:%M:%S").to_string()
}

pub fn init_run_logging(app: &mut App) {
    if app.run_log_active {
        return;
    }
    let base_dir = crate::util::tmp_dir();
    let stamp = Local::now().format("%Y%m%d-%H%M%S").to_string();
    let file = tempfile::Builder::new()
        .prefix(&format!("agentic-{stamp}."))
        .disable_cleanup(true)
        .tempfile_in(&base_dir);
    if let Ok(file) = file {
        let path = file.path().to_path_buf();
        app.changed_paths_report_file = format!("{}.changes", path.display());
        app.run_log_file = path.to_string_lossy().to_string();
        app.run_log_active = true;
        log(app, &format!("Run log initialized: {}", app.run_log_file));
    }
}

fn write_run_log_line(app: &App, line: &str) {
    if app.run_log_active && !app.run_log_file.is_empty() {
        if let Ok(mut f) = std::fs::OpenOptions::new()
            .append(true)
            .create(true)
            .open(&app.run_log_file)
        {
            let _ = writeln!(f, "{line}");
        }
    }
}

fn emit(app: &App, stderr: bool, tag: &str, message: &str, color: &str) {
    let (line, plain) = if app.run_log_active {
        let ts = timestamp_now();
        let plain = format!("{ts} {tag} {message}");
        let line = if !color.is_empty() {
            format!("{ts} {color}{tag}{} {message}", app.colors.reset)
        } else {
            plain.clone()
        };
        (line, plain)
    } else {
        let plain = format!("{tag} {message}");
        let line = if !color.is_empty() {
            format!("{color}{tag}{} {message}", app.colors.reset)
        } else {
            plain.clone()
        };
        (line, plain)
    };
    if stderr {
        eprintln!("{line}");
    } else {
        println!("{line}");
    }
    write_run_log_line(app, &plain);
}

pub fn log(app: &App, message: &str) {
    emit(app, false, "[agentic]", message, &app.colors.info.clone());
}

pub fn warn(app: &mut App, message: &str) {
    let color = app.colors.warn.clone();
    emit(app, false, "[agentic][warn]", message, &color);
    app.warnings.push(message.to_string());
}

pub fn error(app: &App, message: &str) {
    emit(
        app,
        true,
        "[agentic][error]",
        message,
        &app.colors.error.clone(),
    );
}

/// Plain stderr error for contexts without an `App` (startup failures).
pub fn error_plain(message: &str) {
    eprintln!("[agentic][error] {message}");
}

pub fn out(app: &App, message: &str) {
    out_color(app, message, "");
}

pub fn out_color(app: &App, message: &str, color: &str) {
    if message.is_empty() {
        println!();
        write_run_log_line(app, "");
        return;
    }
    let (line, plain) = if app.run_log_active {
        let ts = timestamp_now();
        let plain = format!("{ts} {message}");
        let line = if !color.is_empty() {
            format!("{ts} {color}{message}{}", app.colors.reset)
        } else {
            plain.clone()
        };
        (line, plain)
    } else {
        let plain = message.to_string();
        let line = if !color.is_empty() {
            format!("{color}{message}{}", app.colors.reset)
        } else {
            plain.clone()
        };
        (line, plain)
    };
    println!("{line}");
    write_run_log_line(app, &plain);
}

pub fn log_file_block(app: &App, label: &str, path: &std::path::Path) {
    if !(app.run_log_active && !app.run_log_file.is_empty() && path.is_file()) {
        return;
    }
    write_run_log_line(
        app,
        &format!("{} --- {label} output begin ---", timestamp_now()),
    );
    if let Ok(content) = std::fs::read_to_string(path) {
        for line in content.lines() {
            write_run_log_line(app, &format!("{} {line}", timestamp_now()));
        }
    }
    write_run_log_line(
        app,
        &format!("{} --- {label} output end ---", timestamp_now()),
    );
}

pub fn write_changed_paths_report(app: &mut App) {
    if app.changed_paths_report_file.is_empty() {
        let base_dir = crate::util::tmp_dir();
        let stamp = Local::now().format("%Y%m%d-%H%M%S").to_string();
        app.changed_paths_report_file = base_dir
            .join(format!("agentic-changed-paths-{stamp}"))
            .to_string_lossy()
            .to_string();
    }
    let mut body = String::new();
    body.push_str("Agentic changed paths report\n");
    body.push_str(&format!("Generated at: {}\n", timestamp_now()));
    body.push_str(&format!("Project dir: {}\n", app.project_dir));
    body.push_str(&format!("Knowledge base repo: {}\n\n", app.kb.root_label()));

    body.push_str(&format!(
        "Created directories ({})\n",
        app.created_paths.len()
    ));
    if app.created_paths.is_empty() {
        body.push_str("- (none)\n");
    } else {
        for p in &app.created_paths {
            body.push_str(&format!("- {p}\n"));
        }
    }
    body.push('\n');
    body.push_str(&format!(
        "Copied/generated paths ({})\n",
        app.copied_paths.len()
    ));
    if app.copied_paths.is_empty() {
        body.push_str("- (none)\n");
    } else {
        for p in &app.copied_paths {
            body.push_str(&format!("- {p}\n"));
        }
    }
    body.push('\n');
    body.push_str(&format!("Warnings ({})\n", app.warnings.len()));
    if app.warnings.is_empty() {
        body.push_str("- (none)\n");
    } else {
        for w in &app.warnings {
            body.push_str(&format!("- {w}\n"));
        }
    }
    let _ = std::fs::write(&app.changed_paths_report_file, body);
}
