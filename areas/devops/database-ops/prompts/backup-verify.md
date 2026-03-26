---
workflow: backup-verify
---

# Prompt: `/backup-verify`

Use when: verifying database backup integrity or practicing a PITR restore.

---

## Example 1 — Weekly backup verification (automated)

**EN:**
```
/backup-verify

Database: postgres-primary / Backup tool: pgBackRest / Stanza: main
Task: weekly automated backup verification
Steps:
  1. Check backup catalog: pgbackrest --stanza=main info
  2. Verify latest full backup age < 24h
  3. Perform restore test to isolated postgres instance (restore-test pod in K8s)
  4. After restore: run integrity queries (row counts on 5 critical tables vs production)
  5. Report result to #ops-monitoring Slack channel
  6. If any step fails → alert on-call immediately (P1)
Expected runtime: < 30 min total
```

**RU:**
```
/backup-verify

База данных: postgres-primary / Инструмент бэкапа: pgBackRest / Stanza: main
Задача: еженедельная автоматизированная верификация бэкапа
Шаги:
  1. Проверить каталог бэкапов: pgbackrest --stanza=main info
  2. Убедиться что возраст последнего полного бэкапа < 24ч
  3. Выполнить тест восстановления в изолированный postgres instance (restore-test под в K8s)
  4. После восстановления: проверочные запросы (количество строк в 5 критических таблицах vs production)
  5. Отправить результат в Slack канал #ops-monitoring
  6. Если любой шаг завершился неудачей → немедленный алерт on-call (P1)
Ожидаемое время выполнения: < 30 мин
```

---

## Example 2 — Emergency PITR after accidental DELETE

**EN:**
```
/backup-verify

Database: postgres-primary / DB: production_db
Incident: developer accidentally ran "DELETE FROM payments WHERE status='pending'" at 14:33 UTC
Deleted rows: ~12,000 payment records
Recovery target: 14:32 UTC (1 min before deletion)
Backup tool: pgBackRest / WAL archiving: enabled (to MinIO)
Procedure needed:
  1. Identify correct recovery target timestamp
  2. Restore to isolated instance at 14:32:00 UTC (PITR)
  3. Extract deleted rows: SELECT * FROM payments WHERE status='pending'
  4. Re-insert into production (NOT full restore — use surgical row recovery)
  5. Verify row count matches pre-deletion state
  6. Document as incident; follow up with safer DB access controls
```

**RU:**
```
/backup-verify

База данных: postgres-primary / БД: production_db
Инцидент: разработчик случайно выполнил "DELETE FROM payments WHERE status='pending'" в 14:33 UTC
Удалённые строки: ~12,000 записей платежей
Цель восстановления: 14:32 UTC (за 1 мин до удаления)
Инструмент: pgBackRest / WAL архивирование: включено (в MinIO)
Необходимая процедура:
  1. Определить правильную временную метку цели восстановления
  2. Восстановить в изолированный instance в 14:32:00 UTC (PITR)
  3. Извлечь удалённые строки: SELECT * FROM payments WHERE status='pending'
  4. Повторно вставить в production (НЕ полное восстановление — хирургическое восстановление строк)
  5. Убедиться что количество строк соответствует состоянию до удаления
  6. Задокументировать как инцидент; устранить более безопасные контроли доступа к БД
```
