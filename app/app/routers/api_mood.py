from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_device, get_current_user
from ..models import Device, MoodLog, User
from ..schemas import (
    MoodClassifyRequest,
    MoodClassifyResponse,
    MoodLogOut,
    MoodLogRequest,
)
from ..services.llm import classify_mood, get_popish_cue

router = APIRouter(prefix="/api/mood", tags=["mood"])


@router.post("/classify", response_model=MoodClassifyResponse)
async def mood_classify(
    body: MoodClassifyRequest,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    result = await classify_mood(body.transcript)
    mood = result["mood"]
    intent = result["intent"]
    confidence = result["confidence"]
    popish_cue = get_popish_cue(mood)

    # Auto-log the mood event; store transcript only if opted in
    log = MoodLog(
        device_id=device.id,
        mood=mood,
        intent=intent,
        popish_cue=popish_cue,
        user_transcript=body.transcript if body.store_transcript else None,
    )
    db.add(log)
    await db.commit()

    return MoodClassifyResponse(
        mood=mood,
        intent=intent,
        popish_cue=popish_cue,
        confidence=confidence,
        server_time=datetime.now(timezone.utc),
    )


@router.post("/log")
async def mood_log(
    body: MoodLogRequest,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    log = MoodLog(
        device_id=device.id,
        mood=body.mood,
        intent=body.intent,
        popish_cue=body.popish_cue,
    )
    db.add(log)
    await db.commit()
    return {"logged": True, "id": log.id}


@router.get("/history/{device_id}", response_model=list[MoodLogOut])
async def mood_history(
    device_id: int,
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify the device belongs to this user
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await db.execute(
        select(MoodLog)
        .where(MoodLog.device_id == device_id)
        .order_by(MoodLog.logged_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
