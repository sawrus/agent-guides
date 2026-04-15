---
name: component-design
type: skill
description: "Design reusable React components with compound patterns, controlled/uncontrolled hybrids, typed prop APIs, async state handling, and ARIA accessibility. Use when the user creates, refactors, or reviews React components, or mentions props, hooks, .tsx files, component APIs, or accessible UI patterns."
related-rules:
  - architecture.md
  - accessibility.md
allowed-tools: Read, Write, Edit, Bash
---

# Component Design Patterns Skill

> **Expertise:** Compound components, controlled/uncontrolled, render props, component API design, accessibility requirements.

## When to load

When creating, refactoring, or reviewing React components — especially when choosing between compound, controlled/uncontrolled, or headless patterns, designing typed prop APIs, or implementing accessible interactive widgets.

## Component Design Workflow

1. **Choose pattern** — use the decision tree below to select the right component pattern
2. **Define typed props** — follow the Props API Design Rules (explicit variants, no boolean explosion)
3. **Implement all states** — loading, error, empty, success for any async data
4. **Add accessibility** — use the ARIA requirements table to add correct roles and keyboard support
5. **Verify** — confirm keyboard navigation works, screen reader announces states, and TypeScript compiles with `--strict`

## Pattern Selection Guide

```
Multiple visual zones in one component?         → Slot / Children Props
Coordinated subcomponents sharing state?        → Compound Components
Works with react-hook-form / external control?  → Controlled/Uncontrolled Hybrid
Self-contained widget with internal state?      → Uncontrolled with defaults
Highly customizable rendering?                  → Render Props / Headless
```

## Pattern 1: Compound Components

Use when: a component has multiple coordinated parts sharing implicit state.

```tsx
// Context shared between sub-components
const MenuContext = createContext<{ open: boolean; toggle: () => void } | null>(null);

const Menu = ({ children }: { children: React.ReactNode }) => {
  const [open, setOpen] = useState(false);
  return (
    <MenuContext.Provider value={{ open, toggle: () => setOpen(o => !o) }}>
      <div role="menu" aria-expanded={open}>{children}</div>
    </MenuContext.Provider>
  );
};

Menu.Trigger = function MenuTrigger({ children }: { children: React.ReactNode }) {
  const ctx = useContext(MenuContext)!;
  return (
    <button onClick={ctx.toggle} aria-haspopup="true" aria-expanded={ctx.open}>
      {children}
    </button>
  );
};

Menu.Items = function MenuItems({ children }: { children: React.ReactNode }) {
  const { open } = useContext(MenuContext)!;
  if (!open) return null;
  return <ul role="listbox">{children}</ul>;
};

// Usage — caller controls structure
<Menu>
  <Menu.Trigger>Options</Menu.Trigger>
  <Menu.Items>
    <li role="option">Edit</li>
    <li role="option">Delete</li>
  </Menu.Items>
</Menu>
```

## Pattern 2: Controlled / Uncontrolled Hybrid

Use when: component works standalone OR integrates with external form libraries.

```tsx
interface InputProps {
  value?: string;           // controlled mode if provided
  defaultValue?: string;    // uncontrolled mode
  onChange?: (value: string) => void;
  label: string;
  error?: string;
}

const Input = ({ value, onChange, defaultValue, label, error }: InputProps) => {
  const [internal, setInternal] = useState(defaultValue ?? '');
  const isControlled = value !== undefined;
  const current = isControlled ? value : internal;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!isControlled) setInternal(e.target.value);
    onChange?.(e.target.value);
  };

  const id = useId();   // stable ID for label association
  return (
    <div>
      <label htmlFor={id}>{label}</label>
      <input id={id} value={current} onChange={handleChange}
             aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined} />
      {error && <span id={`${id}-error`} role="alert">{error}</span>}
    </div>
  );
};
```

## Component States — Always Implement All

Every component that fetches or receives async data must handle all states:

```tsx
interface DataComponentProps {
  userId: string;
}

const UserCard = ({ userId }: DataComponentProps) => {
  const { data, isLoading, isError, error } = useUser(userId);

  // 1. Loading state — skeleton or spinner
  if (isLoading) return <UserCardSkeleton />;

  // 2. Error state — meaningful message, not blank
  if (isError) return (
    <div role="alert">
      <p>Failed to load user data.</p>
      <button onClick={() => refetch()}>Try again</button>
    </div>
  );

  // 3. Empty state — explicit, not silent blank area
  if (!data) return <p>No user found.</p>;

  // 4. Success state — the happy path
  return <div>{data.name}</div>;
};
```

## Props API Design Rules

```tsx
// ✅ Good: explicit, typed, small surface area
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
  'aria-label'?: string;  // Allow a11y override
}

// ❌ Bad: too many booleans (boolean explosion)
interface ButtonProps {
  isPrimary?: boolean;
  isSecondary?: boolean;
  isSmall?: boolean;
  isLarge?: boolean;
  // Can set isPrimary + isSecondary simultaneously — ambiguous
}

// ❌ Bad: style overrides passed as strings
interface ButtonProps {
  className?: string;   // Breaks component encapsulation
  style?: CSSProperties; // Creates leaky styling contract
}
```

## Accessibility Requirements Per Component

| Component | Required ARIA | Keyboard | Notes |
|---|---|---|---|
| Dialog/Modal | `role="dialog"`, `aria-modal`, `aria-labelledby` | Trap focus; Escape closes | Focus returns to trigger on close |
| Dropdown/Select | `role="listbox"`, `aria-expanded` | Arrow keys navigate; Enter selects | Announce selection |
| Toggle/Switch | `role="switch"`, `aria-checked` | Space toggles | |
| Alert/Toast | `role="alert"` or `aria-live="polite"` | — | Screen reader announces immediately |
| Tab panel | `role="tablist"`, `role="tab"`, `role="tabpanel"` | Arrow keys between tabs | |
| Form field | `<label>` with `htmlFor` | — | Never skip label |
