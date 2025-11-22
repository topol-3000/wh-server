"""HTTP handlers for tunnel service."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_502_BAD_GATEWAY, HTTP_504_GATEWAY_TIMEOUT

from src.shared.models import InternalRequest, InternalResponse
from src.tunnel_service.tunnel.base_transport import TunnelTransport
from src.shared.logging import get_logger

logger = get_logger(__name__)


async def proxy_request_handler(request: Request) -> Response:
    """Handle incoming HTTP request and proxy through tunnel."""
    tunnel_id = request.state.tunnel_id
    tunnel_transport: TunnelTransport = request.app.state.tunnel_transport

    try:
        body = await request.body()
        internal_request = InternalRequest(
            tunnel_id=tunnel_id,
            method=request.method,
            path=request.url.path,
            query=request.url.query or "",
            headers=dict(request.headers),
            body=body.hex()
        )
        internal_response: InternalResponse = await tunnel_transport.send_request(internal_request)
        response_body = bytes.fromhex(internal_response.body) if internal_response.body else b""

        return Response(
            content=response_body,
            status_code=internal_response.status_code,
            headers=internal_response.headers,
        )

    except TimeoutError:
        logger.error(f"Request to tunnel {tunnel_id} timed out")
        return Response(content="Tunnel request timeout", status_code=HTTP_504_GATEWAY_TIMEOUT)

    except Exception as exc:
        logger.exception(f"Request to tunnel {tunnel_id} failed: {exc}")
        return Response(content="Tunnel error", status_code=HTTP_502_BAD_GATEWAY)
