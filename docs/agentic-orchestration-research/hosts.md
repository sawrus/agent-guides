# Ограничения сред: Claude Code, Codex, OpenCode

Часть исследования [README.md](README.md). Для каждого аспекта три колонки:

- **Рекомендовано** — что обещает документация host или наш docs; в коде agentic не используется.
- **Применено** — что agentic делает в коде (с ссылкой).
- **Наблюдалось** — что подтверждено трассами benchmark (раунд 4) или blackbox-проверками.

Пустая ячейка «Наблюдалось» означает: в измерениях это не проверено.

## Claude Code

| Аспект | Рекомендовано | Применено | Наблюдалось |
|---|---|---|---|
| Хуки | `.claude/settings.json`; события UserPromptSubmit, PreToolUse, PostToolUse, PermissionRequest, SubagentStart, SubagentStop, Stop; JSON-ответ может нести `systemMessage` для пользователя | Gate: Stop (900 с) и PreToolUse guard (10 с), `src/gate.rs:208-223`; JEV: шесть событий по 12 с, `src/jev_hooks.rs:231-254`. Команда привязана к `$CLAUDE_PROJECT_DIR`, потому что хук может стартовать из подкаталога (`gate.rs:196-201`). `systemMessage` не используется | Stop `decision: block` сработал в 9 из 9 ячеек T5 (lean, lean + JEV, team + JEV); агент продолжил и исправил lint. UserPromptSubmit `additionalContext` с workflow — 3 ячейки T6 на каждый JEV-режим |
| Смена модели | Модель сессии задаётся `--model` или `/model`; хук её не меняет. Инструмент `Agent` принимает только алиасы `haiku`, `sonnet`, `opus` | `routing.py:69-71` ограничивает кандидатов алиасами; `adapters.py:314-316` пишет `updatedInput.model`; frontmatter `model:` агентов — pin (`src/claude.rs:99`), под JEV убирается | В раунде 4 на Claude не было ни одного spawn, поэтому подмена модели не наблюдалась. Ранее: без `hosts.claude` в `model-defaults.json` сабагенты наследовали `opus` сессии (`docs/jev-integration/session-gate/README.md`, проблема 3) |
| Передача контекста | `CLAUDE.md` импортирует `@../AGENTS.md`; все файлы `.claude/rules/` грузятся в каждую сессию, `paths:` ограничивает по glob; сабагент получает только текст запроса и свой system prompt, возвращает только финальное сообщение; тип `fork` наследует разговор | `extensions/claude/CLAUDE.md:3`; `src/copydir.rs:35-36`, `:134-146` не копирует `trigger: manual` в `.claude/rules/`; обёртки команд `src/claude.rs:178-205` | K1: 1.9k always-on токенов. Транскрипты и auto-memory живут в `~/.claude/projects/<path>/`; benchmark стирает их перед ячейкой (`scripts/bench_sdlc.py:81-84`) |
| Сабагенты | Сабагент не запускает сабагентов; параллельные запуски в фоне; `--agent <name>` делает роль главной сессией | `docs/claude-code/README.md`, раздел «SDLC team»; team пишет `agent: product-owner` в settings | Lean: 0 сабагентов во всех 63 ячейках; `explorer` и `reviewer` не запускались ни разу |
| Завершение и приёмка | Stop-хук может блокировать многократно; нет native-понятия «принято» | `gate.py:125-127` отпускает после `max_blocks = 3` | `max_blocks` не достигался. Между блоками агент сам запускал проверки (`verified_after_edit` = true в 62 из 63 lean-ячеек) |
| Кэш и стоимость | Prompt cache 1 час; `total_cost_usd` в stream-json | Benchmark читает `total_cost_usd`; `--strict-mcp-config` выравнивает инструменты между режимами (`bench_sdlc.py:74-76`) | Эффект порядка кэша: team + JEV показал 5.3k uncached против 11.3k plain, потому что длинный префикс уже лежал в кэше (`results.md`, раунд 4) |
| Cross-project | Дополнительные рабочие каталоги (`--add-dir`); хуки и правила читаются из корня основного проекта | Не используется | |

## Codex

| Аспект | Рекомендовано | Применено | Наблюдалось |
|---|---|---|---|
| Хуки | `.codex/hooks.json`; доверие выдаётся через `/hooks` на каждый абсолютный путь проекта; события UserPromptSubmit, PreToolUse, PostToolUse, PermissionRequest, SubagentStart, Stop | Gate: Stop и PreToolUse `Bash|apply_patch` (`src/gate.rs:225-241`); JEV: пять событий (`src/jev_hooks.rs:201-227`). Benchmark отказывается запускать ячейку без записи о доверии (`bench_sdlc.py:229-244`, `:263-265`) | Недоверенные хуки молча не выполняются: в `bench-r4` 38 ячеек Codex имеют статус `harness_error`; валидные прогоны Codex лежат в `bench-r5`. Stop-блокировка gate на Codex в раунде 4 **не наблюдалась**: lean-агент сам запускал `make lint` |
| Смена модели | Модель сессии `-m`; `spawn_agent` принимает `model`; `model` в TOML custom-агента перекрывает аргументы spawn; аккаунт может не отдавать модель из конфига | `adapters.py:199-201` пишет `updatedInput.model` в PreToolUse; `src/copydir.rs:72-90` убирает `model =` из TOML под JEV; `prepared.py` даёт явный билет для spawn с TTL 600 с | `verification.md` (2026-10-14): `gpt-6-luna` применён к developer и qa. Раунд 2: reviewer на `gpt-6.1-sol` вернул 0 токенов, Codex повторил на модели сессии (tech debt 20). Раунд 4: правило `single_eligible_model` отправило reviewer на `gpt-6-astra` (2 ячейки T6 lean + JEV, 9 observation в team + JEV) |
| Передача контекста | Иерархия `AGENTS.md`; skills из `.agents/skills`; текст назначения сабагента может быть зашифрован (`gAAAA`) и недоступен хуку; memories добавляют кросс-проектную память в каждый запрос | `adapters.py:164-168` помечает зашифрованные назначения; memories включены только в team (`src/install.rs:497-510`); `AGENTS.override.md` только в team (`src/profile.rs:39-41`) | Memories стоили около 1.8k токенов на запрос (CHANGELOG v2.0.0). Раунд 1: native `explore` потратил 47.8k uncached на 200-строчном репозитории |
| Сабагенты | `spawn_agent` с `agent_type`, `resume`, `fork_turns`; лимит `agents.max_threads` | `max_threads = 8` только для team + JEV (`src/install.rs:514-522`); токены по `agent_path` читаются из rollout (`bench_sdlc.py:318-319`) | Lean: 0.14 сабагента на ячейку (reviewer на T6/T7); team + JEV: 0.62, два token cap на T6 |
| Завершение и приёмка | Stop-хук как у Claude | Gate Stop (`src/gate.rs:233`) | `last.json` есть во всех 21 lean-ячейках; блокировок не было |
| Слэш-команды | Проектных слэш-команд нет | JEV принимает голое `jev off|on|status` (`hook.py:51`); workflow запускается только через JEV или явное имя в промпте (`hook.py:337-339`) | |
| Стоимость | План ChatGPT не отчитывает цену; API-эквивалент по `tests/bench/prices.json` | `bench_sdlc.py:420-432` | Цены вторичные; `cached_input` нет в оценке |
| Cross-project | Доверие хукам per path → каждый репозиторий требует ручного `/hooks` | Не используется | |

## OpenCode

| Аспект | Рекомендовано | Применено | Наблюдалось |
|---|---|---|---|
| Хуки (plugin API 2.0.28+) | `session.hook("prompt")` меняет текст, но не отменяет ход; `tool.hook("execute.before")` меняет `input` сабагента; `permission.hook("evaluate")` ставит `deny`; `event.subscribe` даёт `session.execution.succeeded`; `session.prompt` шлёт новый промпт; `session.switchAgent` | JEV: `extensions/opencode/hooks/agentic-jev.ts:78-110` (prompt), `:112-148` (execute.before, `input.model`), `:156-165` (permission), `:171-176` (model.request → observation). Gate: `extensions/opencode/plugins/agentic-gate.ts:44-54` (guard), `:56-70` (Stop как follow-up промпт) | Gate-follow-up не дошёл до одноразового `opencode run`: в трассах нет сообщений gate, `last.json` есть в 16 из 21 lean-ячеек, T5 принят в 1 из 9 не-plain ячеек. Guard live не доказан (tech debt 8) |
| Смена модели | Модель на агента в `opencode.json`; профили `openai`, `githubcopilot`; `subagent.model` переопределяется в `execute.before` | `agentic-jev.ts:143-144`; маршрутизация остаётся на провайдере координатора (`AGENTIC_JEV_MODEL_PROVIDER`, `routing.py:143`) | `verification.md`: `openai/gpt-5.5-fast` применён. Раунд 4: `no_tier_routing` в 16 spawn team + JEV (у приватного провайдера нет tier-карты) |
| Передача контекста | `AGENTS.md` + `.opencode/MEMORY.md`; списки skills из трёх папок; primary agent `build` | Lean оставляет native primary и объявляет только `explorer`, `reviewer` (`src/profile.rs:57-84`) | Lean — 1.93 × plain по полным токенам (tech debt 18); источник надбавки не разложен |
| Сабагенты | Инструмент `Task` с именем агента; дочерние сессии с `parentID` | Дочерние сессии читаются через server API (`bench_sdlc.py:294-296`) | Lean: 0.19; team + JEV: 0.95 сабагента на ячейку, T6 медиана 480 с |
| Завершение и приёмка | Нет события «до завершения хода» для блокировки | Follow-up промпт (`agentic-gate.ts:64-67`) | Второй ход (`turns = 2`) в 12 ячейках — это ответ harness на остановку, не gate |
| Стоимость | Приватный LiteLLM не отчитывает кэш | Полные = uncached (`results.md`, раунд 4) | Доллары OpenCode несравнимы с другими host |
| Cross-project | `opencode serve` в каталоге проекта | Benchmark поднимает сервер на проект (`bench_sdlc.py:215-226`) | |

## Следствия для архитектуры

1. Единственный механизм, который работает одинаково на всех трёх host, — Python-runtime, вызываемый из native
   хуков (`gate.py`, `hook.py`). Новые проверки надо добавлять туда, а не в host-специфичные адаптеры.
2. «Блокировать завершение» надёжно только на Claude (наблюдалось) и, по контракту, на Codex (не наблюдалось).
   На OpenCode до починки gate приёмку нельзя привязывать к концу хода.
3. Подмена модели сабагента работает на всех host, но Claude ограничен тремя алиасами, Codex — каталогом
   аккаунта, OpenCode — провайдером координатора. Правило «не выше модели сессии» реализуемо везде: модель сессии
   известна из payload SubagentStart (Codex), `model.request` (OpenCode) и из `tokens.agents` в трассах.
4. Контекст сабагента везде — только текст запроса. Значит, пакет задачи должен собираться детерминированно
   (изменённые файлы, команды, критерии) и вставляться в промпт, а не ожидаться от модели.
5. Хуки, правила и доверие привязаны к корню проекта на всех host. Cross-project оркестрация внутри одной
   сессии противоречит этим ограничениям; внешний драйвер с сессией на репозиторий их соблюдает.
