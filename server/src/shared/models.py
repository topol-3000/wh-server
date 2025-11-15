"""Data models for the WormHole server."""

from pydantic import BaseModel, Field


class InternalRequest(BaseModel):
    """Internal request format sent via NATS to tunnel."""

    request_id: str = Field(description="Unique request identifier")
    tunnel_id: str = Field(description="Target tunnel ID")
    method: str = Field(description="HTTP method")
    path: str = Field(description="Request path")
    query: str = Field(default="", description="Query string")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    body: str = Field(default="", description="Request body (hex encoded)")
    is_websocket: bool = Field(default=False, description="Whether this is a WebSocket upgrade")


class InternalResponse(BaseModel):
    """Internal response format returned via NATS from tunnel."""

    request_id: str = Field(description="Matching request identifier")
    status_code: int = Field(ge=100, le=599, description="HTTP status code")
    headers: dict[str, str] = Field(default_factory=dict, description="Response headers")
    body: str = Field(default="", description="Response body (hex encoded)")
