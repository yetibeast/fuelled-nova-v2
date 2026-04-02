# Railway Deployment — Operations Guide
**Last Updated:** April 2, 2026

---

## Overview

Nova v2 runs on Railway with three services: PostgreSQL database, FastAPI backend, and Next.js frontend. The scraper runner on Proxmox connects to the same database via the public PostgreSQL URL.

## Project

| Field | Value |
|-------|-------|
| **Project** | fuelled-nova |
| **Project ID** | `b9aa6076-cae3-47a7-bd47-e6b041ec1426` |
| **Dashboard** | https://railway.com/project/b9aa6076-cae3-47a7-bd47-e6b041ec1426 |
| **Workspace** | yeti-lynch projects |
| **Environment** | production |
| **Source Repo** | github.com/yetibeast/fuelled-nova-v2 (branch: main) |
| **Auto-deploy** | Yes — pushes to main trigger rebuild |

## Services

### PostgreSQL (Postgres-4SR7)

| Field | Value |
|-------|-------|
| **Service ID** | Check Railway dashboard |
| **Internal Host** | `postgres-4sr7.railway.internal` |
| **Public Host** | `trolley.proxy.rlwy.net:34278` |
| **Database** | `railway` |
| **User** | `postgres` |
| **Password** | `tFUtNBaGcBAzVFocfLriTjxwkxRTQKsZ` |
| **Public URL** | `postgresql://postgres:tFUtNBaGcBAzVFocfLriTjxwkxRTQKsZ@trolley.proxy.rlwy.net:34278/railway` |

**Data:**
- ~40K listings across 13 sources
- Users, gold tables (RCN, market, depreciation), canonical categories
- Scrape targets + run history
- Conversations, evidence, calibration data

### Backend (FastAPI)

| Field | Value |
|-------|-------|
| **Service ID** | `963a0b0c-1240-4f85-a398-7d142d6e80e0` |
| **Domain** | `backend-production-6a3f7.up.railway.app` |
| **Root Directory** | `backend` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port 8100` |
| **Port** | 8100 |
| **Health Check** | `https://backend-production-6a3f7.up.railway.app/api/health` |

**Environment Variables:**

| Variable | Value/Source |
|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://${{Postgres-4SR7.PGUSER}}:...` (Railway template) |
| `ANTHROPIC_API_KEY` | Anthropic SDK key |
| `JWT_SECRET` | 64-char hex secret |
| `CORS_ORIGINS` | `https://fuellednova.com,https://frontend-production-2ceb.up.railway.app` |
| `PRICING_V2_ENABLED` | `true` |
| `PORT` | `8100` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse cloud public key |
| `LANGFUSE_SECRET_KEY` | Langfuse cloud secret key |
| `LANGFUSE_BASE_URL` | `https://us.cloud.langfuse.com` |

### Frontend (Next.js)

| Field | Value |
|-------|-------|
| **Service ID** | `3bda9635-3090-4fac-9a1c-c607a71f578b` |
| **Domain** | `frontend-production-2ceb.up.railway.app` |
| **Root Directory** | `frontend/nova-app` |
| **Port** | 3000 (default Next.js) |

**Environment Variables:**

| Variable | Value/Source |
|----------|-------------|
| `BACKEND_URL` | `http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8100` |

## Deployment

### Auto-deploy

Push to `main` on GitHub triggers automatic rebuild of both backend and frontend.

```bash
git push origin main
```

### Manual Redeploy

Via CLI:
```bash
railway redeploy --service backend --yes
railway redeploy --service frontend --yes
```

Via API (if CLI auth issues):
```bash
TOKEN=$(python3 -c "import json; print(json.load(open('$HOME/.railway/config.json'))['user']['accessToken'])")
curl -s https://backboard.railway.app/graphql/v2 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"mutation { serviceInstanceRedeploy(serviceId: \"963a0b0c-1240-4f85-a398-7d142d6e80e0\", environmentId: \"010b6d17-97b1-4deb-b678-5b8af3c8cb3e\") }"}'
```

### Set Variables

```bash
railway variable set KEY=value --service backend
railway variable set KEY=value --service frontend
```

## Database Operations

### Connect via psql

```bash
/opt/homebrew/opt/postgresql@16/bin/psql "postgresql://postgres:tFUtNBaGcBAzVFocfLriTjxwkxRTQKsZ@trolley.proxy.rlwy.net:34278/railway"
```

### Dump and Restore

```bash
# Dump from Railway
pg_dump "postgresql://postgres:tFUtNBaGcBAzVFocfLriTjxwkxRTQKsZ@trolley.proxy.rlwy.net:34278/railway" > backup.sql

# Restore to Railway
psql "postgresql://postgres:tFUtNBaGcBAzVFocfLriTjxwkxRTQKsZ@trolley.proxy.rlwy.net:34278/railway" < backup.sql
```

### Seed Users

From the backend container terminal in Railway:
```bash
PYTHONPATH=. python3 seed_users.py
```

All users get password `fuelled2026`:
- `curtis@arcanosai.com` (admin)
- `harsh.kansara@fuelled.com` (analyst)
- `mark.ledain@fuelled.com` (admin)
- `raj.singh@fuelled.com` (analyst)

## Custom Domain

To point `fuellednova.com` to the Railway frontend:

1. In Railway dashboard → frontend service → Settings → Domains → Add Custom Domain
2. Enter `fuellednova.com`
3. Railway gives you a CNAME target
4. Update your DNS: `CNAME fuellednova.com → <railway-target>`
5. Do the same for `api.fuellednova.com` → backend service

Update `CORS_ORIGINS` on the backend after adding custom domains.

## Architecture

```
User Browser
    │
    ├── https://frontend-production-2ceb.up.railway.app (Next.js)
    │       │
    │       └── /api/* rewrites → http://backend.railway.internal:8100
    │
    └── (API calls from Next.js server-side)
            │
            └── backend.railway.internal:8100 (FastAPI)
                    │
                    ├── PostgreSQL (postgres-4sr7.railway.internal:5432)
                    ├── Anthropic API (Claude Sonnet)
                    └── Langfuse (us.cloud.langfuse.com)

Proxmox Scraper Runner (100.68.229.127:8200)
    │
    └── Railway PostgreSQL (trolley.proxy.rlwy.net:34278) — public URL
```

## Monitoring

- **Backend health:** `curl https://backend-production-6a3f7.up.railway.app/api/health`
- **Railway dashboard:** Deployment logs, metrics, usage
- **Langfuse:** Token usage, costs, traces at `us.cloud.langfuse.com`
- **Scraper runner:** `curl http://100.68.229.127:8200/health` (Tailscale)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Deploy failed | Check Railway dashboard → Deployments → build logs |
| Backend 500 | `railway logs --service backend --lines 100` |
| Frontend 404 | Check root directory is `frontend/nova-app`, verify build output |
| DB connection error | Check `DATABASE_URL` in env vars, verify Postgres service is running |
| CORS error | Update `CORS_ORIGINS` to include the requesting domain |
| Auth failing | Re-run `seed_users.py` via Railway terminal |
| Langfuse not tracking | Verify `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set |

## CLI Reference

```bash
railway status --json                    # Current context
railway service status --all --json      # All service statuses
railway logs --service backend --lines 50 # Backend logs
railway logs --service frontend --lines 50 # Frontend logs
railway variable list --service backend   # Backend env vars
railway variable set KEY=val --service backend  # Set variable
railway redeploy --service backend --yes  # Redeploy
```
