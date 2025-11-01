from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.open = False

    async def dispatch(self, request: Request, call_next):
        if self.open:
            return Response(status_code=503)
        return await call_next(request)
