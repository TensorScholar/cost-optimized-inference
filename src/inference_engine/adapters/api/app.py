from __future__ import annotations

from fastapi import FastAPI

from .routes.cache import router as cache_router
from .routes.metrics import router as metrics_router
from .routes.models import router as models_router

app = FastAPI(
    title="Honest LLM Inference Gateway",
    version="0.1.0",
    description="SLO-aware LLM routing and benchmark lab. Provider inference is not implemented in Phase 0.",
)

app.include_router(models_router, prefix="/v1")
app.include_router(metrics_router, prefix="/v1")
app.include_router(cache_router, prefix="/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "phase": "phase-0-repair"}


@app.get("/health/ready")
async def ready() -> dict[str, bool]:
    return {"ready": True}


@app.get("/health/live")
async def live() -> dict[str, bool]:
    return {"alive": True}

