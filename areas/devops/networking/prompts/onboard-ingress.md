---
workflow: onboard-ingress
---

# Prompt: `/onboard-ingress`

Use when: exposing a service through Kubernetes ingress, including TLS issuance, DNS wiring, and production traffic controls.

---

## Example 1 — Public API with TLS (Let's Encrypt)

**EN:**
```
/onboard-ingress

Service: api-gateway / Namespace: production
Expose at: api.example.com
Backend: api-gateway service, port 8080
TLS: Let's Encrypt via cert-manager (cluster-issuer: letsencrypt-prod)
Requirements:
  - HTTP → HTTPS redirect
  - HSTS header (max-age 1 year)
  - Rate limit: 200 RPS, max 50 connections per IP
  - Security headers: X-Frame-Options DENY, X-Content-Type-Options nosniff
  - CORS: allow origin https://app.example.com only
  - Timeouts: connect 10s, read 60s
Bare-metal: MetalLB in L2 mode, IP pool already configured
```

**RU:**
```
/onboard-ingress

Сервис: api-gateway / Namespace: production
Публикуем по адресу: api.example.com
Backend: сервис api-gateway, порт 8080
TLS: Let's Encrypt через cert-manager (cluster-issuer: letsencrypt-prod)
Требования:
  - Редирект HTTP → HTTPS
  - HSTS заголовок (max-age 1 год)
  - Rate limit: 200 RPS, макс 50 соединений с одного IP
  - Security headers: X-Frame-Options DENY, X-Content-Type-Options nosniff
  - CORS: разрешить только origin https://app.example.com
  - Таймауты: connect 10s, read 60s
Bare-metal: MetalLB в режиме L2, IP pool уже настроен
```

---

## Example 2 — Internal service with canary routing

**EN:**
```
/onboard-ingress

Service: payment-service / Namespace: production
Expose at: payments.internal.example.com (internal DNS only, not public)
TLS: internal CA via cert-manager (cluster-issuer: vault-pki)
Canary: 10% traffic to payment-service-v2 (new version being tested)
Canary header: X-Canary: true → 100% to v2 (for QA testing)
No CORS needed (internal service-to-service only)
```

**RU:**
```
/onboard-ingress

Сервис: payment-service / Namespace: production
Публикуем по адресу: payments.internal.example.com (только внутренний DNS, не публичный)
TLS: внутренний CA через cert-manager (cluster-issuer: vault-pki)
Canary: 10% трафика на payment-service-v2 (новая версия тестируется)
Canary header: X-Canary: true → 100% на v2 (для тестирования QA)
CORS не нужен (только внутренний service-to-service)
```

---

## Example 3 — cert-manager certificate stuck in Pending

**EN:**
```
/onboard-ingress

Tool: cert-manager / Issuer: letsencrypt-prod (ClusterIssuer)
Certificate: api-example-com-tls in namespace production
Status: kubectl get certificate → "False / Issuing" for > 10 min
Ingress host: api.example.com
Debug workflow:
  1. kubectl describe certificate api-example-com-tls -n production
  2. kubectl describe certificaterequest -n production (find matching CR)
  3. kubectl describe order -n production (ACME order status)
  4. kubectl describe challenge -n production (HTTP-01 or DNS-01 challenge status)
  5. Common failure modes:
     - HTTP-01: Ingress not serving /.well-known/acme-challenge/ (check ingress annotations)
     - HTTP-01: firewall blocking port 80 from Let's Encrypt IPs
     - DNS-01: wrong Route53 permissions or wrong hosted zone
     - Rate limit: too many failed attempts (check cert-manager logs)
```

**RU:**
```
/onboard-ingress

Инструмент: cert-manager / Issuer: letsencrypt-prod (ClusterIssuer)
Сертификат: api-example-com-tls в namespace production
Статус: kubectl get certificate → "False / Issuing" уже > 10 мин
Хост Ingress: api.example.com
Процесс отладки:
  1. kubectl describe certificate api-example-com-tls -n production
  2. kubectl describe certificaterequest -n production (найти соответствующий CR)
  3. kubectl describe order -n production (статус ACME order)
  4. kubectl describe challenge -n production (статус HTTP-01 или DNS-01 challenge)
  5. Типичные причины отказа:
     - HTTP-01: Ingress не обслуживает /.well-known/acme-challenge/ (проверить аннотации ingress)
     - HTTP-01: firewall блокирует порт 80 от IP Let's Encrypt
     - DNS-01: неверные права Route53 или неверный hosted zone
     - Rate limit: слишком много неудачных попыток (проверить логи cert-manager)
```
