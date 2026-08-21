//! Line-based interactive prompts used during CLI installs (mirror of the
//! bash index-menu fallbacks).

use crate::app::App;
use crate::ui;
use std::io::Write;

#[cfg(test)]
thread_local! {
    static TEST_ANSWERS: std::cell::RefCell<Vec<String>> = const { std::cell::RefCell::new(Vec::new()) };
}

#[cfg(test)]
pub fn set_test_answers(answers: &[&str]) {
    TEST_ANSWERS.with(|q| {
        *q.borrow_mut() = answers.iter().rev().map(|s| s.to_string()).collect();
    });
}

pub fn read_line_prompt(prompt: &str) -> String {
    #[cfg(test)]
    {
        let injected = TEST_ANSWERS.with(|q| q.borrow_mut().pop());
        if let Some(answer) = injected {
            return answer;
        }
    }
    print!("{prompt}");
    let _ = std::io::stdout().flush();
    let mut answer = String::new();
    if std::io::stdin().read_line(&mut answer).is_err() {
        return String::new();
    }
    answer.trim().to_string()
}

#[allow(dead_code)]
pub fn prompt_with_default(prompt: &str, default: &str) -> String {
    let answer = read_line_prompt(&format!("{prompt} [{default}]: "));
    if answer.is_empty() {
        default.to_string()
    } else {
        answer
    }
}

pub fn prompt_text_interactive(prompt: &str, default: &str) -> String {
    let answer = if default.is_empty() {
        read_line_prompt(&format!("{prompt}: "))
    } else {
        read_line_prompt(&format!("{prompt} [keep current]: "))
    };
    if answer.is_empty() {
        default.to_string()
    } else {
        answer
    }
}

pub fn confirm_action_interactive(prompt: &str) -> bool {
    let answer = read_line_prompt(&format!("{prompt} [y/N]: "));
    let lower = answer.to_lowercase();
    lower == "y" || lower == "yes"
}

/// Single-choice numbered menu; empty answer = first option;
/// invalid index -> exit 1.
pub fn choose_single_by_index(
    app: &App,
    prompt: &str,
    options: &[String],
) -> crate::Result<String> {
    eprintln!("{prompt}");
    for (i, option) in options.iter().enumerate() {
        eprintln!("  {}) {option}", i + 1);
    }
    let answer = read_line_prompt("Select one (empty=1): ");
    if answer.is_empty() {
        return Ok(options[0].clone());
    }
    match answer.parse::<usize>() {
        Ok(idx) if idx >= 1 && idx <= options.len() => Ok(options[idx - 1].clone()),
        _ => {
            ui::error(app, "Invalid choice");
            Err(crate::exit1())
        }
    }
}

/// Multi-choice numbered menu with comma-separated indexes; empty -> empty
/// selection; invalid index -> exit 1.
pub fn choose_multi_by_index(
    app: &App,
    prompt: &str,
    options: &[String],
) -> crate::Result<Vec<String>> {
    eprintln!("{prompt}");
    for (i, option) in options.iter().enumerate() {
        eprintln!("  {}) {option}", i + 1);
    }
    let answer = read_line_prompt("Select one or more (comma-separated indexes): ");
    if answer.is_empty() {
        return Ok(Vec::new());
    }
    let mut out: Vec<String> = Vec::new();
    for raw in answer.split(',') {
        let idx_str = raw.trim();
        match idx_str.parse::<usize>() {
            Ok(idx) if idx >= 1 && idx <= options.len() => {
                crate::util::unique_append(&mut out, &options[idx - 1]);
            }
            _ => {
                ui::error(app, &format!("Invalid selection index: {idx_str}"));
                return Err(crate::exit1());
            }
        }
    }
    Ok(out)
}

pub fn configure_context7_key_interactive(app: &mut App) -> crate::Result<()> {
    if !app.is_interactive_terminal() {
        return Ok(());
    }
    let options = vec![
        "Use without API key".to_string(),
        "Enter CONTEXT7_API_KEY".to_string(),
    ];
    let choice = choose_single_by_index(app, "Context7 API key mode:", &options)?;
    if choice == "Enter CONTEXT7_API_KEY" {
        let current = app.context7_api_key.clone();
        app.context7_api_key = prompt_text_interactive("CONTEXT7_API_KEY", &current);
    } else {
        app.context7_api_key.clear();
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn app() -> App {
        App::new().unwrap()
    }

    #[test]
    fn prompt_defaults_and_values() {
        set_test_answers(&["", "value", "", "custom"]);
        assert_eq!(prompt_with_default("p", "def"), "def");
        assert_eq!(prompt_with_default("p", "def"), "value");
        assert_eq!(prompt_text_interactive("p", "keep"), "keep");
        assert_eq!(prompt_text_interactive("p", ""), "custom");
    }

    #[test]
    fn confirm_variants() {
        set_test_answers(&["y", "YES", "n", ""]);
        assert!(confirm_action_interactive("q"));
        assert!(confirm_action_interactive("q"));
        assert!(!confirm_action_interactive("q"));
        assert!(!confirm_action_interactive("q"));
    }

    #[test]
    fn single_choice_menu() {
        let app = app();
        let options = vec!["a".to_string(), "b".to_string()];
        set_test_answers(&["", "2", "9"]);
        assert_eq!(choose_single_by_index(&app, "t", &options).unwrap(), "a");
        assert_eq!(choose_single_by_index(&app, "t", &options).unwrap(), "b");
        assert!(choose_single_by_index(&app, "t", &options).is_err());
    }

    #[test]
    fn multi_choice_menu() {
        let app = app();
        let options = vec!["a".to_string(), "b".to_string(), "c".to_string()];
        set_test_answers(&["", "1,3,1", "0"]);
        assert!(choose_multi_by_index(&app, "t", &options)
            .unwrap()
            .is_empty());
        assert_eq!(
            choose_multi_by_index(&app, "t", &options).unwrap(),
            vec!["a", "c"]
        );
        assert!(choose_multi_by_index(&app, "t", &options).is_err());
    }

    #[test]
    fn context7_key_flow() {
        let mut app = app();
        app.interactive_override = Some(true);
        app.context7_api_key = "old".to_string();
        set_test_answers(&["1"]);
        configure_context7_key_interactive(&mut app).unwrap();
        assert!(app.context7_api_key.is_empty());
        set_test_answers(&["2", "newkey"]);
        configure_context7_key_interactive(&mut app).unwrap();
        assert_eq!(app.context7_api_key, "newkey");
    }
}
