from uuid import uuid4

from nats.aio.client import Client as NATSClient
from starlette.requests import Request
from starlette.responses import Response

from src.shared.config import Settings, get_settings
from src.shared.logging import get_logger
from src.shared.models import InternalRequest, InternalResponse

logger = get_logger(__name__)


class TunnelRequestHandler:
    """
    Encapsulates all logic related to handling HTTP requests that must be
    forwarded to tunnels via NATS.
    """

    def __init__(self):
        self.__settings: Settings = get_settings()
        self.__base_domain: str = self.__settings.base_domain
        self.__request_timeout: float = self.__settings.request_timeout

    def _get_nats_client(self, request: Request) -> NATSClient:
        """Get the NATS client from the application state."""
        nats_client = request.app.state.nats
        if nats_client is None:
            raise RuntimeError("NATS client is not initialized")
        return nats_client

    async def handle(self, request: Request) -> Response:
        """Public entry point used by Starlette router."""
        tunnel_id = self._extract_tunnel_id(request)
        request_id = str(uuid4())

        try:
            logger.info(f"Incoming request {request_id} for tunnel {tunnel_id}")

            internal_req = await self._build_internal_request(request, request_id, tunnel_id)
            internal_resp = await self._send_to_nats(request, tunnel_id, internal_req)

            return self._build_http_response(internal_resp)

        except TimeoutError:
            logger.error(f"Request {request_id} timed out")
            return Response(content="Tunnel request timeout", status_code=504)

        except Exception as exc:
            logger.exception(f"Request {request_id} failed due to unexpected error: {exc}")
            return Response(content="Tunnel error", status_code=502)

    def _extract_tunnel_id(self, request: Request) -> str:
        """
        Extract the tunnel_id from the incoming Host header.
        Falls back to the raw host if base domain is not matched.
        """
        host = request.headers.get("host", "").split(":")[0]

        if host.endswith(f".{self.__base_domain}"):
            return host[: -len(f".{self.__base_domain}")]

        return host  # fallback: localhost / IP / unknown host

    async def _build_internal_request(
        self,
        request: Request,
        request_id: str,
        tunnel_id: str,
    ) -> InternalRequest:
        """Convert incoming Starlette request → InternalRequest."""
        body_bytes = await request.body()

        return InternalRequest(
            request_id=request_id,
            tunnel_id=tunnel_id,
            method=request.method,
            path=request.url.path,
            query=request.url.query or "",
            headers=dict(request.headers),
            body=body_bytes.hex() if body_bytes else "",
            is_websocket=False,
        )

    async def _send_to_nats(
        self, request: Request, tunnel_id: str, internal_req: InternalRequest
    ) -> InternalResponse:
        """
        Send the request to the corresponding tunnel via NATS and wait for response.
        """
        logger.debug(f"Sending request to NATS subject tunnel.{tunnel_id}")

        nats_client = self._get_nats_client(request)
        subject = f"tunnel.{tunnel_id}"
        payload = internal_req.model_dump_json().encode()

        msg = await nats_client.request(
            subject,
            payload,
            timeout=self.__request_timeout,
        )

        logger.debug(f"Received response from NATS for tunnel {tunnel_id}")

        return InternalResponse.model_validate_json(msg.data)

    def _build_http_response(self, internal_resp: InternalResponse) -> Response:
        """
        Translate InternalResponse → Starlette Response.
        """
        body_bytes = bytes.fromhex(internal_resp.body) if internal_resp.body else b""

        return Response(
            content=body_bytes,
            status_code=internal_resp.status_code,
            headers=internal_resp.headers,
        )
