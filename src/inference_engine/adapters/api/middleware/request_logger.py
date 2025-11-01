from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog


logger = structlog.get_logger()


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info("request_start", method=request.method, path=request.url.path)
        response: Response = await call_next(request)
        logger.info("request_end", status_code=response.status_code, path=request.url.path)
        return response
