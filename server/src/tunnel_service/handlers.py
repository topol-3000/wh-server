"""HTTP handlers for tunnel service (data plane only)."""

import logging
from uuid import uuid4

from aiohttp import web

from src.shared.config import Settings
from src.shared.models import InternalRequest, InternalResponse

logger = logging.getLogger(__name__)


async def handle_proxied_request(request: web.Request) -> web.Response:
    """
    Handle incoming HTTP request for a tunnel.

    Extracts tunnel_id from request, converts to InternalRequest,
    sends via NATS, waits for response, converts back to HTTP response.
    """
    settings: Settings = request.app["settings"]
    tunnel_id: str = request["tunnel_id"]
    nats_client = request.app["nats"]

    # Generate unique request ID
    request_id = str(uuid4())

    # Read request body
    body = await request.read()

    # Convert HTTP request to internal format
    internal_req = InternalRequest(
        request_id=request_id,
        tunnel_id=tunnel_id,
        method=request.method,
        path=request.path,
        query=request.query_string,
        headers=dict(request.headers),
        body=body.hex() if body else "",
        is_websocket=False,
    )

    try:
        # Send request via NATS and wait for response
        logger.info(f"Forwarding request {request_id} to tunnel {tunnel_id}")

        response = await nats_client.request(
            f"tunnel.{tunnel_id}",
            internal_req.model_dump_json().encode(),
            timeout=settings.request_timeout,
        )

        # Parse response
        internal_resp = InternalResponse.model_validate_json(response.data)

        # Convert back to HTTP response
        body_bytes = bytes.fromhex(internal_resp.body) if internal_resp.body else b""

        return web.Response(
            status=internal_resp.status_code,
            headers=internal_resp.headers,
            body=body_bytes,
        )

    except TimeoutError:
        logger.error(f"Request {request_id} timed out")
        return web.Response(status=504, text="Tunnel request timeout")
    except Exception as e:
        logger.error(f"Request {request_id} failed: {e}")
        return web.Response(status=502, text="Tunnel error")


