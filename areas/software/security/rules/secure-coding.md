---
description: Output encoding, shell and file path handling, and error response safety in application code.
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.py"
  - "**/*.go"
  - "**/*.java"
---

# Secure coding

- Encode user-controlled data before you render it in HTML; do not use `dangerouslySetInnerHTML` or `v-html` without `DOMPurify`.
- Never pass user input to a shell; call the process with an argument array and an allowlist of values.
- Resolve file paths from user input to a canonical path and reject paths outside the allowed base directory.
- Check file uploads for type and size, and store them outside the web root.
- Return generic error messages to clients; never return stack traces or SQL errors in a response.
- Require authentication on every endpoint by default and annotate public endpoints explicitly.
- Do not use a hidden or unlisted endpoint path as an access control.
