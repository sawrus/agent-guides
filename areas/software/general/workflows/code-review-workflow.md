---
name: code-review-workflow
type: workflow
trigger: /code-review
description: Conduct a structured, constructive code review of a pull or merge request.
inputs:
  - pull_request_or_merge_request
  - codebase_context
outputs:
  - review_comments
  - approval_or_change_requests
roles:
  - team-lead
  - developer
  - qa
execution:
  initiator: developer
related-rules:
  - code-style-guide.md
  - git-workflow-guide.md
  - sdlc-methodology-guide.md
uses-skills:
  - general-dev-tools
quality-gates:
  - CI pipeline passes before manual review begins
  - all blocking comments resolved before approval
  - no secrets or credentials in diff
---

## Steps

### 1. Automated Pre-check — `@developer` (author)
- **Input:** feature branch with changes
- **Actions:** confirm CI passes (lint / tests / build); no merge conflicts; branch up to date with target
- **Output:** CI-green PR
- **Done when:** automated checks pass — only then request review

### 2. Context Understanding — `@team-lead`
- **Input:** PR description and linked issue/task
- **Actions:** read PR description and linked ticket; check scope focus; if diff > 400 lines of logic — request splitting the PR
- **Output:** decision to proceed or split
- **Done when:** reviewer understands the intent and scope is acceptable

### 3. Code Review — `@team-lead` + `@qa`
- **Input:** PR diff + context
- **Actions — Correctness:**
  - Does the code do what the ticket describes?
  - Are edge cases and error paths handled?
- **Actions — Design & Architecture:**
  - Does the change follow existing codebase patterns?
  - No unnecessary complexity or over-engineering?
  - Abstractions at the right level?
- **Actions — Code Quality:**
  - Names are clear and intention-revealing?
  - No duplicated logic that could be extracted?
  - No magic numbers or strings?
- **Actions — Tests:**
  - New behaviors covered by tests?
  - Tests assert meaningful behavior, not implementation details?
  - Edge cases tested?
- **Actions — Security:**
  - No secrets or credentials committed
  - User input validated/sanitized
  - Permissions and access control respected
- **Output:** review comments with blocking / non-blocking labels; at least one positive comment
- **Done when:** all review dimensions checked

### 4. Feedback Resolution — `@developer`
- **Input:** review comments
- **Actions:** address all blocking comments; push fixes as new commits (no force-push during review); re-request review
- **Output:** updated PR
- **Done when:** no open blocking comments

### 5. Approval & Merge — `@team-lead`
- **Input:** resolved PR
- **Actions:** re-check fixes; approve; author squashes or rebases per project convention; merge; delete feature branch
- **Output:** merged PR; branch deleted
- **Done when:** change merged and feature branch removed

## Iteration Loop
If fixes introduce new issues → reviewer re-raises blocking comments; loop repeats until clean.

## Exit
Approved and merged PR = review complete.
