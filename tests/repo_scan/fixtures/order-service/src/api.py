import os

import httpx
from fastapi import FastAPI

from shared_lib.api import send_application_context

app = FastAPI()
CATALOG_LIB_ENDPOINT = os.getenv("CATALOG_LIB_ENDPOINT", "http://catalog-lib:8000")


@app.get("/rules")
async def rules():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CATALOG_LIB_ENDPOINT}/rules")
    send_application_context(CATALOG_LIB_ENDPOINT, {"rules": len(response.json())})
    return response.json()
