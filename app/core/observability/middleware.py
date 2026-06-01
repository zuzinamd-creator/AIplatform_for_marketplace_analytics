import time
import uuid
from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.observability.context import clear_context, set_correlation_id
from app.core.observability.logging import get_logger

logger = get_logger("http")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
        correlation_id = set_correlation_id(incoming or str(uuid.uuid4()))
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "http_request_failed",
                extra={
                    "duration_ms": duration_ms,
                    "method": request.method,
                    "path": request.url.path,
                    "status": "error",
                },
            )
            raise
        else:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "http_request",
                extra={
                    "duration_ms": duration_ms,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "status": "ok",
                },
            )
            response.headers["X-Request-ID"] = correlation_id
            return cast(Response, response)
        finally:
            clear_context()
