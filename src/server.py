"""
WormHole Server - HTTP Tunneling Service
Allows exposing local services to the public internet.
"""

import asyncio
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime

import aiohttp_cors
from aiohttp import WSMsgType, web

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class Tunnel:
    """Represents an active tunnel connection."""

    tunnel_id: str
    subdomain: str
    websocket: web.WebSocketResponse
    created_at: datetime
    request_count: int = 0


class WormHoleServer:
    """Main server class for managing tunnels and proxying requests."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.tunnels: dict[str, Tunnel] = {}
        self.pending_requests: dict[str, asyncio.Future] = {}

    async def handle_tunnel_connect(
        self, request: web.Request
    ) -> web.WebSocketResponse:
        """Handle WebSocket connection from client wanting to create a tunnel."""
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)

        # Generate unique tunnel ID and subdomain
        tunnel_id = str(uuid.uuid4())
        subdomain = secrets.token_urlsafe(8)

        tunnel = Tunnel(
            tunnel_id=tunnel_id,
            subdomain=subdomain,
            websocket=ws,
            created_at=datetime.now(),
        )

        self.tunnels[subdomain] = tunnel

        # Send tunnel info to client
        await ws.send_json(
            {
                "type": "connected",
                "tunnel_id": tunnel_id,
                "subdomain": subdomain,
                "public_url": f"http://{request.host}/{subdomain}",
            }
        )

        logger.info(f"New tunnel created: {subdomain} (ID: {tunnel_id})")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = msg.json()
                    await self._handle_tunnel_message(subdomain, data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break
        finally:
            # Clean up tunnel
            if subdomain in self.tunnels:
                del self.tunnels[subdomain]
            logger.info(f"Tunnel closed: {subdomain}")

        return ws

    async def _handle_tunnel_message(self, subdomain: str, data: dict):
        """Handle messages from tunnel client (responses to proxied requests)."""
        request_id = data.get("request_id")

        if request_id and request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            if not future.done():
                future.set_result(data)

    async def handle_proxied_request(self, request: web.Request) -> web.Response:
        """Handle HTTP requests that should be proxied through a tunnel."""
        # Extract subdomain from path
        path = request.path.strip("/")
        parts = path.split("/", 1)

        if not parts:
            return web.Response(
                text="WormHole Server - No tunnel specified", status=404
            )

        subdomain = parts[0]
        target_path = "/" + parts[1] if len(parts) > 1 else "/"

        # Check if tunnel exists
        if subdomain not in self.tunnels:
            return web.Response(
                text=f"Tunnel '{subdomain}' not found or not connected", status=404
            )

        tunnel = self.tunnels[subdomain]
        tunnel.request_count += 1

        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Read request body
        body = await request.read()

        # Prepare request data to send to client
        request_data = {
            "type": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": target_path,
            "query_string": request.query_string,
            "headers": dict(request.headers),
            "body": body.decode("utf-8", errors="ignore") if body else "",
        }

        # Send request to tunnel client
        try:
            await tunnel.websocket.send_json(request_data)
        except Exception as e:
            logger.error(f"Failed to send request to tunnel: {e}")
            return web.Response(text="Tunnel connection error", status=502)

        # Wait for response from client
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        try:
            # Wait up to 30 seconds for response
            response_data = await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout for {subdomain}")
            return web.Response(text="Gateway timeout", status=504)
        finally:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]

        # Build response
        status = response_data.get("status", 200)
        headers = response_data.get("headers", {})
        body = response_data.get("body", "")

        return web.Response(text=body, status=status, headers=headers)

    async def handle_status(self, request: web.Request) -> web.Response:
        """Return server status and active tunnels."""
        tunnels_info = [
            {
                "subdomain": subdomain,
                "tunnel_id": tunnel.tunnel_id,
                "created_at": tunnel.created_at.isoformat(),
                "request_count": tunnel.request_count,
            }
            for subdomain, tunnel in self.tunnels.items()
        ]

        return web.json_response(
            {
                "status": "running",
                "active_tunnels": len(self.tunnels),
                "tunnels": tunnels_info,
            }
        )

    async def handle_index(self, request: web.Request) -> web.Response:
        """Return welcome page."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>WormHole Server</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #333; }}
                .info {{ background: #e3f2fd; padding: 15px; border-radius: 4px; margin: 20px 0; }}
                code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 WormHole Server</h1>
                <p>HTTP tunneling service - Expose your localhost to the internet</p>
                
                <div class="info">
                    <h3>Active Tunnels: {len(self.tunnels)}</h3>
                </div>
                
                <h3>API Endpoints:</h3>
                <ul>
                    <li><code>GET /status</code> - Server status and active tunnels</li>
                    <li><code>WS /tunnel</code> - Create new tunnel (WebSocket)</li>
                    <li><code>* /:subdomain/*</code> - Proxied requests</li>
                </ul>
                
                <h3>Quick Start:</h3>
                <p>Connect a client to <code>ws://{self.host if self.host != "0.0.0.0" else "localhost"}:{self.port}/tunnel</code> to create a tunnel.</p>
            </div>
        </body>
        </html>
        """

        return web.Response(text=html, content_type="text/html")

    def setup_routes(self, app: web.Application):
        """Configure application routes."""
        app.router.add_get("/", self.handle_index)
        app.router.add_get("/status", self.handle_status)
        app.router.add_get("/tunnel", self.handle_tunnel_connect)
        app.router.add_route("*", "/{tail:.*}", self.handle_proxied_request)

    async def start(self):
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

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"WormHole server started on http://{self.host}:{self.port}")
        logger.info("Waiting for tunnel connections...")

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await runner.cleanup()


def main():
    """Entry point for the server."""
    import os

    host = os.getenv("WH_HOST", "0.0.0.0")
    port = int(os.getenv("WH_PORT", "8080"))

    server = WormHoleServer(host=host, port=port)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()
