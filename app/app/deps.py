from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Cookie, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import decode_token, get_session_email
from .database import get_db
from .models import Device, User


async def get_current_device(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> Device:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    if not payload or payload.get("role") != "device":
        raise HTTPException(status_code=401, detail="Invalid or expired device token")
    serial = payload["sub"]
    result = await db.execute(select(Device).where(Device.serial == serial))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    if not payload or payload.get("role") != "user":
        raise HTTPException(status_code=401, detail="Invalid or expired user token")
    email = payload["sub"]
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_admin_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    email = get_session_email(session_token)
    if not email:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_admin:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return user
