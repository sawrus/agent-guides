---
name: streaming-patterns
description: "Provides Kafka producer and consumer best practices and dead letter queue patterns for streaming data; use when designing Kafka consumers or producers or implementing real-time pipelines."
---

# Skill: Streaming Data Patterns

## When to load

When designing Kafka consumers/producers or implementing real-time pipelines.

## Producer Best Practices

```python
producer = Producer({
    "bootstrap.servers": settings.KAFKA_BROKERS,
    "acks": "all",               # Wait for all replicas
    "retries": 5,
    "enable.idempotence": True,  # Exactly-once delivery
    "compression.type": "snappy",
})
```

## Consumer Pattern

```python
consumer = Consumer({
    "group.id": "order-processor-v1",  # Version when changing logic
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,        # Manual commit: only after successful processing
})

msg = consumer.poll(timeout=1.0)
try:
    process(deserialize(msg.value()))
    consumer.commit(msg)  # Commit only after success
except ProcessingError as e:
    publish_to_dlq(msg, e)  # Dead-letter, don't block partition
    consumer.commit(msg)
```

## Dead Letter Queue

```json
{
  "original_topic": "orders.created.v1",
  "original_offset": 12345,
  "original_payload": "...",
  "error_message": "Deserialization failed",
  "error_timestamp": "2026-02-16T10:30:00Z",
  "retry_count": 3
}
```
