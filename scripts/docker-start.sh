#!/usr/bin/env bash
# Start the full stack with Docker Compose (demo laptop)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Building and starting containers (first run may take 5–10 minutes)..."
docker compose up --build -d

echo ""
echo "Waiting for backend..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo ""
echo "=============================================="
echo "  Deepfake KYC Demo is running"
echo "=============================================="
echo "  App (use this in browser):  http://localhost"
echo "  From another device on WiFi: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'YOUR_LAPTOP_IP')"
echo ""
echo "  Login:  demo@example.com / demo12345"
echo ""
echo "  Logs:   docker compose logs -f"
echo "  Stop:   docker compose down"
echo "=============================================="
