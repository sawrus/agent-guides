# agent-guides

Унифицированный каталог специализаций AgentOS и установщик `agentos-install.sh`.

## Структура репозитория

```text
areas/
  software/
    backend/
    frontend/
    data-engineering/
    full-stack/
    mlops/
    mobile/
    platform/
    qa/
    security/
extensions/
  opencode/
  codex/
  antigravity/
  gemini/
agentos-install.sh
```

Каждая специализация под `areas/software/<specialization>/` хранит:
- `AGENTS.md` (шаблон специализации)
- `rules/`
- `skills/`
- `workflows/`
- `prompts/`

## Что делает installer

1. Создаёт целевую директорию проекта (если не существует).
2. Копирует выбранное расширение AgentOS из `extensions/<agentos>` в `<project>/.<agentos>`.
3. Копирует выбранные специализации в общий слой:
   - `<project>/.agent/rules`
   - `<project>/.agent/skills`
   - `<project>/.agent/workflows`
   - `<project>/.agent/prompts`
4. Генерирует итоговый `<project>/AGENTS.md` на основе шаблонов выбранных специализаций.
5. Печатает сгруппированный отчёт о созданных/скопированных путях.

## CLI режим

### Доступные сущности

```bash
./agentos-install.sh list agentos
./agentos-install.sh list areas
./agentos-install.sh list specs --area software
```

### Установка

```bash
./agentos-install.sh install \
  --project-dir /tmp/test \
  --agent-os opencode \
  --areas software \
  --specializations software.backend,software.frontend
```

Сухой прогон:

```bash
./agentos-install.sh install \
  --project-dir /tmp/test \
  --agent-os codex \
  --areas software \
  --specializations software.frontend \
  --dry-run
```

## TUI режим

```bash
./agentos-install.sh tui
```

Пример запуска TUI:

![Пример запуска AgentOS installer в TUI режиме](docs/images/tui-example.svg)

Пошагово:
1. Ввод директории проекта.
2. Выбор AgentOS (`codex`, `antigravity`, `opencode`, `gemini`, ...).
3. Множественный выбор `areas` (сейчас минимум `software`).
4. Для каждой area — множественный выбор специализаций (`backend`, `frontend`, ...).

При старте TUI отображает ASCII-арт.

## E2E тесты

```bash
./tests/e2e/agentos-install.e2e.sh
```

Сценарии:
- CLI: `opencode + software.backend`
- CLI: `codex + software.frontend`
- TUI: `default + software.backend,software.frontend`
