---
workflow: visual-regression
---

# Prompt: `/visual-regression`

Use when: detecting unintended UI changes before merging a PR or releasing.

---

## Example 1 — PR visual diff review

**EN:**
```
/visual-regression

Scope: components changed in PR #156 (Button, Card, Modal)
Baseline: main branch snapshots (Percy baseline)
Changed: updated design tokens (spacing +4px, border-radius change)
Expected diffs: all Button, Card sizes will have slightly more padding - intentional
Unexpected diffs to catch: any text overflow, icon misalignment, broken dark mode
Designer must review: all diffs before baseline is updated
```

**RU:**
```
/visual-regression

Скоуп: компоненты изменённые в PR #156 (Button, Card, Modal)
Baseline: снапшоты ветки main (Percy baseline)
Изменено: обновлены design tokens (spacing +4px, изменение border-radius)
Ожидаемые diff: все размеры Button, Card будут иметь немного больше отступов - намеренно
Неожиданные diff для обнаружения: любое переполнение текста, смещение иконок, сломанный dark mode
Дизайнер должен проверить: все diff перед обновлением baseline
```

---

## Example 2 — Release candidate route sweep

**EN:**
```
/visual-regression

Scope: release candidate v4.3.0 on routes /pricing, /signup, /checkout, /account/billing
Baseline source: Chromatic snapshots from main after design system token freeze
Recent changes:
- pricing cards switched to responsive CSS grid
- signup flow moved validation messages from inline text to floating summary panel
- checkout uses a new sticky order summary on tablet widths
Acceptance criteria:
- no overlap or clipping in EN + DE locales
- loading and error states reviewed in light and dark themes
- approved intentional diffs documented before updating the baseline
Output: visual diff report grouped by route, list of blocker diffs, and approved baseline updates with designer sign-off
```

**RU:**
```
/visual-regression

Скоуп: release candidate v4.3.0 для маршрутов /pricing, /signup, /checkout, /account/billing
Источник baseline: Chromatic snapshots из main после заморозки design system token'ов
Недавние изменения:
- pricing cards переведены на responsive CSS grid
- signup flow перенёс validation messages из inline текста в floating summary panel
- checkout использует новый sticky order summary на tablet-ширинах
Критерии приёмки:
- отсутствие overlap или clipping в локалях EN + DE
- loading и error состояния проверены в light и dark themes
- все намеренные diff'ы задокументированы до обновления baseline
Результат: visual diff report, сгруппированный по маршрутам, список blocker diff'ов и approved baseline updates с sign-off от дизайнера
```
