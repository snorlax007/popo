# Popo Cloud Backend — Ops Runbook
*AiNa Stage 9: Deployment, monitoring, incident response*

---

## Deployment

### Stack
- **Server:** Hetzner CX21 (2 vCPU / 4GB RAM, €5.29/mo) or CX31 for Phase 4+
- **Docker Compose:** backend + PostgreSQL 16 + Redis 7 + Mosquitto 2
- **Reverse proxy:** Caddy (automatic HTTPS / Let's Encrypt)
- **Registry:** GitHub Container Registry (GHCR)

### First Deploy (from scratch)
```bash
# 1. Provision server (Hetzner Cloud console or hcloud CLI)
hcloud server create --type cx21 --image ubuntu-24.04 --name popo-prod

# 2. SSH in and install Docker
ssh root@<ip>
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin caddy

# 3. Clone and configure
git clone https://github.com/your-org/popo-backend /opt/popo
cd /opt/popo
cp .env.example .env
# Edit .env: set SECRET_KEY, ANTHROPIC_API_KEY, OWM_API_KEY, S3 creds

# 4. Configure Caddy
cat > /etc/caddy/Caddyfile << 'EOF'
api.popo.io {
  reverse_proxy localhost:8000
}
EOF
systemctl reload caddy

# 5. Start stack
docker compose up -d
docker compose logs -f backend
```

### Rolling Update (CI/CD path)
```bash
# GitHub Actions builds Docker image on push to main and SSHes in:
docker compose pull backend
docker compose up -d --no-deps backend
docker compose exec backend python3 -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

---

## Health Checks

**Primary health endpoint:**
```bash
curl https://api.popo.io/healthz
# Expected: {"status":"ok","db":"ok","redis":"ok"}
```

**What each check means:**
- `db: ok` → PostgreSQL is reachable and accepting queries
- `redis: ok` → Redis is reachable and responding to PING
- `redis: not_configured` → Redis URL not set (SQLite dev mode)
- `mqtt: ok` → Mosquitto broker connected (logged at startup, not in /healthz yet)

**Caddy health proxy:**
```bash
systemctl status caddy
caddy validate --config /etc/caddy/Caddyfile
```

---

## Monitoring

### Structured logs
All logs are JSON to stdout, collected by Docker logging driver.

```bash
# Live backend logs
docker compose logs -f backend

# Filter for errors only
docker compose logs backend | python3 -c "import sys,json; [print(l) for l in sys.stdin if 'ERROR' in l]"
```

### Key log patterns to watch
| Pattern | Meaning | Action |
|---|---|---|
| `LLM classify failed` | Anthropic API error → fell back to rule-based | Check API key + billing |
| `OWM request failed` | Weather API unreachable → returned mock | Check OWM quota |
| `MQTT publish failed` | Broker unreachable → OTA push dropped | Restart mqtt container |
| `Could not seed admin user` | DB write failed at startup | Check DB connection |

### Sentry (optional)
Set `SENTRY_DSN=https://...@sentry.io/...` in `.env` to enable error tracking.

### Uptime monitoring
Use UptimeRobot (free) to ping `/healthz` every 5 minutes. Alert on non-200 for >2 checks.

---

## Incident Response

### P0 — Backend Down (devices can't auth or classify mood)
1. `docker compose ps` — check which container is down
2. `docker compose logs backend --tail=100` — find the crash cause
3. Restart: `docker compose restart backend`
4. If DB crash: `docker compose restart db && docker compose restart backend`
5. If still down: roll back to last known good image: `docker compose pull --rollback backend`

### P1 — LLM gateway returning errors
1. Check Anthropic status page (status.anthropic.com)
2. Verify `ANTHROPIC_API_KEY` is set and valid: `docker compose exec backend env | grep ANTHROPIC`
3. Backend auto-falls back to rule-based mood classifier — devices still function, just at lower accuracy
4. No user action required; log the incident

### P2 — Weather data stale / incorrect
1. Check OWM quota: free tier is 1,000 calls/day
2. `docker compose exec redis redis-cli KEYS "weather:*"` — check cache entries
3. Clear cache: `docker compose exec redis redis-cli FLUSHDB`
4. If OWM is down: switch to Open-Meteo (free, no key): update `services/weather.py` OWM_URL

### P3 — MQTT broker down (OTA push fails)
1. `docker compose restart mqtt`
2. Devices can still poll `/api/ota/check` directly — OTA still works, just not push-notified

---

## Backup

### PostgreSQL
```bash
# Daily backup (add to cron on server)
docker compose exec db pg_dump -U popo popo | gzip > /backups/popo-$(date +%Y%m%d).sql.gz

# Restore
gunzip -c /backups/popo-20260620.sql.gz | docker compose exec -T db psql -U popo popo
```

### Redis
Redis is used for ephemeral cache only — no backup needed. Sessions (in-process dict) are also ephemeral. On restart, users/devices re-login.

---

## Secrets Management

All secrets are in `.env` on the server. Do not commit `.env` to git.

| Secret | Where | Rotation |
|---|---|---|
| `SECRET_KEY` | `.env` | Rotate annually or after breach; all JWTs invalidated |
| `ANTHROPIC_API_KEY` | `.env` | Rotate on team departure |
| `OWM_API_KEY` | `.env` | Rotate on team departure |
| `AWS_ACCESS_KEY_ID` / `SECRET` | `.env` | Rotate quarterly |
| `ADMIN_PASSWORD` | `.env` | Change on first login |

---

## Cost Summary (Phase 2–4)

| Service | Monthly cost |
|---|---|
| Hetzner CX21 | €5.29 |
| Cloudflare R2 (OTA storage, ~100MB) | ~$0.02 |
| Anthropic Claude Haiku (50 devices × 100 req/day) | ~$1.25 |
| OpenWeatherMap | Free tier |
| UptimeRobot | Free |
| **Total** | **~€7/mo** |

Phase 5 (500+ devices): upgrade to CX31 (€15/mo), enable Sentry, consider managed DB (~€20/mo).
