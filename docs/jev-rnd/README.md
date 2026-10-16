# JEV для Agentic: результаты первоначального исследования

Текущая реализация упрощена по уточнению заказчика: [нативные хуки и флаг TUI/CLI](../jev-integration/README.md). Отдельный Rust evaluator удалён; описание CLI-прототипа и его результаты ниже — историческая запись R&D, а не текущие команды.

Дата: 2026-10-13. Статус: R&D и opt-in CLI-прототип; подключение к установщику
и автоматическое изменение рабочих workflow в этот этап не входят.

## Требования исследования

Проверить применимость JEV к выбору модели, оценке доказательств тестирования,
управлению повторными исправлениями, очередности инкрементов epic и итоговым
действиям REVIEW_PIPELINE. Спроектировать опциональное включение в CLI/TUI
и поддержку всех сред Agentic без обязательной зависимости от JEV.

Результат: архитектура, ограничения, рабочая команда `agentic jev`, воспроизводимые реальные
эксперименты на синтетических данных, измерения и план внедрения. Ключ читается
из окружения или локального `.env`, никогда не сохраняется в артефакты.
Исследование не меняет действующие quality gates, роли или настройки сред.

Уточнения заказчика: разрешены code/diff/log excerpts после удаления секретов;
лимит исследования $5; реальное тестирование использует приобретённый hosted
ключ, а прототип должен также поддерживать официальный TypeSafe API.

## Дизайн прототипа до реализации

Добавить `src/jev.rs` и диспетчер `agentic jev` без нового runtime/dependency.
Использовать существующие reqwest/serde_json/regex. Команда принимает JSON из
файла/stdin, preset route/evidence/loop/epic/review, provider hosted/typesafe.
Включение только явное; наличие ключа само по себе не включает запросы.
Disabled возвращает fallback без чтения input/key и без сети. Dry-run позволяет
просмотреть очищенный запрос без сети. Ответ всегда advisory (`applied=false`).

Hosted endpoint: `https://jevtypesafeai.com/api/v1/decide`, `JEV_API_KEY`.
Официальный endpoint: `https://api.typesafe.ai/v1/systemone`, `TYPESAFE_API_KEY`.
Общий body: model/state/questions. Не смешивать ключи; не делать credential
failover. Официальный endpoint проверяется локальным HTTP mock, реальная quota
не приобретена. Сетевые ошибки/недостаток confidence возвращают исходный workflow.

Проверка evidence сначала локально сравнивает текущий tree_id, обязательные
команды, exit_code, skips и заявленный источник records. Происхождение record
должен обеспечить независимый executor; само поле source не доказывает подлинность.
JEV не запускает тесты и не получает полномочий acceptance. Числа/зависимости epic
обрабатываются кодом; score оценивает только предоставленный смысл.

Для архитектурной проверки: отдельный модуль, фиксированные provider URLs,
timeouts, отключённые redirects и отсутствие автоматических retries; удаление
типичных credential fields/строк перед сетью; строгая проверка схемы ответов и
ограничение input. Не обещать полноту redaction; вызывающая сторона обязана
предварительно исключить конфиденциальные данные. В прототипе нет общего бюджета
между процессами: единичный вызов ограничен размером, исследовательский harness
ведёт отдельный bounded budget. Production ledger — отдельный инкремент.

## Критерии результата

- Для каждого применения указаны входные доказательства, решение и fallback.
- Рекомендация модели отделена от возможности среды применить её.
- Проверка отчёта не выдаётся за доказательство выполнения тестов.
- Приоритет epic учитывает зависимости и согласованные ограничения.
- Итог review содержит конкретное следующее действие либо недостаток evidence.
- Реальные запросы имеют ограничение расходов, результаты и ограничения выборки.

## Вывод исследования

JEV подходит как слой узких решений между этапами SDLC: выбрать tier,
оценить противоречие, классифицировать следующий шаг, оценить один фактор
приоритета. Генерацию требований, сложный design/review и полномочия принятия
оставляем ролям. Наибольшая ожидаемая экономия — прекратить передачу каждого
рутинного отчёта дорогому агенту и передавать ему только исключения и итоговый
пакет доказательств. Экономия всего workflow пока не измерена.

TypeSafe отдельно объясняет, почему JEV нельзя поставить вместо coding LLM:
он возвращает ограниченные решения, не пишет код и текст.
[JEV with coding agents](https://docs.typesafe.ai/introduction/coding-agents).

### Текущая архитектура Agentic

Agentic устанавливает инструкции; полноценного runner/телеметрии исполнения
сейчас нет. OpenCode mapper в `src/mapper.rs` выбирает модели статически при
установке. Codex PO в `extensions/codex/agents/product-owner.toml` закреплён
за `gpt-6.1-sol` с высоким reasoning. Поэтому экономия требует двух отдельных
возможностей: получить решение JEV и применить его при конкретном вызове роли.

`develop-feature` требует ровно шесть SDLC subagents, QA recommendation и
team-lead sign-off. Замена этих ролей JEV нарушила бы текущий контракт.
Первый rollout сохраняет роли, но уменьшает частоту/объём их reasoning и
выбирает подходящий tier для каждого вызова. Удаление mandatory agents —
возможный будущий профиль workflow, который нужно отдельно определить и проверить.

### Возможности JEV и соответствие задачам

| Задача | Примитив / вход | Что делает код и владелец |
| --- | --- | --- |
| Выбор модели | Choice по prompt + шагу + рискам | Фильтрует доступные модели, применяет ограничения и tier mapping |
| Проверка developer report | Choice по claim и независимым records | Проверяет tree, команды, exit codes, skips и provenance |
| Fix loop | Choice по открытым finding IDs, прогрессу, следующей гипотезе | Считает попытки, сохраняет предел, маршрутизирует владельцу |
| Epic priority | Отдельные Score value/urgency/risk reduction | Проверяет DAG, считает веса/effort, PO утверждает последовательность |
| Review follow-up | Choice по наблюдениям двух специалистов | Сохраняет конкретные задачи из findings и назначает владельца |
| Acceptance coverage | Noul/Choice на один критерий и его evidence | Строит матрицу, не подменяет продуктовую acceptance |
| Retrieval / память | Noul relevance и Choice canonical home | Получает кандидатов из поиска; не пишет память автоматически |

Choice выбирает вариант, Score задаёт позицию на описанной шкале, Noul —
вероятность yes. В официальном API вопросы независимы: результат одного нельзя
использовать внутри другого в том же вызове. Следующие решения комбинируются
кодом либо отдельным вызовом. Имена questions сами по себе не несут инструкции;
условия нужно писать явно.
[API](https://docs.typesafe.ai/api),
[Parallel fan-out](https://docs.typesafe.ai/patterns/fan-out).

`confidence` — производная распределения, не независимая гарантия правильности.
У Noul отдельного confidence нет. Пороги настраиваются для конкретной задачи,
версии модели и стоимости ошибки.
[Confidence](https://docs.typesafe.ai/confidence).

## Работающий прототип

В репозитории реализованы `src/jev.rs`, диспетчер команды, примеры и тесты.
Никакие новые зависимости, MCP server или автоматическое переключение LLM
прототипом не установлены. CLI работает в любой среде, где разрешён shell и
доступен бинарник Agentic. Нативные адаптеры пока являются проектом.

```bash
make build
./target/debug/agentic jev route --dry-run --input docs/jev-rnd/examples/route.json
# JEV_API_KEY уже установлен в окружении; значение не передавать в аргументах.
./target/debug/agentic jev route --enabled --provider hosted --input docs/jev-rnd/examples/route.json
# После приобретения официального ключа — TYPESAFE_API_KEY в окружении.
./target/debug/agentic jev route --enabled --provider typesafe --input docs/jev-rnd/examples/route.json
./target/debug/agentic jev route --disabled
```

Опции: `--input <file|->`, `--provider hosted|typesafe`, `--enabled`,
`--disabled`, `--dry-run`. Также `AGENTIC_ENABLE_JEV=1|y|true` и
`AGENTIC_JEV_PROVIDER=hosted|typesafe`. `--disabled` имеет приоритет над
`--enabled` и dry-run: input и ключ не читаются, запроса нет. Без включения
обычная команда возвращает `fallback: disabled`. Dry-run отдельно разрешает
локальный просмотр подготовленного запроса, не читает ключ и не использует сеть.
CLI не загружает `.env` автоматически; это делает только исследовательский harness.

Все входы — JSON object, максимум 32 KiB. Поля:

| Preset | Обязательные поля | Результат |
| --- | --- | --- |
| route | `task`: непустой текст; дополнительные constraints/context допустимы | fast / balanced / frontier / clarify |
| evidence | `current_tree`, непустой `required[]`; для оценки JEV также `claim`, `records[]` | supported / contradicted / insufficient; локально gather_evidence / fix_failed_checks |
| loop | `attempt`: integer, `limit`: 1..3, `remaining[]`; для JEV также `summary` | continue / complete / replan / escalate / gather_evidence |
| epic | `completed[]`, `increments[]` с уникальным id, description, effort > 0, depends_on[] | priorities только для ready increments |
| review | `observations`: текст; candidate_actions/source/evidence по возможности | keep / docs_task / instructions_task / both / insufficient |

`records[]`: command, tree, source (`independent_executor` или `ci`), integer
exit_code, boolean skipped, summary. Любое отсутствие необходимых доказательств,
stale tree или self-authored source приводит к локальному gather_evidence;
неуспешный exit code — к fix_failed_checks без API. Не выдаём source label за
криптографическое подтверждение. Для production нужны records из реально
контролируемого executor/CI, а не JSON, составленный developer.

На последней разрешённой попытке с открытыми blockers — локальная escalation.
Если blockers закрыты, оценка завершения разрешена и на последней попытке;
JEV не может разрешить ещё одну попытку поверх лимита. `complete` — advisory,
окончательное завершение проверяет оркестратор с QA/TL/PO.

JSON output содержит status (`recommendation`, `fallback`, `local_check`,
`dry_run`), next_action, applied=false. Сетевые результаты также содержат provider,
model, answers, latency_ms и доступные input/output/cost usage. Баланс аккаунта
не выводится. Confidence threshold прототипа 0.9 — экспериментальная настройка,
а не рекомендованный production threshold. При низком confidence/ошибке —
existing_workflow. Ошибка CLI/input завершает команду exit 1; semantic verdict,
local gate и provider fallback — exit 0. Exit 0 команды не означает успешную
acceptance или прохождение тестов: нужно читать status/next_action.

Поиск ключевых полей/типичных credential strings удаляет API keys, bearer,
password assignments и private-key blocks перед отправкой. Это ограниченная
защита, не полное обнаружение секретов: нестандартные credentials/PII должны
быть исключены вызывающим агентом. Провайдер не получает ключи из другого
провайдера, redirects отключены, автоматических retries нет. Runtime timeout
10 секунд, connect timeout 3 секунды; ответ ограничен 256 KiB.

Hosted key применяется только к независимому gateway. Официальный ключ
получается в [TypeSafe console](https://console.typesafe.ai/keys) и применяется
только к `api.typesafe.ai`. Общие model/state/questions не означают одинаковые
ошибки и usage: gateway имеет 402/502 и стоимость/баланс, официальный API
документирует 422/429/529 и token usage. Настройки транспорта отделены от policy.
[Hosted API](https://jevtypesafeai.com/docs),
[Official API](https://docs.typesafe.ai/api).

## Изменения develop-feature при полном rollout

1. На входе prompt классифицируется по сложности и отдельно по security,
   architecture, migration, ambiguity. Пользовательский model pin и enterprise
   allowlist сохраняются. Модель выбирается для шага, не один раз на всю фичу.
2. PO/PM формируют требования, TL/designer — design. JEV помогает выявить
   недостаточные acceptance criteria, но сам их не придумывает.
3. Developer передаёт finding IDs и указатели на независимые execution records.
   Parser сначала проверяет обязательные gates, затем JEV семантические
   противоречия/coverage. Для low-risk рутинного handoff достаточно узкой
   проверки дешевым агентом; TL получает изменения, которые требуют reasoning.
4. TL один раз делает полноценный code/architecture review. На исправлениях
   JEV классифицирует связанные findings, наличие прогресса и риск нового diff;
   повторный TL review ограничивается изменившимися блокерами. Архитектурные,
   security и migration изменения направляются TL всегда, независимо от score.
5. Loop controller выбирает continue/replan/escalate/gather_evidence. При
   повторении того же failure signature без новой гипотезы эскалирует раньше
   третьего круга. JEV может рекомендовать replan, но изменение ТЗ делает PO.
6. Acceptance получает одну матрицу criterion → evidence → status с открытыми
   blockers, docs/changelog/version и рисками. PO остаётся владельцем acceptance;
   дорогая модель нужна на неоднозначных trade-offs, не на переписывании логов.

Автоматическая проверка facts обычно дешевле JEV: команды из Makefile,
exit code, revision, file existence, обязательные criteria IDs, blocking severity.
Такие условия вообще не нужно отдавать модели. JEV оценивает только то,
что остаётся семантически неопределённым. Pattern cheap generator → verifier →
reasoning model имеет официальный пример; его численные результаты нельзя
переносить на наши workflow.
[SDE cascade](https://docs.typesafe.ai/cookbooks/sde_cascade).

## Приоритет инкрементов develop-epic

Планирование уже предписывает value/risk/dependencies; JEV сделает критерии
явными и повторяемыми. Сначала DAG исключает невыполнимые increments, обязательные
security/rollout constraints ограничивают множество кандидатов. Отдельными
вопросами оцениваются business value, urgency/cost of delay и risk reduction.
Effort, dependency IDs и deadlines берутся из подтверждённых данных, не угадываются.

Прототип использует нормализованные score 0..4 и формулу
`(0.5*value + 0.3*urgency + 0.2*risk_reduction) / effort` только для ready items.
Это прозрачная стартовая эвристика, не валидированная финансовая модель WSJF.
Веса/effort — решения PO/PM. Детерминированный tie-break — id. Низкая confidence
возвращает планирование ролям. После каждого принятого инкремента пересчитываются
только изменившиеся кандидаты. Нельзя автоматически отменять уже согласованный
milestone или переупорядочивать обязательную архитектурную основу.
[Composite scoring](https://docs.typesafe.ai/patterns/composite-scoring).

## Другая рутина PO / team-lead

| Рутина | Возможная экономия | Когда нужна сильная роль |
| --- | --- | --- |
| Проверка полноты handoff | Schema checks + JEV coverage/contradiction | Новый/неоднозначный контракт |
| Разделение review feedback | blocking/nonblocking + candidate owner | Спор о severity или scope |
| Duplicate/closed findings | Сопоставление конечных candidate IDs | Нет доказательств исправления |
| Risk triage diff | auth/data/migration/concurrency flags | Содержательные изменения в этих областях |
| Acceptance traceability | Проверка поддержки одного criterion evidence | Product trade-off и итоговая acceptance |
| Release readiness checklist | Parser для version/changelog/CI; JEV для явно описанных gaps | Go/no-go и остаточный риск |
| Проверка ссылок в отчёте | Проверка существования/цитат кодом, смысл JEV | Неизвестный источник или сложный вывод |

JEV не генерирует точные правки документации. Дешёвый LLM/специалист формирует
candidate action, JEV оценивает поддержку evidence, код сохраняет исходный текст
и source IDs. Аналогичный подход к проверке цитат сначала исключает отсутствующие
цитаты кодом, затем оценивает смысл в контексте.
[Citation checks](https://docs.typesafe.ai/cookbooks/citation_check).

## REVIEW_PIPELINE: результат, пригодный для следующего действия

Текущие специалисты уже должны предлагать точные edits и follow-ups. Проблема
закрывается усилением итогового контракта, а не одной новой моделью. Предлагается
добавить в summary обязательные поля:

- effectiveness: effective / inefficient / insufficient_evidence;
- docs_action и instructions_action: keep / task_needed / insufficient_evidence;
- для каждого candidate: source, observed friction, proposed edit, owner,
  priority, done_when и evidence IDs;
- next_task_required: yes / no / insufficient_evidence;
- next_task_prompt: шаблон из выбранных существующих findings, не выдуманный JEV.

JEV оценивает отдельные hypotheses: есть ли подтверждённый instruction conflict,
документирован ли новый behavior, повторяется ли friction, пригоден ли candidate
к выполнению. Итог формирует код/координатор. Если оба reviewer unavailable —
нельзя вывести keep или effective. Отсутствие token/cost telemetry означает
`not measured`, даже если качественные рекомендации убедительны.

После успешной top-level delivery запускается одна пара read-only specialists;
JEV применяется к её ограниченному пакету и findings. Не появляются дополнительные
review cycles на каждый increment. Специалисты остаются обязательными по текущему
контракту; можно уменьшать их model tier/объём контекста. Применение edits/запись
памяти остаются отдельной задачей. Прототип preset review пока классифицирует тип
follow-up; полная схема summary и выбор отдельных action IDs — следующий инкремент.

## Среды: общий путь и нативное применение модели

| Среда | Конфигурация MCP при будущем rollout | Model routing |
| --- | --- | --- |
| Codex | `.codex/config.toml`, mcp_servers | Выбор модели/effort при spawn или custom agent; не обещать смену активного parent |
| Claude Code | `.mcp.json`, mcpServers | Per-invocation subagent model; зависит от версии и availableModels |
| Gemini CLI | `.gemini/settings.json`, mcpServers | Subagent model; BeforeModel позволяет менять outgoing model, после smoke проверки версии |
| OpenCode | `opencode.json`, top-level mcp; legacy path поддерживается | SDK session.prompt задаёт providerID/modelID; plugin hook проверять по установленной версии |
| Cursor | `.cursor/mcp.json` | Пока recommendation-only; нативное автоуправление не проверено |
| KiloCode | `.kilocode/mcp.json` | Пока recommendation-only; нативное автоуправление не проверено |
| Antigravity | user-global Gemini antigravity mcp_config.json | Пока recommendation-only; важно отдельно согласовать глобальную конфигурацию |
| default / иная shell-среда | CLI и общие `.agent` instructions | Recommendation-only |

Подтверждённые upstream возможности, но не end-to-end проверенные нами адаптеры:
[Codex subagent models](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Claude subagent model selection](https://code.claude.com/docs/en/sub-agents#choose-a-model),
[Gemini hooks](https://geminicli.com/docs/hooks/reference/#beforemodel),
[Gemini subagents](https://geminicli.com/docs/core/subagents/),
[OpenCode SDK](https://opencode.ai/docs/sdk/).

Правило capability negotiation: if host permits runtime model override →
применить allowlisted tier mapping; иначе сохранить текущую модель и вывести
рекомендацию. MCP сам по себе не меняет coding model и не перехватывает prompt
до первого вызова LLM. Для экономии первого frontier-вызова нужен launcher/hook,
который вызывает JEV до отправки prompt. Для CLI-прототипа это внешний caller.

Не закреплять названия моделей в JEV prompts. Локальный catalog содержит provider,
доступность, поддерживаемые tools/context/reasoning, pricing timestamp, user pin
и tier. JEV выбирает tier и task flags; код выбирает доступную модель. Все шесть
ролей сохраняются, role consolidation не используется. Long-session rerouting
производится на границе шага с compact handoff и model-change hysteresis.

## CLI/TUI enablement при полном rollout

В существующий registry `src/mcp.rs` добавить `jev` как sensitive outbound
integration, выключенный по умолчанию. TUI использует этот registry и показывает
JEV рядом с Context7/MemPalace. После включения выбрать:

1. Provider: hosted / official TypeSafe.
2. Mode: observe (решения логируются) / assist (advisory) / auto (только
   проверенные low-risk маршруты). Первоначальное значение — assist.
3. Возможности: routing, evidence, loop, epic priority, post-review отдельно.
4. Model tier mapping, budget, timeout и уровень передаваемых excerpts.
5. Key source: environment reference; если нужен persistent key, отдельное
   защищённое user storage. Не копировать ключ в `.agentic.json`/guidance/backup.

Предлагаемые будущие настройки проекта:

```json
{
  "integrations": {
    "jev": {
      "enabled": true,
      "provider": "hosted",
      "mode": "assist",
      "key_env": "JEV_API_KEY",
      "model": "jev-1.13.0",
      "capabilities": ["routing", "evidence", "loop", "epic", "review"],
      "budget_usd_per_task": 0.10
    }
  }
}
```

Этот manifest и modes ещё не реализованы. В прототипе включение ограничено CLI/env.
Production precedence: explicit off > явные command options > project manifest >
user defaults > off. Наличие ключа не является enablement. Отключение требует
прекратить calls/hooks и убрать только управляемую MCP entry; пользовательские
изменения сохраняются. В уже открытой среде может потребоваться reload, что
installer сообщает. Upgrade сохраняет выбор; dry-run ничего не запускает и не
пишет credentials. `doctor` отдельно сообщает transport, policy и native routing
capability, а не одно обманчивое «JEV работает».

Предпочтительный production путь: общий Rust decision core → `agentic jev`
и local MCP facade → native adapters. Существующий сторонний
[jev-mcp](https://github.com/codaaiteam/jev-mcp) годится для sandbox exploration,
но его generic tools не обеспечивают наши evidence/loop/budget contracts.
Не ставить mutable GitHub package автоматически без pinning и проверки.

## Ошибки, ограничения и экономика

JEV 1.13 имеет известные ограничения: числа/даты вычисляет код, большие нерелевантные
пакеты следует отфильтровывать, adversarial state и порядок вариантов могут влиять
на ответ. Generation не является его задачей.
[Known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

В production сохранять request/policy/rubric version и resolved model, input hash,
source IDs, decision distribution, applied/fallback reason, latency и стоимость.
Не сохранять полный transcript/секреты. Изменившийся tree/diff/findings инвалидирует
cached verdict; одинаковый model+policy+rubric+evidence hash позволяет cache hit.

Usage ledger резервирует worst-case стоимость до отправки, учитывает параллельные
calls/unknown timeout outcomes и бюджет задачи. На 401/402/403 не retry; на transient
errors bounded backoff с общим deadline. Недоступность JEV возвращает штатный
workflow, не устраняет QA, не означает pass. Прототип имеет timeout/no-retry,
но ledger/cache/native hooks пока не реализованы.

Официально опубликовано $0.042/M input tokens для текущего Jev 1.13; gateway
указывает $0.42/M на стандартных credits. Это разные цены; официальная quota
не предполагает применимость hosted key. В наших 47 вызовах gateway charged
$0.008803 за 20 905 input tokens. Цены/лимиты нужно сверять при rollout.
[Official models](https://docs.typesafe.ai/models),
[Hosted billing](https://jevtypesafeai.com/docs#billing).

Gateway сообщает, что не сохраняет request bodies, но передаёт их upstream
TypeSafe и gateway failover. Политика независимого посредника не тождественна
официальному enterprise ZDR. Передаваемые excerpts ограничиваются настройкой
проекта и проходят redaction.
[Gateway privacy](https://jevtypesafeai.com/privacy).

Сравнение эффективности: total cost per accepted feature, latency до acceptance,
frontier calls/tokens, reopen rate, missed blocking defects, reruns без нового diff,
follow-up actionability. Считать весь каскад, включая дополнительный JEV и
повторные checks, а не только дешёвую цену evaluator. При подписках денежная
экономия пользователя может отличаться от API token savings.

## Реальные эксперименты

Harness: [experiment.py](experiment.py), данные [results.json](results.json),
offline checks [analyze.py](analyze.py), сводка [summary.json](summary.json).
47 реальных запросов, 24 разных простых синтетических кейса, hosted gateway,
pin `jev-1.13.0`; исходные код/логи проектов не отправлялись.

| Семейство | Calls | Согласие с заранее заданным ожиданием |
| --- | ---: | ---: |
| Model tier, включая русский prompt | 10 | 10 |
| Evidence, включая stale/self-report/skips/injection | 14 | 14 |
| Continue/replan/escalate/completion | 10 | 10 |
| Review follow-up / missing evidence | 8 | 8 |
| Epic impact score: outage vs cosmetic | 4 | 4 |
| Один mixed Choice/Score/Noul вызов | 1 | 0 по составному порогу |

В mixed call Choice contradicted имел confidence=1 и Score blocking severity=2
из 2, но Noul «CI явно сообщает failure?» вернул 0.85 при заранее выбранном
пороге >=0.9. Не меняли ожидание после получения результата. Typed response
корректен, а blanket threshold оказался непригоден даже на этом простом случае.

Для Choice normal/reversed порядок criteria не изменил labels; максимальная
разница confidence 0.11. Score rubric не переворачивалась: второй score call —
повтор, иначе изменилась бы сама шкала. Вызовы попарные, не независимая выборка.
E2E median=1100.7 ms, nearest-rank p95=1324.8 ms, range=1025.2..1430.1 ms.
Это клиентская задержка через gateway без повторного использования соединений,
не latency самой модели. Прототип измеряется отдельно.

Не проверены production calibration, полный code review, качество выполнения
выбранных coding моделей, большие epic, все языки и экономия workflow. Эти
результаты достаточны для prototype feasibility, недостаточны для automatic
acceptance. Official provider пока без оплаченных real calls: только mock/dry-run.

## План внедрения по приоритету

| Инкремент | Результат и критерий завершения | Зависимости |
| --- | --- | --- |
| P0 — CLI-прототип (этот этап) | Пять advisory presets, оба provider contracts, fixtures, real hosted smoke, offline mock tests | Нет |
| P1 — evidence и бюджет | Независимый executor records, tree/diff hashes, ledger/cache/redaction tests; raw developer prose никогда не даёт pass | P0 |
| P2 — CLI/TUI install + common policy | Opt-in registry, manifest replay/disable/upgrade, secret references, installed protocol и MCP facade; off даёт zero calls | P1 |
| P3 — native model routing | Сначала Codex/Claude/Gemini/OpenCode, per-step model catalog/capabilities, no pin override; unsupported hosts recommendation-only | P2 |
| P4 — adaptive loops + epic | Progress signatures, early escalation, dependency-feasible ordering, PO-controlled replan, bounded retries | P1/P3 |
| P5 — review action synthesis | Один итоговый next-task verdict, candidate IDs/owners/done_when, insufficient_evidence при отсутствии reports | P2 |
| P6 — quality/cost rollout | Shadow/observe corpus → assist → low-risk auto; regression evidence и общая экономика | P3–P5 |

Стартовать с evidence/ledger: без достоверных records нельзя безопасно экономить
на verification. На held-out реальных traces измерить false-support/false-complete
и недопустимый выбор слишком слабой модели; confidence сам по себе не критерий
приёмки. Для количественного gate заранее согласовать допустимый риск, объём
выборки и baseline. Например, отсутствие ошибок на 300 независимых негативных
кейсов даёт лишь приблизительную верхнюю 95% границу около 1%, а не нулевой риск.
Промпт, rubric, JEV version и host version меняются только с повторной оценкой.

## Дополнительные предложения

- Skill/workflow routing из короткого локального shortlist, включая none/clarify;
  не читать весь каталог на каждый prompt.
  [Skill suggestion](https://docs.typesafe.ai/cookbooks/skill_suggestion).
- Rerank Context7/MemPalace результатов по relevance/contradiction, сохраняя
  обязательные guidance и conflicts. Это фильтр поверх retrieval, не замена поиска.
  [RAG passage classification](https://docs.typesafe.ai/cookbooks/classifying_rag_passages).
- Durable-fact triage/canonical-home для memory-curator; executor сохраняет
  approved факт, JEV не делает automatic store/delete.
  [Memory example](https://docs.typesafe.ai/cookbooks/basic_memory).
- Context keep/truncate/drop для устаревших tool results после локальных фильтров;
  protected инструкции, acceptance, blockers и свежие execution records не удалять.
- Test-selection hints по impacted modules; mandatory/regression suites нельзя
  пропускать из-за вероятностной рекомендации.
- Blocker dedup и выбор следующей debugging hypothesis из готовых candidates;
  не просить JEV генерировать исправление.
- Opt-in risk triage tool calls как дополнительный сигнал; не выдавать JEV
  право обходить host approvals или разрешать destructive actions.

## Проверки и воспроизведение

```bash
make lint test test-coverage
make jev-rnd-verify
# Только по явной необходимости: оплаченные запросы, повторный запуск меняет результаты.
make -f docs/jev-rnd/Makefile live
make -f docs/jev-rnd/Makefile live-primitives
make jev-prototype-live
```

R&D harness по умолчанию ограничен $0.01 за основной набор; additional primitives
использует тот же сохранённый бюджет. Prototype smoke — пять небольших hosted
вызовов с защитным research budget $0.10. Это не общий production ledger.
Реальные smoke results сохраняются в [prototype-results.json](prototype-results.json).
Нормальные tests/CI не читают paid key и используют только localhost mocks.

### Реальные результаты CLI-прототипа

Дополнительно выполнены пять hosted calls через скомпилированный `agentic jev`,
стоимость $0.001170. Вместе с исследовательским набором — 52 вызова за $0.009973
в пределах разрешённых $5. Сырые структурированные ответы сохранены отдельно.

| Preset | Наблюдение | Поведение CLI |
| --- | --- | --- |
| route | fast, confidence 0.49 | low_confidence → existing_workflow |
| evidence | insufficient, confidence 0.49; fixture прямо назван synthetic | low_confidence → existing_workflow |
| loop | continue, confidence 0.99 | advisory recommendation |
| epic | Разная уверенность factors, минимум 0.45 | low_confidence → existing_workflow; blocked checkout не оценивается |
| review | docs_task, confidence 1.0 | advisory recommendation |

Транспорт/validation прошли для пяти presets, но automatic decision coverage
оказался 2/5 при prototype threshold. Это не показатель production качества:
пять prompts слишком мало, evidence fixture намеренно не настоящий run.
Особенно важно: другой wording route rubric дал гораздо меньшую уверенность
для простого typo, чем первоначальный исследовательский prompt. Прежде чем
включать auto, нужны regression fixtures на exact production rubric. Не снижать
порог до желаемого результата на этих же пяти примерах.

`make lint` проходит; `make test-coverage` — 83.21% line coverage (gate 80%),
141 Rust unit tests, 35 CLI integration tests и 13 e2e tests прошли под coverage.
Финальный `make test` также прошёл, включая шесть Python content contract tests.
Sandbox запрещал localhost bind; mock tests выполнялись с разрешением на сеть,
не с реальными API. Недостающие rustfmt/clippy/LLVM tools скачаны в `/tmp`;
системная установка и project dependencies не изменены. Existing e2e assertion
на старую версию заменён на CARGO_PKG_VERSION для корректной проверки version bump.

Acceptance checks прототипа: disabled не читает input/ключ, explicit off побеждает;
dry-run очищает fixtures без сети; official provider не использует hosted key;
stale/failed/missing/skipped records не дают положительную проверку; loop не
превышает лимит; epic не нарушает DAG; malformed/uncertain/provider errors
возвращают fallback; output не выводит произвольные provider text/баланс.

Research и prototype scope сверены отдельным read-only product-owner до
реализации. Полная публикация/включение в пользовательские проекты этим change
set не выполняется. Version Cargo/npm обновлена до 1.3.0 для нового CLI behavior.
