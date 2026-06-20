# FastAPI + HTMX golden starter

A professional, server-rendered app shell that AiNa seeds **backend-heavy**
generated apps from. No client build, no CDN — styling is the committed design
system (`static/css/app.css`), interactivity is vendored HTMX
(`static/js/htmx.min.js`). This is why it can't render "bland": the chrome and
styles ship with the repo and can't fail to compile.

## Layout
```
app/main.py              FastAPI app — routes, demo data, HTMX partial endpoints
templates/base.html      Sidebar + topbar + toast shell (every page extends it)
templates/pages/         dashboard · items · roadmap
templates/partials/      HTMX response fragments (item_row)
static/css/app.css       Self-contained design system (light + dark)
static/js/htmx.min.js    Vendored HTMX 2.0.4 (pinned, no CDN)
Dockerfile               Portable deploy unit (VPS / Fly)
```

## Run locally
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # http://localhost:8000
```

## Deploy
Built as a Docker image and run on the **Hetzner VPS** (nginx vhost +
`<slug>.ocdevide.com` + certbot TLS) or **Fly**. Never Vercel — it's Python.

## Extending (for the AiNa Dev cluster)
- Keep `base.html` and the design system — that's the professional baseline.
- Add nav entries in `NAV` (`app/main.py`) and a `templates/pages/<x>.html` per page.
- Replace the in-memory `_ITEMS` demo with real models/DB.
- Keep the `/roadmap` page current so users see the road ahead.
- Use the existing classes: `.card`, `.btn`, `.table`, `.badge`, `.field/.input`,
  `.stat`, `.grid`. Don't invent a parallel styling system.
