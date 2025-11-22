"""Tunnel service entry point (data plane)."""

from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.routing import Route

from src.shared.config import get_settings
from src.shared.logging import get_logger, setup_logging
from src.tunnel_service.handlers import TunnelRequestHandler
from src.tunnel_service.nats_client import cleanup_nats, setup_nats

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: Starlette):
    """Manage application lifecycle (startup/shutdown)."""
    setup_logging()
    settings = get_settings()
    logger.info("Starting Tunnel Service")
    logger.info(f"Base domain: {settings.base_domain}")
    logger.info(f"NATS: {settings.nats_url}")

    nats_client = await setup_nats()
    app.state.nats = nats_client
    app.state.settings = settings

    yield

    await cleanup_nats(nats_client)
    logger.info("Tunnel Service stopped")


def create_app() -> Starlette:
    """Create and configure the tunnel service application."""
    handler = TunnelRequestHandler()
    
    app = Starlette(
        debug=False,
        routes=[
            Route("/{path:path}",
                  handler.handle,
                  methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]),
        ],
        lifespan=lifespan,
    )

    return app


app = create_app()
