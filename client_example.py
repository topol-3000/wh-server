"""
WormHole Client Example
Connects to WormHole server and tunnels requests to a local service.
"""

import asyncio
import logging
from typing import Optional

import aiohttp
from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WormHoleClient:
    """Client that creates a tunnel to expose local service."""
    
    def __init__(
        self,
        server_url: str,
        local_port: int,
        local_host: str = "localhost"
    ):
        self.server_url = server_url
        self.local_host = local_host
        self.local_port = local_port
        self.public_url: Optional[str] = None
        self.tunnel_id: Optional[str] = None
        
    async def start(self):
        """Connect to WormHole server and start tunneling."""
        tunnel_url = f"{self.server_url}/tunnel"
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(tunnel_url) as ws:
                logger.info(f"Connected to WormHole server: {self.server_url}")
                
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = msg.json()
                        await self._handle_message(ws, data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {ws.exception()}")
                        break
    
    async def _handle_message(self, ws: aiohttp.ClientWebSocketResponse, data: dict):
        """Handle messages from the server."""
        msg_type = data.get("type")
        
        if msg_type == "connected":
            self.tunnel_id = data.get("tunnel_id")
            self.public_url = data.get("public_url")
            logger.info("Tunnel established!")
            logger.info(f"Tunnel ID: {self.tunnel_id}")
            logger.info(f"Public URL: {self.public_url}")
            logger.info(f"Forwarding to: http://{self.local_host}:{self.local_port}")
            
        elif msg_type == "http_request":
            # Forward request to local service
            await self._forward_request(ws, data)
    
    async def _forward_request(self, ws: aiohttp.ClientWebSocketResponse, data: dict):
        """Forward HTTP request to local service and send response back."""
        request_id = data.get("request_id")
        method = data.get("method")
        path = data.get("path")
        headers = data.get("headers", {})
        body = data.get("body", "")
        
        logger.info(f"Forwarding {method} {path}")
        
        # Make request to local service
        local_url = f"http://{self.local_host}:{self.local_port}{path}"
        query_string = data.get("query_string", "")
        if query_string:
            local_url += f"?{query_string}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=local_url,
                    headers=headers,
                    data=body.encode("utf-8") if body else None
                ) as response:
                    response_body = await response.text()
                    response_headers = dict(response.headers)
                    
                    # Send response back to server
                    await ws.send_json({
                        "request_id": request_id,
                        "status": response.status,
                        "headers": response_headers,
                        "body": response_body
                    })
                    
                    logger.info(f"Response sent: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error forwarding request: {e}")
            # Send error response
            await ws.send_json({
                "request_id": request_id,
                "status": 502,
                "headers": {},
                "body": f"Error forwarding request: {str(e)}"
            })


async def run_local_test_server(port: int = 3000):
    """Run a simple local HTTP server for testing."""
    
    async def handle_request(request: web.Request) -> web.Response:
        """Handle test requests."""
        return web.Response(
            text=f"Hello from local server!\nPath: {request.path}\nMethod: {request.method}",
            content_type="text/plain"
        )
    
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handle_request)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", port)
    await site.start()
    
    logger.info(f"Local test server running on http://localhost:{port}")


async def main():
    """Main entry point."""
    import sys
    
    server_url = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8080"
    local_port = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    
    # Start local test server
    await run_local_test_server(local_port)
    
    # Connect to WormHole server
    client = WormHoleClient(server_url, local_port)
    await client.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
