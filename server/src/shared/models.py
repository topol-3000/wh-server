"""Data models for the WormHole server."""

from typing import Annotated
from pydantic import BaseModel, Field


class InternalRequest(BaseModel):
    """Internal request format sent via NATS to tunnel."""

    request_id: Annotated[str, Field(description="Unique request identifier")]
    tunnel_id: Annotated[str, Field(description="Target tunnel ID")]
    method: Annotated[str, Field(description="HTTP method")]
    path: Annotated[str, Field(description="Request path")]
    query: Annotated[str, Field(description="Query string")] = ""
    headers: Annotated[dict[str, str], Field(description="HTTP headers")] = {}
    body: Annotated[str, Field(description="Request body (hex encoded")] = ""


class InternalResponse(BaseModel):
    """Internal response format returned via NATS from tunnel."""

    request_id: Annotated[str, Field(description="Matching request identifier")]
    status_code: Annotated[int, Field(ge=100, le=599, description="HTTP status code")]
    headers: Annotated[dict[str, str], Field(description="Response headers")] = {}
    body: Annotated[str, Field(description="Response body (hex encoded")] = ""