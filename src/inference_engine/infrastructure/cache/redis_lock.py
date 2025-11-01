import asyncio
from typing import Optional
from .redis_client import RedisClient


class RedisLock:
    def __init__(self, url: str, name: str, ttl_seconds: int = 10):
        self._client = RedisClient.get_client(url)
        self.name = f"lock:{name}"
        self.ttl = ttl_seconds

    async def acquire(self) -> bool:
        return await self._client.set(self.name, "1", ex=self.ttl, nx=True) is True

    async def release(self) -> None:
        await self._client.delete(self.name)

    async def __aenter__(self) -> "RedisLock":
        while not await self.acquire():
            await asyncio.sleep(0.05)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.release()
