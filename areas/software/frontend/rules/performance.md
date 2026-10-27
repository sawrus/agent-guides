---
description: Performance budget for web frontends covering Core Web Vitals, bundle size, lazy loading, and images.
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.vue"
  - "package.json"
  - "vite.config.*"
  - "webpack.config.*"
  - "next.config.*"
---

# Frontend performance

- Keep LCP under 2.5 s, INP under 200 ms, and CLS under 0.1 on the production build.
- Limit the initial JavaScript bundle to 200 KB gzipped on the critical path.
- Use lazy loading for every route (`React.lazy` with `Suspense`, or the framework's dynamic `import()`).
- Check the size of a new dependency; document the reason in the change when it adds more than 50 KB gzipped.
- Do not read `localStorage` synchronously in the render path.
- Use WebP or AVIF images and set `width` and `height` attributes on every `img`.
- Run the bundle size check (for example `size-limit` or `bundlesize`) in CI and fail the job when the budget is exceeded.
