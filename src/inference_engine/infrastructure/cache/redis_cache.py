from typing import Optional
from .redis_client import RedisClient


class RedisCache:
    def __init__(self, url: str):
        self._client = RedisClient.get_client(url)

    async def get(self, key: str) -> Optional[str]:
        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        if ttl_seconds is not None:
            await self._client.setex(key, ttl_seconds, value)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)
