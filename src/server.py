"""
WormHole Server - HTTP Tunneling Service
Allows exposing local services to the public internet.
"""

import asyncio
import logging

import aiohttp_cors
import uvloop
from aiohttp import web

from .config import Settings, get_settings
from .handlers import RequestHandlers
from .tunnel_manager import TunnelManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class WormHoleServer:
    """Main server class for managing tunnels and proxying requests."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.tunnel_manager = TunnelManager()
        self.handlers = RequestHandlers(self.tunnel_manager, self.settings)

    def setup_routes(self, app: web.Application) -> None:
        """Configure application routes."""
        app.router.add_get("/", self.handlers.handle_index)
        app.router.add_get("/status", self.handlers.handle_status)
        app.router.add_get("/tunnel", self.handlers.handle_tunnel_connect)
        app.router.add_route("*", "/{tail:.*}", self.handlers.handle_proxied_request)

    async def start(self) -> None:
        """Start the WormHole server."""
        app = web.Application()

        # Setup CORS
        cors = aiohttp_cors.setup(
            app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                )
            },
        )

        self.setup_routes(app)

        # Configure CORS on all routes except the wildcard route
        for route in list(app.router.routes()):
            # Skip CORS for wildcard routes to avoid conflicts
            if route.method == "*":
                continue
            cors.add(route)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, self.settings.host, self.settings.port)
        await site.start()

        logger.info(f"WormHole server started on http://{self.settings.host}:{self.settings.port}")
        logger.info("Waiting for tunnel connections...")

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await runner.cleanup()


def main() -> None:
    """Entry point for the server."""
    # Install uvloop as the default event loop
    uvloop.install()

    settings = get_settings()
    server = WormHoleServer(settings)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()
