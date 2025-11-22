"""Tunnel service entry point."""

from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.routing import Route

from src.shared.config import get_settings
from src.shared.logging import get_logger, setup_logging
from src.tunnel_service.tunnel.nats.transport import NATSTunnelTransport
from src.tunnel_service.handlers import proxy_request_handler
from src.tunnel_service.middleware import TunnelRoutingMiddleware
from src.tunnel_service.tunnel.nats.client import cleanup_nats, setup_nats

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: Starlette):
    """Manage application lifecycle (startup/shutdown)."""
    setup_logging()
    settings = get_settings()
    logger.info("Starting Tunnel Service")
    logger.info(f"Base domain: {settings.base_domain}")

    nats_client = await setup_nats(settings.nats_url)
    transport = NATSTunnelTransport(nats_client, timeout=settings.request_timeout)
    app.state.tunnel_transport = transport

    yield

    await cleanup_nats(nats_client)
    logger.info("Tunnel Service stopped")


def create_app() -> Starlette:
    """Create and configure the tunnel service application."""
    app = Starlette(
        debug=False,
        routes=[
            Route(
                "/{path:path}",
                proxy_request_handler,
                methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
            ),
        ],
        lifespan=lifespan,
    )

    app.add_middleware(TunnelRoutingMiddleware)

    return app


app = create_app()
