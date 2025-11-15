import logging
from uuid import uuid4

from aiohttp import web
from nats.aio.client import Client as NATSClient

from src.shared.config import Settings
from src.shared.models import InternalRequest, InternalResponse

logger = logging.getLogger(__name__)


class TunnelRequestHandler:
    """
    Encapsulates all logic related to handling HTTP requests that must be
    forwarded to tunnels via NATS.
    """

    def __init__(self, app: web.Application):
        self.__app: web.Application = app
        settings: Settings = app["settings"]
        self.__base_domain: str = settings.base_domain
        self.__request_timeout: float = settings.request_timeout

    @property
    def _nats_client(self) -> NATSClient:
        """Get the NATS client from the application context."""
        if self.__app.get("nats") is None:
            raise RuntimeError("NATS client is not initialized")

        return self.__app["nats"]

    async def handle(self, request: web.Request) -> web.Response:
        """Public entry point used by aiohttp router."""
        tunnel_id = self._extract_tunnel_id(request)
        request_id = str(uuid4())

        try:
            logger.info("Incoming request %s for tunnel %s", request_id, tunnel_id)

            internal_req = await self._build_internal_request(request, request_id, tunnel_id)
            internal_resp = await self._send_to_nats(tunnel_id, internal_req)

            return self._build_http_response(internal_resp)

        except TimeoutError:
            logger.error("Request %s timed out", request_id)
            return web.Response(status=504, text="Tunnel request timeout")

        except Exception as exc:
            logger.exception("Request %s failed due to unexpected error: %s", request_id, exc)
            return web.Response(status=502, text="Tunnel error")

    def _extract_tunnel_id(self, request: web.Request) -> str:
        """
        Extract the tunnel_id from the incoming Host header.
        Falls back to the raw host if base domain is not matched.
        """
        host = request.headers.get("Host", "").split(":")[0]

        if host.endswith(f".{self.__base_domain}"):
            return host[: -len(f".{self.__base_domain}")]

        return host  # fallback: localhost / IP / unknown host

    async def _build_internal_request(
        self,
        request: web.Request,
        request_id: str,
        tunnel_id: str,
    ) -> InternalRequest:
        """Convert incoming aiohttp request → InternalRequest."""
        body_bytes = await request.read()

        return InternalRequest(
            request_id=request_id,
            tunnel_id=tunnel_id,
            method=request.method,
            path=request.path,
            query=request.query_string,
            headers=dict(request.headers),
            body=body_bytes.hex() if body_bytes else "",
            is_websocket=False,
        )

    async def _send_to_nats(
        self, tunnel_id: str, internal_req: InternalRequest
    ) -> InternalResponse:
        """
        Send the request to the corresponding tunnel via NATS and wait for response.
        """
        logger.debug("Sending request to NATS subject tunnel.%s", tunnel_id)

        subject = f"tunnel.{tunnel_id}"
        payload = internal_req.model_dump_json().encode()

        msg = await self._nats_client.request(
            subject,
            payload,
            timeout=self.__request_timeout,
        )

        logger.debug("Received response from NATS for tunnel %s", tunnel_id)

        return InternalResponse.model_validate_json(msg.data)

    def _build_http_response(self, internal_resp: InternalResponse) -> web.Response:
        """
        Translate InternalResponse → aiohttp.Response.
        """
        body_bytes = bytes.fromhex(internal_resp.body) if internal_resp.body else b""

        return web.Response(
            status=internal_resp.status_code,
            headers=internal_resp.headers,
            body=body_bytes,
        )
