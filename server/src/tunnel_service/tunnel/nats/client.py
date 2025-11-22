"""NATS client for tunnel service."""

import nats
from nats.aio.client import Client as NATSClient

from src.shared.logging import get_logger

logger = get_logger(__name__)


async def setup_nats(url: str) -> NATSClient:
    """Connect to NATS server."""
    nc = await nats.connect(url)
    logger.info(f"Connected to NATS at {url}")

    return nc


async def cleanup_nats(nc: NATSClient | None):
    """Disconnect from NATS server."""
    if nc:
        await nc.drain()
        logger.info("Disconnected from NATS")
