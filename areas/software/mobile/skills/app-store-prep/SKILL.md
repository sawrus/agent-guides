---
name: app-store-prep
description: "Provides a pre-submission checklist for App Store and Google Play releases; use when preparing a mobile release build or responding to store rejection reasons."
---

# Skill: App Store Submission Preparation

## When to load

When preparing a release build or responding to rejection reasons.

## Pre-Submission Checklist

### Both Platforms
- [ ] Version code/build number incremented
- [ ] Release notes written (plain language, user-facing changes)
- [ ] All new permissions declared with usage descriptions
- [ ] Deep links tested end-to-end
- [ ] Crash-free rate > 99.5% in pre-release testing
- [ ] No debug flags in release build

### iOS Specific
- [ ] `Info.plist` usage descriptions for all capabilities
- [ ] Privacy nutrition labels updated in App Store Connect
- [ ] TestFlight validated on ≥ 5 real devices
- [ ] Screenshots updated for new features

### Android Specific
- [ ] `targetSdkVersion` current year's API level
- [ ] Data safety form updated in Play Console
- [ ] App Bundle (`.aab`) submitted (not APK)
- [ ] Internal → Closed → Production promotion flow followed
