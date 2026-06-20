"""Popo Cloud Backend — FastAPI + HTMX.

Device REST API + HTMX admin dashboard for the Popo AI desk companion.

Run locally:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .database import init_db
from .routers import api_auth, api_devices, api_mood, api_ota, api_push, api_weather
from .routers.admin import router as admin_router
from .services import mqtt as mqtt_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Starting Popo Cloud Backend...")
    await init_db()
    await _seed_admin()
    await mqtt_service.connect()
    yield
    logger.info("Shutdown complete.")


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(api_auth.router)
app.include_router(api_devices.router)
app.include_router(api_mood.router)
app.include_router(api_ota.router)
app.include_router(api_push.router)
app.include_router(api_weather.router)
app.include_router(admin_router)


@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse("/admin/")


@app.get("/healthz")
async def healthz():
    checks: dict[str, str] = {"status": "ok"}

    try:
        from .database import AsyncSessionLocal
        async with AsyncSessionLocal() as s:
            await s.execute(__import__("sqlalchemy", fromlist=["text"]).text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc}"

    try:
        from .services.weather import _redis
        if _redis:
            await _redis.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not_configured"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    return checks


async def _seed_admin():
    """Create the default admin user on first run if it doesn't exist."""
    try:
        from sqlalchemy import select
        from .database import AsyncSessionLocal
        from .models import User
        from .auth import hash_password

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == settings.admin_email))
            if not result.scalar_one_or_none():
                admin = User(
                    email=settings.admin_email,
                    hashed_password=hash_password(settings.admin_password),
                    name="Admin",
                    is_admin=True,
                )
                db.add(admin)
                await db.commit()
                logger.info("Default admin user created: %s", settings.admin_email)
    except Exception as exc:
        logger.warning("Could not seed admin user: %s", exc)
