# Mobile — guidance index

## What this area covers

iOS, Android, and cross-platform mobile development (React Native, Flutter): offline-first architecture, platform compliance (App Store / Play Store), performance budgets, native module integration, push notifications, OTA update delivery, release builds, and crash triage.

## Guidance chain

1. Project `.agent/` baseline (`AGENTS.md` + `.agent/*`)
2. `.agent/rules/*` — always active
3. `.agent/rules/*` — load all for this spec
4. `.agent/skills/*/SKILL.md` — load only the skill matching the current task
5. `.agent/workflows/*` — load the workflow matching the triggered command

## Inherited from general

- SDLC methodology and handoff contracts
- Git / CI / lint and code style baselines

## Mobile-specific constraints

- Offline-first is the default architecture; network availability is assumed intermittent, not guaranteed.
- Platform compliance rules (HIG for iOS, Material for Android) are enforced before store submission — not negotiable.
- Performance budget (TTI, frame rate, memory) is defined before implementing any new screen.
- Crash rate threshold defined in `rules/performance-budget.md` is a release blocker if exceeded.

## Spec map

```text
.agent/
├── rules/
│   ├── offline-first.md          ← local state, sync strategy, conflict resolution
│   ├── performance-budget.md     ← frame rate, TTI, memory, crash rate thresholds
│   ├── platform-compliance.md    ← HIG, Material, store review requirements
│   └── security-mobile.md        ← keychain/keystore, certificate pinning, jailbreak detection
├── skills/
│   ├── navigation-patterns/SKILL.md    ← stack, tab, drawer navigation; deep links
│   ├── state-sync/SKILL.md             ← optimistic UI, background sync, conflict resolution
│   ├── native-modules/SKILL.md         ← bridging, JSI, platform-specific APIs
│   ├── push-notifications/SKILL.md     ← APNs, FCM, notification permissions, rich content
│   ├── mobile-testing/SKILL.md         ← Detox, XCTest, Espresso, device farms
│   └── app-store-prep/SKILL.md         ← metadata, screenshots, signing, compliance checklist
├── workflows/
│   ├── release-build.md       ← /release-build
│   ├── store-submission.md    ← /store-submission
│   ├── crash-triage.md        ← /crash-triage
│   ├── ota-update.md          ← /ota-update
│   └── device-testing.md      ← /device-testing
└── prompts/
    └── *.md
```

## Discovery patterns

- `.agent/rules/*.md`
- `.agent/skills/*/SKILL.md`
- `.agent/workflows/*.md`
- `.agent/prompts/*.md`
