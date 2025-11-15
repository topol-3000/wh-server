"""Subdomain routing middleware for tunnel service."""

import logging

from aiohttp import web

from src.shared.config import Settings

logger = logging.getLogger(__name__)


def extract_subdomain(host: str, base_domain: str) -> str | None:
    """
    Extract subdomain (tunnel_id) from Host header.

    Examples:
        abc123.wormhole.app -> abc123
        wormhole.app -> None
        localhost:8080 -> None
    """
    if not host:
        return None

    # Remove port if present
    host_without_port = host.split(":")[0]

    # Check if this is the base domain
    if host_without_port == base_domain:
        return None

    # Extract subdomain
    if host_without_port.endswith(f".{base_domain}"):
        subdomain = host_without_port[: -len(f".{base_domain}")]
        return subdomain if subdomain else None

    return None


@web.middleware
async def subdomain_routing_middleware(request: web.Request, handler):
    """
    Route requests based on subdomain.

    - Base domain (e.g., wormhole.app) -> pass to normal handlers
    - Subdomain (e.g., abc123.wormhole.app) -> proxy to tunnel
    """
    settings: Settings = request.app["settings"]
    host = request.headers.get("Host", "")

    tunnel_id = extract_subdomain(host, settings.base_domain)

    if tunnel_id:
        # This is a tunneled request - always proxy
        request["tunnel_id"] = tunnel_id
        from src.tunnel_service.handlers import handle_proxied_request

        return await handle_proxied_request(request)

    # Base domain - pass to registered handlers
    return await handler(request)
