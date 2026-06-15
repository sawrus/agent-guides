---
name: a11y-fix
type: workflow
trigger: /a11y-fix
description: Detect, fix, and validate accessibility issues for UI routes or components with WCAG compliance evidence.
inputs:
  - target_route_or_component
outputs:
  - remediated_accessibility_issues
  - a11y_report
roles:
  - qa
  - designer
  - developer
  - team-lead
execution:
  initiator: qa
related-rules:
  - accessibility.md
  - quality.md
uses-skills:
  - a11y-audit
  - testing-patterns
quality-gates:
  - no blocking WCAG A issues remaining
  - keyboard and screen-reader critical paths validated
  - automated a11y checks pass in CI
---

## Steps

### 1. Audit & Severity Classification — `@qa`
- **Input:** target route or component
- **Actions:** run automated audit (axe, Lighthouse, jest-axe); classify each finding by WCAG level (A / AA / AAA) and user impact; identify keyboard navigation and screen reader critical paths
- **Output:** `a11y_audit.md` — finding list with WCAG criterion, severity, and affected element
- **Done when:** all findings classified; critical path issues flagged

### 2. UX Decision for Ambiguous Fixes — `@designer`
- **Input:** audit findings that require UX judgment (alt text wording, focus order, label copy)
- **Actions:** review findings requiring design input; provide decisions on: alt text wording, ARIA label content, focus order, color contrast alternatives
- **Output:** design decisions documented per ambiguous finding
- **Done when:** all ambiguous findings have designer-approved decisions

### 3. Implement Fixes — `@developer`
- **Input:** audit + design decisions
- **Actions:** implement ARIA attributes, role corrections, focus management, color contrast fixes, keyboard handler improvements; follow `accessibility.md` rules; do not introduce visual regressions
- **Output:** fixes on feature branch
- **Done when:** all A-level issues addressed; AA issues addressed per project policy

### 4. Re-test & Regression Checks — `@qa`
- **Input:** fix branch
- **Actions:** re-run automated audit: zero new WCAG A issues; test keyboard navigation (Tab / Shift+Tab / Enter / Escape / Arrow keys); test with screen reader on at least one critical path; run visual regression to confirm no visual regressions
- **Output:** updated `a11y_report.md` — before/after comparison
- **Done when:** zero blocking A issues; critical keyboard and screen reader paths confirmed

### 5. Final Review & Acceptance — `@team-lead`
- **Input:** a11y report + fix branch
- **Actions:** verify fixes are complete and don't introduce regressions; sign off on WCAG compliance status
- **Output:** `@team-lead` approval
- **Done when:** approved; CI a11y checks added or confirmed

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /a11y-fix"])
  role_1["qa"]
  role_2["designer"]
  role_3["developer"]
  role_4["team-lead"]
  step_1["1. Audit & Severity Classification"]
  step_2["2. UX Decision for Ambiguous Fixes"]
  step_3["3. Implement Fixes"]
  step_4["4. Re-test & Regression Checks"]
  step_5["5. Final Review & Acceptance"]
  exit(["Zero WCAG A issues + screen reader path validated + @team-lead approval = a..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_3 -. owns .-> step_3
  role_1 -. owns .-> step_4
  role_4 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Zero WCAG A issues + screen reader path validated + `@team-lead` approval = a11y fix complete.
