//! Fullscreen ratatui wizard for `agentic tui` (and no-args interactive runs).
//! The flow mirrors the bash TUI: theme -> banner -> project dir -> agent OS ->
//! MCP servers (with detection checkboxes) -> areas -> per-area specs -> install.

use crate::app::App;
use crate::config;
use crate::install;
use crate::mcp;
use crate::ui;
use crossterm::event::{self, Event, KeyCode, KeyEventKind, KeyModifiers};
use ratatui::backend::Backend;
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph};
use ratatui::{Frame, Terminal};

pub const ASCII_BANNER: &str = r#"    _    ____ _____ _   _ _____ ___ ____
   / \  / ___| ____| \ | |_   _|_ _/ ___|
  / _ \| |  _|  _| |  \| | | |  | | |
 / ___ \ |_| | |___| |\  | | |  | | |___
/_/   \_\____|_____|_| \_| |_| |___\____|"#;

/// Pure, testable state for a single/multi select menu.
#[derive(Debug, Clone)]
pub struct SelectState {
    pub title: String,
    pub options: Vec<String>,
    pub cursor: usize,
    pub selected: Vec<bool>,
    pub multi: bool,
    pub done: bool,
    pub cancelled: bool,
}

impl SelectState {
    pub fn new(title: &str, options: Vec<String>, multi: bool) -> SelectState {
        let len = options.len();
        SelectState {
            title: title.to_string(),
            options,
            cursor: 0,
            selected: vec![false; len],
            multi,
            done: false,
            cancelled: false,
        }
    }

    pub fn preselect(&mut self, values: &[String]) {
        for (i, option) in self.options.iter().enumerate() {
            if values.iter().any(|v| v == option) {
                self.selected[i] = true;
            }
        }
    }

    pub fn handle_key(&mut self, code: KeyCode) {
        match code {
            KeyCode::Up => {
                if self.cursor == 0 {
                    self.cursor = self.options.len().saturating_sub(1);
                } else {
                    self.cursor -= 1;
                }
            }
            KeyCode::Down => {
                self.cursor = (self.cursor + 1) % self.options.len().max(1);
            }
            KeyCode::Char(' ') if self.multi => {
                if let Some(v) = self.selected.get_mut(self.cursor) {
                    *v = !*v;
                }
            }
            KeyCode::Tab if self.multi => {
                if let Some(v) = self.selected.get_mut(self.cursor) {
                    *v = !*v;
                }
                self.cursor = (self.cursor + 1) % self.options.len().max(1);
            }
            KeyCode::Enter => {
                if !self.multi {
                    if let Some(v) = self.selected.get_mut(self.cursor) {
                        *v = true;
                    }
                }
                self.done = true;
            }
            KeyCode::Esc => {
                self.cancelled = true;
                self.done = true;
            }
            _ => {}
        }
    }

    pub fn picked(&self) -> Vec<String> {
        if self.cancelled {
            return Vec::new();
        }
        self.options
            .iter()
            .zip(self.selected.iter())
            .filter(|(_, sel)| **sel)
            .map(|(opt, _)| opt.clone())
            .collect()
    }
}

/// Pure, testable state for a text-input prompt.
#[derive(Debug, Clone)]
pub struct InputState {
    pub title: String,
    pub default: String,
    pub value: String,
    pub done: bool,
    pub cancelled: bool,
}

impl InputState {
    pub fn new(title: &str, default: &str) -> InputState {
        InputState {
            title: title.to_string(),
            default: default.to_string(),
            value: String::new(),
            done: false,
            cancelled: false,
        }
    }

    pub fn handle_key(&mut self, code: KeyCode) {
        match code {
            KeyCode::Char(c) => self.value.push(c),
            KeyCode::Backspace => {
                self.value.pop();
            }
            KeyCode::Enter => self.done = true,
            KeyCode::Esc => {
                self.cancelled = true;
                self.done = true;
            }
            _ => {}
        }
    }

    pub fn result(&self) -> String {
        let trimmed = self.value.trim();
        if trimmed.is_empty() {
            self.default.clone()
        } else {
            trimmed.to_string()
        }
    }
}

/// Theme palette derived from the fzf colors of the bash version.
struct Palette {
    base: Style,
    header: Style,
    highlight: Style,
    dim: Style,
}

fn theme_style(active_theme: &str) -> Palette {
    if active_theme == "light" {
        // fzf light: fg #1f2937, bg #f8fafc, fg+ #111827, bg+ #dbeafe
        Palette {
            base: Style::default()
                .fg(Color::Rgb(0x1f, 0x29, 0x37))
                .bg(Color::Rgb(0xf8, 0xfa, 0xfc)),
            header: Style::default()
                .fg(Color::Rgb(0x25, 0x63, 0xeb))
                .bg(Color::Rgb(0xf8, 0xfa, 0xfc))
                .add_modifier(Modifier::BOLD),
            highlight: Style::default()
                .fg(Color::Rgb(0x11, 0x18, 0x27))
                .bg(Color::Rgb(0xdb, 0xea, 0xfe)),
            dim: Style::default()
                .fg(Color::Rgb(0x33, 0x41, 0x55))
                .bg(Color::Rgb(0xf8, 0xfa, 0xfc)),
        }
    } else {
        // fzf dark: fg #e5e7eb, bg #111827, fg+ #ffffff, bg+ #1f2937
        Palette {
            base: Style::default()
                .fg(Color::Rgb(0xe5, 0xe7, 0xeb))
                .bg(Color::Rgb(0x11, 0x18, 0x27)),
            header: Style::default()
                .fg(Color::Rgb(0x60, 0xa5, 0xfa))
                .bg(Color::Rgb(0x11, 0x18, 0x27))
                .add_modifier(Modifier::BOLD),
            highlight: Style::default()
                .fg(Color::Rgb(0xff, 0xff, 0xff))
                .bg(Color::Rgb(0x1f, 0x29, 0x37)),
            dim: Style::default()
                .fg(Color::Rgb(0xd1, 0xd5, 0xdb))
                .bg(Color::Rgb(0x11, 0x18, 0x27)),
        }
    }
}

fn fill_background(frame: &mut Frame, base: Style) {
    frame.render_widget(Block::default().style(base), frame.area());
}

fn layout_chunks(area: Rect) -> Vec<Rect> {
    Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(7),
            Constraint::Min(5),
            Constraint::Length(1),
        ])
        .split(area)
        .to_vec()
}

pub fn render_banner(frame: &mut Frame, area: Rect, active_theme: &str, subtitle: &str) {
    let palette = theme_style(active_theme);
    let mut lines: Vec<Line> = ASCII_BANNER
        .lines()
        .map(|l| Line::from(Span::styled(l.to_string(), palette.header)))
        .collect();
    lines.push(Line::from(Span::styled(subtitle.to_string(), palette.dim)));
    frame.render_widget(Paragraph::new(lines).style(palette.base), area);
}

pub fn render_select(frame: &mut Frame, state: &SelectState, active_theme: &str, subtitle: &str) {
    let palette = theme_style(active_theme);
    fill_background(frame, palette.base);
    let chunks = layout_chunks(frame.area());
    render_banner(frame, chunks[0], active_theme, subtitle);
    let (header, highlight, dim) = (palette.header, palette.highlight, palette.dim);
    let items: Vec<ListItem> = state
        .options
        .iter()
        .enumerate()
        .map(|(i, option)| {
            let marker = if state.multi {
                if state.selected[i] {
                    "[x] "
                } else {
                    "[ ] "
                }
            } else {
                ""
            };
            ListItem::new(format!("{marker}{option}"))
        })
        .collect();
    let help = if state.multi {
        "Use ↑/↓ to navigate • Space to select • Enter to confirm • Esc to skip"
    } else {
        "Use ↑/↓ to navigate • Enter to select"
    };
    let list = List::new(items)
        .style(palette.base)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(palette.base)
                .title(Span::styled(state.title.clone(), header)),
        )
        .highlight_style(highlight)
        .highlight_symbol("> ");
    let mut list_state = ListState::default();
    list_state.select(Some(state.cursor));
    frame.render_stateful_widget(list, chunks[1], &mut list_state);
    frame.render_widget(Paragraph::new(Span::styled(help, dim)), chunks[2]);
}

pub fn render_input(frame: &mut Frame, state: &InputState, active_theme: &str, subtitle: &str) {
    let palette = theme_style(active_theme);
    fill_background(frame, palette.base);
    let chunks = layout_chunks(frame.area());
    render_banner(frame, chunks[0], active_theme, subtitle);
    let (header, dim) = (palette.header, palette.dim);
    let shown = format!("{}▏", state.value);
    let body = Paragraph::new(vec![
        Line::from(shown),
        Line::from(Span::styled(format!("(empty = {})", state.default), dim)),
    ])
    .style(palette.base)
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(palette.base)
            .title(Span::styled(state.title.clone(), header)),
    );
    frame.render_widget(body, chunks[1]);
    frame.render_widget(
        Paragraph::new(Span::styled(
            "Type path and press Enter to confirm • Esc to cancel",
            dim,
        )),
        chunks[2],
    );
}

fn wait_key() -> crate::Result<Option<KeyCode>> {
    loop {
        match event::read()? {
            Event::Key(key) if key.kind == KeyEventKind::Press => {
                if key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL) {
                    return Ok(None);
                }
                return Ok(Some(key.code));
            }
            _ => continue,
        }
    }
}

fn run_select<B: Backend>(
    terminal: &mut Terminal<B>,
    mut state: SelectState,
    active_theme: &str,
    subtitle: &str,
) -> crate::Result<SelectState> {
    while !state.done {
        terminal.draw(|frame| render_select(frame, &state, active_theme, subtitle))?;
        match wait_key()? {
            Some(code) => state.handle_key(code),
            None => {
                state.cancelled = true;
                state.done = true;
            }
        }
    }
    Ok(state)
}

fn run_input<B: Backend>(
    terminal: &mut Terminal<B>,
    mut state: InputState,
    active_theme: &str,
    subtitle: &str,
) -> crate::Result<InputState> {
    while !state.done {
        terminal.draw(|frame| render_input(frame, &state, active_theme, subtitle))?;
        match wait_key()? {
            Some(code) => state.handle_key(code),
            None => {
                state.cancelled = true;
                state.done = true;
            }
        }
    }
    Ok(state)
}

struct TerminalGuard;

impl TerminalGuard {
    fn enter() -> crate::Result<TerminalGuard> {
        crossterm::terminal::enable_raw_mode()?;
        crossterm::execute!(std::io::stdout(), crossterm::terminal::EnterAlternateScreen)?;
        Ok(TerminalGuard)
    }
}

impl Drop for TerminalGuard {
    fn drop(&mut self) {
        let _ = crossterm::execute!(std::io::stdout(), crossterm::terminal::LeaveAlternateScreen);
        let _ = crossterm::terminal::disable_raw_mode();
    }
}

fn wizard_subtitle() -> String {
    format!("{} {}", crate::APP_TUI_TITLE, crate::app_version_label())
}

/// One-shot fullscreen single select. Returns None on cancel (Esc/Ctrl-C).
pub fn screen_select_single(app: &App, title: &str, options: &[String]) -> Option<String> {
    if options.is_empty() {
        return None;
    }
    let _guard = TerminalGuard::enter().ok()?;
    let backend = ratatui::backend::CrosstermBackend::new(std::io::stdout());
    let mut terminal = Terminal::new(backend).ok()?;
    let state = SelectState::new(title, options.to_vec(), false);
    let state = run_select(&mut terminal, state, &app.active_theme, &wizard_subtitle()).ok()?;
    if state.cancelled {
        return None;
    }
    state.picked().first().cloned()
}

/// One-shot fullscreen multi select with optional preselected values.
/// Returns None on cancel (Esc/Ctrl-C), otherwise the picked options.
pub fn screen_select_multi(
    app: &App,
    title: &str,
    options: &[String],
    preselected: &[String],
) -> Option<Vec<String>> {
    if options.is_empty() {
        return Some(Vec::new());
    }
    let _guard = TerminalGuard::enter().ok()?;
    let backend = ratatui::backend::CrosstermBackend::new(std::io::stdout());
    let mut terminal = Terminal::new(backend).ok()?;
    let mut state = SelectState::new(title, options.to_vec(), true);
    state.preselect(preselected);
    let state = run_select(&mut terminal, state, &app.active_theme, &wizard_subtitle()).ok()?;
    if state.cancelled {
        return None;
    }
    Some(state.picked())
}

/// One-shot fullscreen text input. Returns None on cancel.
pub fn screen_input(app: &App, title: &str, default: &str) -> Option<String> {
    let _guard = TerminalGuard::enter().ok()?;
    let backend = ratatui::backend::CrosstermBackend::new(std::io::stdout());
    let mut terminal = Terminal::new(backend).ok()?;
    let state = InputState::new(title, default);
    let state = run_input(&mut terminal, state, &app.active_theme, &wizard_subtitle()).ok()?;
    if state.cancelled {
        return None;
    }
    Some(state.result())
}

/// One-shot yes/no question rendered as a TUI select ("Yes"/"No").
pub fn screen_yes_no(app: &App, prompt: &str) -> bool {
    let options = vec!["Yes".to_string(), "No".to_string()];
    matches!(
        screen_select_single(app, prompt, &options).as_deref(),
        Some("Yes")
    )
}

/// One-shot Confirm/Cancel question (mirror of the fzf confirm menu).
pub fn screen_confirm(app: &App, prompt: &str) -> bool {
    let options = vec!["Confirm".to_string(), "Cancel".to_string()];
    matches!(
        screen_select_single(app, prompt, &options).as_deref(),
        Some("Confirm")
    )
}

/// Wizard outcome collected from the fullscreen phase.
#[derive(Debug, Default, Clone)]
pub struct WizardSelections {
    pub theme: Option<String>,
    pub project_dir: String,
    pub agent_os: Vec<String>,
    pub mcps: Vec<String>,
    pub clear_mcps: bool,
    pub areas: Vec<String>,
    pub specs: Vec<String>,
}

pub fn run_tui(app: &mut App) -> crate::Result<()> {
    if !app.is_interactive_terminal() {
        ui::error(app, "TUI mode requires an interactive terminal");
        return Err(crate::exit1());
    }

    let selections = run_wizard_screens(app)?;
    apply_selections(app, selections);
    config::save_user_config(app);
    app.tui_mode = true;
    install::run_install(app)
}

/// Apply wizard selections to the app state
/// (mirror of the bash TUI post-processing).
pub fn apply_selections(app: &mut App, selections: WizardSelections) {
    if let Some(theme) = selections.theme {
        app.theme = theme;
        app.set_theme_colors();
    }
    app.project_dir = selections.project_dir;
    app.selected_agent_os = if selections.agent_os.is_empty() {
        vec![crate::DEFAULT_AGENT_OS.to_string()]
    } else {
        selections.agent_os
    };
    app.selected_mcps.clear();
    app.enable_context7_env = Some("n".to_string());
    app.enable_mempalace_env = Some("n".to_string());
    for id in &selections.mcps {
        mcp::add_selected_mcp(app, id);
    }
    mcp::sync_legacy_mcp_env_from_selected(app);
    app.selected_areas = if selections.areas.is_empty() {
        vec!["software".to_string()]
    } else {
        selections.areas
    };
    app.selected_specs = selections.specs;
}

fn run_wizard_screens(app: &mut App) -> crate::Result<WizardSelections> {
    let _guard = TerminalGuard::enter()?;
    let backend = ratatui::backend::CrosstermBackend::new(std::io::stdout());
    let mut terminal = Terminal::new(backend)?;
    let subtitle = format!("{} {}", crate::APP_TUI_TITLE, crate::app_version_label());

    let mut selections = WizardSelections::default();

    // 1. Theme picker (skipped when explicit or loaded from config)
    if !app.theme_explicit && !app.theme_loaded_from_config {
        let state = SelectState::new(
            "Select interface theme:",
            crate::THEME_CHOICES.iter().map(|s| s.to_string()).collect(),
            false,
        );
        let state = run_select(&mut terminal, state, &app.active_theme, &subtitle)?;
        if !state.cancelled {
            if let Some(theme) = state.picked().first() {
                selections.theme = Some(theme.clone());
                app.theme = theme.clone();
                let (active, _) = crate::theme::resolve(&app.theme, false);
                app.active_theme = active;
            }
        }
    }

    // 2. Project directory
    let input = InputState::new("Target project directory", "/tmp/agentic-project");
    let input = run_input(&mut terminal, input, &app.active_theme, &subtitle)?;
    if input.cancelled {
        drop(_guard);
        ui::error(app, "Directory input canceled");
        return Err(crate::exit1());
    }
    selections.project_dir = input.result();

    // 3. Agent OS multi-select
    let state = SelectState::new("Select Agent OS target(s):", app.kb.agentos_choices(), true);
    let state = run_select(&mut terminal, state, &app.active_theme, &subtitle)?;
    selections.agent_os = state.picked();

    // 4. MCP servers with detections
    let detected =
        mcp::detect_configured_mcps(std::path::Path::new(&selections.project_dir), &app.home);
    let mut mcp_options: Vec<String> = vec![mcp::MCP_NONE_OPTION.to_string()];
    let mut preselected: Vec<String> = Vec::new();
    for id in mcp::MCP_REGISTRY_IDS {
        let row = format!("{id:<20} {}", mcp::mcp_description(id));
        if detected.iter().any(|d| d == id) {
            preselected.push(row.clone());
        }
        mcp_options.push(row);
    }
    let mut state = SelectState::new("Select MCP servers to enable:", mcp_options, true);
    state.preselect(&preselected);
    let state = run_select(&mut terminal, state, &app.active_theme, &subtitle)?;
    let picked = state.picked();
    if picked.is_empty() && !detected.is_empty() {
        selections.mcps = detected;
    } else {
        for row in picked {
            if row == mcp::MCP_NONE_OPTION {
                selections.mcps.clear();
                selections.clear_mcps = true;
                break;
            }
            let id = mcp::mcp_id_from_display_row(&row);
            if !id.is_empty() {
                selections.mcps.push(id);
            }
        }
    }

    // 5. Areas
    let state = SelectState::new("Select area(s):", app.kb.list_areas(), true);
    let state = run_select(&mut terminal, state, &app.active_theme, &subtitle)?;
    selections.areas = state.picked();
    let areas = if selections.areas.is_empty() {
        vec!["software".to_string()]
    } else {
        selections.areas.clone()
    };

    // 6. Per-area specializations
    for area in &areas {
        let state = SelectState::new(
            &format!("Select specialization(s) for '{area}':"),
            app.kb.list_specs(area),
            true,
        );
        let state = run_select(&mut terminal, state, &app.active_theme, &subtitle)?;
        let chosen = state.picked();
        if chosen.is_empty() {
            drop(_guard);
            ui::error(app, &format!("No specialization selected for {area}"));
            return Err(crate::exit1());
        }
        for spec in chosen {
            selections.specs.push(format!("{area}.{spec}"));
        }
    }

    Ok(selections)
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;

    #[test]
    fn select_state_multi_toggles() {
        let mut state = SelectState::new("t", vec!["a".into(), "b".into(), "c".into()], true);
        state.handle_key(KeyCode::Char(' '));
        state.handle_key(KeyCode::Down);
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.picked(), vec!["a", "b"]);
        assert_eq!(state.cursor, 2);
        state.handle_key(KeyCode::Enter);
        assert!(state.done);
    }

    #[test]
    fn select_state_single_picks_cursor() {
        let mut state = SelectState::new("t", vec!["x".into(), "y".into()], false);
        state.handle_key(KeyCode::Down);
        state.handle_key(KeyCode::Enter);
        assert_eq!(state.picked(), vec!["y"]);
    }

    #[test]
    fn select_state_cursor_wraps() {
        let mut state = SelectState::new("t", vec!["x".into(), "y".into()], false);
        state.handle_key(KeyCode::Up);
        assert_eq!(state.cursor, 1);
        state.handle_key(KeyCode::Down);
        assert_eq!(state.cursor, 0);
    }

    #[test]
    fn select_state_esc_cancels() {
        let mut state = SelectState::new("t", vec!["x".into()], true);
        state.handle_key(KeyCode::Char(' '));
        state.handle_key(KeyCode::Esc);
        assert!(state.done);
        assert!(state.cancelled);
        assert!(state.picked().is_empty());
    }

    #[test]
    fn preselect_marks_detected() {
        let mut state = SelectState::new("t", vec!["a".into(), "b".into()], true);
        state.preselect(&["b".to_string()]);
        state.handle_key(KeyCode::Enter);
        assert_eq!(state.picked(), vec!["b"]);
    }

    #[test]
    fn input_state_editing() {
        let mut state = InputState::new("dir", "/tmp/default");
        for c in "/opt/x".chars() {
            state.handle_key(KeyCode::Char(c));
        }
        state.handle_key(KeyCode::Backspace);
        state.handle_key(KeyCode::Enter);
        assert!(state.done);
        assert_eq!(state.result(), "/opt/");

        let mut empty = InputState::new("dir", "/tmp/default");
        empty.handle_key(KeyCode::Enter);
        assert_eq!(empty.result(), "/tmp/default");

        let mut cancelled = InputState::new("dir", "/tmp/default");
        cancelled.handle_key(KeyCode::Esc);
        assert!(cancelled.cancelled);
    }

    #[test]
    fn render_select_draws_checkboxes_and_banner() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = SelectState::new(
            "Select MCP servers to enable:",
            vec!["[ ] context7".into(), "[x] mempalace".into()],
            true,
        );
        state.selected[1] = true;
        terminal
            .draw(|f| render_select(f, &state, "dark", "Agentic installer (TUI mode) v1.0.0"))
            .unwrap();
        let buffer = terminal.backend().buffer().clone();
        let content: String = buffer
            .content()
            .iter()
            .map(|c| c.symbol().to_string())
            .collect();
        assert!(content.contains("Select MCP servers to enable:"));
        assert!(content.contains("AGENTIC") || content.contains("_"));
        assert!(content.contains("[x]"));
    }

    #[test]
    fn apply_selections_defaults_and_mcps() {
        let mut app = App::new().unwrap();
        let selections = WizardSelections {
            theme: Some("light".to_string()),
            project_dir: "/tmp/p".to_string(),
            agent_os: vec![],
            mcps: vec![
                "context7".to_string(),
                "mempalace".to_string(),
                "bogus".to_string(),
            ],
            clear_mcps: false,
            areas: vec![],
            specs: vec!["software.backend".to_string()],
        };
        apply_selections(&mut app, selections);
        assert_eq!(app.theme, "light");
        assert_eq!(app.selected_agent_os, vec!["default"]);
        assert_eq!(app.selected_areas, vec!["software"]);
        assert_eq!(app.selected_mcps, vec!["context7", "mempalace"]);
        assert_eq!(app.enable_context7_env.as_deref(), Some("y"));
        assert_eq!(app.enable_mempalace_env.as_deref(), Some("y"));
        assert_eq!(app.selected_specs, vec!["software.backend"]);
    }

    #[test]
    fn apply_selections_explicit_values() {
        let mut app = App::new().unwrap();
        let selections = WizardSelections {
            theme: None,
            project_dir: "/tmp/p".to_string(),
            agent_os: vec!["opencode".to_string()],
            mcps: vec![],
            clear_mcps: true,
            areas: vec!["devops".to_string()],
            specs: vec!["devops.sre".to_string()],
        };
        apply_selections(&mut app, selections);
        assert_eq!(app.selected_agent_os, vec!["opencode"]);
        assert_eq!(app.selected_areas, vec!["devops"]);
        assert!(app.selected_mcps.is_empty());
        assert_eq!(app.enable_context7_env.as_deref(), Some("n"));
    }

    #[test]
    fn render_input_draws_default_hint() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let state = InputState::new("Target project directory", "/tmp/agentic-project");
        terminal
            .draw(|f| render_input(f, &state, "light", "subtitle"))
            .unwrap();
        let buffer = terminal.backend().buffer().clone();
        let content: String = buffer
            .content()
            .iter()
            .map(|c| c.symbol().to_string())
            .collect();
        assert!(content.contains("Target project directory"));
        assert!(content.contains("/tmp/agentic-project"));
    }
}
