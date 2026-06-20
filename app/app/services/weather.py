from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Optional Redis cache; gracefully degrades to no-cache if Redis is unavailable.
_redis = None

try:
    import redis.asyncio as aioredis
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
except Exception:
    logger.warning("Redis unavailable — weather cache disabled")


_OWM_URL = "https://api.openweathermap.org/data/2.5/weather"

# Map OWM icon codes to simple condition labels
_CONDITION_MAP = {
    "01": "clear", "02": "partly_cloudy", "03": "cloudy", "04": "cloudy",
    "09": "rainy", "10": "rainy", "11": "stormy", "13": "snowy", "50": "foggy",
}


def _cache_key(lat: float, lon: float) -> str:
    return f"weather:{round(lat, 2)}:{round(lon, 2)}"


async def get_weather(lat: float, lon: float) -> dict:
    key = _cache_key(lat, lon)

    if _redis:
        try:
            cached = await _redis.get(key)
            if cached:
                data = json.loads(cached)
                data["cached"] = True
                return data
        except Exception:
            pass  # Redis miss; fall through to OWM

    if not settings.owm_api_key:
        return _mock_weather(lat, lon)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(_OWM_URL, params={
                "lat": lat, "lon": lon,
                "appid": settings.owm_api_key,
                "units": "metric",
            })
            resp.raise_for_status()
            raw = resp.json()
    except Exception as exc:
        logger.warning("OWM request failed: %s", exc)
        return _mock_weather(lat, lon)

    icon_code = raw.get("weather", [{}])[0].get("icon", "01d")
    prefix = icon_code[:2]
    condition = _CONDITION_MAP.get(prefix, "cloudy")

    result = {
        "condition": condition,
        "temp_c": round(raw.get("main", {}).get("temp", 20.0), 1),
        "icon": icon_code,
        "humidity": raw.get("main", {}).get("humidity"),
        "cached": False,
    }

    if _redis:
        try:
            await _redis.setex(key, settings.weather_cache_ttl, json.dumps(result))
        except Exception:
            pass

    return result


def _mock_weather(lat: float, lon: float) -> dict:
    return {
        "condition": "cloudy",
        "temp_c": 18.0,
        "icon": "03d",
        "humidity": 65,
        "cached": False,
    }
