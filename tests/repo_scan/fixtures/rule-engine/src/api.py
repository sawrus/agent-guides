import os

import httpx
from fastapi import FastAPI

from apiutil.api import send_application_context

app = FastAPI()
RULE_CATALOG_ENDPOINT = os.getenv("RULE_CATALOG_ENDPOINT", "http://rule-catalog:8000")


@app.get("/rules")
async def rules():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{RULE_CATALOG_ENDPOINT}/rules")
    send_application_context(RULE_CATALOG_ENDPOINT, {"rules": len(response.json())})
    return response.json()
