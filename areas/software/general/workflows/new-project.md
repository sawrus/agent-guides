---
name: new-project
type: workflow
trigger: /new-project
description: Start a new project from an idea to a spec, a domain model, a minimal skeleton, and a ticket list.
inputs:
  - project_idea
outputs:
  - spec
  - domain_model
  - project_skeleton
  - tickets
selection:
  general: false
  use-when: "The request starts a new project or a new repository from an idea and asks for requirements, a plan or a first structure, not a change to existing code."
  avoid-when: "The repository already has code and the request adds a feature, fixes a bug, or restructures existing code."
uses-skills: []
related-rules:
  - docs-layout.md
  - makefile-guide.md
checks:
  - make lint
  - make test
artifacts:
  - docs/spec.md
  - GLOSSARY.md
  - Makefile
---

# Start a new project

Example request: I want a service that stores customer notes and shows them in a web page; set up the project.

## Steps

### 1. Interview for requirements

- **Do:** if skill `grilling` or `grill-me` is installed, run it. Otherwise ask the user questions in rounds of
  at most five: goal, users, scope, out of scope, constraints, and success measures. Stop when each answer is
  clear.
- **Done when:** the goal, the scope, and the out-of-scope list are written down and the user confirmed them.

### 2. Write the spec

- **Do:** if skill `to-spec` is installed, run it. Otherwise write `docs/spec.md` with the goal, users,
  requirements with ids, out-of-scope items, and open questions.
- **Done when:** `docs/spec.md` exists and every requirement has an id and one checkable acceptance line.

### 3. Model the domain

- **Do:** if skill `domain-modeling` is installed, run it. Otherwise list the key terms and rules yourself. Write
  them to `GLOSSARY.md`. Write each hard-to-reverse decision as `docs/adr/0001-<slug>.md`.
- **Done when:** `GLOSSARY.md` defines each term of the spec and `docs/adr/` holds one ADR per decision.

### 4. Create the minimal skeleton

- **Do:** create only a `Makefile` with `test` and `lint` targets, one CI config that runs both, and the docs
  layout (`docs/`, `GLOSSARY.md`, `docs/adr/`). Do not add a framework or language app template. Ask the user
  to choose the stack first; leave the stack setup to the first ticket.
- **Done when:** `make test` and `make lint` run and exit 0, and the CI config calls both.

### 5. Break the work into tickets

- **Do:** if skill `to-tickets` is installed, run it. Otherwise write `docs/tickets.md`: one ticket per
  requirement id, each with a goal, an acceptance line, and its dependencies. Put the stack setup first.
- **Done when:** every requirement id appears in at least one ticket.

### 6. Install the rules and the gate

- **Do:** run `agentic install` in the project root. Commit the skeleton and the docs.
- **Done when:** `agentic install` exits 0, the quality gate is in place, and all `checks` commands exit 0.
