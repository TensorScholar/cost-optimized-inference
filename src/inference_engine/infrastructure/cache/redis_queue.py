from typing import Optional, List, Dict, Any
from .redis_client import RedisClient


class RedisQueue:
    def __init__(self, url: str, stream_key: str):
        self._client = RedisClient.get_client(url)
        self.stream_key = stream_key

    async def push(self, data: Dict[str, Any]) -> str:
        return await self._client.xadd(self.stream_key, data)

    async def read(self, last_id: str = "$", count: int = 10, block_ms: int = 0) -> List:
        return await self._client.xread({self.stream_key: last_id}, count=count, block=block_ms)
