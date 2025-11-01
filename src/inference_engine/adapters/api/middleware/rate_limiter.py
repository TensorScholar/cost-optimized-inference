from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import time
from ...infrastructure.cache.redis_client import RedisClient
from ...config import settings


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 600):
        super().__init__(app)
        self.redis = RedisClient.get_client(settings.redis_url)
        self.rpm = requests_per_minute

    async def dispatch(self, request: Request, call_next):
        key = f"ratelimit:{request.client.host}"
        now = int(time.time())
        window = 60
        pipe = self.redis.pipeline(True)
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window)
        _, _, count, _ = await pipe.execute()
        if count > self.rpm:
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        return await call_next(request)
