"""HTTP and WebSocket request handlers."""

import asyncio
import logging
import uuid

from aiohttp import WSMsgType, web

from .config import Settings
from .models import (
    HTTPRequestMessage,
    HTTPResponseMessage,
    ServerStatusResponse,
    TunnelConnectedMessage,
)
from .tunnel_manager import TunnelManager

logger = logging.getLogger(__name__)


class RequestHandlers:
    """HTTP and WebSocket request handlers for the WormHole server."""

    def __init__(self, tunnel_manager: TunnelManager, settings: Settings) -> None:
        self.tunnel_manager = tunnel_manager
        self.settings = settings

    async def handle_tunnel_connect(
        self, request: web.Request
    ) -> web.WebSocketResponse:
        """Handle WebSocket connection from client wanting to create a tunnel."""
        ws = web.WebSocketResponse(heartbeat=self.settings.websocket_heartbeat)
        await ws.prepare(request)

        # Create tunnel
        tunnel = self.tunnel_manager.create_tunnel(websocket=ws)

        # Send tunnel info to client
        message = TunnelConnectedMessage(
            tunnel_id=tunnel.tunnel_id,
            subdomain=tunnel.subdomain,
            public_url=f"http://{request.host}/{tunnel.subdomain}",
        )
        await ws.send_json(message.model_dump())

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = msg.json()
                    await self._handle_tunnel_message(tunnel.subdomain, data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break
        finally:
            self.tunnel_manager.remove_tunnel(tunnel.subdomain)

        return ws

    async def _handle_tunnel_message(
        self, subdomain: str, data: dict[str, str | int]
    ) -> None:
        """Handle messages from tunnel client (responses to proxied requests)."""
        request_id = data.get("request_id")
        if isinstance(request_id, str):
            self.tunnel_manager.resolve_pending_request(request_id, data)

    async def handle_proxied_request(self, request: web.Request) -> web.Response:
        """Handle HTTP requests that should be proxied through a tunnel."""
        # Extract subdomain from path
        path = request.path.strip("/")
        parts = path.split("/", 1)

        if not parts or not parts[0]:
            return web.Response(
                text="WormHole Server - No tunnel specified", status=404
            )

        subdomain = parts[0]
        target_path = "/" + parts[1] if len(parts) > 1 else "/"

        # Check if tunnel exists
        tunnel = self.tunnel_manager.get_tunnel(subdomain)
        if tunnel is None:
            return web.Response(
                text=f"Tunnel '{subdomain}' not found or not connected", status=404
            )

        tunnel.request_count += 1

        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Read request body
        body = await request.read()

        # Prepare request data to send to client
        request_message = HTTPRequestMessage(
            request_id=request_id,
            method=request.method,
            path=target_path,
            query_string=request.query_string,
            headers=dict(request.headers),
            body=body.decode("utf-8", errors="ignore") if body else "",
        )

        # Send request to tunnel client
        try:
            await tunnel.websocket.send_json(request_message.model_dump())
        except Exception as e:
            logger.error(f"Failed to send request to tunnel: {e}")
            return web.Response(text="Tunnel connection error", status=502)

        # Register pending request and wait for response
        future = self.tunnel_manager.register_pending_request(request_id)

        try:
            response_data = await asyncio.wait_for(
                future, timeout=self.settings.request_timeout
            )
        except TimeoutError:
            logger.warning(f"Request timeout for {subdomain}")
            return web.Response(text="Gateway timeout", status=504)
        finally:
            self.tunnel_manager.cleanup_pending_request(request_id)

        # Parse and validate response
        try:
            response = HTTPResponseMessage.model_validate(response_data)
        except Exception as e:
            logger.error(f"Invalid response data from tunnel: {e}")
            return web.Response(text="Invalid tunnel response", status=502)

        return web.Response(
            text=response.body, status=response.status, headers=response.headers
        )

    async def handle_status(self, request: web.Request) -> web.Response:
        """Return server status and active tunnels."""
        tunnels = self.tunnel_manager.get_all_tunnels()
        tunnels_info = [tunnel.to_info() for tunnel in tunnels.values()]

        response = ServerStatusResponse(
            active_tunnels=self.tunnel_manager.get_tunnel_count(),
            tunnels=tunnels_info,
        )

        return web.json_response(response.model_dump(mode="json"))

    async def handle_index(self, request: web.Request) -> web.Response:
        """Return welcome page."""
        tunnel_count = self.tunnel_manager.get_tunnel_count()
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
                    <h3>Active Tunnels: {tunnel_count}</h3>
                </div>
                
                <h3>API Endpoints:</h3>
                <ul>
                    <li><code>GET /status</code> - Server status and active tunnels</li>
                    <li><code>WS /tunnel</code> - Create new tunnel (WebSocket)</li>
                    <li><code>* /:subdomain/*</code> - Proxied requests</li>
                </ul>
                
                <h3>Quick Start:</h3>
                <p>Connect a client to <code>ws://{request.host}/tunnel</code> to create a tunnel.</p>
            </div>
        </body>
        </html>
        """

        return web.Response(text=html, content_type="text/html")
