//! Theme handling: dark/light/auto detection and ANSI palettes.

use std::io::IsTerminal;

#[derive(Debug, Clone, Default)]
pub struct Colors {
    pub reset: String,
    pub header: String,
    pub info: String,
    pub warn: String,
    pub error: String,
    pub dim: String,
}

pub fn detect_auto_theme_from(colorfgbg: Option<&str>) -> &'static str {
    if let Some(bg) = colorfgbg {
        if let Some(idx) = bg.rfind(';') {
            let code = &bg[idx + 1..];
            if !code.is_empty() && code.len() <= 2 && code.chars().all(|c| c.is_ascii_digit()) {
                return match code {
                    "0" | "1" | "2" | "3" | "4" | "5" | "6" | "8" | "15" => "light",
                    _ => "dark",
                };
            }
        }
    }
    "dark"
}

pub fn detect_auto_theme() -> &'static str {
    let value = std::env::var("COLORFGBG").ok();
    detect_auto_theme_from(value.as_deref())
}

pub fn supports_color() -> bool {
    if !std::io::stdout().is_terminal() {
        return false;
    }
    if std::env::var("NO_COLOR")
        .map(|v| !v.is_empty())
        .unwrap_or(false)
    {
        return false;
    }
    true
}

/// Resolve theme name ("auto" -> detected) and build the ANSI palette.
pub fn resolve(theme: &str, use_ansi: bool) -> (String, Colors) {
    let resolved = if theme == "auto" {
        detect_auto_theme().to_string()
    } else {
        theme.to_string()
    };
    let active = if resolved == "light" { "light" } else { "dark" };

    let mut colors = Colors::default();
    if use_ansi {
        colors.reset = "\x1b[0m".to_string();
        colors.warn = "\x1b[1;33m".to_string();
        colors.error = "\x1b[1;31m".to_string();
        match active {
            "light" => {
                colors.header = "\x1b[1;34m".to_string();
                colors.info = "\x1b[1;36m".to_string();
                colors.dim = "\x1b[2;30m".to_string();
            }
            _ => {
                colors.header = "\x1b[1;36m".to_string();
                colors.info = "\x1b[1;32m".to_string();
                colors.dim = "\x1b[2;37m".to_string();
            }
        }
    }
    (active.to_string(), colors)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn auto_theme_detection_from_colorfgbg() {
        assert_eq!(detect_auto_theme_from(Some("15;0")), "light");
        assert_eq!(detect_auto_theme_from(Some("0;15")), "light");
        assert_eq!(detect_auto_theme_from(Some("15;7")), "dark");
        assert_eq!(detect_auto_theme_from(Some("0;7")), "dark");
        assert_eq!(detect_auto_theme_from(Some("0;8")), "light");
        assert_eq!(detect_auto_theme_from(Some("garbage")), "dark");
        assert_eq!(detect_auto_theme_from(None), "dark");
    }

    #[test]
    fn resolve_palettes() {
        let (active, colors) = resolve("light", true);
        assert_eq!(active, "light");
        assert_eq!(colors.header, "\x1b[1;34m");
        let (active, colors) = resolve("dark", true);
        assert_eq!(active, "dark");
        assert_eq!(colors.header, "\x1b[1;36m");
        let (_, colors) = resolve("dark", false);
        assert!(colors.header.is_empty());
    }

    #[test]
    fn resolve_unknown_falls_back_to_dark() {
        let (active, _) = resolve("weird", true);
        assert_eq!(active, "dark");
    }
}
