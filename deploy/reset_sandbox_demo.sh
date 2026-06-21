#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/mini-payment-gateway}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.sandbox.yml}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/mini-payment-gateway}"
HEALTH_ATTEMPTS="${HEALTH_ATTEMPTS:-30}"
HEALTH_SLEEP_SECONDS="${HEALTH_SLEEP_SECONDS:-2}"
SERVICES_STOPPED=false

log() {
  printf '[sandbox-reset] %s\n' "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '[sandbox-reset] Missing required command: %s\n' "$1" >&2
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

restart_services_on_exit() {
  local exit_code=$?
  if [[ "$SERVICES_STOPPED" == "true" ]]; then
    log "Reset failed; attempting to restore application services"
    docker compose -f "$COMPOSE_FILE" up -d backend worker demo-merchant || true
  fi
  return "$exit_code"
}

poll_url() {
  local label="$1"
  local url="$2"
  local attempt

  for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
    if curl -fsS "$url" >/dev/null; then
      log "$label health check passed on attempt $attempt"
      return
    fi
    sleep "$HEALTH_SLEEP_SECONDS"
  done

  printf '[sandbox-reset] %s health check failed: %s\n' "$label" "$url" >&2
  return 1
}

trap restart_services_on_exit EXIT

if [[ $# -ne 1 || "$1" != "--confirm-reset" ]]; then
  printf '[sandbox-reset] Pass --confirm-reset to acknowledge destructive sandbox data removal.\n' >&2
  exit 2
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  printf '[sandbox-reset] App directory is not a git checkout: %s\n' "$APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  printf '[sandbox-reset] Compose file not found: %s/%s\n' "$APP_DIR" "$COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -f ".env" ]]; then
  printf '[sandbox-reset] Expected server-only .env at %s/.env\n' "$APP_DIR" >&2
  exit 1
fi

APP_ENV_VALUE="$(env_value_or_default APP_ENV '')"
if [[ "$APP_ENV_VALUE" != "sandbox" ]]; then
  printf '[sandbox-reset] Reset requires APP_ENV=sandbox; found %s.\n' "${APP_ENV_VALUE:-unset}" >&2
  exit 1
fi

require_command docker
require_command curl
require_command gzip

log "Validating sandbox Compose configuration"
docker compose -f "$COMPOSE_FILE" config --quiet

if ! docker compose -f "$COMPOSE_FILE" ps --status running --services postgres \
  | grep -qx postgres; then
  printf '[sandbox-reset] PostgreSQL service must be running before reset.\n' >&2
  exit 1
fi

umask 077
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/pre-demo-reset-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"

log "Stopping services that can read or write demo state"
SERVICES_STOPPED=true
docker compose -f "$COMPOSE_FILE" stop backend worker demo-merchant

log "Backing up PostgreSQL to $BACKUP_FILE"
docker compose -f "$COMPOSE_FILE" exec -T postgres sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  | gzip > "$BACKUP_FILE"

if [[ ! -s "$BACKUP_FILE" ]]; then
  printf '[sandbox-reset] Database backup is empty: %s\n' "$BACKUP_FILE" >&2
  exit 1
fi

log "Truncating business tables while preserving alembic_version"
docker compose -f "$COMPOSE_FILE" exec -T postgres sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
DO $reset$
DECLARE
  table_list text;
BEGIN
  SELECT string_agg(format('%I.%I', schemaname, tablename), ', ')
  INTO table_list
  FROM pg_tables
  WHERE schemaname = 'public'
    AND tablename <> 'alembic_version';

  IF table_list IS NOT NULL THEN
    EXECUTE 'TRUNCATE TABLE ' || table_list || ' RESTART IDENTITY CASCADE';
  END IF;
END
$reset$;
SQL

log "Starting backend, worker, and demo merchant"
docker compose -f "$COMPOSE_FILE" up -d backend worker demo-merchant
SERVICES_STOPPED=false

BACKEND_BIND_ADDR_VALUE="$(env_value_or_default BACKEND_BIND_ADDR 127.0.0.1)"
BACKEND_PORT_VALUE="$(env_value_or_default BACKEND_PORT 8000)"
DEMO_MERCHANT_BIND_ADDR_VALUE="$(env_value_or_default DEMO_MERCHANT_BIND_ADDR 127.0.0.1)"
DEMO_MERCHANT_PORT_VALUE="$(env_value_or_default DEMO_MERCHANT_PORT 8100)"

BACKEND_URL="http://$(probe_host_for_bind_addr "$BACKEND_BIND_ADDR_VALUE"):${BACKEND_PORT_VALUE}/health"
DEMO_MERCHANT_URL="http://$(probe_host_for_bind_addr "$DEMO_MERCHANT_BIND_ADDR_VALUE"):${DEMO_MERCHANT_PORT_VALUE}/health"

poll_url "Backend" "$BACKEND_URL"
poll_url "Demo merchant" "$DEMO_MERCHANT_URL"

log "Sandbox demo reset complete. Ops Dashboard now requires first-admin bootstrap."
log "Backup retained at $BACKUP_FILE"
