from fastapi import FastAPI
from .routes.inference import router as inference_router
from .routes.models import router as models_router
from .routes.metrics import router as metrics_router
from .routes.cache import router as cache_router
from ...infrastructure.monitoring.logging import configure_logging

configure_logging()
app = FastAPI(
    title="Cost-Optimized Inference Engine",
    version="0.1.0",
    description="Intelligent LLM inference orchestration with cost optimization",
)

# Include all routers
app.include_router(inference_router, prefix="/v1")
app.include_router(models_router, prefix="/v1")
app.include_router(metrics_router, prefix="/v1")
app.include_router(cache_router, prefix="/v1")


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "cost-optimized-inference"}


@app.get("/health/ready")
async def ready() -> dict:
    """Readiness probe for Kubernetes."""
    # In production, check if Redis and model backends are ready
    return {"ready": True}


@app.get("/health/live")
async def live() -> dict:
    """Liveness probe for Kubernetes."""
    return {"alive": True}


