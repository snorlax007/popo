# Popo Cloud Backend — Ideation PRD
*AiNa Stage 3: Architecture, stack, data model, API, UX, NFRs, feature list*

---

## Domain Architect

### Architectural posture (tier_recommended)
Monolith-first, server-rendered for the admin dashboard, API-first for device + mobile. FastAPI serves both HTML (HTMX admin) and JSON (device REST + mobile REST) from the same process. Single VPS deployment — no microservices at Phase 2–4 scale.

### Data shape (high-level)
Mostly relational tabular records: users, devices, mood_logs, firmware_versions, push_tokens, weather_cache. One time-series-ish pattern (mood_logs by device + timestamp). No document store needed; PostgreSQL's JSONB is sufficient for flexible event payloads.

### Integration footprint
- **Outbound**: OpenWeatherMap REST (weather data), Anthropic API via LiteLLM (mood/intent), AWS S3/R2 (OTA binary storage)
- **Inbound**: MQTT over TCP (device → broker → backend subscriber), REST (device + mobile app)
- **Internal**: Redis for cache + session tokens, PostgreSQL for persistence

### Latency / scale ceiling
- Primary device action (LLM mood classify): target p95 ≤ 800ms at the backend (total device reaction SLA is 1,500ms including device-side STT + audio)
- Weather proxy: p95 ≤ 100ms (Redis cache hit); p95 ≤ 1,500ms (cache miss, upstream OWM call)
- V1 scale ceiling: 500 concurrent devices, 50 simultaneous API requests — a single Hetzner CX21 (2 vCPU / 4GB RAM) is sufficient

### Non-obvious constraint
The device has **no persistent clock** across power cycles (ESP32 NVS stores state but RTC is not battery-backed in the prototype). All API responses that need time context must include a `server_time` field so the device can synchronize. This is easy to miss when designing response shapes.

---

## Stack Selector

### Backend
- **Language + framework:** Python 3.12 + FastAPI 0.115
- **Persistence:** PostgreSQL 16 via SQLAlchemy 2.0 (async) + Alembic migrations
- **Cache:** Redis 7 (aioredis) for weather TTL cache and session tokens
- **Background work:** APScheduler for periodic weather pre-warming (optional); MQTT subscriber as a FastAPI lifespan task
- **Why:** PRD §10 explicitly names FastAPI. SQLAlchemy 2.0 async mode handles concurrent device writes cleanly. Redis is the natural fit for the 10-minute weather cache.

### Frontend
- **Approach:** HTMX + Jinja2 server-rendered templates (fastapi golden stack)
- **Styling:** Bundled professional design system (sidebar/topbar/cards/tables) from aina-skill golden starter — extended, not replaced
- **Key pages:** Dashboard (fleet overview), Device Detail (mood timeline + OTA), User Management, Firmware Upload

### Hosting / deployment
- **Where:** Hetzner CX21 VPS (€5/mo), Docker Compose (backend + PostgreSQL + Redis + Mosquitto)
- **Database hosting:** PostgreSQL in Docker Compose volume (Phase 2–3); migrate to managed DB for Phase 5
- **CI/CD shape:** GitHub Actions — lint + test on PR, Docker build + SSH deploy on main push
- **Cost band:** ~€20–30/mo total (VPS + S3/R2 storage for OTA binaries)

### Auth
- **Mechanism:** JWT (device auth) + session cookie (admin dashboard)
- **Device auth:** POST `/api/auth/device` with device serial → returns signed JWT; device includes `Authorization: Bearer <token>` on all subsequent calls
- **Admin auth:** Username + bcrypt password → sets `session` cookie (HTTPOnly, SameSite=strict); 24h session lifetime
- **Mobile user auth:** POST `/api/auth/user` → JWT; user links device via 6-digit pairing code
- **Provider:** No external provider; self-managed with `python-jose` + `passlib`

### Skipped on purpose
- **Async task queue (Celery/RQ)**: The only async workload is the MQTT subscriber, which runs as a FastAPI lifespan coroutine. No Celery overhead for V1.
- **GraphQL**: REST is simpler for embedded device clients and React Native; no query flexibility needed.
- **Next.js / React for admin**: HTMX is sufficient for a single-admin fleet dashboard with no offline requirements.

---

## Data Modeler

### Entities

**User**
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `email`: TEXT NOT NULL UNIQUE
- `hashed_password`: TEXT NOT NULL
- `name`: TEXT NULLABLE
- `created_at`: TIMESTAMP NOT NULL DEFAULT now()
- `is_admin`: BOOLEAN NOT NULL DEFAULT false

**Device**
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `serial`: TEXT NOT NULL UNIQUE · device hardware serial (burned into firmware)
- `name`: TEXT NOT NULL DEFAULT 'Popo' · user-assigned name
- `user_id`: INTEGER FK → User.id NULLABLE · NULL until paired
- `pairing_code`: TEXT NULLABLE · 6-digit code, expires after 10 min
- `pairing_expires_at`: TIMESTAMP NULLABLE
- `firmware_version`: TEXT NULLABLE · e.g. "0.3.1"
- `last_seen_at`: TIMESTAMP NULLABLE
- `timezone`: TEXT NOT NULL DEFAULT 'UTC'
- `weather_lat`: FLOAT NULLABLE
- `weather_lon`: FLOAT NULLABLE
- `registered_at`: TIMESTAMP NOT NULL DEFAULT now()

**MoodLog**
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `device_id`: INTEGER FK → Device.id NOT NULL
- `mood`: TEXT NOT NULL · enum: happy/sad/excited/confused/sleepy/scared/neutral
- `intent`: TEXT NULLABLE · raw intent label from LLM
- `user_transcript`: TEXT NULLABLE · what the user said (for Phase 2 analytics)
- `popish_cue`: TEXT NULLABLE · phoneme sequence hint returned to device
- `logged_at`: TIMESTAMP NOT NULL DEFAULT now()

**FirmwareVersion**
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `version`: TEXT NOT NULL UNIQUE · semver e.g. "0.4.0"
- `s3_key`: TEXT NOT NULL · path in bucket
- `sha256`: TEXT NOT NULL · hex digest for device verification
- `changelog`: TEXT NULLABLE
- `is_stable`: BOOLEAN NOT NULL DEFAULT false
- `uploaded_at`: TIMESTAMP NOT NULL DEFAULT now()

**PushToken**
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id`: INTEGER FK → User.id NOT NULL
- `platform`: TEXT NOT NULL · 'ios' | 'android'
- `token`: TEXT NOT NULL UNIQUE
- `created_at`: TIMESTAMP NOT NULL DEFAULT now()

**WeatherCache** (Redis, not PostgreSQL)
- Key: `weather:{lat}:{lon}` (rounded to 2 decimal places)
- Value: JSON blob from OWM response + `cached_at`
- TTL: 600 seconds (10 minutes)

### Relationships
A User has many Devices (after pairing). A Device has many MoodLogs. A Device belongs to one FirmwareVersion (current). A User has many PushTokens.

### Indices that matter for V1
- `mood_logs(device_id, logged_at DESC)` — mood history queries by device, time-ordered
- `devices(user_id)` — find all devices owned by a user
- `devices(serial)` — device auth lookup (already covered by UNIQUE constraint)
- `firmware_versions(is_stable, uploaded_at DESC)` — find latest stable release for OTA check

### Migration strategy
Alembic auto-generated migrations with timestamp prefixes; never edit applied migrations; `alembic upgrade head` runs on container startup.

### Open questions for the customer
- Does mood log need to store `user_transcript` permanently (privacy/GDPR risk) or only for the current session?
- Multi-user device sharing (one Popo, two family members)? If yes, `Device.user_id` needs to become a many-to-many relationship.
- Weather location: does the device send GPS coordinates, or does the user set a fixed location in the app?

---

## API Designer

### Route groups

```
## /api/auth
POST   /api/auth/device          → device registers/re-authenticates, gets JWT
POST   /api/auth/user            → user login, gets JWT
POST   /api/auth/user/register   → new user account
POST   /api/auth/pair            → user submits 6-digit code to claim device
POST   /api/auth/pair/generate   → device requests a pairing code

## /api/devices
GET    /api/devices              → list devices owned by authenticated user
GET    /api/devices/{id}         → fetch one device + current firmware status
PATCH  /api/devices/{id}         → update name / location / timezone
DELETE /api/devices/{id}         → unlink device from user

## /api/mood
POST   /api/mood/classify        → device sends transcript → returns {mood, popish_cue}
POST   /api/mood/log             → device reports mood state change (persists to DB)
GET    /api/mood/history/{device_id} → returns mood logs for a device (mobile app)

## /api/weather
GET    /api/weather              → device sends ?lat=&lon= → returns weather JSON + server_time

## /api/ota
GET    /api/ota/check            → device sends ?version= → returns {update_available, download_url, sha256}
POST   /api/admin/firmware       → admin uploads new firmware binary (multipart)

## /api/push
POST   /api/push/token           → mobile app registers FCM/APNS token
DELETE /api/push/token/{token}   → unregister

## /admin (HTMX, returns HTML)
GET    /admin/                   → dashboard: device fleet overview
GET    /admin/devices/{id}       → device detail: mood timeline + OTA panel
GET    /admin/firmware           → firmware management
POST   /admin/firmware/upload    → upload new firmware binary
POST   /admin/ota/push/{device_id} → notify device of pending OTA via MQTT
```

### Request / response shape (key endpoints)

```json
POST /api/auth/device
{ "serial": "POPO-A1B2C3D4", "firmware_version": "0.3.1" }
→ 200 { "access_token": "eyJ...", "token_type": "bearer", "server_time": "2026-06-20T10:42:00Z" }

POST /api/mood/classify
Authorization: Bearer <device_token>
{ "transcript": "I'm feeling really stressed today" }
→ 200 {
  "mood": "sad",
  "intent": "emotional_share",
  "popish_cue": "Poo-po… po-o.",
  "confidence": 0.87,
  "server_time": "2026-06-20T10:42:01Z"
}

GET /api/weather?lat=48.85&lon=2.35
Authorization: Bearer <device_token>
→ 200 {
  "condition": "cloudy",
  "temp_c": 14.2,
  "icon": "04d",
  "cached": true,
  "server_time": "2026-06-20T10:42:00Z"
}

GET /api/ota/check?version=0.3.1
Authorization: Bearer <device_token>
→ 200 {
  "update_available": true,
  "version": "0.4.0",
  "download_url": "https://r2.example.com/firmware/popo-0.4.0.bin?X-Amz-Signature=...",
  "sha256": "a3f2c1...",
  "changelog": "Fixes wake word false positives, improves OLED animation frame rate"
}
```

### Auth requirements per endpoint
All `/api/*` routes require `Authorization: Bearer <JWT>`. The JWT payload includes `sub` (device serial or user email) and `role` (`device` or `user`). Admin dashboard routes require session cookie. `/api/auth/*` routes are public (no auth required).

### Error shape
```json
{ "error": "device_not_registered", "detail": "No device with serial POPO-XXXXXXXX found.", "status": 404 }
```
HTTP status code is the primary error signal; `error` is a snake_case machine-readable code; `detail` is human-readable. No RFC 7807 envelope at V1 scale.

### Webhooks
None inbound or outbound in V1. MQTT handles real-time device push; no webhook consumer or producer needed.

---

## UI/UX Composer

### Pages

```
### /admin/ (Dashboard)
Purpose: Overview of the entire device fleet — health at a glance.
Primary action: Click into a device to see its detail.
Layout: Sidebar nav + top stats bar (total devices / online / offline /
  latest OTA version). Main area: table of devices with serial, name,
  user, firmware version, last seen, mood badge. Sortable, filterable.
Calls: GET /admin/devices (server-rendered)

### /admin/devices/{id} (Device Detail)
Purpose: Deep-dive on a single device — mood history + OTA management.
Primary action: Push OTA update to this device.
Layout: Top: device metadata card (serial, name, user, firmware, last seen).
  Below: two columns — left: mood timeline (chronological log, mood badges,
  last 24h); right: OTA panel (current version, available update, push button).
Calls: GET /admin/devices/{id}, POST /admin/ota/push/{device_id}

### /admin/firmware (Firmware Management)
Purpose: Upload new firmware binaries and see release history.
Primary action: Upload a .bin file and mark it stable.
Layout: Upload form (file input + version field + changelog textarea +
  "mark stable" checkbox). Below: table of all firmware versions with
  version, sha256, stable badge, uploaded date, device count on this version.
Calls: GET /admin/firmware, POST /admin/firmware/upload

### /admin/login (Admin Login)
Purpose: Authenticate admin user.
Primary action: Submit username + password.
Layout: Centered card, email + password fields, submit button.
Calls: POST /api/auth/user (adapted for session cookie flow)
```

### User flows (golden paths)

**Flow: Admin pushes OTA update**
1. Admin on `/admin/` → sees device "Popo-Desk-01" shows firmware 0.3.1, badge "Update available"
2. → clicks device row → `/admin/devices/42`
3. → OTA panel shows "0.4.0 available" + changelog
4. → clicks "Push Update" → POST `/admin/ota/push/42` → MQTT message sent to device
5. → toast: "OTA notification sent. Device will download and reboot."
6. → `last_seen_at` refreshes when device comes back online

**Flow: Device reports mood event**
1. Device POSTs to `/api/mood/log` with `{mood: "happy", device_id: ...}`
2. Backend persists MoodLog → no user action
3. On `/admin/devices/42`, mood timeline shows new "happy" entry with timestamp
4. (Phase 3) Mobile app calls `GET /api/mood/history/42` → renders mood chart

**Flow: New device pairing**
1. Device boots, POSTs `/api/auth/device` with serial → gets JWT
2. Device displays 6-digit code on TFT screen
3. User in mobile app enters code → POST `/api/auth/pair` → device linked to user
4. Device now appears in user's device list via `GET /api/devices`

### Component inventory
- `DeviceTable` — sortable table with mood badge + firmware version column
- `MoodBadge` — colored chip (happy=green, sad=blue, excited=yellow, etc.)
- `MoodTimeline` — chronological list of mood log entries with icon + time
- `OTAPanel` — current version + available version + push button
- `FirmwareTable` — release history with stable badge
- `StatsBar` — top-level fleet metrics (total / online / update-pending count)
- `ToastNotification` — HTMX out-of-band swap for success/error feedback

### Design tokens
- Typography: Inter (system-ui fallback). Headings 1.5rem, body 0.875rem.
- Spacing: 4px base unit, 8/16/24/32px rhythm.
- Accent: Popo purple `#7C3AED` for primary buttons + active states. Error: `#DC2626`. Success: `#16A34A`.
- Component library: aina-skill golden starter design system (sidebar/topbar/cards/tables). No external CDN dependency.

### Empty states + error states
- Device list empty: "No devices registered yet. Ship your first Popo unit and it will appear here when it boots."
- Mood timeline empty: "No mood events in the last 24 hours. Device may be offline."
- OTA push failure: "Failed to send OTA notification. Check that the device is connected to MQTT." (toast)
- Network error on admin page: inline banner "Could not load device data. Retry?" with refresh button.

---

## NFR Specialist

### Auth + access
Admin dashboard: single admin user (email + bcrypt password), session cookie, 24h lifetime. Device API: JWT, 30-day lifetime (devices don't logout). Mobile user API: JWT, 7-day lifetime + refresh token. No MFA in V1 — too early.

### Performance budget
- LLM mood classify (p95): ≤ 800ms (backend processing only)
- Weather proxy (cache hit p95): ≤ 100ms
- Admin dashboard page load: ≤ 500ms
- Concurrent devices V1: 500 (single VPS, async FastAPI handles easily)
- DB row volume: MoodLogs at 50 devices × 100 events/day × 365 days = 1.8M rows/year — trivial for PostgreSQL

### Security baseline
- All API input validated via Pydantic v2 models; no raw SQL.
- Secrets (DB URL, Anthropic key, Redis URL, S3 creds) via environment variables only; no `.env` committed to repo.
- HTTPS: Let's Encrypt via Caddy reverse proxy (handles cert renewal automatically).
- Device JWT signed with RS256; admin session uses `secrets.token_urlsafe(32)`.
- Specific risks: (1) Device serial guessing — auth token is signed, not serial-based, so guessing a serial doesn't grant access. (2) OTA binary tampering — SHA256 sent separately in OTA check response; device verifies before flashing.

### Privacy
- Mood logs include optional `user_transcript` (raw speech text). This is PII. Store only if user opts in. Default: classify and log only the mood label, not the transcript.
- User email is the only PII stored in PostgreSQL. No sensitive fields beyond that in V1.
- Mood data never leaves the VPS to any third party except: the raw transcript sent to Claude Haiku API (Anthropic). Anthropic's data handling policy applies.

### Observability
- Structured JSON logging (Python `logging` + `python-json-logger`) to stdout; collected by Docker logging driver.
- `GET /healthz` → `{"status": "ok", "db": "ok", "redis": "ok", "mqtt": "ok"}`.
- Error tracking: Sentry SDK (free tier) for unhandled exceptions in production. One env var to enable/disable.
- No metrics pipeline in V1; structured logs are queryable enough at this scale.

### Error handling philosophy
All API errors return a consistent `{"error": "code", "detail": "message", "status": N}` shape. Unhandled exceptions are caught by FastAPI's exception handler, logged with stack trace, and return `500 {"error": "internal_error"}` — no stack traces in API responses. HTMX errors show inline toast via out-of-band swap.

### i18n / accessibility
- i18n: English only, hardcoded. No i18n infrastructure in V1.
- a11y: Admin dashboard uses semantic HTML (`<table>`, `<nav>`, `<button>`), ARIA labels on icon-only buttons, keyboard navigable. WCAG AA color contrast on all text. Screen reader support for the MoodBadge component.

### Cost-ceiling guardrails
- **Claude Haiku**: At 50 devices × 100 mood classifications/day = 5,000 requests/day. Each request ~200 input tokens + ~50 output tokens. Daily cost: ~$0.04. Yearly: ~$15. No surprise billing risk. Add a per-device daily cap of 500 requests in V1 to prevent runaway loops.
- **OpenWeatherMap**: Free tier 1,000 calls/day. With 10-minute TTL cache and 50 devices all sharing a cache keyed by location, actual upstream calls ≈ 6/hour for 1 unique location. No risk of exceeding free tier.

---

## PRD Synthesizer

### Name
Popo Cloud Backend

### Elevator pitch
A FastAPI backend that connects Popo desk companions to weather data, LLM-powered mood analysis, and OTA firmware updates. Built for device + mobile app teams to develop against Phase 2 and Phase 3 in parallel.

### Chosen variant
`tier_recommended`

### Tech stack (one-line)
Python 3.12 + FastAPI 0.115 · HTMX + Jinja2 · PostgreSQL 16 + Redis 7 · Hetzner VPS / Docker Compose

### Features

- **Device Authentication** [P0]
  - what: Devices register by serial and receive a JWT for API access
  - acceptance: POST `/api/auth/device` with valid serial returns 200 + JWT; invalid serial returns 404; JWT is verifiable with RS256 public key
  - depends on: Device entity · `/api/auth/device` · none (no UI page)

- **Weather Proxy with Cache** [P0]
  - what: Backend fetches weather from OpenWeatherMap, caches 10 min in Redis, returns to device
  - acceptance: First request for a location hits OWM and caches result; second request within 10 min returns `cached: true` and does not hit OWM; response includes `server_time`
  - depends on: WeatherCache (Redis) · `/api/weather` · none

- **LLM Mood Classification** [P0]
  - what: Device sends user transcript; backend classifies mood + intent via Claude Haiku, returns mood label + popish_cue
  - acceptance: POST `/api/mood/classify` with transcript returns one of {happy/sad/excited/confused/sleepy/scared/neutral} + popish_cue string within 800ms p95; unknown/empty transcript returns `neutral`
  - depends on: MoodLog entity · `/api/mood/classify` · none

- **Mood Logging** [P0]
  - what: Device reports mood state changes; backend persists to mood_logs table
  - acceptance: POST `/api/mood/log` appends a MoodLog row; GET `/api/mood/history/{device_id}` returns logs ordered by `logged_at DESC`, paginated
  - depends on: MoodLog entity · `/api/mood/log`, `/api/mood/history/{device_id}` · MoodTimeline component

- **User Account + Device Pairing** [P0]
  - what: Users register, log in, and link their Popo device via 6-digit code
  - acceptance: Register → login → POST `/api/auth/pair` with 6-digit code → device's `user_id` is set; expired code returns 400; already-claimed device returns 409
  - depends on: User + Device entities · `/api/auth/*`, `/api/auth/pair` · none

- **Admin Dashboard** [P0]
  - what: HTMX admin web UI showing device fleet, mood timelines, and OTA management
  - acceptance: `/admin/` shows all devices with last-seen timestamp; `/admin/devices/{id}` shows mood timeline for last 24h; admin can log in and log out; unauthorized access to `/admin/*` redirects to `/admin/login`
  - depends on: User + Device + MoodLog entities · all `/admin/*` routes · DeviceTable, MoodTimeline, StatsBar

- **OTA Firmware Distribution** [P0]
  - what: Admin uploads firmware binary; backend stores in S3/R2, generates signed URL; device checks for updates and downloads
  - acceptance: Admin uploads .bin via `/admin/firmware/upload`; device GET `/api/ota/check?version=X` returns `update_available: true` when newer stable version exists, with signed URL and sha256; URL expires in 1h
  - depends on: FirmwareVersion entity · `/api/ota/check`, `/admin/firmware/upload` · OTAPanel, FirmwareTable

- **MQTT OTA Push** [P1]
  - what: Admin triggers OTA notification via MQTT; device receives message and begins OTA check
  - acceptance: POST `/admin/ota/push/{device_id}` publishes to `popo/{serial}/ota` topic; device (simulated by test script) receives message within 2s of publish
  - depends on: Mosquitto broker · `/admin/ota/push/{device_id}` · OTAPanel

- **Push Token Registration** [P1]
  - what: Mobile app registers FCM/APNS token; backend stores for future notification delivery
  - acceptance: POST `/api/push/token` stores token + platform; duplicate token upserts; DELETE removes it
  - depends on: PushToken entity · `/api/push/token` · none (no UI in V1)

- **Subscription billing** [P2]
  - what: $5/mo cloud AI subscription tier with usage quotas
  - depends on: pricing model decision (PRD open question #3)

### Data model summary
- **User** — account + admin flag
- **Device** — registered Popo unit, linked to user after pairing
- **MoodLog** — time-series mood events per device
- **FirmwareVersion** — OTA binary metadata + S3 key
- **PushToken** — mobile app notification tokens
- **WeatherCache** — Redis TTL cache, not a DB table

### API contract summary
`/api/auth` · `/api/devices` · `/api/mood` · `/api/weather` · `/api/ota` · `/api/push` · `/admin` (HTMX)

### NFR highlights
1. LLM classify p95 ≤ 800ms (backend-only); all API responses include `server_time` for device clock sync
2. Per-device LLM cap of 500 requests/day to prevent runaway cost
3. No `user_transcript` stored by default — only mood label persists unless user opts in
4. HTTPS enforced via Caddy; Let's Encrypt auto-renewal; no plain HTTP
5. Structured JSON logs to stdout; `/healthz` checks DB + Redis + MQTT connectivity

### Open questions
1. Device weather polling frequency — affects Redis TTL tuning
2. Mood log retention window — affects DB storage sizing and GDPR deletion scope
3. Subscription vs. one-time pricing — P2 feature, but affects backend architecture if chosen
4. Offline AI mode requirement — determines if LLM gateway is required or optional
5. App required for setup vs. standalone captive portal — affects device provisioning API design

### What's NOT in V1 (deliberate)
1. React Native mobile app — Phase 3 work; this build ships the REST API it consumes
2. Popish TTS audio synthesis — creative/audio work; backend only returns the `popish_cue` text tag
3. Smart home integration — out of scope per PRD §4
4. Subscription billing — pricing model not finalized
5. Multi-device sharing (one Popo, multiple users) — schema deferred; V1 is one device : one user
