# Question Bank — Prompt Project Planner

Questions are asked BY SECTIONS and IN ORDER.
If the answer is already known, skip the question.

---

## 1. Project Context

- Is this a new project or an extension of an existing one?
- Are there legacy constraints?
- Are deadlines critical?
- Is this production or PoC?

---

## 2. Technical Stack

- Programming language and version?
- Primary framework?
- Async or background processing involved?
- Any restricted or forbidden libraries?

---

## 3. Data & Inputs

- Data source? (Kafka / HTTP / DB / Files)
- Is the input format stable?
- Is idempotency required?
- Expected data volume?

---

## 4. Business Logic

- Primary goal of the processing?
- Key invariants that must not be violated?
- What is considered an error?
- Critical edge cases?

---

## 5. Storage

- New tables or existing ones?
- Are migrations required?
- Consistency requirements?
- Expected data growth?

---

## 6. Integrations

- External services involved?
- Contracts or schemas defined?
- Synchronous or asynchronous interaction?

---

## 7. Non-functional Requirements

- Performance expectations?
- Logging and metrics requirements?
- Required test coverage?
- Security constraints?

---

## 8. Delivery

- Feature flags required?
- Rollback strategy needed?
- CI/CD constraints?

---

## Stop Condition

When all sections are answered, proceed to plan generation.
