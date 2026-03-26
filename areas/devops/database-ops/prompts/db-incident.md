---
workflow: db-incident
---

# Prompt: `/db-incident`

Use when: responding to a production database incident or high-risk operational change affecting performance, locks, or stateful data services.

---

## Example 1 — Identify and fix slow queries

**EN:**
```
/db-incident

Database: production_db / DB: order_db
Symptom: order-service p99 latency increased from 80ms to 450ms 3 days ago
Observation: CPU on postgres-primary up from 15% to 65% (Prometheus)
Available: pg_stat_statements extension enabled
Investigation:
  1. Top-10 queries by total_time (pg_stat_statements, last reset: 3 days ago)
  2. Check for: sequential scans on large tables, high rows_examined vs rows_returned ratio
  3. EXPLAIN ANALYZE the top offender
  4. Identify missing index (likely new query after code deploy)
  5. Test index creation on staging first (measure latency improvement)
  6. Apply CREATE INDEX CONCURRENTLY in production (verify no lock)
Output: slow query + EXPLAIN output + CREATE INDEX CONCURRENTLY statement
```

**RU:**
```
/db-incident

База данных: production_db / БД: order_db
Симптом: p99 latency order-service вырос с 80мс до 450мс 3 дня назад
Наблюдение: CPU на postgres-primary вырос с 15% до 65% (Prometheus)
Доступно: расширение pg_stat_statements включено
Расследование:
  1. Топ-10 запросов по total_time (pg_stat_statements, последний сброс: 3 дня назад)
  2. Проверить: sequential scans на больших таблицах, высокое отношение rows_examined к rows_returned
  3. EXPLAIN ANALYZE для главного виновника
  4. Определить отсутствующий индекс (вероятно новый запрос после деплоя кода)
  5. Протестировать создание индекса на staging сначала (измерить улучшение latency)
  6. Применить CREATE INDEX CONCURRENTLY в production (убедиться в отсутствии блокировки)
Результат: медленный запрос + вывод EXPLAIN + оператор CREATE INDEX CONCURRENTLY
```

---

## Example 2 — Safe migration: add non-null column to large table

**EN:**
```
/db-incident

Database: production_db / Table: orders (85M rows)
Migration: add column processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
Problem: naive ALTER TABLE would lock 85M rows for minutes (unacceptable in production)
Required approach:
  1. Estimate lock duration on staging with production-size data first
  2. Use safe sequence: ADD COLUMN (nullable, no default) → backfill in batches of 10k → ADD NOT NULL constraint
  3. Backfill script: Python with batched UPDATE + commit every 10k rows + sleep 50ms between batches
  4. Estimate total backfill time: 85M / 10k per batch × ~100ms per batch ≈ ?
  5. Final constraint: ALTER TABLE orders ALTER COLUMN processed_at SET NOT NULL (fast, no backfill needed if no NULLs)
  6. Rollback: DROP COLUMN processed_at (fast even on large table)
Show: complete migration SQL + backfill Python script + timing estimate
```

**RU:**
```
/db-incident

База данных: production_db / Таблица: orders (85М строк)
Миграция: добавить столбец processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
Проблема: наивный ALTER TABLE заблокирует 85М строк на минуты (недопустимо в production)
Необходимый подход:
  1. Оценить продолжительность блокировки на staging с данными размером production сначала
  2. Использовать безопасную последовательность: ADD COLUMN (nullable, без default) → backfill батчами по 10k → ADD NOT NULL constraint
  3. Скрипт backfill: Python с батчевым UPDATE + коммит каждые 10k строк + sleep 50мс между батчами
  4. Оценить общее время backfill: 85М / 10k на батч × ~100мс на батч ≈ ?
  5. Финальный constraint: ALTER TABLE orders ALTER COLUMN processed_at SET NOT NULL (быстро, без backfill если нет NULL)
  6. Откат: DROP COLUMN processed_at (быстро даже на большой таблице)
Показать: полный SQL миграции + Python скрипт backfill + оценка времени
```

---

## Example 3 — Redis memory pressure: eviction policy tuning

**EN:**
```
/db-incident

Redis setup: standalone Redis 7.2 (K8s StatefulSet), 2Gi maxmemory
Symptom: Redis hitting maxmemory; evicting keys needed for active sessions (data loss)
Current eviction policy: allkeys-lru (evicting ALL keys by LRU)
Use cases in this Redis instance:
  - User sessions (must not evict, TTL 24h)
  - Rate limiting counters (can evict, TTL 60s)
  - Cache of DB query results (can evict, TTL 5m)
Solution needed:
  1. Separate key namespaces: sessions:*, rate:*, cache:*
  2. Change eviction to volatile-lru (only evict keys WITH TTL set)
  3. Verify: sessions never have TTL (prevent eviction), cache/rate always have TTL
  4. Add Redis memory monitoring: alert at 80% usage, 90% critical
  5. Long term: split into 2 Redis instances (session store vs cache)
```

**RU:**
```
/db-incident

Redis конфигурация: standalone Redis 7.2 (K8s StatefulSet), 2Gi maxmemory
Симптом: Redis достигает maxmemory; вытесняет ключи нужные для активных сессий (потеря данных)
Текущая политика вытеснения: allkeys-lru (вытесняет ВСЕ ключи по LRU)
Use cases в этом Redis:
  - Пользовательские сессии (нельзя вытеснять, TTL 24ч)
  - Счётчики rate limiting (можно вытеснять, TTL 60с)
  - Кэш результатов DB запросов (можно вытеснять, TTL 5м)
Необходимое решение:
  1. Разделить пространства имён ключей: sessions:*, rate:*, cache:*
  2. Изменить вытеснение на volatile-lru (вытеснять только ключи С установленным TTL)
  3. Убедиться: sessions никогда не имеют TTL (предотвращение вытеснения), cache/rate всегда имеют TTL
  4. Добавить мониторинг памяти Redis: алерт при 80% использовании, critical при 90%
  5. Долгосрочно: разделить на 2 Redis инстанса (session store vs cache)
```
