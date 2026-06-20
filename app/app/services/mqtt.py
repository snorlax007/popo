from __future__ import annotations

import logging

from ..config import settings

logger = logging.getLogger(__name__)

_client = None


async def connect() -> None:
    global _client
    if not settings.mqtt_host:
        return
    try:
        import aiomqtt
        _client = aiomqtt.Client(
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
            username=settings.mqtt_user or None,
            password=settings.mqtt_pass or None,
        )
        logger.info("MQTT client configured for %s:%s", settings.mqtt_host, settings.mqtt_port)
    except Exception as exc:
        logger.warning("MQTT setup failed: %s", exc)


async def publish(topic: str, payload: str) -> bool:
    """Publish a message; returns True on success, False on failure."""
    if not _client:
        logger.warning("MQTT not connected — publish skipped (topic=%s)", topic)
        return False
    try:
        async with _client as c:
            await c.publish(topic, payload=payload.encode(), qos=1)
        logger.info("MQTT published to %s", topic)
        return True
    except Exception as exc:
        logger.error("MQTT publish failed: %s", exc)
        return False


def ota_topic(serial: str) -> str:
    return f"popo/{serial}/ota"


def command_topic(serial: str) -> str:
    return f"popo/{serial}/cmd"
