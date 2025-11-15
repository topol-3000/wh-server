"""Data models for the WormHole server."""

from datetime import datetime

from aiohttp import web
from pydantic import BaseModel, Field


class TunnelInfo(BaseModel):
    """Tunnel metadata and statistics."""

    tunnel_id: str = Field(description="Unique tunnel identifier")
    subdomain: str = Field(description="Subdomain assigned to this tunnel")
    created_at: datetime = Field(description="Tunnel creation timestamp")
    request_count: int = Field(default=0, description="Number of requests handled")


class Tunnel:
    """Active tunnel connection with WebSocket."""

    def __init__(
        self,
        tunnel_id: str,
        subdomain: str,
        websocket: web.WebSocketResponse,
        created_at: datetime | None = None,
    ) -> None:
        self.tunnel_id = tunnel_id
        self.subdomain = subdomain
        self.websocket = websocket
        self.created_at = created_at or datetime.now()
        self.request_count = 0

    def to_info(self) -> TunnelInfo:
        """Convert to TunnelInfo for serialization."""
        return TunnelInfo(
            tunnel_id=self.tunnel_id,
            subdomain=self.subdomain,
            created_at=self.created_at,
            request_count=self.request_count,
        )


class TunnelConnectedMessage(BaseModel):
    """Message sent to client when tunnel is established."""

    type: str = Field(default="connected", frozen=True)
    tunnel_id: str
    subdomain: str
    public_url: str


class HTTPRequestMessage(BaseModel):
    """HTTP request forwarded to tunnel client."""

    type: str = Field(default="http_request", frozen=True)
    request_id: str
    method: str
    path: str
    query_string: str = Field(default="")
    headers: dict[str, str]
    body: str = Field(default="")


class HTTPResponseMessage(BaseModel):
    """HTTP response from tunnel client."""

    request_id: str
    status: int = Field(ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = Field(default="")


class ServerStatusResponse(BaseModel):
    """Server status information."""

    status: str = Field(default="running")
    active_tunnels: int
    tunnels: list[TunnelInfo]
