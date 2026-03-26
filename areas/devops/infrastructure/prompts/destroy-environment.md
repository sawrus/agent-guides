---
workflow: destroy-environment
---

# Prompt: `/destroy-environment`

Use when: safely tearing down a temporary or obsolete environment and validating cleanup before cost, security, or data risks remain.

---

## Example 1 — Decommission sandbox environment

**EN:**
```
/destroy-environment

Environment: sandbox-us-east-2
Provider: AWS
Resources expected: VPC, ECS service, RDS instance, S3 state bucket
Safety checks:
- confirm no production tags
- ensure latest backup snapshot exists
- require team-lead approval
Output: destruction plan, executed steps, leftover resources report
```

**RU:**
```
/destroy-environment

Окружение: sandbox-us-east-2
Провайдер: AWS
Ожидаемые ресурсы: VPC, ECS сервис, RDS инстанс, S3 state bucket
Проверки безопасности:
- подтвердить отсутствие production-тегов
- убедиться, что есть свежий backup snapshot
- обязательное подтверждение team-lead
Результат: план удаления, выполненные шаги, отчёт по оставшимся ресурсам
```

---

## Example 2 — Emergency cleanup of abandoned preview environment

**EN:**
```
/destroy-environment

Environment: pr-482-preview
Provider: Hetzner Cloud + Cloudflare DNS
Reason: preview stack was left running after branch deletion; monthly cost already > EUR 180
Resources expected:
- 3 VMs (1 control plane, 2 workers)
- k3s load balancer IP
- wildcard DNS record *.pr-482.dev.example.com
- object storage bucket with test uploads
Safety checks:
- verify no shared production bucket or DNS zone is referenced
- export last Terraform state and inventory before destroy
- confirm no QA session scheduled in the next 24h
Output: ordered teardown plan, DNS cleanup confirmation, cost savings estimate, and list of any dangling resources that require manual follow-up
```

**RU:**
```
/destroy-environment

Окружение: pr-482-preview
Провайдер: Hetzner Cloud + Cloudflare DNS
Причина: preview-стек остался запущенным после удаления ветки; ежемесячная стоимость уже > EUR 180
Ожидаемые ресурсы:
- 3 VM (1 control plane, 2 workers)
- k3s load balancer IP
- wildcard DNS запись *.pr-482.dev.example.com
- bucket объектного хранилища с тестовыми загрузками
Проверки безопасности:
- убедиться, что не используется общий production bucket или DNS зона
- экспортировать последний Terraform state и inventory перед удалением
- подтвердить, что в ближайшие 24ч не запланирована QA сессия
Результат: упорядоченный план удаления, подтверждение очистки DNS, оценка экономии и список dangling-ресурсов для ручного завершения
```
