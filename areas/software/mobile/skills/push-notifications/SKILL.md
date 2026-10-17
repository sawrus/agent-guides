---
name: push-notifications
description: "Implements mobile push notifications with well-timed permission requests and deep-linking notification categories; use when implementing push notifications, handling notification permissions, or debugging delivery."
---

# Skill: Push Notifications

## When to load

When implementing push notifications, handling notification permissions, or debugging delivery.

## Permission Request (Ask at Right Moment)

```typescript
// ❌ Never ask at app launch
// ✅ Ask when user understands the value
async function requestNotificationPermission(context: string): Promise<boolean> {
  // Show custom pre-permission explanation first
  const userAgreed = await showNotificationExplanation(context);
  if (!userAgreed) return false;

  const { status } = await Notifications.requestPermissionsAsync();
  return status === 'granted';
}
```

## Notification Categories (Deep Link on Tap)

```typescript
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

// Handle tap → navigate to correct screen
Notifications.addNotificationResponseReceivedListener(response => {
  const data = response.notification.request.content.data;
  if (data.type === 'order_update') {
    navigationRef.navigate('OrderDetail', { orderId: data.order_id });
  }
});
```
