# Popo Cloud Backend — Dev Notes
*AiNa Stage 4: Architecture, how to run, what's stubbed*

---

## Architecture

```
popo/aina-out/popo/app/
├── app/
│   ├── main.py          FastAPI app entry point + lifespan (DB init, admin seed, MQTT connect)
│   ├── config.py        Pydantic Settings — reads from env vars / .env
│   ├── database.py      SQLAlchemy async engine + Base + session factory
│   ├── models.py        ORM models: User, Device, MoodLog, FirmwareVersion, PushToken
│   ├── schemas.py       Pydantic request/response shapes
│   ├── auth.py          JWT (python-jose) + bcrypt password hashing + session token store
│   ├── deps.py          FastAPI dependency functions (get_current_device, get_admin_user, …)
│   ├── routers/
│   │   ├── api_auth.py    POST /api/auth/device, /user, /user/register, /pair/*
│   │   ├── api_devices.py GET/PATCH/DELETE /api/devices
│   │   ├── api_mood.py    POST /api/mood/classify, /log · GET /api/mood/history/{id}
│   │   ├── api_weather.py GET /api/weather
│   │   ├── api_ota.py     GET /api/ota/check · POST /admin/firmware
│   │   ├── api_push.py    POST/DELETE /api/push/token
│   │   └── admin.py       /admin/* HTMX admin dashboard
│   └── services/
│       ├── llm.py         Claude Haiku mood classify + rule-based fallback
│       ├── weather.py     OWM proxy + Redis TTL cache
│       ├── storage.py     S3/R2 firmware upload + signed URL generation
│       └── mqtt.py        aiomqtt client + publish helpers
├── templates/             Jinja2 templates (HTMX, server-rendered)
├── static/css/app.css     AiNa golden design system + Popo extensions
├── static/js/htmx.min.js  Vendored HTMX
├── tests/                 pytest test suite (28 tests, all passing)
├── docker-compose.yml     Full stack: backend + postgres + redis + mosquitto
├── mosquitto.conf         Mosquitto broker config
├── Dockerfile             Multi-stage Docker build
└── requirements.txt       Python dependencies
```

## How to Run

### Local dev (SQLite, no external services)
```bash
cd app/
pip install -r requirements.txt
DATABASE_URL=sqlite+aiosqlite:///./popo.db uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000 → redirects to admin dashboard.
Default admin: `admin@popo.local` / `changeme123` (set via `ADMIN_EMAIL` + `ADMIN_PASSWORD`).

### Full stack (Docker Compose)
```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, OWM_API_KEY, S3 credentials
docker compose up -d
# Server at http://localhost:8000
```

### Tests
```bash
DATABASE_URL=sqlite+aiosqlite:///:memory: python3 -m pytest tests/ -v --asyncio-mode=auto
# 28 tests, all passing
```

## Key Design Decisions

### Graceful degradation
Every external service (Redis, S3, MQTT, Anthropic) degrades gracefully:
- **No Redis**: Weather cache disabled; OWM called on every request (acceptable at low device count)
- **No Anthropic API key**: Rule-based mood classifier kicks in (keyword matching, 7 moods)
- **No S3 credentials**: Firmware binaries written to `/tmp` with local path served (dev only)
- **No MQTT**: OTA push notifications logged as "skipped"; device can still poll `/api/ota/check`

This means the server always starts and serves requests — no hard crash on missing config.

### SQLite for dev, PostgreSQL for production
`DATABASE_URL=sqlite+aiosqlite:///./popo.db` works out of the box for dev/testing.
Switch to `postgresql+asyncpg://...` in production via env var. Alembic handles migrations.

### JWT auth (no OAuth)
Devices get a 30-day JWT, users get a 7-day JWT. Both are signed HS256 with `SECRET_KEY`.
No refresh tokens in V1 — devices re-authenticate after 30 days.
Admin dashboard uses session cookies (module-level dict in V1; move to Redis in production).

### Mood classification: LLM → fallback
`POST /api/mood/classify` calls Claude Haiku via the Anthropic SDK. If the API key is absent
or the call fails, a keyword-based rule engine returns one of the 7 moods with confidence 0.5–0.7.
The `popish_cue` is always returned regardless of which path ran.

### Per-device daily LLM cap
`device_llm_daily_cap = 500` (config). **Not yet enforced in code** — add a Redis counter
(`llm_cap:{serial}:{date}`) before Phase 4 beta if LLM costs become a concern.

## What's Stubbed / Not Implemented

| Item | Status | What's needed |
|---|---|---|
| Alembic migrations | Not set up (auto-creates tables via `init_db()`) | `alembic init` + version files |
| Per-device LLM cap enforcement | Config exists, not enforced | Redis counter in `/api/mood/classify` |
| Push notification delivery | Token stored, not delivered | FCM/APNS integration (Phase 3) |
| Admin session store | In-memory dict | Move to Redis (single-process only) |
| Signed OTA URLs from S3 | Working for S3; local fallback returns non-signed path | Wire up Cloudflare R2 |
| User delete / GDPR | No deletion endpoint | Add DELETE /api/users/me before EU launch |
| OWM API key | Falls back to mock | Set `OWM_API_KEY` in `.env` |

## Verified Working
- `GET /healthz` → `{"status":"ok","db":"ok","redis":"not_configured"}`
- `POST /api/auth/device` → device auto-registered, JWT returned with `server_time`
- `GET /api/weather?lat=X&lon=Y` → mock weather (with API key: live OWM data + Redis cache)
- `POST /api/mood/classify` → rule-based mood detection + Popish cue (with API key: Haiku)
- `POST /api/mood/log` → mood event persisted to DB
- `GET /api/ota/check?version=X` → `update_available: false` (no firmware uploaded yet)
- Admin login → session cookie → dashboard → device list → firmware page → roadmap
- 28 pytest tests, all passing
