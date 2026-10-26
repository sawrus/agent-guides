# План небольших изменений

Часть исследования [README.md](README.md). Шаги упорядочены по приоритету. Каждый шаг: модули, зависимости,
критерии приёмки, проверяемая гипотеза, откат. Все шаги отключаемы и не добавляют always-on текста
(`make context-budget CONTEXT_BUDGET_MAX=4000` остаётся зелёным).

Порядок: 0 ∥ 1 → 2 → 4 (измерение) → 3 → 5 → 6 → 7. Шаг 4 решает, остаются ли reviewer и workflow-контракт в
плане.

## Шаг 0. Bugfix: tier helper-сабагентов не выше модели сессии (параллельно шагу 1)

- **Проблема.** `routing.py:205-206` при единственной модели в пуле маршрутизирует без вопроса; на Codex lean + JEV
  это был `gpt-6-astra` для `reviewer` (2 ячейки T6, по 28k uncached), стоимость 1.43 × lean. Tech debt 21.
- **Модули.** `extensions/codex/hooks/jev/routing.py` (`spawn_rule`, `plan_spawn`), `hook.py:357-387`
  (`handle_spawn`: пробросить профиль и tier модели сессии), `tests/jev/`, `docs/jev-integration/README.md`
  («Lean + JEV»), `docs/agentic-v2-lean/tech_debt.md` (пункт 21).
- **Правило.** Под lean для `explorer` и `reviewer`: кандидаты не выше tier модели сессии; если tier сессии
  неизвестен, не выше `balanced`. `single_eligible_model` не выбирает `frontier`; вместо этого `fallback`
  с `reason_code = tier_above_session`, и host запускает helper на модели сессии.
- **Зависимости.** Нет.
- **Приёмка.** `make test-jev-hooks` с новыми тестами; `make lint`. Платная проверка позже, в раунде E1:
  Codex lean + JEV стоимость за принятую задачу ≤ 1.1 × lean (правило из `docs/agentic-v2-lean/README.md`).
- **Гипотеза.** H0: после правки ни один helper-spawn под lean не получает модель дороже сессии; стоимость
  lean + JEV на Codex падает до ≤ 1.1 × lean при той же доле принятых.
- **Откат.** Revert коммита; записи JEV сохраняют старые reason codes, формат не меняется.

## Шаг 1. Запись о приёмке в gate (минимальное полезное изменение)

- **Проблема.** Gate отличает «проверки прошли» от «агента отпустили по `max_blocks`» только полем `released` в
  `.agentic/gate/last.json` (`gate.py:124-127`). Нет SHA, версии pack и профиля; инженер не видит статус.
- **Модули.** `extensions/codex/hooks/gate/gate.py` (`stop()`), `tests/gate/`, `scripts/bench_sdlc.py`
  (`run_cell`, `summarize`, `report`: столбцы `accepted_by_gate`, `released`), `docs/agentic-v2-lean/README.md`
  (раздел «Quality gate»), `CHANGELOG.md`.
- **Изменение.** `last.json` получает поля: `accepted` (bool), `reason_code` (`checks_passed`, `checks_failed`,
  `max_blocks`, `no_changes`, `changelog_missing`), `head` (`git rev-parse HEAD`), `pack_version`
  (`.agentic.json` → `version`), `profile`, `commands` (как сейчас), `rules_read` (пока пусто; заполняет шаг 2б).
  При отпуске по `max_blocks` текст `reason` остаётся пустым (блокировки нет), но gate пишет
  `accepted: false`, а в `state.json` — `last_release`. Инструкция для отчёта: одна строка в обёртках команд
  (`src/claude.rs:198`) и в `AGENTS.md:27-28` не добавляется; вместо этого benchmark и будущий драйвер читают
  `last.json`. На Claude Code дополнительно вернуть `systemMessage` «Agentic gate: NOT ACCEPTED (<reason_code>)»
  — это рекомендованная документацией Claude Code возможность; её надо проверить одной live-сессией до включения.
- **Зависимости.** Нет. Repo-scan даёт candidate `.agent/gate.json`; поле `commands` не меняется.
- **Приёмка.** `make test-gate` с тестами на все `reason_code`; `make test`, `make lint`; `make bench-report` на
  сохранённых ячейках раунда 4 показывает `accepted_by_gate` = `delivered_green` в 100 % ячеек, где есть
  `last.json`; схема `last.json` описана в docs.
- **Гипотеза.** H1: в ячейках, которые заканчиваются по `max_blocks` (новая задача T8 с неисправимым lint в
  запрещённом для правки файле, 6 платных ячеек на Claude и Codex), `last.json` содержит `accepted: false` в
  100 % случаев, а финальный отчёт агента называет проваленную проверку не реже, чем в 5 из 6.
- **Откат.** Поля не читаются никем, кроме benchmark; удалить поля и столбцы. `max_blocks`-поведение не меняется.

## Шаг 2. Пакет задачи для helper-сабагентов и учёт прочитанных правил

- **Проблема.** Explorer и reviewer получают только то, что напишет модель. Reviewer на Codex lean T7 потратил
  22.8k uncached и 95k cached, чтобы заново прочитать diff и запустить проверки, вывод которых уже был у главной
  сессии. Какие правила читались в задаче — неизвестно.
- **Модули.** 2а: `extensions/claude/agents/explorer.md`, `reviewer.md`; `extensions/codex/agents/explorer.toml`,
  `reviewer.toml`; `extensions/opencode/agents/explorer.md`, `reviewer.md`; `src/claude.rs:198` (обёртка:
  «передай reviewer пакет задачи»). 2б: `src/gate.rs` (новая запись PostToolUse `Read|Bash` → `--event observe`,
  10 с), `gate.py` (`observe`: пути `.agent/rules/*.md` и `.claude/rules/*.md` из `tool_input` → `.agentic/gate/reads.json`),
  `tests/gate/`.
- **Изменение.** Шаблон пакета задачи в тексте агента: цель и критерии (цитата из запроса), список изменённых
  файлов (`git status --porcelain`), команды проверок и их последний вывод (из `.agentic/gate/last.json`),
  запрет повторного запуска проверок при наличии вывода. Это prose для главной сессии, но входные данные
  детерминированы и дешёвы.
- **Зависимости.** Шаг 1 (`last.json` как источник вывода проверок).
- **Приёмка.** `make test-gate`, `make lint`; `make context-budget` без роста (тексты агентов не always-on, только
  их `description`). 2б: измеренная надбавка времени PostToolUse-хука ≤ 100 мс на вызов на 20 вызовах; иначе 2б
  не включать.
- **Гипотеза.** H2: на E1 reviewer с пакетом тратит ≤ 0.7 × uncached токенов reviewer без пакета при том же
  числе найденных дефектов (ручная разметка true/false positive). H2б: `rules_read` показывает, что на
  question-задаче T3 правила не читаются (0 в ≥ 8 из 9 ячеек).
- **Откат.** Вернуть прежние тексты агентов; убрать запись хука из `hook_sets()`.

## Шаг 3. Контракт этапа v0: `checks` и `artifacts` во frontmatter workflow

- **Проблема.** `quality-gates` в workflow — текст (`develop-feature.md:36-39`). Проверки этапа нигде не
  исполняются. Repo-scan даёт candidate `.agent/gate.json` на репозиторий, но не знает про workflow.
- **Модули.** Frontmatter workflow в `areas/**/workflows/*.md` (новые поля `checks:` — список команд,
  `artifacts:` — список путей-глобов); `scripts/lint_prompts.py` (валидация полей); `src/install.rs` /
  `src/gate.rs` (при установке писать `workflow_checks: {id: [...]}` в `.agent/gate.json`, не трогая `commands`);
  `gate.py` (`settings()`: если `.agentic/task.json` содержит `workflow`, добавить его проверки к `commands`;
  `--event prompt` на UserPromptSubmit: промпт вида `/<workflow-id>` → `.agentic/task.json`); `hook.py:471-488`
  (`gate_session`: при выбранном workflow писать тот же `task.json`); `tests/gate/`, `tests/jev/`,
  `scripts/build_docs_catalog.py` (показывать `checks` в каталоге).
- **Что не делается.** Нет статусов этапов, нет зависимостей между этапами, нет исполнителя. `artifacts` только
  записываются в `last.json` как «ожидались / найдены», без блокировки.
- **Зависимости.** Шаг 1. Repo-scan: candidate `gate.json` как источник `commands`; формат должен оставить место
  для `workflow_checks`.
- **Приёмка.** `make test-gate`, `make test-jev-hooks`, `make lint-content` (валидация новых полей),
  `make context-budget` без роста. Один workflow (`add-migration`) получает `checks` в виде проверки наличия
  файла миграции; benchmark-задача T9 (изменение схемы без миграции) принимается только при наличии миграции.
- **Гипотеза.** H3: на T9 `delivered_green` в lean с контрактом ≥ lean без контракта на ≥ 3 из 9 ячеек, при
  стоимости ≤ 1.1 ×.
- **Откат.** Gate игнорирует неизвестные поля; удалить `workflow_checks` из `gate.json` при install.

## Шаг 4. Измерение: задачи, где plain падает, и A/B reviewer

- **Проблема.** T6/T7 не разделяют режимы; польза reviewer не измерена; все решения о делегировании без данных.
- **Модули.** `tests/bench/tasks.json`, `tests/bench/hidden/`, `tests/bench/seed/`, `tests/bench/reference/`
  (T8: скрытый дефект логики с явным критерием приёмки; T9: схема без миграции; T10: вопрос, требующий правила
  из `.agent/rules/`); `scripts/bench_sdlc.py` (режим `lean-noreviewer`: после install удалять файлы `reviewer`
  из `.claude/agents`, `.codex/agents`, `.opencode/agents`); `docs/agentic-v2-lean/README.md`.
- **Зависимости.** Шаги 0–2 (чтобы сравнивать уже исправленную версию).
- **Приёмка.** `make bench-selftest` зелёный для T8–T10; правило решения зафиксировано в README до запуска;
  платный раунд E1 по [experiments.md](experiments.md).
- **Гипотеза.** H4: reviewer повышает долю принятых на T8 не менее чем на 2 из 9 ячеек при стоимости ≤ 1.3 × lean
  без reviewer. Если нет — reviewer убирается из умолчания lean, и шаг 2 остаётся только для explorer.
- **Откат.** Измерение; откатывать нечего.

## Шаг 5. Длинные задачи: история gate и возобновление

- **Проблема.** Нет данных о длинных задачах; нет чекпоинта. Host-native compaction есть у Claude и Codex, но
  agentic не знает, что уже сделано.
- **Модули.** `gate.py` (`stop()`: дописывать строку в `.agentic/gate/history.jsonl`: время, `head`, изменённые
  файлы, результаты проверок, `accepted`); обёртки команд (`src/claude.rs`) и lean-подсказка JEV
  (`adapters.py:33-36`): одна фраза «при продолжении задачи прочитай `.agentic/gate/history.jsonl`»;
  `scripts/bench_sdlc.py` (многоходовые задачи: `prompts: [...]` в `tasks.json`, метрики «повторные чтения
  одного файла», рост cached-токенов по ходам); `tests/gate/`.
- **Более простая альтернатива.** Полагаться на native todos/compaction. Выбирается она, если E2 не покажет
  разницы.
- **Зависимости.** Шаг 1 (поля `last.json`), шаг 4 (harness для многоходовых задач).
- **Приёмка.** `make test-gate`; history пишется только при изменённых файлах; `make context-budget` без роста.
- **Гипотеза.** H5: на E2 lean с history даёт не меньше принятых инкрементов, чем lean, и на ≥ 20 % меньше
  повторных чтений тех же файлов на третьем ходе.
- **Откат.** Убрать запись history и фразу из обёрток.

## Шаг 6. Ledger моделей (offline) и обновление умолчаний

- **Проблема.** Выбор модели не опирается на измерения; цены Claude/Codex в runtime неизвестны.
- **Модули.** Новый `scripts/model_ledger.py` (offline): читает `tokens.agents` из `result.json` benchmark и
  `observation`-записи JEV, строит таблицу «host × роль/назначение × модель → токены, принято»; Makefile-цель
  `bench-ledger`; `extensions/*/model-tiers.json` и `extensions/claude/profiles/anthropic/profile.json` правятся
  вручную по таблице; `docs/jev-integration/README.md`.
- **Зависимости.** Шаги 0, 4.
- **Приёмка.** Цель работает на сохранённых ячейках раунда 4 и печатает таблицу; `make lint`.
- **Гипотеза.** H6: explorer на `fast` tier даёт ту же долю принятых, что на модели сессии, при ≤ 0.5 × стоимости
  explorer (проверка на E1 с `explorer`-задачей T11: вопрос о потоке данных в репозитории на 2k строк).
- **Откат.** Скрипт offline; умолчания возвращаются к прежним значениям.

## Шаг 7. Cross-project драйвер v0

- **Проблема.** Нет механизма для задач с зависимостями между репозиториями; хуки и доверие привязаны к корню
  проекта (hosts.md, следствие 5).
- **Модули.** Новый `scripts/xproject.py` (как `bench_sdlc.py`, но для реальных репозиториев): вход —
  `relationships.json` из repo-scan и пакет задачи (цель, затронутые репозитории, критерии); топологический
  порядок; на каждый репозиторий: `agentic install` (уже есть), одна host-сессия с пакетом, чтение `last.json`;
  после провайдера — запуск проверок потребителей против ветки провайдера (их `make test` с путём/версией
  провайдера); сводный отчёт с `accepted` по репозиториям. Docs: новый раздел в этом каталоге.
- **Что не делается.** Нет агента-оркестратора внутри сессии, нет общего контекста между сессиями, кроме пакета
  задачи и отчётов `last.json`.
- **Зависимости.** Шаги 1, 3; готовый `relationships.json` с evidence и confidence; ответы на вопросы 4–5, 7 в
  README.
- **Приёмка.** Offline-тест на фикстуре из двух репозиториев (provider + consumer); `make lint`. Платная проверка —
  E3.
- **Гипотеза.** H7: драйвер v0 достигает «оба pipeline зелёные» не реже, чем инженер с двумя ручными сессиями,
  при меньшем числе действий инженера (считаются промпты и ручные правки).
- **Откат.** Скрипт не меняет runtime; удалить.

## Сводка зависимостей

| Шаг | Требует | Даёт |
|---|---|---|
| 0 | — | Корректная стоимость lean + JEV |
| 1 | — | `accepted`, `head`, `pack_version` в evidence; столбец `released` в benchmark |
| 2 | 1 | Дешёвый reviewer/explorer; `rules_read` |
| 3 | 1, repo-scan `gate.json` | Исполняемые проверки workflow |
| 4 | 0–2 | Данные для решения о reviewer и контракте |
| 5 | 1, 4 | Данные о длинных задачах |
| 6 | 0, 4 | Умолчания моделей по измерениям |
| 7 | 1, 3, repo-scan, ответы на вопросы | Cross-project v0 |
