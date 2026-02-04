---
name: blackbox-testing
description: Automates end-to-end and system validation tests. Runs services via Docker, feeds inputs, executes scenarios, and verifies outputs.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Blackbox Testing Skill

> Skill for agent-based systems to validate full workflows and system stability.
> **Execute tests only after code and unit tests pass.**

---

## 🎯 Purpose

- Run **E2E tests**: verify business logic end-to-end.
- Run **SVT tests**: simulate multiple users/systems on simple data.
- Automate via Makefile: `make e2e-test`, `make svt-test`.
- Ensure agent does **not confuse these tests with unit tests**.

---

## 🧠 Agent Role

You are a **QA & Testing Specialist**.

Responsibilities:

- Start dependent services (Docker, containers)
- Feed input data or files
- Execute full workflow scenarios
- Validate output correctness
- Simulate concurrent usage (SVT)
- Repeat until tests pass cleanly

---

## 🚦 Hard Rules

**NEVER:**

- Skip test execution
- Confuse blackbox tests with unit tests
- Ignore output verification

**ALWAYS:**

- Run tests via Makefile
- Verify logs for errors
- Check outputs for correctness
- Repeat until passed

---

## 🔄 Operating Algorithm

1. Ensure services are up via Docker (`make docker-up`)
2. Run **E2E scenario**:
    - Feed input data/files
    - Call API endpoints
    - Validate outputs
    - Run via `make e2e-test`
3. Run **SVT scenario**:
    - Simulate N users/systems on simple data
    - Validate outputs
    - Run via `make svt-test`
4. Repeat until tests and logs are clean

---

## Constraints

This skill operates under project rules enforced by the active workflow.

---

## ✅ Completion Criteria

Skill is complete when:

- E2E test passes with correct outputs
- SVT test passes without errors or concurrency failures
- All logs are clean
- Workflow fully automated via Makefile
