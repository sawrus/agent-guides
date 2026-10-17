---
name: mobile-testing
description: "Provides Detox end-to-end test patterns for mobile apps; use when writing mobile E2E tests or configuring Detox."
---

# Skill: Mobile Testing (Detox)

## When to load

When writing E2E tests for mobile or configuring Detox.

## Detox Test Pattern

```typescript
describe('Login flow', () => {
  beforeAll(async () => { await device.launchApp({ newInstance: true }); });
  beforeEach(async () => { await device.reloadReactNative(); });

  it('should login with valid credentials', async () => {
    await element(by.id('email-input')).typeText('test@example.com');
    await element(by.id('password-input')).typeText('password123');
    await element(by.id('login-button')).tap();

    await waitFor(element(by.id('home-screen')))
      .toBeVisible()
      .withTimeout(5000);
  });

  it('should show error for wrong password', async () => {
    await element(by.id('email-input')).typeText('test@example.com');
    await element(by.id('password-input')).typeText('wrongpassword');
    await element(by.id('login-button')).tap();

    await waitFor(element(by.id('error-message')))
      .toBeVisible()
      .withTimeout(3000);
  });
});
```

**Key**: Use `testID` prop on elements for reliable Detox selection. Never rely on text content alone.
