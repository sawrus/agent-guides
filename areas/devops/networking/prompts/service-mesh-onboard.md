---
workflow: service-mesh-onboard
---

# Prompt: `/service-mesh-onboard`

Use when: onboarding a service to Istio/Linkerd, configuring mTLS, traffic policies, or debugging mesh issues.

---

## Example 1 — Onboard service to Istio with mTLS

**EN:**
```
/service-mesh-onboard

Mesh: Istio (installed cluster-wide, sidecar injection enabled per namespace)
Service: payment-service / Namespace: production
Task: onboard to Istio mesh with strict mTLS and traffic policies
Requirements:
  1. Enable sidecar injection for production namespace
  2. PeerAuthentication: STRICT mTLS for payment-service (no plaintext)
  3. AuthorizationPolicy: payment-service only accepts traffic from checkout-service and api-gateway
  4. DestinationRule: circuit breaker (5 consecutive 5xx → eject upstream for 30s)
  5. VirtualService: retries (3×, 500ms interval) for 503/504; timeout 5s
  6. Verify: kiali graph shows mTLS lock icons on all connections
```

**RU:**
```
/service-mesh-onboard

Меш: Istio (установлен на весь кластер, инжекция sidecar включена по namespace)
Сервис: payment-service / Namespace: production
Задача: подключение к Istio меш с strict mTLS и traffic policies
Требования:
  1. Включить инжекцию sidecar для namespace production
  2. PeerAuthentication: STRICT mTLS для payment-service (без plaintext)
  3. AuthorizationPolicy: payment-service принимает трафик только от checkout-service и api-gateway
  4. DestinationRule: circuit breaker (5 последовательных 5xx → исключить upstream на 30с)
  5. VirtualService: retries (3×, интервал 500мс) для 503/504; timeout 5с
  6. Проверить: граф kiali показывает значки mTLS на всех соединениях
```

---

## Example 2 — Debug: mTLS handshake failures

**EN:**
```
/service-mesh-onboard

Mesh: Istio / Symptom: order-service → payment-service returning "connection refused" or TLS handshake errors
Error in envoy log: "upstream connect error or disconnect/reset before headers. retried and the latest reset reason: connection failure, transport failure reason: TLS error"
Checklist:
  1. Check PeerAuthentication mode (STRICT vs PERMISSIVE) on both namespaces
  2. Check certificate validity: istioctl proxy-config secret <pod>
  3. Check AuthorizationPolicy on payment-service (may be blocking order-service)
  4. Verify both pods have sidecar injected (check annotations)
  5. Test with PERMISSIVE mode temporarily to isolate mTLS vs auth issue
Output: root cause + YAML fix
```

**RU:**
```
/service-mesh-onboard

Меш: Istio / Симптом: order-service → payment-service возвращает "connection refused" или ошибки TLS handshake
Ошибка в envoy log: "upstream connect error or disconnect/reset before headers..."
Чеклист:
  1. Проверить режим PeerAuthentication (STRICT vs PERMISSIVE) в обоих namespace
  2. Проверить действительность сертификата: istioctl proxy-config secret <pod>
  3. Проверить AuthorizationPolicy на payment-service (может блокировать order-service)
  4. Убедиться что оба пода имеют инжектированный sidecar (проверить аннотации)
  5. Временно проверить режим PERMISSIVE для разграничения проблем mTLS vs auth
Результат: корневая причина + YAML исправление
```
