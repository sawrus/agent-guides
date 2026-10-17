---
name: performance-tuning
description: "Tunes frontend performance through re-render prevention, code splitting, image optimization, and bundle analysis; use when optimizing Core Web Vitals, reducing bundle size, diagnosing render performance, or reviewing images and fonts."
---

# Skill: Frontend Performance Tuning

## When to load

When optimizing Core Web Vitals, reducing bundle size, diagnosing render performance, or reviewing images/fonts.

## Re-render Prevention

```tsx
// Memoize expensive computations
const sorted = useMemo(
  () => [...items].sort((a, b) => a.name.localeCompare(b.name)),
  [items]
);

// Stable callback references
const handleClick = useCallback(() => doSomething(id), [id]);

// Memoize child components receiving object/function props
const ExpensiveList = React.memo(({ items, onSelect }: ListProps) => (
  // rendering
));

// ❌ Inline objects create new references every render
<MyComponent config={{ timeout: 3000 }} />
// ✅ Stable reference
const CONFIG = { timeout: 3000 };
<MyComponent config={CONFIG} />
```

## Code Splitting (Mandatory)

```tsx
const UserDashboard = lazy(() => import('./features/users/UserDashboard'));

<Suspense fallback={<PageSkeleton />}>
  <UserDashboard />
</Suspense>
```

## Image Optimization Checklist

- [ ] Explicit `width` and `height` to prevent CLS
- [ ] WebP/AVIF via `<picture>` with JPG fallback
- [ ] `loading="lazy"` for below-fold images
- [ ] `loading="eager"` + `fetchpriority="high"` for LCP image

## Bundle Analysis

```bash
npx vite-bundle-visualizer
```

| Library | Problem | Solution |
|:---|:---|:---|
| `moment.js` | 300KB+ | Replace with `date-fns` |
| `lodash` | Full import | Use `lodash-es` named imports |
| `@mui/material` | Full import | Path imports: `@mui/material/Button` |
