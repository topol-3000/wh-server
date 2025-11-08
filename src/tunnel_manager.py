"""Tunnel management functionality."""

import asyncio
import logging
import secrets
import uuid
from collections.abc import Mapping

from .models import Tunnel

logger = logging.getLogger(__name__)


class TunnelManager:
    """Manages active tunnel connections and request routing."""

    def __init__(self) -> None:
        self._tunnels: dict[str, Tunnel] = {}
        self._pending_requests: dict[str, asyncio.Future[dict[str, str | int]]] = {}

    def create_tunnel(
        self,
        websocket,
        subdomain: str | None = None,
    ) -> Tunnel:
        """Create a new tunnel with unique ID and subdomain."""
        tunnel_id = str(uuid.uuid4())
        if subdomain is None:
            subdomain = secrets.token_urlsafe(8)

        tunnel = Tunnel(
            tunnel_id=tunnel_id,
            subdomain=subdomain,
            websocket=websocket,
        )

        self._tunnels[subdomain] = tunnel
        logger.info(f"Tunnel created: {subdomain} (ID: {tunnel_id})")
        return tunnel

    def get_tunnel(self, subdomain: str) -> Tunnel | None:
        """Get tunnel by subdomain."""
        return self._tunnels.get(subdomain)

    def remove_tunnel(self, subdomain: str) -> None:
        """Remove tunnel by subdomain."""
        if subdomain in self._tunnels:
            del self._tunnels[subdomain]
            logger.info(f"Tunnel removed: {subdomain}")

    def get_all_tunnels(self) -> Mapping[str, Tunnel]:
        """Get all active tunnels."""
        return self._tunnels

    def register_pending_request(
        self, request_id: str
    ) -> asyncio.Future[dict[str, str | int]]:
        """Register a pending request and return a future for the response."""
        future: asyncio.Future[dict[str, str | int]] = asyncio.Future()
        self._pending_requests[request_id] = future
        return future

    def resolve_pending_request(
        self, request_id: str, response_data: dict[str, str | int]
    ) -> None:
        """Resolve a pending request with response data."""
        if request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            if not future.done():
                future.set_result(response_data)

    def cleanup_pending_request(self, request_id: str) -> None:
        """Clean up a pending request."""
        if request_id in self._pending_requests:
            del self._pending_requests[request_id]

    def get_tunnel_count(self) -> int:
        """Get count of active tunnels."""
        return len(self._tunnels)
