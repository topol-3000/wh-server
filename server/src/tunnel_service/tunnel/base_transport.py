"""Abstract base classes for tunnel service."""

from abc import ABC, abstractmethod

from src.shared.models import InternalRequest, InternalResponse


class TunnelTransport(ABC):
    """Abstract interface for tunnel communication transport."""

    @abstractmethod
    async def send_request(self, request: InternalRequest) -> InternalResponse:
        """
        Send a request to a tunnel and wait for response.

        Args:
            request: Request to forward

        Returns:
            Response from the tunnel

        Raises:
            TimeoutError: If request times out
            Exception: For transport errors
        """
        pass
