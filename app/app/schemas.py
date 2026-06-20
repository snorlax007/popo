from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class DeviceAuthRequest(BaseModel):
    serial: str
    firmware_version: str | None = None


class UserRegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class PairRequest(BaseModel):
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    server_time: datetime


# ── Devices ───────────────────────────────────────────────────────────────────

class DeviceOut(BaseModel):
    id: int
    serial: str
    name: str
    user_id: int | None
    firmware_version: str | None
    last_seen_at: datetime | None
    registered_at: datetime
    weather_lat: float | None
    weather_lon: float | None
    timezone: str

    class Config:
        from_attributes = True


class DevicePatch(BaseModel):
    name: str | None = None
    timezone: str | None = None
    weather_lat: float | None = None
    weather_lon: float | None = None


# ── Mood ──────────────────────────────────────────────────────────────────────

MoodLabel = Literal["happy", "sad", "excited", "confused", "sleepy", "scared", "neutral"]


class MoodClassifyRequest(BaseModel):
    transcript: str
    store_transcript: bool = False  # opt-in for GDPR


class MoodClassifyResponse(BaseModel):
    mood: MoodLabel
    intent: str
    popish_cue: str
    confidence: float
    server_time: datetime


class MoodLogRequest(BaseModel):
    mood: MoodLabel
    intent: str | None = None
    popish_cue: str | None = None


class MoodLogOut(BaseModel):
    id: int
    mood: str
    intent: str | None
    popish_cue: str | None
    logged_at: datetime

    class Config:
        from_attributes = True


# ── Weather ───────────────────────────────────────────────────────────────────

class WeatherResponse(BaseModel):
    condition: str
    temp_c: float
    icon: str
    humidity: int | None = None
    cached: bool
    server_time: datetime


# ── OTA ───────────────────────────────────────────────────────────────────────

class OTACheckResponse(BaseModel):
    update_available: bool
    version: str | None = None
    download_url: str | None = None
    sha256: str | None = None
    changelog: str | None = None
    server_time: datetime


class FirmwareOut(BaseModel):
    id: int
    version: str
    sha256: str
    changelog: str | None
    is_stable: bool
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ── Push ──────────────────────────────────────────────────────────────────────

class PushTokenRequest(BaseModel):
    platform: Literal["ios", "android"]
    token: str


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: str
    status: int
