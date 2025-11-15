"""Middleware for routing requests based on subdomain."""

import logging
from collections.abc import Awaitable, Callable

from aiohttp import web

from ..shared.config import Settings

logger = logging.getLogger(__name__)


def extract_subdomain(host: str, base_domain: str) -> str | None:
    """Extract subdomain from Host header. Returns None for base domain."""
    if not host:
        return None

    host_without_port = host.split(":")[0]

    if host_without_port == base_domain:
        return None

    if not host_without_port.endswith(f".{base_domain}"):
        return None

    subdomain = host_without_port[: -(len(base_domain) + 1)]
    return subdomain if subdomain else None


@web.middleware
async def subdomain_routing_middleware(
    request: web.Request, handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    """
    Middleware to handle subdomain-based routing.

    - Base domain requests go to admin routes (/, /status, /tunnel)
    - Subdomain requests are always proxied to tunnels (including /status, /tunnel paths)
    """
    settings: Settings = request.app["settings"]
    host = request.headers.get("Host", "")
    subdomain = extract_subdomain(host, settings.base_domain)

    request["subdomain"] = subdomain

    if subdomain is not None:
        route_name = request.match_info.route.name if request.match_info.route else None
        if route_name != "proxy":
            # Force routing to the proxy handler by getting it from the app
            proxy_handler = request.app["proxy_handler"]
            return await proxy_handler(request)

    return await handler(request)
