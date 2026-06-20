#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/mini-payment-gateway}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.sandbox.yml}"
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

env_value_or_default() {
  local key="$1"
  local default_value="$2"
  local current_value=""

  current_value="$(
    awk -F= -v wanted_key="$key" '
      $0 !~ /^[[:space:]]*#/ && $1 == wanted_key {
        print substr($0, index($0, "=") + 1)
      }
    ' .env | tail -n 1
  )"

  if [[ -n "$current_value" ]]; then
    printf '%s\n' "$current_value"
    return
  fi

  printf '%s\n' "$default_value"
}

probe_host_for_bind_addr() {
  local bind_addr="$1"

  if [[ -z "$bind_addr" || "$bind_addr" == "0.0.0.0" ]]; then
    printf '127.0.0.1\n'
    return
  fi

  printf '%s\n' "$bind_addr"
}

print_failure_context() {
  log "Deployment failed. Recent compose state and logs:"
  docker compose -f "$COMPOSE_FILE" ps || true
  docker compose -f "$COMPOSE_FILE" logs --tail 100 backend worker ops-dashboard merchant-dashboard postgres || true
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

BACKEND_BIND_ADDR_VALUE="$(env_value_or_default BACKEND_BIND_ADDR 127.0.0.1)"
BACKEND_PORT_VALUE="$(env_value_or_default BACKEND_PORT 8000)"
OPS_DASHBOARD_BIND_ADDR_VALUE="$(env_value_or_default OPS_DASHBOARD_BIND_ADDR 127.0.0.1)"
OPS_DASHBOARD_PORT_VALUE="$(env_value_or_default OPS_DASHBOARD_PORT 4173)"
MERCHANT_DASHBOARD_BIND_ADDR_VALUE="$(env_value_or_default MERCHANT_DASHBOARD_BIND_ADDR 127.0.0.1)"
MERCHANT_DASHBOARD_PORT_VALUE="$(env_value_or_default MERCHANT_DASHBOARD_PORT 4174)"

HEALTH_URL="${HEALTH_URL:-http://$(probe_host_for_bind_addr "$BACKEND_BIND_ADDR_VALUE"):${BACKEND_PORT_VALUE}/health}"
OPS_DASHBOARD_URL="${OPS_DASHBOARD_URL:-http://$(probe_host_for_bind_addr "$OPS_DASHBOARD_BIND_ADDR_VALUE"):${OPS_DASHBOARD_PORT_VALUE}/}"
MERCHANT_DASHBOARD_URL="${MERCHANT_DASHBOARD_URL:-http://$(probe_host_for_bind_addr "$MERCHANT_DASHBOARD_BIND_ADDR_VALUE"):${MERCHANT_DASHBOARD_PORT_VALUE}/}"

log "Updating checkout to origin/main"
git fetch --prune origin main
git checkout main
git pull --ff-only origin main

log "Building backend, worker, and dashboard images"
docker compose -f "$COMPOSE_FILE" build backend worker ops-dashboard merchant-dashboard

log "Starting PostgreSQL"
docker compose -f "$COMPOSE_FILE" up -d postgres

log "Applying Alembic migrations"
docker compose -f "$COMPOSE_FILE" run --rm backend python -m alembic upgrade head

log "Starting backend, worker, and dashboards"
docker compose -f "$COMPOSE_FILE" up -d backend worker ops-dashboard merchant-dashboard

log "Polling backend health endpoint: $HEALTH_URL"
for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
  if curl -fsS "$HEALTH_URL" >/dev/null; then
    log "Health check passed on attempt $attempt"
    break
  fi
  sleep "$HEALTH_SLEEP_SECONDS"
done

if ! curl -fsS "$HEALTH_URL" >/dev/null; then
  log "Backend health check did not pass after $HEALTH_ATTEMPTS attempts"
  exit 1
fi

log "Polling ops dashboard root: $OPS_DASHBOARD_URL"
for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
  if curl -fsS "$OPS_DASHBOARD_URL" >/dev/null; then
    log "Ops dashboard check passed on attempt $attempt"
    break
  fi
  sleep "$HEALTH_SLEEP_SECONDS"
done

if ! curl -fsS "$OPS_DASHBOARD_URL" >/dev/null; then
  log "Ops dashboard check did not pass after $HEALTH_ATTEMPTS attempts"
  exit 1
fi

log "Polling merchant dashboard root: $MERCHANT_DASHBOARD_URL"
for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
  if curl -fsS "$MERCHANT_DASHBOARD_URL" >/dev/null; then
    log "Merchant dashboard check passed on attempt $attempt"
    git rev-parse --short HEAD
    exit 0
  fi
  sleep "$HEALTH_SLEEP_SECONDS"
done

log "Merchant dashboard check did not pass after $HEALTH_ATTEMPTS attempts"
exit 1
