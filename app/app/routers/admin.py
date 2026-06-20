from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_session, delete_session, verify_password
from ..database import get_db
from ..deps import get_admin_user
from ..models import Device, FirmwareVersion, MoodLog, User
from ..services import mqtt, storage

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/admin", tags=["admin"])

MOOD_COLORS = {
    "happy": "#16A34A",
    "sad": "#2563EB",
    "excited": "#D97706",
    "confused": "#7C3AED",
    "sleepy": "#6B7280",
    "scared": "#DC2626",
    "neutral": "#9CA3AF",
}

_ICONS = {
    "grid": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/></svg>',
    "cpu": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>',
    "upload": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
    "map": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M9 3 4 5v16l5-2 6 2 5-2V3l-5 2-6-2Z"/><line x1="9" y1="3" x2="9" y2="19"/><line x1="15" y1="5" x2="15" y2="21"/></svg>',
}

NAV = [
    {"key": "dashboard", "label": "Fleet", "href": "/admin/", "icon": _ICONS["grid"]},
    {"key": "devices", "label": "Devices", "href": "/admin/", "icon": _ICONS["cpu"]},
    {"key": "firmware", "label": "Firmware", "href": "/admin/firmware", "icon": _ICONS["upload"]},
    {"key": "roadmap", "label": "Roadmap", "href": "/admin/roadmap", "icon": _ICONS["map"]},
]


def _ctx(request: Request, active: str, **extra):
    from ..config import settings
    return {
        "request": request,
        "app_name": settings.app_name,
        "app_tagline": settings.app_tagline,
        "nav": NAV,
        "active": active,
        "mood_colors": MOOD_COLORS,
        **extra,
    }


def _toast(html: str, message: str, ok: bool = True) -> HTMLResponse:
    safe = message.encode("ascii", "replace").decode("ascii")
    status = 200 if ok else 422
    return HTMLResponse(html, status_code=status, headers={"X-Toast": safe})


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "pages/login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_admin or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request, "pages/login.html",
            {"request": request, "error": "Invalid credentials or not an admin."},
            status_code=401,
        )
    token = create_session(email)
    response = RedirectResponse("/admin/", status_code=303)
    response.set_cookie("session", token, httponly=True, samesite="strict", max_age=86400)
    return response


@router.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session", "")
    delete_session(token)
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie("session")
    return response


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device))
    devices = result.scalars().all()

    now = datetime.now(timezone.utc)
    online_cutoff = now - timedelta(minutes=5)

    def _as_utc(dt):
        if dt is None:
            return None
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

    total = len(devices)
    online = sum(
        1 for d in devices
        if _as_utc(d.last_seen_at) is not None and _as_utc(d.last_seen_at) >= online_cutoff
    )
    offline = total - online

    # Check for OTA updates pending
    fw_result = await db.execute(
        select(FirmwareVersion)
        .where(FirmwareVersion.is_stable == True)
        .order_by(FirmwareVersion.uploaded_at.desc())
        .limit(1)
    )
    latest_fw = fw_result.scalar_one_or_none()
    update_pending = sum(
        1 for d in devices
        if latest_fw and d.firmware_version != latest_fw.version
    ) if latest_fw else 0

    stats = [
        {"label": "Total Devices", "value": str(total), "delta": "", "dir": "up"},
        {"label": "Online (5m)", "value": str(online), "delta": "", "dir": "up"},
        {"label": "Offline", "value": str(offline), "delta": "", "dir": "down" if offline else "up"},
        {"label": "Update Pending", "value": str(update_pending), "delta": "", "dir": "down" if update_pending else "up"},
    ]

    # Annotate devices with pre-computed delta seconds so template avoids tz comparison
    def _delta(dt) -> float | None:
        if dt is None:
            return None
        aware = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        return (now - aware).total_seconds()

    for d in devices:
        d.last_seen_delta = _delta(d.last_seen_at)

    return templates.TemplateResponse(
        request, "pages/dashboard.html",
        _ctx(request, "dashboard", devices=devices, stats=stats, latest_fw=latest_fw, now=now),
    )


# ── Device Detail ─────────────────────────────────────────────────────────────

@router.get("/devices/{device_id}", response_class=HTMLResponse)
async def device_detail(
    device_id: int,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    logs_result = await db.execute(
        select(MoodLog)
        .where(MoodLog.device_id == device_id)
        .order_by(MoodLog.logged_at.desc())
        .limit(50)
    )
    mood_logs = logs_result.scalars().all()

    fw_result = await db.execute(
        select(FirmwareVersion)
        .where(FirmwareVersion.is_stable == True)
        .order_by(FirmwareVersion.uploaded_at.desc())
        .limit(1)
    )
    latest_fw = fw_result.scalar_one_or_none()
    update_available = latest_fw and latest_fw.version != device.firmware_version

    return templates.TemplateResponse(
        request, "pages/device_detail.html",
        _ctx(request, "devices", device=device, mood_logs=mood_logs,
             latest_fw=latest_fw, update_available=update_available),
    )


@router.post("/ota/push/{device_id}", response_class=HTMLResponse)
async def ota_push(
    device_id: int,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        return _toast("", "Device not found", ok=False)

    ok = await mqtt.publish(
        mqtt.ota_topic(device.serial),
        json.dumps({"action": "ota_check"}),
    )
    msg = "OTA notification sent. Device will download and reboot." if ok else "MQTT not connected — notification skipped."
    return _toast("", msg, ok=ok)


# ── Firmware Management ───────────────────────────────────────────────────────

@router.get("/firmware", response_class=HTMLResponse)
async def firmware_page(
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FirmwareVersion).order_by(FirmwareVersion.uploaded_at.desc())
    )
    versions = result.scalars().all()
    return templates.TemplateResponse(
        request, "pages/firmware.html",
        _ctx(request, "firmware", versions=versions),
    )


@router.get("/roadmap", response_class=HTMLResponse)
async def roadmap_page(
    request: Request,
    admin: User = Depends(get_admin_user),
):
    roadmap = [
        {"title": "Device auth + registration API", "state": "done", "note": "Shipped in v0.1"},
        {"title": "Weather proxy with Redis cache", "state": "done", "note": "Shipped in v0.1"},
        {"title": "LLM mood classification (Claude Haiku)", "state": "done", "note": "Shipped in v0.1"},
        {"title": "Admin HTMX dashboard", "state": "done", "note": "Shipped in v0.1"},
        {"title": "OTA firmware distribution", "state": "done", "note": "Shipped in v0.1"},
        {"title": "MQTT OTA push notifications", "state": "progress", "note": "Requires Mosquitto broker"},
        {"title": "Push notification delivery (FCM/APNS)", "state": "planned", "note": "Phase 3 — mobile app"},
        {"title": "Subscription billing (Stripe)", "state": "planned", "note": "P2 — pricing model TBD"},
        {"title": "Multi-user device sharing", "state": "planned", "note": "P2 — schema extension needed"},
        {"title": "GDPR data deletion API", "state": "planned", "note": "Required before EU launch"},
    ]
    return templates.TemplateResponse(
        request, "pages/roadmap.html",
        _ctx(request, "roadmap", roadmap=roadmap),
    )


@router.post("/firmware/upload", response_class=HTMLResponse)
async def firmware_upload(
    request: Request,
    version: str = Form(...),
    changelog: str = Form(""),
    is_stable: bool = Form(False),
    file: UploadFile = File(...),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FirmwareVersion).where(FirmwareVersion.version == version)
    )
    if result.scalar_one_or_none():
        return _toast("", f"Version {version} already exists", ok=False)

    content = await file.read()
    if not content:
        return _toast("", "Empty firmware file", ok=False)

    try:
        s3_key, sha256 = await storage.upload_firmware(content, version)
    except Exception as exc:
        return _toast("", f"Upload failed: {exc}", ok=False)

    fw = FirmwareVersion(
        version=version,
        s3_key=s3_key,
        sha256=sha256,
        changelog=changelog or None,
        is_stable=is_stable,
    )
    db.add(fw)
    await db.commit()

    html = templates.get_template("partials/firmware_row.html").render(
        {"firmware": fw, "request": request}
    )
    return _toast(html, f"Firmware {version} uploaded successfully.")
