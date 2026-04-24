#!/usr/bin/env bash
# Production deployment script for Xmail
# Usage: ./scripts/deploy.sh [--skip-build] [--skip-migrate]
set -euo pipefail

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
SKIP_BUILD=0
SKIP_MIGRATE=0

for arg in "$@"; do
  case $arg in
    --skip-build)   SKIP_BUILD=1 ;;
    --skip-migrate) SKIP_MIGRATE=1 ;;
  esac
done

# ── Preflight ────────────────────────────────────────────────────────────────
echo "▶ Checking required env vars..."
required_vars=(DOMAIN ACME_EMAIL DB_PASSWORD REDIS_PASSWORD SECRET_KEY
               GRAFANA_ADMIN_PASSWORD FLOWER_BASIC_AUTH ENCRYPTION_KEY)
missing=()
for var in "${required_vars[@]}"; do
  [[ -z "${!var:-}" ]] && missing+=("$var")
done
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "✗ Missing required env vars: ${missing[*]}"
  echo "  Copy .env.prod.example → .env.prod and fill in all values."
  exit 1
fi

# ── Build ────────────────────────────────────────────────────────────────────
if [[ $SKIP_BUILD -eq 0 ]]; then
  echo "▶ Building images..."
  $COMPOSE build --no-cache backend worker beat frontend
fi

# ── Traefik ACME volume — acme.json must exist with mode 600 ─────────────────
echo "▶ Ensuring ACME storage volume is initialised..."
docker volume inspect xmail_traefik_acme >/dev/null 2>&1 || \
  docker volume create xmail_traefik_acme
# Create acme.json inside the volume if not present
docker run --rm \
  -v xmail_traefik_acme:/acme \
  busybox sh -c "[ -f /acme/acme.json ] || (touch /acme/acme.json && chmod 600 /acme/acme.json)"

# ── Start infrastructure first ───────────────────────────────────────────────
echo "▶ Starting infrastructure services..."
$COMPOSE up -d postgres redis traefik

echo "▶ Waiting for Postgres to be healthy..."
timeout 60 bash -c "until docker inspect xmail-postgres | \
  python3 -c \"import sys,json; s=json.load(sys.stdin)[0]['State']['Health']['Status']; print(s); sys.exit(0 if s=='healthy' else 1)\" 2>/dev/null; \
  do sleep 2; done"

# ── Migrations ───────────────────────────────────────────────────────────────
if [[ $SKIP_MIGRATE -eq 0 ]]; then
  echo "▶ Running database migrations..."
  $COMPOSE run --rm --no-deps backend \
    alembic upgrade head
fi

# ── Deploy application ───────────────────────────────────────────────────────
echo "▶ Deploying application services..."
$COMPOSE up -d backend worker beat frontend flower prometheus grafana

# ── Health check ─────────────────────────────────────────────────────────────
echo "▶ Waiting for backend health..."
timeout 60 bash -c "until curl -sf http://localhost/api/health >/dev/null 2>&1; \
  do sleep 3; done" || {
  echo "✗ Backend health check timed out. Check logs:"
  echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml logs backend"
  exit 1
}

echo ""
echo "✓ Xmail deployed successfully!"
echo ""
echo "  Frontend:   https://${DOMAIN}"
echo "  API:        https://${DOMAIN}/api/docs"
echo "  Grafana:    https://grafana.${DOMAIN}"
echo "  Flower:     https://flower.${DOMAIN}"
echo "  Traefik:    https://traefik.${DOMAIN}"
