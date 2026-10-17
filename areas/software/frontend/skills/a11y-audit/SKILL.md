---
name: a11y-audit
description: "Audits and fixes frontend accessibility with common WCAG violation fixes and a keyboard navigation checklist; use when building interactive components, reviewing a PR for accessibility, or fixing a11y lint errors."
---

# Skill: Accessibility Audit & Remediation

## When to load

When building interactive components, reviewing a PR for accessibility, or fixing a11y lint errors.

## Most Common Violations & Fixes

### 1. Icon-only button without label
```tsx
// ❌
<button onClick={onClose}><CloseIcon /></button>

// ✅
<button onClick={onClose} aria-label="Close dialog">
  <CloseIcon aria-hidden="true" />
</button>
```

### 2. Input without label
```tsx
// ❌
<input type="email" placeholder="Email address" />

// ✅
<label htmlFor="email">Email address</label>
<input id="email" type="email" placeholder="jane@example.com" />
```

### 3. Modal focus management
```tsx
const Modal = ({ isOpen, onClose, children }: ModalProps) => {
  const firstFocusableRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (isOpen) firstFocusableRef.current?.focus();
  }, [isOpen]);

  return isOpen ? (
    <div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
      {children}
      <button ref={firstFocusableRef} onClick={onClose}>Close</button>
    </div>
  ) : null;
};
```

### 4. Dynamic content announcements
```tsx
const StatusMessage = ({ message }: { message: string }) => (
  <div aria-live="polite" aria-atomic="true" className="sr-only">
    {message}
  </div>
);
```

## Keyboard Navigation Checklist

- [ ] Tab order follows visual reading order (no `tabindex > 0`)
- [ ] Custom dropdown: Arrow keys navigate, Escape closes, Enter selects
- [ ] Modals: Focus trapped inside; Escape closes; focus returns to trigger
- [ ] All hover interactions have keyboard equivalent
