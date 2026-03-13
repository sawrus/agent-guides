# Agent Prompts — Generate a New Area from GUIDE.md

---

## Short prompt

**EN:**

```
Read the file areas/templates/GUIDE.md completely before doing anything else.

After reading, build a new area: areas/marketing

Work through all 8 phases in order. At each Phase checkpoint, output the
checklist with every item explicitly marked ✅ or ❌ before proceeding.
Do not generate any files until Phase 3.

Domain context to use in Phase 1:
- Practitioners: copywriter, SEO specialist, paid media manager,
  content strategist, email marketer, brand manager, analytics manager
- Tools: HubSpot, Ahrefs, Meta Ads Manager, Google Ads, Mailchimp,
  Figma, GA4, Notion, Semrush, Canva
- A "production incident" = campaign live with wrong audience targeting,
  compliance violation in ad copy, email sent to wrong segment
- Language: all prompt examples must be bilingual EN + RU

Stop after Phase 2 and show me the taxonomy.
Wait for my confirmation before proceeding to Phase 3.
```

---

**RU:**

```
Прочитай файл areas/templates/GUIDE.md полностью, прежде чем делать что-либо ещё.

После прочтения построй новую область: areas/marketing

Проходи все 8 фаз по порядку. В конце каждой фазы выведи чеклист
с явной пометкой ✅ или ❌ для каждого пункта, и только потом переходи дальше.
Не генерируй никаких файлов до Фазы 3.

Контекст домена для Фазы 1:
- Специалисты: копирайтер, SEO-специалист, менеджер платного трафика,
  контент-стратег, email-маркетолог, бренд-менеджер, аналитик перформанса
- Инструменты: HubSpot, Ahrefs, Meta Ads Manager, Google Ads, Mailchimp,
  Figma, GA4, Notion, Semrush, Canva
- «Производственный инцидент» = кампания запущена на неправильную аудиторию,
  нарушение комплаенса в рекламном тексте, письмо отправлено не тому сегменту
- Язык: все примеры в промптах должны быть двуязычными EN + RU

Остановись после Фазы 2 и покажи мне таксономию.
Жди моего подтверждения перед тем, как переходить к Фазе 3.
```

---

## Full prompt

**EN:**

```
## Task: Generate a new agent-guides area

### Step 0 — Load the guide (do this first, nothing else)
Read the file at this path: areas/templates/GUIDE.md
Confirm you have read it by outputting:
  1. The first sentence of Phase 1
  2. The total number of phases
  3. The names of all 4 artifact types defined in the Concepts section

Do not proceed to Step 1 until you have output all three confirmations.

### Step 1 — Domain analysis (GUIDE.md Phase 1)
Answer all 7 questions from section 1.1 for domain: marketing
Use this seed data:

Practitioners:
  - Copywriter (landing pages, ads, email, UX copy)
  - SEO specialist (keyword research, on-page, technical SEO, link building)
  - Paid media manager (Meta Ads, Google Ads, programmatic)
  - Content strategist (editorial planning, thought leadership, distribution)
  - Email marketer (campaigns, automation, list segmentation)
  - Brand manager (voice, identity, guidelines enforcement)
  - Performance analyst (attribution, A/B testing, reporting)

Core tools:
  HubSpot, Ahrefs, Semrush, Meta Ads Manager, Google Ads,
  Google Analytics 4, Mailchimp / Klaviyo, Notion, Figma, Canva

A "production incident" is any of:
  - Campaign running with wrong audience → budget waste
  - Ad copy with unsubstantiated claim → legal / compliance risk
  - Email sent to wrong segment or without unsubscribe → GDPR violation
  - Brand asset published outside style guide → brand inconsistency

Non-negotiable constraints:
  - No unsubstantiated performance claims ("guaranteed results", "#1")
  - All email must comply with CAN-SPAM / GDPR
  - Paid copy must match landing page message (Google Quality Score)
  - Budget changes above €500 require manager approval

Output: Phase 1 answers in full + Phase 1 checkpoint with every item ✅ or ❌.

### Step 2 — Taxonomy design (GUIDE.md Phase 2)
Using the output of Step 1, complete Phase 2:
  - Map activity clusters to specializations
  - Validate each spec against the 5-item checklist from section 2.2
  - Draw the lifecycle axis (section 2.3)
  - Output the final directory tree (section 2.4)

Constraints:
  - Target 7–8 specs. Minimum 6, maximum 9.
  - Each spec must have a clear single-role owner
  - No two specs may share more than 20% of their activities

Output: taxonomy directory tree + lifecycle axis diagram + Phase 2 checkpoint.
Then STOP. Do not proceed to Phase 3 until I confirm the taxonomy.

### Step 3 — [Send this after confirming the taxonomy]
Proceed to Phase 3 (scaffold) and Phase 4 (rules).
Build all rules for every spec before moving to Phase 5.
After completing Phase 4, output the Phase 4 checkpoint for each spec,
then stop and wait.

### Step 4 — [Send this after confirming rules]
Proceed to Phase 5 (skills).
Build all skills for every spec before moving to Phase 6.
Constraint: every skill must contain at least 2 real, non-placeholder examples.
After completing Phase 5, output the Phase 5 checkpoint for each spec,
then stop and wait.

### Step 5 — [Send this after confirming skills]
Proceed to Phase 6 (workflows) and Phase 7 (prompts) together.
All prompt examples must be bilingual: EN block followed by RU block.
No placeholder strings of the form [YOUR X] or {{INSERT_Y}} are permitted.
After completing both phases, run Phase 8 (quality gate) and output
the completeness matrix and lifecycle coverage audit.
```

---

**RU:**

```
## Задача: сгенерировать новую область agent-guides

### Шаг 0 — Загрузи guide (сделай это первым, ничего больше)
Прочитай файл по пути: areas/templates/GUIDE.md
Подтверди прочтение, выведя:
  1. Первое предложение Фазы 1
  2. Общее количество фаз
  3. Названия всех 4 типов артефактов из раздела Concepts

Не переходи к Шагу 1 до тех пор, пока не выведешь все три подтверждения.

### Шаг 1 — Анализ домена (GUIDE.md Фаза 1)
Ответь на все 7 вопросов из раздела 1.1 для домена: маркетинг
Используй следующие исходные данные:

Специалисты:
  - Копирайтер (лендинги, реклама, email, UX-тексты)
  - SEO-специалист (подбор ключей, on-page, технический SEO, линкбилдинг)
  - Менеджер платного трафика (Meta Ads, Google Ads, programmatic)
  - Контент-стратег (редпланирование, thought leadership, дистрибуция)
  - Email-маркетолог (кампании, автоматизации, сегментация базы)
  - Бренд-менеджер (голос бренда, айдентика, соблюдение гайдлайнов)
  - Аналитик перформанса (атрибуция, A/B-тесты, отчётность)

Основные инструменты:
  HubSpot, Ahrefs, Semrush, Meta Ads Manager, Google Ads,
  Google Analytics 4, Mailchimp / Klaviyo, Notion, Figma, Canva

«Производственный инцидент» — любое из следующего:
  - Кампания запущена на неправильную аудиторию → перерасход бюджета
  - Рекламный текст с недоказанным утверждением → юридический / комплаенс-риск
  - Письмо отправлено не тому сегменту или без кнопки отписки → нарушение GDPR
  - Брендовый материал опубликован вне стайлгайда → размытие бренда

Обязательные ограничения:
  - Запрещены недоказанные заявления о результатах («гарантированный рост», «лучший в отрасли»)
  - Все email-рассылки должны соответствовать CAN-SPAM / GDPR
  - Текст платной рекламы обязан совпадать с сообщением лендинга (Google Quality Score)
  - Изменения бюджета свыше €500 требуют согласования с руководителем

Вывод: полные ответы на вопросы Фазы 1 + чеклист Фазы 1 с пометкой ✅ или ❌ для каждого пункта.

### Шаг 2 — Построение таксономии (GUIDE.md Фаза 2)
Используя результаты Шага 1, выполни Фазу 2:
  - Сопоставь кластеры активностей со специализациями
  - Проверь каждый spec по чеклисту из раздела 2.2 (5 пунктов)
  - Нарисуй ось жизненного цикла (раздел 2.3)
  - Выведи финальное дерево директорий (раздел 2.4)

Ограничения:
  - Целевое количество specs: 7–8. Минимум 6, максимум 9.
  - У каждого spec должен быть один чёткий владелец-роль
  - Два spec не могут пересекаться более чем на 20% активностей

Вывод: дерево директорий таксономии + диаграмма оси жизненного цикла + чеклист Фазы 2.
Затем ОСТАНОВИСЬ. Не переходи к Фазе 3 до моего подтверждения таксономии.

### Шаг 3 — [Отправь после подтверждения таксономии]
Переходи к Фазе 3 (скаффолдинг) и Фазе 4 (rules).
Построй все rules для каждого spec прежде чем переходить к Фазе 5.
После завершения Фазы 4 выведи чеклист Фазы 4 для каждого spec,
затем остановись и жди.

### Шаг 4 — [Отправь после подтверждения rules]
Переходи к Фазе 5 (skills).
Построй все skills для каждого spec прежде чем переходить к Фазе 6.
Ограничение: каждый skill обязан содержать минимум 2 реальных, непустых примера.
После завершения Фазы 5 выведи чеклист Фазы 5 для каждого spec,
затем остановись и жди.

### Шаг 5 — [Отправь после подтверждения skills]
Переходи к Фазе 6 (workflows) и Фазе 7 (prompts) одновременно.
Все примеры в промптах должны быть двуязычными: блок EN, затем блок RU.
Строки-заглушки вида [YOUR X] или {{INSERT_Y}} запрещены.
После завершения обеих фаз выполни Фазу 8 (quality gate) и выведи
матрицу полноты и аудит покрытия жизненного цикла.
```
