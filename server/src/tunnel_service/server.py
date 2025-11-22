"""Tunnel service entry point (data plane)."""

import logging

from aiohttp import web

from src.shared.config import Settings
from src.tunnel_service.handlers import TunnelRequestHandler
from src.tunnel_service.nats_client import cleanup_nats, setup_nats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> web.Application:
    """Create and configure the tunnel service application."""
    if settings is None:
        settings = Settings()

    app = web.Application()
    app["settings"] = settings

    handler = TunnelRequestHandler(app)
    app.router.add_route("*", "/{tail:.*}", handler.handle)

    # Startup/cleanup
    app.on_startup.append(setup_nats)
    app.on_cleanup.append(cleanup_nats)

    return app


def main():
    """Run the tunnel service."""
    settings = Settings()
    app = create_app(settings)

    logger.info(f"Starting Tunnel Service on {settings.host}:{settings.port}")
    logger.info(f"Base domain: {settings.base_domain}")
    logger.info(f"NATS: {settings.nats_url}")

    web.run_app(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
