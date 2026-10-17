---
name: testing-patterns
description: "Provides frontend testing patterns for component tests, custom hook tests, and MSW API mocks; use when writing tests for components, hooks, or integration flows."
---

# Skill: Frontend Testing Patterns

## When to load

When writing tests for components, hooks, or integration flows.

## Philosophy

Test **behavior**, not implementation. A user doesn't care that you called `setState`; they care that clicking "Submit" shows a success message.

## Component Test Template

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserCard } from './UserCard';

const defaultUser: User = {
  id: '1', name: 'Jane Smith', email: 'jane@example.com', role: 'admin',
};

describe('UserCard', () => {
  it('renders user information', () => {
    render(<UserCard user={defaultUser} />);
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', async () => {
    const onEdit = vi.fn();
    render(<UserCard user={defaultUser} onEdit={onEdit} />);
    await userEvent.click(screen.getByRole('button', { name: /edit/i }));
    expect(onEdit).toHaveBeenCalledWith(defaultUser.id);
  });
});
```

## Custom Hook Testing

```tsx
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

it('increments count', () => {
  const { result } = renderHook(() => useCounter(0));
  act(() => { result.current.increment(); });
  expect(result.current.count).toBe(1);
});
```

## MSW: Mock API Calls

```ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/users', () =>
    HttpResponse.json([{ id: '1', name: 'Jane' }])
  ),
];
```

## Test Type Decision

| Scenario | Test Type |
|:---|:---|
| Component renders | Unit (RTL) |
| User interaction | Unit (RTL + userEvent) |
| Data fetching states | Unit (RTL + MSW) |
| Full user journey | E2E (Playwright) |
