from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_admin_user, get_current_device
from ..models import Device, FirmwareVersion, User
from ..schemas import FirmwareOut, OTACheckResponse
from ..services.storage import generate_download_url, upload_firmware

router = APIRouter(tags=["ota"])


@router.get("/api/ota/check", response_model=OTACheckResponse)
async def ota_check(
    version: str = Query(..., description="Current device firmware version"),
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FirmwareVersion)
        .where(FirmwareVersion.is_stable == True)
        .order_by(FirmwareVersion.uploaded_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if not latest or latest.version == version:
        return OTACheckResponse(update_available=False, server_time=now)

    return OTACheckResponse(
        update_available=True,
        version=latest.version,
        download_url=generate_download_url(latest.s3_key),
        sha256=latest.sha256,
        changelog=latest.changelog,
        server_time=now,
    )


@router.post("/admin/firmware")
async def upload_firmware_binary(
    version: str,
    changelog: str = "",
    is_stable: bool = False,
    file: UploadFile = File(...),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    # Check version uniqueness
    result = await db.execute(
        select(FirmwareVersion).where(FirmwareVersion.version == version)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Version {version} already exists")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty firmware file")

    s3_key, sha256 = await upload_firmware(content, version)

    fw = FirmwareVersion(
        version=version,
        s3_key=s3_key,
        sha256=sha256,
        changelog=changelog or None,
        is_stable=is_stable,
    )
    db.add(fw)
    await db.commit()
    return FirmwareOut.model_validate(fw)


@router.get("/admin/firmware", response_model=list[FirmwareOut])
async def list_firmware(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FirmwareVersion).order_by(FirmwareVersion.uploaded_at.desc())
    )
    return result.scalars().all()
