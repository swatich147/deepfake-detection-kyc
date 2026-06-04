# Deepfake Detection for Video KYC

Run the **entire project through Docker**.


---

## What runs in Docker

| Container | Role |
|-----------|------|
| `dfkyc-frontend` | React app + nginx (port **80**) |
| `dfkyc-backend` | Django API + WebSocket (port **8000**) |
| `dfkyc-ai` | FastAPI inference (port **8080**) |

Data persists in Docker volumes: `backend_db` (SQLite), `backend_media` (video chunks).

---

### Prerequisites

1. **Docker Desktop** (or Docker Engine + Compose plugin)
   - [Mac](https://docs.docker.com/desktop/setup/install/mac-install/) / [Windows](https://docs.docker.com/desktop/setup/install/windows-install/) / [Linux](https://docs.docker.com/engine/install/)
2. **8 GB RAM** minimum
3. **Webcam + microphone** (browser will ask permission)
4. **Chrome or Edge** recommended (best WebRTC support)

### Step 1 — Clone the project

Use any of:

```bash
# git clone from your repo
git clone deepfake-detection-kyc
cd deepfake-detection-kyc


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
| `ALLOWED_HOSTS` | `*` | Keep `*` for LAN via laptop IP |

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

**http://localhost**

From **another phone/laptop on the same WiFi** (optional):

1. Find laptop IP:
   - Mac/Linux: `ip addr` or `ifconfig`
   - Windows: `ipconfig`
2. Open **http://YOUR_LAPTOP_IP** (e.g. `http://192.168.1.42`)

### Step 5 — Login

| Field | Value |
|-------|-------|
| Email | `demo@example.com` |
| Password | `demo12345` |

**flow:**

1. Dashboard → **+ New KYC Session**
2. Accept **privacy consent** checkbox
3. **Begin Recording** → follow on-screen prompts (~10+ seconds)
4. **Stop & Submit** → wait for analysis
5. View **Session Review** (verdict, lip-sync, rPPG, frames)

### Step 6 — Stop when done

```bash
docker compose down
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
