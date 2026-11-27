//! Fullscreen ratatui wizard for `agentic tui` (and no-args interactive runs).
//! The flow: theme -> project dir -> agent OS -> role profiles -> MCP servers and JEV (with detection
//! checkboxes) -> Skills (one skill pack) -> issue tracker (pocock only) -> areas -> per-area specs ->
//! company rules -> install.

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
use std::collections::BTreeMap;

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
    /// Optional hint per option, shown in the footer for the row under the cursor.
    pub hints: Vec<String>,
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
            hints: Vec::new(),
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
    pub masked: bool,
}

impl InputState {
    pub fn new(title: &str, default: &str) -> InputState {
        InputState {
            title: title.to_string(),
            default: default.to_string(),
            value: String::new(),
            done: false,
            cancelled: false,
            masked: false,
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
    let footer = state
        .hints
        .get(state.cursor)
        .filter(|h| !h.is_empty())
        .map_or(help, String::as_str);
    frame.render_widget(Paragraph::new(Span::styled(footer, dim)), chunks[2]);
}

pub fn render_input(frame: &mut Frame, state: &InputState, active_theme: &str, subtitle: &str) {
    let palette = theme_style(active_theme);
    fill_background(frame, palette.base);
    let chunks = layout_chunks(frame.area());
    render_banner(frame, chunks[0], active_theme, subtitle);
    let (header, dim) = (palette.header, palette.dim);
    let shown = format!(
        "{}▏",
        if state.masked {
            "•".repeat(state.value.chars().count())
        } else {
            state.value.clone()
        }
    );
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
            if state.masked {
                "Enter key and press Enter to save • Esc to cancel"
            } else {
                "Type path and press Enter to confirm • Esc to cancel"
            },
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

/// The next key of a screen with the title `title`; None on Ctrl-C. The wizard tests script it.
pub type Keys<'a> = dyn FnMut(&str) -> crate::Result<Option<KeyCode>> + 'a;

fn terminal_keys(_title: &str) -> crate::Result<Option<KeyCode>> {
    wait_key()
}

fn run_select<B: Backend>(
    terminal: &mut Terminal<B>,
    state: SelectState,
    active_theme: &str,
    subtitle: &str,
) -> crate::Result<SelectState> {
    run_select_with(terminal, state, active_theme, subtitle, &mut terminal_keys)
}

fn run_select_with<B: Backend>(
    terminal: &mut Terminal<B>,
    mut state: SelectState,
    active_theme: &str,
    subtitle: &str,
    keys: &mut Keys,
) -> crate::Result<SelectState> {
    while !state.done {
        terminal.draw(|frame| render_select(frame, &state, active_theme, subtitle))?;
        match keys(&state.title)? {
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
    state: InputState,
    active_theme: &str,
    subtitle: &str,
) -> crate::Result<InputState> {
    run_input_with(terminal, state, active_theme, subtitle, &mut terminal_keys)
}

fn run_input_with<B: Backend>(
    terminal: &mut Terminal<B>,
    mut state: InputState,
    active_theme: &str,
    subtitle: &str,
    keys: &mut Keys,
) -> crate::Result<InputState> {
    while !state.done {
        terminal.draw(|frame| render_input(frame, &state, active_theme, subtitle))?;
        match keys(&state.title)? {
            Some(code) => state.handle_key(code),
            None => {
                state.cancelled = true;
                state.done = true;
            }
        }
    }
    Ok(state)
}

/// The wizard screens on one terminal with one key source.
struct Screens<'a, 'k, B: Backend> {
    terminal: &'a mut Terminal<B>,
    theme: String,
    subtitle: String,
    keys: &'a mut Keys<'k>,
}

impl<B: Backend> Screens<'_, '_, B> {
    fn select(&mut self, state: SelectState) -> crate::Result<SelectState> {
        run_select_with(self.terminal, state, &self.theme, &self.subtitle, self.keys)
    }

    fn input(&mut self, state: InputState) -> crate::Result<InputState> {
        run_input_with(self.terminal, state, &self.theme, &self.subtitle, self.keys)
    }
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

pub fn screen_secret_input(app: &App, title: &str) -> Option<String> {
    let _guard = TerminalGuard::enter().ok()?;
    let backend = ratatui::backend::CrosstermBackend::new(std::io::stdout());
    let mut terminal = Terminal::new(backend).ok()?;
    let mut state = InputState::new(title, "");
    state.masked = true;
    let state = run_input(&mut terminal, state, &app.active_theme, &wizard_subtitle()).ok()?;
    if state.cancelled {
        None
    } else {
        Some(state.result())
    }
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
    /// Role profile id per host (crate::profile::HOSTS); empty keeps the default.
    pub profiles: std::collections::BTreeMap<String, String>,
    /// Company rules from the optional "Company rules" step; None keeps the feature off.
    pub company_rules: Option<crate::company::CompanyRules>,
    /// The complete pack list after the "Skills" step (one pack, none, or the saved packs).
    pub skill_packs: Vec<crate::skill_packs::SkillPack>,
    /// Issue tracker of the preset `pocock` setup; None keeps the saved one or `local`.
    pub issue_tracker: Option<String>,
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
    for id in &selections.mcps {
        mcp::add_selected_mcp(app, id);
    }
    app.jev_enabled = Some(app.selected_mcp_contains("jev"));
    mcp::sync_legacy_mcp_env_from_selected(app);
    app.selected_areas = if selections.areas.is_empty() {
        vec!["software".to_string()]
    } else {
        selections.areas
    };
    app.selected_specs = selections.specs;
    app.host_profiles = selections.profiles;
    app.company_rules = selections.company_rules;
    app.skill_packs = selections.skill_packs;
    // The "Skills" step gives the complete list: the install does not add the saved packs back, and
    // it removes the files of packs that are gone.
    app.skill_packs_replace = true;
    if selections.issue_tracker.is_some() {
        app.issue_tracker = selections.issue_tracker;
    }
    // One shared choice is also the install-wide profile; mixed choices stay per host.
    let mut ids: Vec<&String> = app.host_profiles.values().collect();
    ids.dedup();
    if let [id] = ids.as_slice() {
        app.install_profile = (*id).clone();
    }
}

/// Role profile select of one host: `(prompt, ids, labels)`. The cursor starts on the current choice.
pub fn profile_step(app: &App, host: &str) -> (String, Vec<String>, Vec<String>) {
    let options = crate::profile::options(app, host);
    let current = crate::profile::id_for(app, host);
    let mut ids: Vec<String> = options.iter().map(|(id, _)| id.clone()).collect();
    let mut labels: Vec<String> = options.into_iter().map(|(_, label)| label).collect();
    if let Some(pos) = ids.iter().position(|id| *id == current) {
        ids.swap(0, pos);
        labels.swap(0, pos);
    }
    (format!("Select role profile for {host}:"), ids, labels)
}

fn run_wizard_screens(app: &mut App) -> crate::Result<WizardSelections> {
    // GitHub answers while the user goes through the steps before "Skills".
    let stars = crate::github_stars::Prefetch::start(app);
    let guard = TerminalGuard::enter()?;
    let backend = ratatui::backend::CrosstermBackend::new(std::io::stdout());
    let mut terminal = Terminal::new(backend)?;
    let result = wizard_steps(
        app,
        &mut terminal,
        &mut terminal_keys,
        Box::new(move || stars.wait()),
    )?;
    drop(guard);
    result.map_err(|e| {
        ui::error(app, &e);
        crate::exit1()
    })
}

/// The wizard steps; `Ok(Err(message))` stops the wizard with that error. `stars` gives the star
/// counts of the presets when the "Skills" step opens.
fn wizard_steps<B: Backend>(
    app: &mut App,
    terminal: &mut Terminal<B>,
    keys: &mut Keys,
    stars: Box<dyn FnOnce() -> BTreeMap<String, crate::github_stars::Stars> + '_>,
) -> crate::Result<Result<WizardSelections, String>> {
    let mut screens = Screens {
        terminal,
        theme: app.active_theme.clone(),
        subtitle: format!("{} {}", crate::APP_TUI_TITLE, crate::app_version_label()),
        keys,
    };
    let mut selections = WizardSelections::default();

    // 1. Theme picker (skipped when explicit or loaded from config)
    if !app.theme_explicit && !app.theme_loaded_from_config {
        let state = SelectState::new(
            "Select interface theme:",
            crate::THEME_CHOICES.iter().map(|s| s.to_string()).collect(),
            false,
        );
        let state = screens.select(state)?;
        if !state.cancelled {
            if let Some(theme) = state.picked().first() {
                selections.theme = Some(theme.clone());
                app.theme = theme.clone();
                let (active, _) = crate::theme::resolve(&app.theme, false);
                app.active_theme = active;
                screens.theme = app.active_theme.clone();
            }
        }
    }

    // 2. Project directory
    let input = InputState::new("Target project directory", "/tmp/agentic-project");
    let input = screens.input(input)?;
    if input.cancelled {
        return Ok(Err("Directory input canceled".into()));
    }
    selections.project_dir = input.result();

    // 3. Agent OS multi-select
    let state = SelectState::new("Select Agent OS target(s):", app.kb.agentos_choices(), true);
    let state = screens.select(state)?;
    selections.agent_os = state.picked();

    // 3b. Role profile per selected host
    for host in crate::profile::HOSTS {
        if !selections.agent_os.iter().any(|a| a == host) {
            continue;
        }
        if !app.dry_run {
            let _ = crate::profile::seed(app, host);
        }
        let (prompt, ids, labels) = profile_step(app, host);
        let state = SelectState::new(&prompt, labels.clone(), false);
        let state = screens.select(state)?;
        let picked = state.picked();
        if let Some(index) = picked
            .first()
            .and_then(|label| labels.iter().position(|l| l == label))
        {
            selections
                .profiles
                .insert(host.to_string(), ids[index].clone());
        }
    }

    // 4. MCP servers with detections (JEV is chosen here)
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
    let mut state = SelectState::new("Select integrations (MCP / skills):", mcp_options, true);
    state.preselect(&preselected);
    let state = screens.select(state)?;
    let picked = state.picked();
    if state.cancelled {
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

    // 4b. Skills: one skill pack (single select) right below the JEV choice.
    let saved_packs = saved_skill_packs(&selections.project_dir);
    let (state, choices) = skills_step(&saved_packs, &stars());
    let state = screens.select(state)?;
    let choice = if state.cancelled {
        SkillsChoice::Keep
    } else {
        state
            .options
            .iter()
            .position(|o| state.picked().first() == Some(o))
            .map(|i| choices[i].clone())
            .unwrap_or(SkillsChoice::Keep)
    };
    let custom = if choice == SkillsChoice::Custom {
        let input = screens.input(InputState::new(
            "Custom skill pack: <url>[#ref][:skills_root] or directory (empty = keep)",
            "",
        ))?;
        if input.cancelled {
            String::new()
        } else {
            input.result()
        }
    } else {
        String::new()
    };
    selections.skill_packs = match skills_selection(saved_packs, &choice, &custom) {
        Ok(packs) => packs,
        Err(e) => return Ok(Err(e)),
    };

    // 4c. Issue tracker of the preset `pocock` setup (only when that preset is chosen).
    if selections
        .skill_packs
        .iter()
        .any(|p| p.preset == crate::pocock_setup::PACK_ID)
    {
        let saved = app
            .issue_tracker
            .clone()
            .or_else(|| saved_issue_tracker(&selections.project_dir));
        let state = issue_tracker_state(saved.as_deref());
        let state = screens.select(state)?;
        if !state.cancelled {
            selections.issue_tracker = state.picked().first().cloned();
        }
    }

    // 5. Areas
    let state = SelectState::new("Select area(s):", app.kb.list_areas(), true);
    let state = screens.select(state)?;
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
        let state = screens.select(state)?;
        let chosen = state.picked();
        if chosen.is_empty() {
            return Ok(Err(format!("No specialization selected for {area}")));
        }
        for spec in chosen {
            selections.specs.push(format!("{area}.{spec}"));
        }
    }

    // 7. Company rules (optional): a directory and/or a git repository.
    let saved = saved_company_rules(&selections.project_dir);
    let (path_default, git_default) = company_defaults(saved.as_ref());
    let path = screens.input(InputState::new(
        "Company rules: directory (relative to the project or absolute; empty = none)",
        &path_default,
    ))?;
    let git = screens.input(InputState::new(
        "Company rules: git repository <url>[#ref][:subdir] (empty = none)",
        &git_default,
    ))?;
    let path = if path.cancelled {
        String::new()
    } else {
        path.result()
    };
    let git = if git.cancelled {
        String::new()
    } else {
        git.result()
    };
    selections.company_rules = match company_selection(saved, &path, &git) {
        Ok(rules) => rules,
        Err(e) => return Ok(Err(e)),
    };

    Ok(Ok(selections))
}

/// One row of the "Skills" step.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SkillsChoice {
    /// The saved packs stay as they are (also Esc).
    Keep,
    /// No skill pack: the saved packs are removed.
    None,
    /// The preset with this id replaces the saved packs.
    Preset(&'static str),
    /// A source from the text input replaces the saved packs.
    Custom,
}

pub const SKILLS_TITLE: &str = "Skills: one skill pack (Enter selects, Esc keeps the saved one):";
pub const SKILLS_CUSTOM_ROW: &str = "Custom source… (git URL or directory)";

/// `mattpocock/skills · 21 skills · MIT · ★ 333.8k`; the summary is the hint line of the row.
pub fn preset_row(
    preset: &crate::skill_packs::Preset,
    stars: Option<&crate::github_stars::Stars>,
) -> String {
    let mut row = format!(
        "{} · {} skills · {}",
        preset.repo,
        preset.select.len(),
        preset.license
    );
    let stars = stars.cloned().unwrap_or(crate::github_stars::Stars {
        count: preset.stars,
        date: Some(preset.stars_date.to_string()),
    });
    row.push_str(" · ");
    row.push_str(&stars.label());
    row
}

/// The single-select "Skills" step and the choice of each row. Rows: `Keep saved: …` (only for saved
/// packs that are not one preset), `None`, the presets, `Custom source…`. The cursor starts on the
/// saved choice, so Enter keeps it.
pub fn skills_step(
    saved: &[crate::skill_packs::SkillPack],
    stars: &BTreeMap<String, crate::github_stars::Stars>,
) -> (SelectState, Vec<SkillsChoice>) {
    let saved_preset = match saved {
        [one] if crate::skill_packs::preset(&one.preset).is_some() => Some(one.preset.as_str()),
        _ => None,
    };
    let mut rows = Vec::new();
    let mut hints = Vec::new();
    let mut choices = Vec::new();
    if !saved.is_empty() && saved_preset.is_none() {
        let names: Vec<String> = saved
            .iter()
            .map(|p| format!("{} ({})", p.id, crate::source::source_id(&p.source)))
            .collect();
        rows.push(format!("Keep saved: {}", names.join(", ")));
        hints.push("Keep the saved skill packs unchanged".to_string());
        choices.push(SkillsChoice::Keep);
    }
    if saved.is_empty() {
        rows.push("None".to_string());
        hints.push("No skill pack".to_string());
    } else {
        rows.push("None (remove the saved pack)".to_string());
        hints.push("Remove the saved skill pack and its files".to_string());
    }
    choices.push(SkillsChoice::None);
    for preset in crate::skill_packs::PRESETS {
        let mut row = preset_row(preset, stars.get(preset.id));
        if saved_preset == Some(preset.id) {
            row.push_str(" · saved");
        }
        rows.push(row);
        hints.push(format!("{}: {}", preset.repo, preset.summary));
        choices.push(SkillsChoice::Preset(preset.id));
    }
    rows.push(SKILLS_CUSTOM_ROW.to_string());
    hints.push("A git spec <url>[#ref][:skills_root], a directory, or a preset id".to_string());
    choices.push(SkillsChoice::Custom);
    let mut state = SelectState::new(SKILLS_TITLE, rows, false);
    state.hints = hints;
    state.cursor = choices
        .iter()
        .position(|c| match (c, saved_preset) {
            (SkillsChoice::Preset(id), Some(saved)) => *id == saved,
            (SkillsChoice::Keep, None) => true,
            _ => false,
        })
        .unwrap_or_default();
    (state, choices)
}

/// The packs after the "Skills" step: one pack at most, unless the saved packs stay. The saved entry of
/// the chosen pack keeps its lock and overrides; every other saved pack goes (the install removes its
/// files). An empty custom source keeps the saved packs.
pub fn skills_selection(
    saved: Vec<crate::skill_packs::SkillPack>,
    choice: &SkillsChoice,
    custom: &str,
) -> Result<Vec<crate::skill_packs::SkillPack>, String> {
    use crate::skill_packs::{parse_spec, upsert};
    let pick = |pack: crate::skill_packs::SkillPack, saved: Vec<crate::skill_packs::SkillPack>| {
        let mut out: Vec<_> = saved.into_iter().filter(|p| p.id == pack.id).collect();
        upsert(&mut out, pack);
        out
    };
    Ok(match choice {
        SkillsChoice::Keep => saved,
        SkillsChoice::None => Vec::new(),
        SkillsChoice::Preset(id) => match saved.iter().find(|p| p.preset == *id) {
            Some(own) => vec![own.clone()],
            None => pick(parse_spec(id)?, saved),
        },
        SkillsChoice::Custom if custom.trim().is_empty() => saved,
        SkillsChoice::Custom => pick(parse_spec(custom)?, saved),
    })
}

/// The tracker step with the cursor on the saved choice (`local` without one), so Enter keeps it.
pub fn issue_tracker_state(saved: Option<&str>) -> SelectState {
    let options: Vec<String> = crate::pocock_setup::TRACKERS
        .iter()
        .map(|s| s.to_string())
        .collect();
    let wanted = saved
        .filter(|t| crate::pocock_setup::TRACKERS.contains(t))
        .unwrap_or(crate::pocock_setup::DEFAULT_TRACKER);
    let mut state = SelectState::new("Issue tracker for the pocock skills:", options, false);
    state.cursor = state
        .options
        .iter()
        .position(|o| o == wanted)
        .unwrap_or_default();
    state
}

fn saved_issue_tracker(project_dir: &str) -> Option<String> {
    let path = std::path::Path::new(project_dir).join(crate::PROJECT_MANIFEST_NAME);
    let data: serde_json::Value = serde_json::from_slice(&std::fs::read(path).ok()?).ok()?;
    data["settings"]["issue_tracker"]
        .as_str()
        .map(str::to_string)
}

fn saved_skill_packs(project_dir: &str) -> Vec<crate::skill_packs::SkillPack> {
    let path = std::path::Path::new(project_dir).join(crate::PROJECT_MANIFEST_NAME);
    std::fs::read(path)
        .ok()
        .and_then(|bytes| serde_json::from_slice::<serde_json::Value>(&bytes).ok())
        .and_then(|data| crate::skill_packs::from_settings(&data["settings"]["skill_packs"]))
        .unwrap_or_default()
}

fn saved_company_rules(project_dir: &str) -> Option<crate::company::CompanyRules> {
    let path = std::path::Path::new(project_dir).join(crate::PROJECT_MANIFEST_NAME);
    let data: serde_json::Value = serde_json::from_slice(&std::fs::read(path).ok()?).ok()?;
    crate::company::from_settings(&data["settings"]["company_rules"])
}

/// Input defaults: the first saved path source and the first saved git source.
pub fn company_defaults(saved: Option<&crate::company::CompanyRules>) -> (String, String) {
    use crate::company::Source;
    let sources = saved.map(|s| s.sources.as_slice()).unwrap_or_default();
    let path = sources.iter().find_map(|s| match s {
        Source::Path(p) => Some(p.clone()),
        _ => None,
    });
    let git = sources.iter().find_map(|s| match s {
        Source::Git {
            url,
            git_ref,
            subdir,
        } => Some(match (git_ref.is_empty(), subdir.is_empty()) {
            (true, true) => url.clone(),
            (false, true) => format!("{url}#{git_ref}"),
            _ => format!("{url}#{git_ref}:{subdir}"),
        }),
        _ => None,
    });
    (path.unwrap_or_default(), git.unwrap_or_default())
}

/// The step answers replace the saved sources; the saved `exclude` list stays.
pub fn company_selection(
    saved: Option<crate::company::CompanyRules>,
    path: &str,
    git: &str,
) -> Result<Option<crate::company::CompanyRules>, String> {
    let mut rules = crate::company::CompanyRules {
        sources: Vec::new(),
        exclude: saved.map(|s| s.exclude).unwrap_or_default(),
    };
    if !path.trim().is_empty() {
        rules
            .sources
            .push(crate::company::Source::Path(path.trim().to_string()));
    }
    if !git.trim().is_empty() {
        rules.sources.push(crate::company::parse_git_spec(git)?);
    }
    Ok((!rules.is_empty()).then_some(rules))
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
    fn issue_tracker_step_keeps_the_saved_choice() {
        // Without a preselect, Enter reset a saved `github` or `gitlab` to `local`.
        for (saved, want) in [
            (Some("github"), "github"),
            (Some("gitlab"), "gitlab"),
            (Some("local"), "local"),
            (None, "local"),
            (Some("jira"), "local"),
        ] {
            let mut state = issue_tracker_state(saved);
            state.handle_key(KeyCode::Enter);
            assert_eq!(state.picked(), vec![want.to_string()], "{saved:?}");
        }
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
            vec!["[ ] context7".into(), "[x] playwright".into()],
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
                "playwright".to_string(),
                "bogus".to_string(),
            ],
            clear_mcps: false,
            areas: vec![],
            specs: vec!["software.backend".to_string()],
            profiles: Default::default(),
            company_rules: None,
            skill_packs: vec![],
            issue_tracker: None,
        };
        apply_selections(&mut app, selections);
        assert_eq!(app.theme, "light");
        assert_eq!(app.selected_agent_os, vec!["default"]);
        assert_eq!(app.selected_areas, vec!["software"]);
        assert_eq!(app.selected_mcps, vec!["context7", "playwright"]);
        assert_eq!(app.enable_context7_env.as_deref(), Some("y"));
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
            profiles: Default::default(),
            company_rules: None,
            skill_packs: vec![],
            issue_tracker: None,
        };
        apply_selections(&mut app, selections);
        assert_eq!(app.selected_agent_os, vec!["opencode"]);
        assert_eq!(app.selected_areas, vec!["devops"]);
        assert!(app.selected_mcps.is_empty());
        assert_eq!(app.enable_context7_env.as_deref(), Some("n"));
        assert_eq!(app.jev_enabled, Some(false));
    }

    fn rendered(state: &SelectState) -> String {
        let mut terminal = Terminal::new(TestBackend::new(140, 30)).unwrap();
        terminal
            .draw(|f| render_select(f, state, "dark", "test"))
            .unwrap();
        let buffer = terminal.backend().buffer().clone();
        let mut out = String::new();
        for y in 0..buffer.area.height {
            for x in 0..buffer.area.width {
                out.push_str(buffer[(x, y)].symbol());
            }
            out.push('\n');
        }
        out
    }

    fn saved_preset(id: &str) -> crate::skill_packs::SkillPack {
        let mut pack = crate::skill_packs::parse_spec(id).unwrap();
        pack.commit = "a".repeat(40);
        pack
    }

    #[test]
    fn skills_step_lists_none_presets_and_custom() {
        let stars: BTreeMap<String, crate::github_stars::Stars> = [(
            "pocock".to_string(),
            crate::github_stars::Stars {
                count: 333_841,
                date: None,
            },
        )]
        .into();
        let (state, choices) = skills_step(&[], &stars);
        assert_eq!(
            choices,
            vec![
                SkillsChoice::None,
                SkillsChoice::Preset("pocock"),
                SkillsChoice::Preset("superpowers"),
                SkillsChoice::Preset("anthropic"),
                SkillsChoice::Custom,
            ]
        );
        assert_eq!(state.cursor, 0);
        assert!(!state.multi);
        assert_eq!(state.options[0], "None");
        assert_eq!(
            state.options[1],
            "mattpocock/skills · 21 skills · MIT · ★ 333.8k"
        );
        assert_eq!(
            state.options[2],
            "obra/superpowers · 13 skills · MIT · ★ 327.8k (2026-11-27)"
        );
        assert_eq!(
            state.options[3],
            "anthropics/skills · 8 skills · Apache-2.0 · ★ 201.2k (2026-11-27)"
        );
        assert_eq!(state.options[4], SKILLS_CUSTOM_ROW);
        assert_eq!(
            state.hints[1],
            "mattpocock/skills: grilling, spec, tickets, TDD, ADR"
        );
        let mut on_superpowers = state.clone();
        on_superpowers.cursor = 2;
        let screen = rendered(&on_superpowers);
        assert!(screen.contains("Skills: one skill pack"), "{screen}");
        assert!(
            screen.contains("obra/superpowers: brainstorm, plans, TDD, debugging, code review"),
            "hint line: {screen}"
        );
    }

    /// Longest row that an 80-column terminal shows whole: borders and the `> ` cursor take 4 columns.
    const SKILLS_ROW_MAX: usize = 76;

    #[test]
    fn skills_rows_fit_80_columns() {
        // The longest case: dated stars with seven digits and the `saved` mark on every preset.
        let old: BTreeMap<String, crate::github_stars::Stars> = crate::skill_packs::PRESETS
            .iter()
            .map(|p| {
                let stars = crate::github_stars::Stars {
                    count: 9_999_999,
                    date: Some("2026-11-27".into()),
                };
                (p.id.to_string(), stars)
            })
            .collect();
        for preset in crate::skill_packs::PRESETS {
            let saved = vec![saved_preset(preset.id)];
            let (state, _) = skills_step(&saved, &old);
            for row in &state.options {
                assert!(
                    row.chars().count() <= SKILLS_ROW_MAX,
                    "{} > {SKILLS_ROW_MAX}: {row}",
                    row.chars().count()
                );
            }
            assert!(state.title.chars().count() <= 78, "{}", state.title);
            for hint in &state.hints {
                assert!(hint.chars().count() <= 80, "{hint}");
            }
            // Rendered at 80 columns, every row ends inside the frame.
            let mut terminal = Terminal::new(TestBackend::new(80, 24)).unwrap();
            terminal
                .draw(|f| render_select(f, &state, "dark", "test"))
                .unwrap();
            let buffer = terminal.backend().buffer().clone();
            let lines: Vec<String> = (0..24)
                .map(|y| (0..80).map(|x| buffer[(x, y)].symbol()).collect())
                .collect();
            for row in &state.options {
                assert!(lines.iter().any(|l| l.contains(row.as_str())), "cut: {row}");
            }
        }
    }

    #[test]
    fn skills_step_preselects_the_saved_pack() {
        let none = BTreeMap::new();
        // One saved preset: its row carries the cursor and the `saved` mark; Enter keeps its lock.
        let saved = vec![saved_preset("superpowers")];
        let (mut state, choices) = skills_step(&saved, &none);
        assert_eq!(choices[state.cursor], SkillsChoice::Preset("superpowers"));
        assert!(state.options[state.cursor].ends_with(" · saved"));
        assert_eq!(state.options[0], "None (remove the saved pack)");
        state.handle_key(KeyCode::Enter);
        let picked = skills_selection(saved.clone(), &choices[state.cursor], "").unwrap();
        assert_eq!(picked, saved);
        // A saved pack from a URL: a `Keep saved` row comes first and is the default.
        let custom =
            vec![
                crate::skill_packs::parse_spec("https://git.example.com/team/skills.git").unwrap(),
            ];
        let (state, choices) = skills_step(&custom, &none);
        assert_eq!(state.cursor, 0);
        assert_eq!(choices[0], SkillsChoice::Keep);
        assert!(state.options[0].starts_with("Keep saved: team-skills ("));
        assert_eq!(choices.len(), 6);
        // A preset with a user id is still that preset.
        let mut renamed = saved_preset("pocock");
        renamed.id = "mp".into();
        let (state, choices) = skills_step(&[renamed], &none);
        assert_eq!(choices[state.cursor], SkillsChoice::Preset("pocock"));
    }

    #[test]
    fn skills_selection_is_single_and_replaces_the_saved_pack() {
        let saved = vec![saved_preset("pocock")];
        assert_eq!(
            skills_selection(saved.clone(), &SkillsChoice::Keep, "").unwrap(),
            saved
        );
        assert!(skills_selection(saved.clone(), &SkillsChoice::None, "")
            .unwrap()
            .is_empty());
        let other =
            skills_selection(saved.clone(), &SkillsChoice::Preset("anthropic"), "").unwrap();
        assert_eq!(other.len(), 1);
        assert_eq!(other[0].preset, "anthropic");
        assert!(other[0].commit.is_empty(), "a new pack has no lock yet");
        // Custom source: replaces; empty keeps; invalid stops with the error.
        let custom = skills_selection(
            saved.clone(),
            &SkillsChoice::Custom,
            "https://github.com/obra/superpowers#main",
        )
        .unwrap();
        let ids: Vec<&str> = custom.iter().map(|p| p.id.as_str()).collect();
        assert_eq!(ids, vec!["obra-superpowers"]);
        assert_eq!(
            skills_selection(saved.clone(), &SkillsChoice::Custom, " ").unwrap(),
            saved
        );
        assert!(skills_selection(
            saved.clone(),
            &SkillsChoice::Custom,
            "https://x.example.com/a.git#m:../up"
        )
        .is_err());
        // A typed preset id is the preset; several saved packs become one.
        let many = vec![
            saved_preset("pocock"),
            crate::skill_packs::parse_spec("vendor/skills").unwrap(),
        ];
        let one = skills_selection(many, &SkillsChoice::Custom, "superpowers").unwrap();
        assert_eq!(one.len(), 1);
        assert_eq!(one[0].preset, "superpowers");
        let mut app = App::new().unwrap();
        apply_selections(
            &mut app,
            WizardSelections {
                skill_packs: one.clone(),
                ..Default::default()
            },
        );
        assert_eq!(app.skill_packs, one);
        assert!(
            app.skill_packs_replace,
            "the install must not add saved packs back"
        );
    }

    /// Drive the whole wizard with scripted keys; return the screen titles in order and the result.
    fn run_scripted(
        app: &mut App,
        project: &str,
        skills_keys: Vec<KeyCode>,
    ) -> (Vec<String>, Result<WizardSelections, String>) {
        let mut terminal = Terminal::new(TestBackend::new(160, 40)).unwrap();
        let mut titles: Vec<String> = Vec::new();
        let mut queue: std::collections::VecDeque<KeyCode> = Default::default();
        let mut keys = |title: &str| -> crate::Result<Option<KeyCode>> {
            if titles.last().map(String::as_str) != Some(title) {
                titles.push(title.to_string());
                queue.clear();
                if title == "Target project directory" {
                    queue.extend(project.chars().map(KeyCode::Char));
                } else if title == SKILLS_TITLE {
                    queue.extend(skills_keys.iter().copied());
                } else if title.starts_with("Select specialization(s)") {
                    queue.push_back(KeyCode::Char(' '));
                }
                queue.push_back(KeyCode::Enter);
            }
            Ok(Some(queue.pop_front().unwrap_or(KeyCode::Enter)))
        };
        let result = wizard_steps(app, &mut terminal, &mut keys, Box::new(BTreeMap::new)).unwrap();
        (titles, result)
    }

    fn wizard_app(home: &std::path::Path) -> App {
        let mut app = App::new().unwrap();
        app.home = home.to_path_buf();
        app.config_home_override = Some(home.join(".config"));
        app.theme_explicit = true;
        app.issue_tracker = None;
        app
    }

    #[test]
    fn wizard_puts_skills_right_below_the_jev_choice() {
        let home = tempfile::tempdir().unwrap();
        let project = tempfile::tempdir().unwrap();
        let dir = project.path().to_string_lossy().to_string();
        let mut app = wizard_app(home.path());
        // Down, Down: the second preset (superpowers).
        let (titles, result) = run_scripted(&mut app, &dir, vec![KeyCode::Down, KeyCode::Down]);
        let at = |t: &str| titles.iter().position(|x| x == t).unwrap();
        assert_eq!(
            at(SKILLS_TITLE),
            at("Select integrations (MCP / skills):") + 1
        );
        assert_eq!(
            at("Select area(s):"),
            at(SKILLS_TITLE) + 1,
            "no tracker step: {titles:?}"
        );
        assert!(
            !titles.iter().any(|t| t.starts_with("Skill pack:")),
            "old step is gone"
        );
        let selections = result.unwrap();
        assert_eq!(selections.project_dir, dir);
        assert_eq!(selections.skill_packs.len(), 1);
        assert_eq!(selections.skill_packs[0].preset, "superpowers");
        // pocock: the issue tracker step follows the Skills step.
        let mut app = wizard_app(home.path());
        let (titles, result) = run_scripted(&mut app, &dir, vec![KeyCode::Down]);
        assert_eq!(
            titles[titles.iter().position(|t| t == SKILLS_TITLE).unwrap() + 1],
            "Issue tracker for the pocock skills:"
        );
        assert_eq!(result.unwrap().skill_packs[0].preset, "pocock");
        // Custom source: the text input opens; Esc on the Skills step keeps the (empty) saved list.
        let mut app = wizard_app(home.path());
        let (titles, result) = run_scripted(&mut app, &dir, vec![KeyCode::Up]);
        assert!(
            titles.iter().any(|t| t.starts_with("Custom skill pack:")),
            "{titles:?}"
        );
        assert!(result.unwrap().skill_packs.is_empty());
        let mut app = wizard_app(home.path());
        let (_, result) = run_scripted(&mut app, &dir, vec![KeyCode::Down, KeyCode::Esc]);
        assert!(result.unwrap().skill_packs.is_empty());
    }

    #[test]
    fn tui_pack_change_replaces_and_none_removes_cleanly() {
        let home = tempfile::tempdir().unwrap();
        let project = tempfile::tempdir().unwrap();
        let src = tempfile::tempdir().unwrap();
        for (pack, skill) in [("a", "alpha"), ("b", "beta")] {
            let file = src
                .path()
                .join(pack)
                .join("skills")
                .join(skill)
                .join("SKILL.md");
            std::fs::create_dir_all(file.parent().unwrap()).unwrap();
            std::fs::write(
                &file,
                "---\nname: x\ndescription: A test skill.\n---\nBody.\n",
            )
            .unwrap();
        }
        let dir = project.path().to_string_lossy().to_string();
        let install_with = |choice: SkillsChoice, custom: &str| {
            let mut app = App::new().unwrap();
            app.home = home.path().to_path_buf();
            app.config_home_override = Some(home.path().join(".config"));
            app.interactive_override = Some(false);
            app.doctor_enabled_env = false;
            let packs = skills_selection(saved_skill_packs(&dir), &choice, custom).unwrap();
            apply_selections(
                &mut app,
                WizardSelections {
                    project_dir: dir.clone(),
                    agent_os: vec!["claude".into(), "codex".into(), "opencode".into()],
                    specs: vec!["software.general".into()],
                    skill_packs: packs,
                    ..Default::default()
                },
            );
            install::run_install(&mut app).unwrap();
        };
        let a = src.path().join("a").to_string_lossy().to_string();
        let b = src.path().join("b").to_string_lossy().to_string();
        install_with(SkillsChoice::Custom, &a);
        let skill = |name: &str| project.path().join(".claude/skills").join(name);
        assert!(skill("alpha").join("SKILL.md").is_file());
        install_with(SkillsChoice::Keep, "");
        assert!(skill("alpha").join("SKILL.md").is_file());
        install_with(SkillsChoice::Custom, &b);
        assert!(!skill("alpha").exists(), "the replaced pack is removed");
        assert!(skill("beta").join("SKILL.md").is_file());
        assert_eq!(saved_skill_packs(&dir).len(), 1);
        install_with(SkillsChoice::None, "");
        for host in [
            ".claude/skills",
            ".agents/skills",
            ".opencode/skills",
            ".agent/skills",
        ] {
            assert!(!project.path().join(host).join("beta").exists(), "{host}");
        }
        assert!(saved_skill_packs(&dir).is_empty());
    }

    #[test]
    fn company_step_replaces_sources_and_keeps_excludes() {
        use crate::company::{CompanyRules, Source};
        let saved = CompanyRules {
            sources: vec![
                Source::Path("rules".into()),
                crate::company::parse_git_spec("<url>#main:rules").unwrap(),
            ],
            exclude: vec!["software/backend/testing".into()],
        };
        assert_eq!(
            company_defaults(Some(&saved)),
            ("rules".to_string(), "<url>#main:rules".to_string())
        );
        assert_eq!(company_defaults(None), (String::new(), String::new()));
        let picked = company_selection(Some(saved.clone()), "", "<url>")
            .unwrap()
            .unwrap();
        assert_eq!(picked.sources.len(), 1);
        assert_eq!(picked.exclude, saved.exclude);
        assert!(company_selection(None, " ", "").unwrap().is_none());
        assert!(company_selection(None, "", "<url>#x:../up").is_err());
        let mut app = App::new().unwrap();
        apply_selections(
            &mut app,
            WizardSelections {
                company_rules: Some(picked.clone()),
                ..Default::default()
            },
        );
        assert_eq!(app.company_rules, Some(picked));
    }

    #[test]
    fn jev_selection_and_deselection_are_explicit() {
        let mut app = App::new().unwrap();
        let selections = WizardSelections {
            project_dir: "/tmp/jev-ui".into(),
            mcps: vec!["jev".into()],
            ..Default::default()
        };
        apply_selections(&mut app, selections);
        assert_eq!(app.jev_enabled, Some(true));
        assert!(app.selected_mcp_contains("jev"));
        let selections = WizardSelections {
            project_dir: "/tmp/jev-ui".into(),
            ..Default::default()
        };
        apply_selections(&mut app, selections);
        crate::mcp::sync_selected_mcps_from_env(&mut app);
        assert_eq!(app.jev_enabled, Some(false));
        assert!(!app.selected_mcp_contains("jev"));
    }

    #[test]
    fn profile_step_lists_roles_and_starts_on_current_choice() {
        let home = tempfile::tempdir().unwrap();
        let mut app = App::new().unwrap();
        app.home = home.path().to_path_buf();
        app.config_home_override = Some(home.path().join(".config"));
        app.install_profile = "team".into();
        let dir = app.user_profiles_dir("claude").join("my");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join("profile.json"),
            r#"{"name":"my","base":"lean","agents":["explorer"],"models":"anthropic"}"#,
        )
        .unwrap();
        let (prompt, ids, labels) = profile_step(&app, "claude");
        assert_eq!(prompt, "Select role profile for claude:");
        assert_eq!(ids, ["team", "lean", "my"]);
        assert_eq!(labels[0], "team · 9 roles: product-owner, pm, team-lead, …");
        assert_eq!(labels[1], "lean · explorer · native main session");
        assert_eq!(labels[2], "my · explorer · base lean · models: anthropic");
    }

    #[test]
    fn apply_selections_saves_host_profiles() {
        let mut app = App::new().unwrap();
        app.install_profile.clear();
        let mixed = WizardSelections {
            project_dir: "/tmp/p".into(),
            agent_os: vec!["claude".into(), "codex".into()],
            profiles: [
                ("claude".into(), "team".into()),
                ("codex".into(), "lean".into()),
            ]
            .into(),
            ..Default::default()
        };
        apply_selections(&mut app, mixed);
        assert_eq!(crate::profile::id_for(&app, "claude"), "team");
        assert_eq!(crate::profile::id_for(&app, "codex"), "lean");
        assert!(app.install_profile.is_empty());
        let same = WizardSelections {
            project_dir: "/tmp/p".into(),
            agent_os: vec!["claude".into()],
            profiles: [("claude".into(), "team".into())].into(),
            ..Default::default()
        };
        apply_selections(&mut app, same);
        assert_eq!(app.install_profile, "team");
    }

    #[test]
    fn tui_profile_choice_is_saved_to_manifest() {
        let home = tempfile::tempdir().unwrap();
        let project = tempfile::tempdir().unwrap();
        let mut app = App::new().unwrap();
        app.home = home.path().to_path_buf();
        app.config_home_override = Some(home.path().join(".config"));
        app.install_profile.clear();
        app.interactive_override = Some(false);
        app.doctor_enabled_env = false;
        let selections = WizardSelections {
            project_dir: project.path().to_string_lossy().into(),
            agent_os: vec!["claude".into(), "codex".into()],
            specs: vec!["software.general".into()],
            profiles: [
                ("claude".into(), "team".into()),
                ("codex".into(), "lean".into()),
            ]
            .into(),
            ..Default::default()
        };
        apply_selections(&mut app, selections);
        install::run_install(&mut app).unwrap();
        let manifest: serde_json::Value = serde_json::from_str(
            &std::fs::read_to_string(project.path().join(".agentic.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(
            manifest["settings"]["profile_ids"],
            serde_json::json!({"claude": "team", "codex": "lean"})
        );
        assert_eq!(manifest["settings"]["profile"], "lean");
        assert!(project.path().join(".claude/agents/developer.md").is_file());
        assert!(!project.path().join(".codex/agents/developer.toml").exists());
        assert!(project.path().join(".codex/agents/explorer.toml").is_file());
    }

    #[test]
    fn secret_input_never_renders_the_key() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = InputState::new("JEV_API_KEY", "");
        state.masked = true;
        state.value = "mock-private-key".into();
        terminal
            .draw(|frame| render_input(frame, &state, "dark", "test"))
            .unwrap();
        let shown: String = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect();
        assert!(!shown.contains("mock-private-key"));
        assert!(shown.contains('•'));
        assert_eq!(state.result(), "mock-private-key");
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
