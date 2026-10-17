---
name: security-headers
description: "Defines required HTTP security headers and API-specific header rules; use when configuring web servers or API gateways or when reviewing HTTP responses."
---

# Skill: HTTP Security Headers

## When to load

When configuring web servers, API gateways, or reviewing HTTP responses.

## Required Headers

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Content-Security-Policy "
  default-src 'self';
  script-src 'self' 'nonce-{NONCE}';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https://cdn.mycompany.com;
  connect-src 'self' https://api.mycompany.com;
  frame-ancestors 'none';
" always;
```

## API-Specific

- Remove: `X-Powered-By`, `Server` (information disclosure)
- Add: `X-Request-ID` (tracing), `Cache-Control: no-store` (auth responses)
- CORS: Never `Access-Control-Allow-Origin: *` for credentialed requests
