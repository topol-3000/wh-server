"""NATS client for tunnel service."""

import nats
from nats.aio.client import Client as NATSClient

from src.shared.config import get_settings
from src.shared.logging import get_logger

logger = get_logger(__name__)


async def setup_nats() -> NATSClient:
    """Connect to NATS server."""
    settings = get_settings()

    nc = await nats.connect(settings.nats_url)
    logger.info(f"Connected to NATS at {settings.nats_url}")

    return nc


async def cleanup_nats(nc: NATSClient | None):
    """Disconnect from NATS server."""
    if nc:
        await nc.drain()
        logger.info("Disconnected from NATS")
