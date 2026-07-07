---
name: threat-model-review
type: workflow
trigger: /threat-model-review
description: Perform a STRIDE threat modeling session for a new feature or system component and produce a mitigation plan.
inputs:
  - feature_name
outputs:
  - threat_model_document
  - required_mitigations
roles:
  - team-lead
  - developer
  - qa
execution:
  initiator: team-lead
related-rules:
  - secure-coding.md
  - compliance-baseline.md
uses-skills:
  - threat-modeling
  - auth-patterns
quality-gates:
  - all trust boundary crossings evaluated for all 6 STRIDE categories
  - required mitigations mapped to controls before implementation
  - threat model saved to docs/security/threat-models/
---

## Steps

### 1. Parse Feature — `@team-lead`
- **Input:** feature description
- **Actions:** extract: data processed, actors, trust boundaries crossed, entry points (APIs, file inputs, queues)
- **Output:** feature decomposition note
- **Done when:** trust boundaries explicitly identified

### 2. Data Flow Diagram — `@developer`
- **Input:** feature decomposition
- **Actions:** map: External Entities → Processes → Data Stores → Trust Boundaries
- **Failure path:** if data-flow diagrams or component inventory are missing or stale, block the review and request updated architecture docs from `@team-lead`; do not model from assumptions
- **Output:** DFD (Mermaid or draw.io)
- **Done when:** all entry points visible in diagram

### 3. STRIDE Analysis — `@team-lead` + `@qa`
- **Input:** DFD
- **Actions:** for each trust boundary crossing, evaluate all 6 STRIDE categories (Spoofing / Tampering / Repudiation / Information Disclosure / Denial of Service / Elevation of Privilege); generate one finding per identified threat
- **Output:** STRIDE finding list
- **Done when:** all crossings evaluated; no category skipped

### 4. Prioritize — `@team-lead`
- **Input:** STRIDE findings
- **Actions:** score each: Likelihood (1–3) × Impact (1–3) = Risk Score; sort descending; classify: Required / Recommended / Accepted risk
- **Output:** prioritized risk register
- **Done when:** all findings classified

### 5. Generate Mitigations — `@developer`
- **Input:** prioritized risks
- **Actions:** map each Required threat to a control from `auth-patterns` or `crypto-standards` skills; document in threat model
- **Output:** `docs/security/threat-models/threat-model-<feature>.md` — DFD + STRIDE table + mitigations
- **Done when:** all Required findings have assigned controls; document complete

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /threat-model-review"])
  role_1["team-lead"]
  role_2["developer"]
  role_3["qa"]
  step_1["1. Parse Feature"]
  step_2["2. Data Flow Diagram"]
  step_3["3. STRIDE Analysis"]
  step_4["4. Prioritize"]
  step_5["5. Generate Mitigations"]
  exit(["Published threat model + Required mitigations assigned = secure implementat..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_3 -. owns .-> step_3
  role_1 -. owns .-> step_4
  role_2 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Published threat model + Required mitigations assigned = secure implementation can proceed.

**Next:** terminal — no follow-up workflow.
