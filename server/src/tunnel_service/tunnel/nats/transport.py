"""NATS transport implementation for tunnel service."""

from nats.aio.client import Client as NATSClient

from src.shared.logging import get_logger
from src.shared.models import InternalRequest, InternalResponse
from src.tunnel_service.tunnel.base_transport import TunnelTransport

logger = get_logger(__name__)


class NATSTunnelTransport(TunnelTransport):
    """NATS-based implementation of tunnel transport."""

    def __init__(self, nats_client: NATSClient, timeout: float = 10.0):
        """
        Initialize NATS transport.

        Args:
            nats_client: Connected NATS client
            timeout: Request timeout in seconds
        """
        self._nats_client = nats_client
        self._timeout = timeout

    async def send_request(self, tunnel_id: str, request: InternalRequest) -> InternalResponse:
        """Send request via NATS and wait for response.
        
        Args:
            tunnel_id: Target tunnel identifier
            request: Request to forward

        Returns:
            Response from the tunnel

        Raises:
            TimeoutError: If request times out
            Exception: For transport errors

        """
        subject = f"tunnel.{tunnel_id}"
        payload = request.model_dump_json().encode()

        logger.debug(f"Sending request to NATS subject", extra={"subject": subject})

        msg = await self._nats_client.request(
            subject,
            payload,
            timeout=self._timeout,
        )

        logger.debug(f"Received response from NATS for tunnel", extra={"tunnel_id": tunnel_id})

        return InternalResponse.model_validate_json(msg.data)
