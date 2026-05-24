# Deepfake Detection for Video KYC — Docker Demo

Run the **entire project in Docker** on your demo laptop. No local Python, Node, Redis, PostgreSQL, or AWS required.

**Cost: $0** — everything runs in 3 containers on one machine.

---

## What runs in Docker

| Container | Role |
|-----------|------|
| `dfkyc-frontend` | React app + nginx (port **80**) |
| `dfkyc-backend` | Django API + WebSocket (port **8000**) |
| `dfkyc-ai` | FastAPI inference (port **8080**) |

Data persists in Docker volumes: `backend_db` (SQLite), `backend_media` (video chunks).

---

## Run on your second laptop (step-by-step)

### Prerequisites on the demo laptop

1. **Docker Desktop** (or Docker Engine + Compose plugin)
   - [Mac](https://docs.docker.com/desktop/setup/install/mac-install/) / [Windows](https://docs.docker.com/desktop/setup/install/windows-install/) / [Linux](https://docs.docker.com/engine/install/)
2. **8 GB RAM** minimum
3. **Webcam + microphone** (browser will ask permission)
4. **Chrome or Edge** recommended (best WebRTC support)

### Step 1 — Copy the project to the laptop

Use any of:

```bash
# USB / shared folder — copy the whole folder
# OR git clone from your repo
git clone <your-repo-url> deepfake-detection-kyc
cd deepfake-detection-kyc

# OR zip from your dev machine and unzip on the laptop
```

### Step 2 — Configure environment

```bash
cd deepfake-detection-kyc
cp .env.example .env
```

Edit `.env` if needed:

| Variable | Default | When to change |
|----------|---------|----------------|
| `MOCK_INFERENCE` | `true` | Set `false` for CPU analysis on real video |
| `SECRET_KEY` | demo key | Change if demo is on a shared network |
| `ALLOWED_HOSTS` | `*` | Keep `*` for LAN demo via laptop IP |

### Step 3 — Start everything

```bash
docker compose up --build -d
```

First build takes **5–15 minutes** (downloads images + installs deps).

Check status:

```bash
docker compose ps
docker compose logs -f
```

Wait until all three services are healthy:

```bash
curl http://localhost:8000/api/v1/health/
curl http://localhost:8080/health
```

### Step 4 — Open the app

On the **same laptop**:

**http://localhost**

From **another phone/laptop on the same WiFi** (optional):

1. Find demo laptop IP:
   - Mac/Linux: `ip addr` or `ifconfig`
   - Windows: `ipconfig`
2. Open **http://YOUR_LAPTOP_IP** (e.g. `http://192.168.1.42`)

### Step 5 — Login and demo

| Field | Value |
|-------|-------|
| Email | `demo@example.com` |
| Password | `demo12345` |

**Demo flow:**

1. Dashboard → **+ New KYC Session**
2. Accept **privacy consent** checkbox
3. **Begin Recording** → follow on-screen prompts (~10+ seconds)
4. **Stop & Submit** → wait for analysis
5. View **Session Review** (verdict, lip-sync, rPPG, frames)

### Step 6 — Stop when done

```bash
docker compose down
```

To wipe all data (fresh demo):

```bash
docker compose down -v
```

---

## Quick start script

```bash
chmod +x scripts/docker-start.sh
./scripts/docker-start.sh
```

---

## Useful Docker commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f ai_service

# Restart after .env change
docker compose up -d --build

# Django admin (optional)
docker compose exec backend python manage.py createsuperuser
# Then open http://localhost:8000/admin/

# Export session JSON (when logged in via API)
# GET /api/v1/sessions/{id}/export/
# GET /api/v1/sessions/export/
```

---

## Phase status (all demo-scoped)

### Phase 1 — MVP ✅ (skipped further work)

Auth, video capture, WebSocket upload, mock AI, dashboard, Docker.

### Phase 2 — AI pipeline ✅ (skipped further work)

Lip-sync heuristics, rPPG, ensemble scoring, CPU pipeline (`MOCK_INFERENCE=false`).

### Phase 3 — Hardening ✅ (Docker demo version)

| Feature | Implementation |
|---------|----------------|
| Rate limiting | DRF throttles on session create + export |
| Input validation | Session serializers |
| GDPR consent | Checkbox before recording |
| Admin panel | Django admin at `/admin/` |
| JSON export | `/api/v1/sessions/{id}/export/` |
| Webhooks | Optional POST if org webhook URL set |
| Health checks | `/api/v1/health/`, Docker healthchecks |

*Skipped (production-only): Terraform, JMeter load tests, AWS deploy.*

### Phase 4 — Enhancements ✅ (Docker demo version)

| Feature | Implementation |
|---------|----------------|
| Challenge-response | Random movement / blink / read-text |
| Anti-replay | Nonce + expiry on challenges |
| Model versioning | `ai_service/model_config.yaml` + `GET /models` |

*Skipped (production-only): TensorRT, continuous training, A/B testing.*

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 80 in use | Change frontend ports in `docker-compose.yml` to `"8081:80"` and open `http://localhost:8081` |
| Camera blocked | Use `localhost` or `https`; allow camera in browser site settings |
| WebSocket failed | Use app via port **80** (nginx proxies `/ws/`); don't open `:8000` directly for KYC |
| Build fails on frontend | Run `docker compose build --no-cache frontend` |
| Slow analysis | Keep `MOCK_INFERENCE=true` in `.env` for live demo |

---

## Architecture

```
Browser → nginx:80 (frontend)
            ├─ /api/*  → backend:8000
            └─ /ws/*   → backend:8000 (WebSocket)
Backend → ai_service:8080 (analysis)
Backend → SQLite + /app/media (chunks)
```

---

## License

Proprietary — project / academic demo use.
