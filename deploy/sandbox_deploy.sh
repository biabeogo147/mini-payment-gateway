#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/mini-payment-gateway}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.sandbox.yml}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"
HEALTH_ATTEMPTS="${HEALTH_ATTEMPTS:-30}"
HEALTH_SLEEP_SECONDS="${HEALTH_SLEEP_SECONDS:-2}"

log() {
  printf '[sandbox-deploy] %s\n' "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "Missing required command: $1"
    exit 1
  fi
}

print_failure_context() {
  log "Deployment failed. Recent compose state and logs:"
  docker compose -f "$COMPOSE_FILE" ps || true
  docker compose -f "$COMPOSE_FILE" logs --tail 100 backend postgres || true
}

trap 'print_failure_context' ERR

require_command git
require_command docker
require_command curl

if [[ ! -d "$APP_DIR/.git" ]]; then
  log "App directory is not a git checkout: $APP_DIR"
  exit 1
fi

cd "$APP_DIR"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  log "Compose file not found: $APP_DIR/$COMPOSE_FILE"
  exit 1
fi

if [[ ! -f ".env" ]]; then
  log "Expected server-only .env at $APP_DIR/.env"
  exit 1
fi

log "Updating checkout to origin/main"
git fetch --prune origin main
git checkout main
git pull --ff-only origin main

log "Building backend image"
docker compose -f "$COMPOSE_FILE" build backend

log "Starting PostgreSQL"
docker compose -f "$COMPOSE_FILE" up -d postgres

log "Applying Alembic migrations"
docker compose -f "$COMPOSE_FILE" run --rm backend python -m alembic upgrade head

log "Starting backend"
docker compose -f "$COMPOSE_FILE" up -d backend

log "Polling health endpoint: $HEALTH_URL"
for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
  if curl -fsS "$HEALTH_URL" >/dev/null; then
    log "Health check passed on attempt $attempt"
    git rev-parse --short HEAD
    exit 0
  fi
  sleep "$HEALTH_SLEEP_SECONDS"
done

log "Health check did not pass after $HEALTH_ATTEMPTS attempts"
exit 1
