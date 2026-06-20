from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    create_device_token,
    create_user_token,
    decode_token,
    generate_pairing_code,
    hash_password,
    verify_password,
)
from ..database import get_db
from ..models import Device, User
from ..schemas import (
    DeviceAuthRequest,
    PairRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/device", response_model=TokenResponse)
async def device_auth(body: DeviceAuthRequest, db: AsyncSession = Depends(get_db)):
    """Device registers or re-authenticates; auto-creates device record on first call."""
    result = await db.execute(select(Device).where(Device.serial == body.serial))
    device = result.scalar_one_or_none()

    if not device:
        device = Device(serial=body.serial, firmware_version=body.firmware_version)
        db.add(device)

    device.last_seen_at = datetime.now(timezone.utc)
    if body.firmware_version:
        device.firmware_version = body.firmware_version
    await db.commit()

    return TokenResponse(
        access_token=create_device_token(body.serial),
        server_time=datetime.now(timezone.utc),
    )


@router.post("/user/register", response_model=TokenResponse)
async def user_register(body: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
    )
    db.add(user)
    await db.commit()
    return TokenResponse(
        access_token=create_user_token(body.email),
        server_time=datetime.now(timezone.utc),
    )


@router.post("/user", response_model=TokenResponse)
async def user_login(body: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(
        access_token=create_user_token(body.email),
        server_time=datetime.now(timezone.utc),
    )


@router.post("/pair/generate")
async def generate_code(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Device calls this to get a 6-digit pairing code (valid 10 minutes)."""
    payload = decode_token(authorization.removeprefix("Bearer "))
    if not payload or payload.get("role") != "device":
        raise HTTPException(status_code=401, detail="Device token required")

    result = await db.execute(select(Device).where(Device.serial == payload["sub"]))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    code = generate_pairing_code()
    device.pairing_code = code
    device.pairing_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.commit()
    return {"pairing_code": code, "expires_in_seconds": 600}


@router.post("/pair")
async def pair_device(
    body: PairRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """User submits 6-digit code to claim a device."""
    payload = decode_token(authorization.removeprefix("Bearer "))
    if not payload or payload.get("role") != "user":
        raise HTTPException(status_code=401, detail="User token required")

    result = await db.execute(select(User).where(User.email == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Device).where(Device.pairing_code == body.code))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=400, detail="Invalid pairing code")
    if device.pairing_expires_at and device.pairing_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Pairing code expired")
    if device.user_id and device.user_id != user.id:
        raise HTTPException(status_code=409, detail="Device already claimed by another user")

    device.user_id = user.id
    device.pairing_code = None
    device.pairing_expires_at = None
    await db.commit()
    return {"paired": True, "device_id": device.id, "device_serial": device.serial}
