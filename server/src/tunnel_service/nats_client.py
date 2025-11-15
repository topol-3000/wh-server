"""NATS client for tunnel service."""

import logging

import nats
from nats.aio.client import Client as NATSClient

from src.shared.config import Settings

logger = logging.getLogger(__name__)


async def setup_nats(app) -> NATSClient:
    """Connect to NATS server."""
    settings: Settings = app["settings"]

    nc = await nats.connect(settings.nats_url)
    logger.info(f"Connected to NATS at {settings.nats_url}")

    app["nats"] = nc
    return nc


async def cleanup_nats(app):
    """Disconnect from NATS server."""
    nc: NATSClient = app.get("nats")
    if nc:
        await nc.drain()
        logger.info("Disconnected from NATS")
