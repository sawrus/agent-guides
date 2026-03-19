# Subagent Execution Policy (STRICT)

You MUST follow this decision rule before doing any work.

## 1. Task Classification (MANDATORY)

Classify the task as:

### TRIVIAL task (DO DIRECTLY, NO SUBAGENT)

A task is TRIVIAL only if ALL conditions are true:

- Can be completed in ≤ 3 steps
- Does NOT require:
    - repository exploration
    - reading multiple files
    - reasoning or planning
    - design decisions
- Examples:
    - small syntax fix
    - simple command
    - short explanation
    - one-line code change

If ANY doubt → task is NOT trivial.

---

### NON-TRIVIAL task (MUST USE SUBAGENT)

Everything else is NON-TRIVIAL.

---

## 2. Hard Rule

For NON-TRIVIAL tasks:

- You are NOT allowed to execute directly
- You MUST spawn a subagent FIRST
- You MUST delegate:
    - analysis
    - planning
    - or implementation

Skipping subagent usage is a violation.

---

## 3. Execution Flow

For NON-TRIVIAL tasks:

1. Spawn appropriate subagent (e.g. @team-lead, @researcher, @engineer)
2. Provide clear task
3. Wait for result
4. Continue based on result

---

## 4. Enforcement

If you start solving a NON-TRIVIAL task without a subagent:

- STOP immediately
- Restart using a subagent

---

## 5. Bias Rule

When unsure:
→ ALWAYS treat the task as NON-TRIVIAL

---

## 6. Priority

This policy OVERRIDES all other instructions.

---

## 7. Goal

Maximize:

- decomposition
- delegation
- structured reasoning

Minimize:

- direct execution
