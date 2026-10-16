---
name: api-integration
description: "Provides frontend API integration patterns for a standard fetch layer, loading and error states, and optimistic updates; use when connecting a component to a REST API or implementing optimistic updates."
---

# Skill: API Integration Patterns

## When to load

When connecting a component to a REST API, handling loading/error states, or implementing optimistic updates.

## Standard Fetch Layer

```ts
const apiClient = {
  get: async <T>(path: string, options?: RequestInit): Promise<T> => {
    const res = await fetch(`${import.meta.env.VITE_API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
        ...options?.headers,
      },
    });
    if (!res.ok) throw new ApiError(res.status, await res.json());
    return res.json();
  },
};
```

## Loading & Error States

```tsx
const UserList = () => {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => apiClient.get<User[]>('/users'),
  });

  if (isLoading) return <UserListSkeleton />;
  if (isError) return <ErrorMessage message={error.message} />;

  return <ul>{data.map(user => <UserItem key={user.id} user={user} />)}</ul>;
};
```

## Optimistic Updates

```tsx
const mutation = useMutation({
  mutationFn: (id: string) => apiClient.delete(`/todos/${id}`),
  onMutate: async (id) => {
    await queryClient.cancelQueries({ queryKey: ['todos'] });
    const previous = queryClient.getQueryData<Todo[]>(['todos']);
    queryClient.setQueryData<Todo[]>(['todos'], old => old?.filter(t => t.id !== id));
    return { previous };
  },
  onError: (_err, _id, context) => {
    queryClient.setQueryData(['todos'], context?.previous);
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['todos'] }),
});
```
