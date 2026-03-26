---
workflow: bundle-analyze
---

# Prompt: `/bundle-analyze`

Use when: investigating bundle size regressions or optimizing for performance budgets.

---

## Example 1 — Regression investigation

**EN:**
```
/bundle-analyze

Build artifacts: dist/ (webpack build)
Baseline: performance-budget.json (main branch)
Detected: main bundle +87KB after merging PR #203
PR added: recharts library for new dashboard charts
Budget: main bundle < 250KB gzipped (currently 337KB)
Goal: identify the culprit and options (tree-shake, lazy-load charts, or alternative library)
```

**RU:**
```
/bundle-analyze

Артефакты сборки: dist/ (webpack build)
Baseline: performance-budget.json (ветка main)
Обнаружено: main bundle +87KB после мержа PR #203
PR добавил: библиотеку recharts для новых графиков dashboard
Бюджет: main bundle < 250KB gzipped (сейчас 337KB)
Цель: определить виновника и варианты решения (tree-shake, lazy-load графиков, или альтернативная библиотека)
```

---

## Example 2 — Route-level split strategy before release

**EN:**
```
/bundle-analyze

App: customer portal (Vite + React)
Problem: /reports route initial JS payload is 1.1MB uncompressed and blocks Lighthouse performance score
Suspected contributors:
- monaco-editor loaded on initial route even though only used in one tab
- shared vendor chunk includes all chart adapters and locale data
- PDF export library imported in top-level page component
Budget target: first-load JS for /reports < 350KB gzipped
Need:
1. chunk breakdown by route and dependency
2. quick wins vs larger refactor suggestions
3. recommendation whether to lazy-load monaco/PDF export and split locale packs
Output: bundle diff report, prioritized optimization backlog, and estimate of savings per action
```

**RU:**
```
/bundle-analyze

Приложение: customer portal (Vite + React)
Проблема: initial JS payload маршрута /reports = 1.1MB без сжатия и он блокирует Lighthouse performance score
Подозреваемые источники:
- monaco-editor загружается на старте маршрута, хотя используется только в одной вкладке
- shared vendor chunk включает все chart adapters и locale data
- библиотека PDF export импортируется в top-level page component
Целевой бюджет: first-load JS для /reports < 350KB gzipped
Нужно:
1. разбивка chunk'ов по маршруту и зависимостям
2. быстрые выигрыши vs предложения для более крупного рефакторинга
3. рекомендация, нужно ли lazy-load monaco/PDF export и разделять locale packs
Результат: bundle diff report, приоритизированный optimization backlog и оценка экономии на каждое действие
```
