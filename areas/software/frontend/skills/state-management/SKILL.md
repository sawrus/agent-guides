---
name: state-management
description: "Classifies frontend state and applies colocation, React Query, and Zustand slice patterns; use when deciding where to put state, choosing between local and global state, integrating server state, or debugging stale data."
---

# Skill: State Management

## When to load

When deciding where to put state, choosing between local/global state, integrating server state, or debugging stale data.

## State Classification Matrix

| State Type | Example | Solution |
|:---|:---|:---|
| **Local UI State** | Modal open/close, input focus | `useState` / `useReducer` |
| **Shared UI State** | Theme, sidebar collapse | React Context + `useReducer` |
| **Server/Remote State** | API data, pagination | React Query / SWR |
| **URL State** | Filters, search params | `useSearchParams` |
| **Global App State** | Auth session, shopping cart | Zustand / Redux Toolkit |
| **Form State** | Input values, validation errors | React Hook Form |

## Colocation Rule

State should live as **close to where it's used** as possible. Only lift state up when two components genuinely need to share it.

```
❌ Storing modal visibility in a global store
✅ Storing modal visibility in the component that renders the modal
```

## React Query: Key Patterns

```tsx
const { data } = useQuery({
  queryKey: ['users', { page, filters }],
  queryFn: () => fetchUsers({ page, filters }),
  staleTime: 5 * 60 * 1000,
});

const mutation = useMutation({
  mutationFn: createUser,
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
});
```

## Zustand: Slice Pattern

```ts
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  login: async (credentials) => {
    const { user, token } = await authApi.login(credentials);
    set({ user, token });
  },
  logout: () => set({ user: null, token: null }),
}));
```
