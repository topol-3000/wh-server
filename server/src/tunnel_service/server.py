"""Tunnel service entry point (data plane)."""

import logging

import uvloop
from aiohttp import web
from aiohttp_cors import ResourceOptions
from aiohttp_cors import setup as setup_cors

from src.shared.config import Settings
from src.tunnel_service.middleware import subdomain_routing_middleware
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

    app = web.Application(middlewares=[subdomain_routing_middleware])
    app["settings"] = settings

    # Setup CORS
    cors = setup_cors(
        app,
        defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*",
            )
        },
    )

    for route in app.router.routes():
        cors.add(route)

    # Startup/cleanup
    app.on_startup.append(lambda app: setup_nats(app))
    app.on_cleanup.append(cleanup_nats)

    return app


def main():
    """Run the tunnel service."""
    uvloop.install()

    settings = Settings()
    app = create_app(settings)

    logger.info(f"Starting Tunnel Service on {settings.host}:{settings.port}")
    logger.info(f"Base domain: {settings.base_domain}")
    logger.info(f"NATS: {settings.nats_url}")

    web.run_app(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
