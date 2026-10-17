---
name: state-sync
description: "Implements offline-first mobile state sync with optimistic updates and an MMKV offline queue; use when implementing offline-first features, handling optimistic updates, or building sync queues."
---

# Skill: Offline State Sync

## When to load

When implementing offline-first features, handling optimistic updates, or building sync queues.

## Optimistic Update Pattern

```typescript
const mutation = useMutation({
  mutationFn: api.createOrder,
  onMutate: async (newOrder) => {
    await queryClient.cancelQueries({ queryKey: ['orders'] });
    const previousOrders = queryClient.getQueryData<Order[]>(['orders']);
    queryClient.setQueryData<Order[]>(['orders'], (old = []) => [
      { ...newOrder, id: `temp_${Date.now()}`, _isOptimistic: true }, ...old
    ]);
    return { previousOrders };
  },
  onError: (_, __, context) => {
    queryClient.setQueryData(['orders'], context?.previousOrders);
    offlineQueue.enqueue({ type: 'CREATE_ORDER', payload: newOrder });
  },
});
```

## Offline Queue (MMKV)

```typescript
import { MMKV } from 'react-native-mmkv';
const storage = new MMKV({ id: 'offline-queue' });

export const offlineQueue = {
  enqueue(action) {
    const queue = this.getAll();
    storage.set('queue', JSON.stringify([...queue, { ...action, id: `action_${Date.now()}`, retryCount: 0 }]));
  },
  getAll(): QueuedAction[] {
    return JSON.parse(storage.getString('queue') ?? '[]');
  },
  async flush() {
    for (const action of this.getAll()) {
      try { await dispatch(action); this.remove(action.id); }
      catch { this.incrementRetry(action.id); }
    }
  },
};
```
