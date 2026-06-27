"""Cache management API routes."""

from fastapi import APIRouter, Depends

from ....application.services.cache.cache_service import CacheService
from ..dependencies import get_cache_service

router = APIRouter()


@router.get("/cache/stats")
async def get_cache_stats(
    cache_service: CacheService = Depends(get_cache_service),
) -> dict:
    """Get cache statistics."""
    return cache_service.get_metrics()


@router.delete("/cache")
async def clear_cache(
    pattern: str | None = None,
    cache_service: CacheService = Depends(get_cache_service),
) -> dict:
    """
    Clear cache entries.

    Args:
        pattern: Optional pattern to match entries for deletion
    """
    count = await cache_service.invalidate(pattern)
    return {"deleted_count": count, "pattern": pattern}

