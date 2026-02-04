---
trigger: model_decision
glob: domain-models-guide
description: ensure strong, explicit, validated domain models
---

# Domain Models Rule

**Goal:** all domain data must be explicit, validated, and modeled.

**Rules:**

- No raw data flows; every domain concept must have a model.
- **Pydantic mandatory** for domain models, I/O contracts, config, validation.
- **SQLModel mandatory** for database models.
- Validation logic lives inside models; models are explicit, strongly typed.
- Prefer value objects over primitives when meaning or validation exists.
- Explicit fields/types only; no dynamic fields, magic defaults, or hybrid models.
- Serialization explicit; no dict spreading, no leaking internal structure.

**Violations:**

- Raw dicts between layers.
- Validation outside models.
- Optional fields “just in case”.
- Models depend on infrastructure.
- Silent coercion of invalid data.
- Pydantic bypassed or inconsistent.
