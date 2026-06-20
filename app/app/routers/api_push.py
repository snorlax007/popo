from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import PushToken, User
from ..schemas import PushTokenRequest

router = APIRouter(prefix="/api/push", tags=["push"])


@router.post("/token")
async def register_push_token(
    body: PushTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PushToken).where(PushToken.token == body.token))
    existing = result.scalar_one_or_none()
    if existing:
        existing.platform = body.platform
        existing.user_id = user.id
    else:
        db.add(PushToken(user_id=user.id, platform=body.platform, token=body.token))
    await db.commit()
    return {"registered": True}


@router.delete("/token/{token}")
async def unregister_push_token(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PushToken).where(PushToken.token == token, PushToken.user_id == user.id)
    )
    pt = result.scalar_one_or_none()
    if not pt:
        raise HTTPException(status_code=404, detail="Token not found")
    await db.delete(pt)
    await db.commit()
    return {"unregistered": True}
