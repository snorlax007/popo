# Popo — Intent & Statement of Work
*AiNa Stage 2: Domain analysis, scope, impact, longevity, dependencies, variants*

---

## Domain Analyst

### Domain
Consumer IoT + AI emotional companion (hardware + cloud + mobile)

### Dynamics
- **Hardware-software bundle**: The product only works as a system — firmware, cloud API, and mobile app must ship together. Any delay in one layer gates all others.
- **Personality as the moat**: The Popish language and mood engine are the brand. A technically competent clone without Popo's voice actor recordings is still Popo. This is unusual for a software project.
- **Micro-run economics**: Initial production runs (500–1000 units) make per-unit cost high and defect tolerance low. Every firmware bug that ships in hardware is expensive to patch at scale vs. a web app hotfix.
- **Regulatory drag**: FCC Part 15 (WiFi + BLE) and CE marking are hard requirements before any retail sale. These are not optional; they are a 4–8 week lead time minimum and can gate the entire Phase 5 timeline.
- **Ambient UX contract**: The user's expectation is *reaction latency under 1.5 seconds* from voice input to Popo response. This is a tight SLA for a cloud round-trip (STT → LLM → TTS → I2S speaker).

### Constraints
- FCC/CE compliance required before retail sale — engage lab by end of Phase 4.
- App Store + Google Play approval adds 1–3 week unpredictable gate to Phase 3 launch.
- ESP32-S3 RAM ceiling (~512KB SRAM) caps what can run on-device; STT and LLM must be cloud-offloaded for V1.
- OpenWeatherMap free tier caps at 1,000 API calls/day — at 50 devices polling every 10 min, this hits in under 90 minutes. Caching is mandatory.

### What downstream personas should pay attention to
The cloud backend is the nervous system of a physical product with a reaction-time SLA. Every route the backend serves must be designed with embedded-device constraints in mind: binary payloads preferred over verbose JSON where possible, aggressive caching for weather/static assets, and graceful degradation when the cloud is unreachable (device should fall back to offline mode, not hang).

---

## Scope Architect

### Executive summary
Popo's cloud backend is the glue layer between a physical device, a mobile app, and external APIs (weather, LLM, OTA). V1 scope is the minimal viable cloud that enables Phase 2 (AI personality) and Phase 3 (mobile app) to function end-to-end with one admin able to manage the fleet.

### In scope (V1)
- Device registers with backend and receives a signed JWT for all subsequent API calls
- Backend proxies weather data from OpenWeatherMap, caches responses for 10 minutes, returns JSON to device on demand
- Backend receives raw user speech transcript from device, calls Claude Haiku for mood + intent classification, returns `{mood, intent, popish_cue}` within 800ms (p95 target excluding network)
- Device sends mood state events to backend; backend persists them to a `mood_logs` table
- User can create an account, link a device (via 6-digit pairing code), and view mood history in the mobile app via REST endpoints
- Admin dashboard (HTMX, web, password-protected) shows device fleet, mood logs per device, and allows pushing OTA firmware update
- OTA: admin uploads a firmware binary; backend generates a signed S3 URL and notifies device via MQTT; device downloads and flashes
- MQTT: backend connects to a Mosquitto broker and relays commands to registered device topics

### Out of scope (V1, deliberate)
- ESP32-S3 firmware code — this build produces the cloud backend only; firmware is Phase 1 hardware work
- React Native mobile app code — Phase 3 work; V1 ships REST endpoints that the app will consume
- Popish TTS synthesis — pre-recorded phoneme library is a Phase 2 audio/creative task; backend only classifies the `popish_cue` tag
- Push notification delivery (FCM/APNS) — backend stores `push_tokens` but delivery wiring is Phase 3 mobile work
- Multi-Popo sync — out of scope per PRD §4 "Could Have"
- Smart home control integration — out of scope per PRD §4 "Won't Have v1"
- Payment / subscription billing — pricing model not finalized (PRD §16 open question #3)

### Why these boundaries
The scope targets the minimum cloud surface needed to validate Phase 2 (AI personality) end-to-end on a breadboard prototype, without waiting for Phase 3 (mobile app) to be complete. The admin HTMX dashboard replaces the mobile app for device management during alpha. REST endpoints are designed contract-first so the mobile app team can build against them independently.

---

## Impact Quantifier

### Who benefits
- **Popo device users** · Responsive, personalized mood reactions · They notice when "Hey Popo" produces a reply in under 2 seconds with the right expression
- **Admin / Popo team** · Fleet visibility without SSH-ing into devices · They notice when they can push an OTA update to 20 beta units in one click
- **Mobile app team** · Clean REST contract to build against in Phase 3 · They notice when the API spec is stable and versioned before they write their first screen

### Magnitude estimate
- Weather caching alone: reduces OpenWeatherMap API calls by ~95% at 50 devices (1,000 → ~50 upstream calls/day) — prevents hitting the free tier ceiling.
- LLM gateway latency: Claude Haiku median response ~300ms; target p95 ≤800ms for the gateway route — within the 1.5s device reaction SLA with margin for STT + audio.
- OTA coverage: at 20 beta units (Phase 4), one admin push replaces 20 manual USB flashes — saves ~2–3h per firmware release.

### Evidence we have
- PRD §10 explicitly calls for FastAPI + LiteLLM proxy → Claude Haiku for LLM gateway.
- PRD §14 success metrics: wake word accuracy >95%, STT >90%, display GIF ≥15fps — all contingent on cloud round-trip staying under budget.
- PRD §11 Phase 4 specifies "Ship 20 units to beta users" — fleet management is a real need.

### Evidence we'd need
- Actual device polling frequency to size weather cache TTL precisely (PRD says "show current weather" but not how often the device polls).
- Whether mood logs need to be queryable by the user in the mobile app (PRD §9 "Mood History" screen exists, but retention period not specified).

### Measurement plan (post-launch)
1. LLM gateway p95 latency (target ≤800ms) — measured per-request in structured logs.
2. Weather cache hit rate (target ≥90%) — Redis/in-memory hit/miss counter.
3. OTA delivery success rate across fleet (target ≥95% of notified devices flash successfully within 24h).

---

## Longevity Critic

### 3-year outlook
Consumer IoT companion hardware is a niche but durable category — Tamagotchi has sold 90M+ units over 25 years. AI-enhanced companions (emotional reactions, voice interaction) are at an early inflection point in 2026. The bet is that Popish language creates a category-defining personality that commoditized hardware cannot replicate.

### Defensibility
- **Voice actor recordings + phoneme library** are the hardest asset to clone. A competitor needs to record and sequence ~200 custom clips; Popo's head start is 6–12 months.
- **Brand affection** (the "charming" rating in user testing) is the moat. Hardware specs can be matched; a character that people love is not easily copied.
- The cloud backend itself has low defensibility — FastAPI + PostgreSQL + MQTT is a commodity stack. The defensibility lives in the product, not the infrastructure.

### Market drift risks
- **On-device LLM (fast, 12 months)**: Qualcomm/Apple chips enabling local LLM at sub-$20 BOM. Could obsolete cloud-dependent mood analysis. Mitigation: design the LLM gateway as a swappable module.
- **Voice assistant consolidation (slow, 3+ years)**: Apple/Google adding ambient personality modes to HomePod/Nest Mini could commoditize the "personality speaker" category.
- **ESP32 supply constraints (medium, 12–18 months)**: Espressif has had allocation issues before. Mitigation: qualify an alternate MCU (STM32 + ESP-AT module pattern) before Phase 4.
- **LLM API pricing shifts (slow)**: Claude Haiku pricing could change. Mitigation: LiteLLM proxy makes swapping providers a config change.

### Kill criteria
- If Phase 0 user testing finds <60% of users rate Popish "charming" (vs. the 80% target), pause hardware and rework voice character.
- If LLM gateway p95 latency exceeds 1,500ms consistently in Phase 2 testing, the 1.5s reaction SLA is broken — must move to on-device or streaming response.
- If NPS from Phase 4 beta users is <20 (vs. PRD target >40), rescope before Phase 5 production run.

### Verdict
**Green.** Ship as scoped. The personality moat is real, the hardware is proven (ESP32-S3 ecosystem is mature), and the cloud backend is a well-understood problem. The key risk to manage proactively is the LLM latency SLA and the Phase 0 voice character validation — both are gated before irreversible hardware investment.

---

## Dependency Mapper

### Data dependencies
- **OpenWeatherMap API**: current conditions + forecast. Owner: Mesonet/OWM. Free tier capped at 1,000 calls/day; must cache. Fallback: Weatherapi.com or Open-Meteo (free, no key).
- **User speech transcript**: arrives from device after on-device VAD + cloud STT. Backend receives text, not audio — STT provider is a device/firmware dependency, not a backend one.
- **Firmware binaries**: admin uploads `.bin` files; backend stores in S3/equivalent. Binary integrity must be verified (SHA256 hash) before serving OTA URL.

### Partner / vendor dependencies
| Vendor | Purpose | Risk if unavailable | Cost band |
|---|---|---|---|
| Claude Haiku (Anthropic) | Mood + intent classification | Backend returns cached/default mood response | ~$0.25/M input tokens; at 50 devices, 100 requests/day = negligible |
| OpenWeatherMap | Weather data | Serve stale cache or switch to Open-Meteo | Free tier sufficient for Phase 2–3 |
| AWS S3 / Cloudflare R2 | Firmware OTA storage | OTA disabled until restored | ~$0.02/GB; tiny for firmware binaries |
| Mosquitto MQTT broker | Real-time device ↔ app messaging | MQTT commands queue or drop; device falls back to polling | Self-hosted: $0 |
| Hetzner VPS | Backend hosting | Service outage | €5–20/mo for CX21–CX31 |

### Regulatory / compliance
- **GDPR / privacy**: User accounts link a physical device to a person. Mood logs are behavioral data. If users are in the EU, GDPR applies — data retention policy, deletion endpoint, and DPA (Data Processing Agreement) needed before public launch. V1 (Phase 2 alpha) with internal users is lower risk.
- **FCC Part 15 / CE**: These are *device* certifications, not backend. Backend has no direct compliance obligation.
- **App Store / Play Store**: Backend must serve valid HTTPS with a real certificate (Let's Encrypt is fine); no HTTP for any API the app calls.

### Distribution dependencies
- React Native app distribution via Apple TestFlight + Google Play Internal Track (Phase 3). Backend API must be live before app beta starts.
- OTA firmware distribution: backend + S3 must be live before Phase 4 beta units ship.

### Critical path callouts
1. **MQTT broker setup** must precede any Phase 2 device testing — device can't receive commands without it. Self-hosted Mosquitto on the same VPS is the simplest path.
2. **Claude API key** must be provisioned and rate-limit tier confirmed before Phase 2 integration testing. Haiku is cheap but the account needs billing enabled.
3. **S3 bucket + IAM policy** for OTA must be configured before Phase 4 beta units ship — this is an infrastructure dependency with lead time.

---

## Variant Designer

### Variant 1: Lean (tier_lean)

**Budget band (USD):** $0–$200/mo infrastructure  
**Engineer-weeks:** 4–6  
**Ops complexity:** low  
**Recommended stack family:** fastapi + sqlite + mosquitto (self-hosted)  
**Target scale:** 1–20 devices, single operator

**Tradeoffs:**
- SQLite is zero-ops and adequate for 20 devices; no managed DB to provision
- No Redis; weather caching is in-process (functools.lru_cache with TTL)
- MQTT broker is Mosquitto on the same VPS; no HA
- No OTA infrastructure — firmware distributed manually over USB
- HTMX admin dashboard gives device visibility without a full SPA

**Kill criteria:**
- If device fleet exceeds 50 → migrate to PostgreSQL; SQLite WAL mode has contention issues at concurrent writes
- If weather polling frequency is >1 call/min per device → in-process cache is not enough; needs Redis

---

### Variant 2: Recommended (tier_recommended)

**Budget band (USD):** $20–$80/mo infrastructure  
**Engineer-weeks:** 8–10  
**Ops complexity:** medium  
**Recommended stack family:** fastapi + postgresql + redis + mosquitto + s3  
**Target scale:** 50–500 devices, 1 admin + 1 mobile app team consuming API

**Tradeoffs:**
- PostgreSQL handles concurrent device writes + relational mood log queries cleanly
- Redis for weather cache + session tokens — keeps DB load low
- S3 (or Cloudflare R2) for OTA firmware binaries — signed URL delivery, durable
- Mosquitto on VPS is sufficient for Phase 2–4 scale; AWS IoT Core is optional upgrade
- HTMX admin dashboard covers Phase 2 fleet management; Phase 3 mobile app consumes REST endpoints
- LiteLLM proxy in front of Claude Haiku makes swapping providers a config change

**Kill criteria:**
- If concurrent MQTT connections exceed 500 → move Mosquitto to AWS IoT Core
- If LLM gateway p95 > 1,500ms → switch to streaming response or on-device fallback

---

### Variant 3: Hardened (tier_hardened)

**Budget band (USD):** $200–$800/mo infrastructure  
**Engineer-weeks:** 16–20  
**Ops complexity:** high  
**Recommended stack family:** fastapi + postgresql (RDS) + redis (ElastiCache) + aws-iot-core + cloudfront  
**Target scale:** 500–10,000 devices, production retail

**Tradeoffs:**
- RDS Multi-AZ + read replicas for mood log queries at scale
- AWS IoT Core replaces Mosquitto — managed, HA, per-device policy enforcement
- CloudFront CDN for OTA firmware delivery — global edge for fast downloads
- Secrets Manager / Vault for API key rotation
- Full GDPR compliance stack (audit log, data deletion API, DPA)
- CI/CD with staging environment and blue/green deploys

**Kill criteria:**
- Overkill for Phases 2–4; only appropriate at Phase 5 production scale

---

### Recommended variant: tier_recommended

Matches Phase 2–4 scale, gives the mobile app team a clean REST contract, includes OTA infrastructure needed before Phase 4 beta, and stays within a €50/mo infrastructure budget. The lean variant is tempting but SQLite won't survive Phase 4's 20-device concurrent write pattern under load testing.

### Open questions / risks

1. **Weather polling frequency**: How often does the device poll for weather? This determines cache TTL. (PRD unspecified.)
2. **Mood log retention**: How long do mood logs persist? User-visible history requires a retention window and a deletion API (GDPR).
3. **Pricing model**: PRD §16 asks "$99 one-time vs. $79 + $5/mo subscription". A subscription model changes the backend — adds billing integration (Stripe), entitlement checks, and usage quotas.
4. **Offline mode**: PRD §16 asks if Popo needs offline AI. If yes, the LLM gateway becomes a fall-through, not a hard dependency — but mood model changes significantly.
5. **App required for setup?**: PRD §16 asks if Popo should work standalone. If yes, the device needs a captive portal WiFi setup flow, which adds backend complexity (device provisioning API).
