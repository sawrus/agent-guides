---
workflow: scaffold-component
---

# Prompt: `/scaffold-component`

Use when: creating a new reusable UI component from scratch.

---

## Example 1 — Form component with validation

**EN:**
```
/scaffold-component "DateRangePicker"

Purpose: allow users to select a start and end date for filtering reports
Design system: Tailwind + shadcn/ui; use existing Calendar primitive
States: default, focused, filled, error (invalid range: end before start), disabled
Accessibility: keyboard navigation (Arrow keys in calendar), screen reader announces selected range
API:
  - value?: { from: Date; to?: Date }
  - onChange: (range: { from: Date; to?: Date }) => void
  - minDate?: Date; maxDate?: Date
  - error?: string
Consumer context: used in Reports filter bar, works with react-hook-form
```

**RU:**
```
/scaffold-component "DateRangePicker"

Назначение: позволяет пользователям выбрать диапазон дат для фильтрации отчётов
Дизайн система: Tailwind + shadcn/ui; использовать существующий Calendar primitive
Состояния: default, focused, filled, error (невалидный диапазон: end раньше start), disabled
Доступность: навигация клавиатурой (стрелки в календаре), screen reader объявляет выбранный диапазон
API:
  - value?: { from: Date; to?: Date }
  - onChange: (range: { from: Date; to?: Date }) => void
  - minDate?: Date; maxDate?: Date
  - error?: string
Контекст: используется в Reports filter bar, совместим с react-hook-form
```

---

## Example 2 — Display component

**EN:**
```
/scaffold-component "StatusBadge"

Purpose: display entity status with color-coded visual (order status, user role, etc.)
States: pending (yellow), active (green), cancelled (red), archived (gray)
Props: status: string; size?: 'sm' | 'md'
No interactive state — purely visual
Must work in both light and dark mode (use CSS custom properties)
```

**RU:**
```
/scaffold-component "StatusBadge"

Назначение: отображение статуса сущности с цветовой кодировкой (статус заказа, роль пользователя и т.д.)
Состояния: pending (жёлтый), active (зелёный), cancelled (красный), archived (серый)
Props: status: string; size?: 'sm' | 'md'
Интерактивных состояний нет — только визуальный компонент
Должен работать в light и dark режиме (использовать CSS custom properties)
```
