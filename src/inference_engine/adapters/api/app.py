from fastapi import FastAPI
from .routes.inference import router as inference_router
from ...infrastructure.monitoring.logging import configure_logging


configure_logging()
app = FastAPI(title="Cost-Optimized Inference Engine", version="0.1.0")

app.include_router(inference_router, prefix="/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


