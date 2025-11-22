"""Middleware for tunnel routing."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from src.shared.config import get_settings
from src.shared.logging import get_logger

logger = get_logger(__name__)


class TunnelRoutingMiddleware(BaseHTTPMiddleware):
    """Extracts tunnel ID from Host header and adds it to request state."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.__base_domain = get_settings().base_domain

    async def dispatch(self, request: Request, call_next):
        """Extract tunnel ID from Host header and attach to request state."""
        host = request.headers.get("host", "").split(":")[0]

        if host.endswith(f".{self.__base_domain}"):
            tunnel_id = host[: -len(f".{self.__base_domain}")]
        else:
            tunnel_id = host  # fallback: localhost / IP / unknown host

        # Attach tunnel_id to request state for handlers to use
        request.state.tunnel_id = tunnel_id

        logger.debug(f"Extracted tunnel ID: {tunnel_id} from host: {host}")

        response = await call_next(request)
        return response
