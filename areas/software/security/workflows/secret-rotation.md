---
name: secret-rotation
type: workflow
trigger: /secret-rotation
description: Safely rotate a production secret with zero downtime using dual-read window.
inputs:
  - secret_name
  - is_emergency
outputs:
  - rotated_secret
  - audit_record
roles:
  - developer
  - team-lead
execution:
  initiator: developer
related-rules:
  - secrets-policy.md
  - security-posture.md
uses-skills:
  - secrets-management
quality-gates:
  - old credential revoked only after zero auth errors confirmed
  - audit log entry created with rotation metadata
  - next rotation date set (+90 days)
---

## Steps

### 1. Prepare New Secret — `@developer`
- **Input:** secret name
- **Actions:** generate new credential (strong, random); store in Secrets Manager as new version — old version stays active
- **Output:** new secret version created; old version still active
- **Done when:** both versions active in Secrets Manager

### 2. Dual-Read Window — `@developer`
- **Input:** new secret version
- **Actions:** update service to accept BOTH old and new credential; if single-credential only → schedule 2-minute maintenance window
- **Output:** service accepts both versions
- **Done when:** service deployed with dual-read capability

### 3. Deploy New Secret — `@developer`
- **Input:** dual-read service
- **Actions:** trigger rolling restart to pick up new version; monitor pod restarts and error rates for 5 minutes
- **Output:** all pods using new secret
- **Done when:** zero auth errors post-restart

### 4. Validate — `@team-lead`
- **Input:** deployed rotation
- **Actions:** confirm zero auth errors in monitoring; verify old credential is rejected by service
- **Output:** validation confirmation
- **Done when:** old credential confirmed rejected

### 5. Revoke Old Secret — `@developer`
- **Input:** validated rotation
- **Actions:** delete old version from Secrets Manager; confirm no reads on old version in audit log
- **Output:** old secret version deleted
- **Done when:** audit log confirms zero reads on old version

### 6. Document — `@developer`
- **Input:** completed rotation
- **Actions:** record in secret inventory: name, date, rotated by; set next rotation date (+90 days)
- **Output:** audit record updated
- **Done when:** inventory current; next rotation scheduled

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /secret-rotation"])
  role_1["developer"]
  role_2["team-lead"]
  step_1["1. Prepare New Secret"]
  step_2["2. Dual-Read Window"]
  step_3["3. Deploy New Secret"]
  step_4["4. Validate"]
  step_5["5. Revoke Old Secret"]
  step_6["6. Document"]
  exit(["Old secret revoked + audit record updated = rotation complete."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> step_6
  step_6 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_1 -. owns .-> step_5
  role_1 -. owns .-> step_6
```
<!-- agent-diagram:end -->

## Exit
Old secret revoked + audit record updated = rotation complete.
