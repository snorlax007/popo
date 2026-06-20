# Popo — Braindoc
*AiNa Stage 1: Framed problem, users, scope, risks*

---

## What It Is

Popo is a physical AI desk companion — a soft-corner cube (~80×80×90mm) with a 2.4" TFT main display and a 1.3" OLED mood face. It shows the time and weather by default, reacts emotionally to what you say, and communicates in "Popish" — an invented phonetic language of made-up syllables (think Minions × R2-D2). A companion mobile app (React Native, iOS + Android) extends the experience. The cloud backend ties it all together.

**North Star:** Make your desk feel like it has a soul.

---

## The Problem

Desks are inert. Clocks don't react. Smart speakers reply in flat, robotic English with no emotional warmth. Nothing on a desk *responds* to how the user feels. Popo fills that gap: an ambient companion with personality, presence, and its own invented language.

| Pain Point | Reality Today |
|---|---|
| Desks are dead | Clocks and smart displays have no personality |
| AI assistants are cold | Siri/Alexa are robotic and impersonal |
| No desk presence | Nothing on a desk *reacts* to your mood |
| Screen fatigue | Another glowing rectangle |

---

## Users

| Persona | Profile |
|---|---|
| **Remote Worker** | Works from home, wants ambient company without distraction |
| **Student** | Needs a fun study companion that tracks time and rewards focus |
| **Tech Gifter** | Buys quirky gadgets for kids, partners, or friends |
| **Creative** | Wants a character on the desk that reflects their mood |

Primary user: 25–45, tech-comfortable, remote-work or creative lifestyle. Not requiring AI fluency — delight is the hook.

---

## Scope (This Build)

The hardware prototype and firmware are for later phases. **This build is the Popo Cloud Backend** — the software layer that makes every Phase 2+ feature work:

**In scope:**
- REST API backend (FastAPI) for mobile app and device communication
- Device registration and JWT authentication
- LLM gateway: Claude Haiku for intent/mood analysis
- Weather data proxy with caching (OpenWeatherMap)
- MQTT broker integration for real-time device ↔ app messaging
- Mood log storage (PostgreSQL)
- OTA firmware distribution (signed S3 URLs)
- Admin dashboard (HTMX, server-rendered) for device fleet management
- User account system

**Out of scope (for this build):**
- ESP32-S3 firmware (Phase 1 hardware)
- React Native mobile app (Phase 3)
- Popish TTS engine (Phase 2 hardware)
- PCB design (Phase 4)
- Compliance/certification (Phase 5)

---

## Key Risks

| Risk | Likelihood | Impact | Note |
|---|---|---|---|
| Popish language feels annoying, not charming | Medium | High | Phase 0 user testing must gate Phase 1 |
| ESP32-S3 too slow for real-time audio + display | Medium | High | STT offloaded to cloud from day one |
| FCC/CE compliance delays | High | High | Engage lab early in Phase 4 |
| LLM API costs at scale | Low | Medium | Cache common intents; cap per-device usage |
| App Store rejection | Low | Low | Standard RN app, no edge-case APIs |

---

## What Success Looks Like

- Say "Hey Popo, how are you?" → device wakes, cloud processes intent, Popo replies in Popish with matching mood face + LED ring color.
- Admin can register a device, view its mood history, and push a firmware update — all from the web dashboard.
- Backend is live on a VPS, handling 50+ concurrent devices with p95 latency under 500ms for the LLM gateway.
- 8/10 beta users rate the Popish language "charming and intuitive" (Phase 0 exit criterion per PRD).
