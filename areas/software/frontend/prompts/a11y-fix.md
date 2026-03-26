---
workflow: a11y-fix
---

# Prompt: `/a11y-fix`

Use when: resolving accessibility issues found in a WCAG audit or accessibility testing tool.

---

## Example 1 — Audit findings batch fix

**EN:**
```
/a11y-fix

Target: /checkout route (all 3 steps)
Audit tool: axe-core via jest-axe + manual keyboard testing
Findings:
  - [Critical] Step 2 payment form: credit card number input has no label (axe: label-content-name-mismatch)
  - [Critical] Error messages appear visually but not announced by screen reader
  - [Serious] "Continue" button disabled state not conveyed to AT (missing aria-disabled)
  - [Moderate] Focus order on mobile: jumps from address field to order summary (skips city/zip)
Designer decisions needed: error message copy (ARIA live region wording)
```

**RU:**
```
/a11y-fix

Цель: маршрут /checkout (все 3 шага)
Инструмент аудита: axe-core через jest-axe + ручное тестирование клавиатурой
Находки:
  - [Critical] Шаг 2 форма оплаты: поле номера карты без label (axe: label-content-name-mismatch)
  - [Critical] Сообщения об ошибках отображаются визуально, но не объявляются screen reader'ом
  - [Serious] Состояние disabled кнопки "Продолжить" не передаётся AT (отсутствует aria-disabled)
  - [Moderate] Порядок фокуса на мобильном: перескакивает с поля адреса на сводку заказа (пропускает city/zip)
Решения дизайнера нужны: текст сообщений об ошибках (формулировка ARIA live region)
```

---

## Example 2 — Component-level screen reader remediation

**EN:**
```
/a11y-fix

Target: AccountSecurityModal component used on /settings/security
Audit inputs:
- VoiceOver on Safari cannot identify the modal title
- Escape key closes the modal visually but focus is not returned to the trigger button
- Password strength meter changes color only; no textual announcement for screen readers
Acceptance criteria:
- dialog has correct aria-labelledby / aria-describedby wiring
- focus trap works with Tab / Shift+Tab and returns focus to the trigger on close
- strength updates are announced in an aria-live region without duplicate chatter
Output: implementation plan, component patch, test updates, and final WCAG criterion mapping
```

**RU:**
```
/a11y-fix

Цель: компонент AccountSecurityModal, используемый на /settings/security
Входные данные аудита:
- VoiceOver в Safari не может определить заголовок модального окна
- Escape визуально закрывает модалку, но фокус не возвращается на кнопку-триггер
- Индикатор сложности пароля меняет только цвет; нет текстового объявления для screen reader
Критерии приёмки:
- у dialog корректно настроены aria-labelledby / aria-describedby
- focus trap работает с Tab / Shift+Tab и возвращает фокус на триггер при закрытии
- обновления strength объявляются через aria-live без дублирующего шума
Результат: план реализации, патч компонента, обновления тестов и финальная привязка к критериям WCAG
```
