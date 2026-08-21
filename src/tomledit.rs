//! Textual TOML editing helpers mirroring the Python regex logic used for
//! `.codex/config.toml` so the output stays byte-compatible.

/// Find the section of `[table]`: returns (start, body_start, end) where end
/// is the index right after the section body (next `[` line at column 0 or EOF).
fn find_table_section(source: &str, header: &str) -> Option<(usize, usize, usize)> {
    let mut offset = 0;
    for line in split_keepends(source) {
        let line_start = offset;
        offset += line.len();
        if line.trim_end_matches('\n') == header && line.ends_with('\n') {
            let body_start = offset;
            // find end: next line starting with '[' at column 0
            let mut end = source.len();
            let mut scan = body_start;
            for body_line in split_keepends(&source[body_start..]) {
                if body_line.starts_with('[') {
                    end = scan;
                    break;
                }
                scan += body_line.len();
            }
            return Some((line_start, body_start, end));
        }
    }
    None
}

/// Set `key = value` inside `[table]`, creating the table at the top when
/// missing (mirror of Python `set_table_key`).
pub fn set_table_key(source: &str, table: &str, key: &str, value: &str) -> String {
    let header = format!("[{table}]");
    let Some((start, body_start, end)) = find_table_section(source, &header) else {
        return format!("[{table}]\n{key} = {value}\n\n{}", source.trim_start());
    };
    let body = &source[body_start..end];
    let mut output: Vec<String> = Vec::new();
    let mut found = false;
    for line in split_keepends(body) {
        if is_key_line(&line, key) {
            let nl = if line.ends_with('\n') { "\n" } else { "" };
            output.push(format!("{key} = {value}{nl}"));
            found = true;
        } else {
            output.push(line);
        }
    }
    if !found {
        if let Some(last) = output.last_mut() {
            if !last.ends_with('\n') {
                last.push('\n');
            }
        }
        output.push(format!("{key} = {value}\n"));
    }
    format!(
        "{}{header}\n{}{}",
        &source[..start],
        output.concat(),
        &source[end..]
    )
}

fn is_key_line(line: &str, key: &str) -> bool {
    let trimmed = line.trim_start();
    if let Some(rest) = trimmed.strip_prefix(key) {
        rest.trim_start().starts_with('=')
    } else {
        false
    }
}

/// Remove a `[mcp_servers.<server>]` block, then trim (mirror of the bash
/// `re.sub(...).strip()` usage).
pub fn remove_server_block(source: &str, server: &str) -> String {
    let header = format!("[mcp_servers.{server}]");
    match find_table_section(source, &header) {
        Some((start, _, end)) => format!("{}{}", &source[..start], &source[end..])
            .trim()
            .to_string(),
        None => source.trim().to_string(),
    }
}

/// Mirror of Python `enable_memories` for `[features]` / `memories = true`.
pub fn enable_codex_memories(text: &str) -> String {
    if let Some((start, body_start, end)) = find_table_section(text, "[features]") {
        let body = &text[body_start..end];
        let mut output: Vec<String> = Vec::new();
        let mut found = false;
        for line in split_keepends(body) {
            if is_key_line(&line, "memories") {
                let nl = if line.ends_with('\n') { "\n" } else { "" };
                output.push(format!("memories = true{nl}"));
                found = true;
            } else {
                output.push(line);
            }
        }
        let replaced = if !found {
            let trailing_len = body.len() - body.trim_end_matches('\n').len();
            let (main, trailing) = body.split_at(body.len() - trailing_len);
            let mut main = main.to_string();
            if !main.is_empty() && !main.ends_with('\n') {
                main.push('\n');
            }
            format!("[features]\n{main}memories = true\n{trailing}")
        } else {
            format!("[features]\n{}", output.concat())
        };
        format!("{}{}{}", &text[..start], replaced, &text[end..])
    } else if !text.trim().is_empty() {
        format!("{}\n\n[features]\nmemories = true\n", text.trim_end())
    } else {
        "[features]\nmemories = true\n".to_string()
    }
}

fn split_keepends(s: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut current = String::new();
    for ch in s.chars() {
        current.push(ch);
        if ch == '\n' {
            out.push(std::mem::take(&mut current));
        }
    }
    if !current.is_empty() {
        out.push(current);
    }
    out
}

pub fn toml_string(value: &str) -> String {
    serde_json::to_string(value).unwrap_or_else(|_| format!("\"{value}\""))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn set_table_key_creates_table() {
        let out = set_table_key("", "sandbox_workspace_write", "network_access", "true");
        assert_eq!(out, "[sandbox_workspace_write]\nnetwork_access = true\n\n");
    }

    #[test]
    fn set_table_key_updates_existing() {
        let src = "[sandbox_workspace_write]\nnetwork_access = false\n\n[other]\nx = 1\n";
        let out = set_table_key(src, "sandbox_workspace_write", "network_access", "true");
        assert!(out.contains("network_access = true\n"));
        assert!(out.contains("[other]\nx = 1\n"));
        assert!(!out.contains("false"));
    }

    #[test]
    fn set_table_key_appends_missing_key() {
        let src = "[sandbox_workspace_write]\nfoo = 1\n";
        let out = set_table_key(src, "sandbox_workspace_write", "network_access", "true");
        assert!(out.contains("foo = 1\nnetwork_access = true\n"));
    }

    #[test]
    fn remove_server_block_removes_only_target() {
        let src = "[mcp_servers.context7]\nurl = \"x\"\n\n[mcp_servers.other]\ncommand = \"y\"\n";
        let out = remove_server_block(src, "context7");
        assert!(!out.contains("context7"));
        assert!(out.contains("[mcp_servers.other]"));
        assert_eq!(remove_server_block("plain = 1\n", "nope"), "plain = 1");
    }

    #[test]
    fn enable_memories_variants() {
        assert_eq!(enable_codex_memories(""), "[features]\nmemories = true\n");
        assert_eq!(
            enable_codex_memories("[other]\nx = 1\n"),
            "[other]\nx = 1\n\n[features]\nmemories = true\n"
        );
        let out = enable_codex_memories("[features]\nmemories = false\n");
        assert_eq!(out, "[features]\nmemories = true\n");
        let out = enable_codex_memories("[features]\nfoo = 1\n\n[z]\na = 2\n");
        assert!(out.contains("foo = 1\nmemories = true\n"));
        assert!(out.contains("[z]\na = 2\n"));
    }

    #[test]
    fn toml_string_escapes() {
        assert_eq!(toml_string("a\"b"), "\"a\\\"b\"");
    }
}
