from typing import Optional
import redis.asyncio as aioredis


class RedisClient:
    _client: Optional[aioredis.Redis] = None

    @classmethod
    def get_client(cls, url: str) -> aioredis.Redis:
        if cls._client is None:
            cls._client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
        return cls._client
