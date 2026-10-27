from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI

app = FastAPI()
DECISIONS = []


@app.get("/rules")
def rules():
    return [{"id": 1, "name": "velocity"}]


async def consume_decisions():
    consumer = AIOKafkaConsumer(bootstrap_servers="kafka:9092")
    consumer.subscribe(["rules.decisions"])
    async for message in consumer:
        DECISIONS.append(message.value)
