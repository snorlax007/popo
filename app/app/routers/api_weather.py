from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from ..deps import get_current_device
from ..models import Device
from ..schemas import WeatherResponse
from ..services.weather import get_weather

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("", response_model=WeatherResponse)
async def weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    device: Device = Depends(get_current_device),
):
    data = await get_weather(lat, lon)
    return WeatherResponse(
        **data,
        server_time=datetime.now(timezone.utc),
    )
