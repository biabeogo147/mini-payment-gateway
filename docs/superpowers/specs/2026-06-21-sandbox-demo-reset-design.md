# Sandbox Demo Reset Script Design

## Goal

Provide one safe host-side command that returns the sandbox to first-admin
bootstrap state before an instructor demo.

## Command

```bash
cd /opt/mini-payment-gateway
bash deploy/reset_sandbox_demo.sh --confirm-reset
```

The script runs only when `.env` contains `APP_ENV=sandbox` and the explicit
confirmation flag is present.

## Reset Flow

1. Validate commands, checkout, `.env`, Compose interpolation, and PostgreSQL.
2. Stop `backend`, `worker`, and `demo-merchant` to prevent concurrent writes.
3. Create a timestamped compressed `pg_dump` under
   `$HOME/backups/mini-payment-gateway`.
4. Truncate every public table except `alembic_version` with
   `RESTART IDENTITY CASCADE`.
5. Start the stopped services and poll backend and Demo Merchant health.

Restart is protected by an exit trap. If backup or truncate fails after the
services stop, the script still attempts to restore the runtime before exiting
with the original failure.

## Result

All users, merchants, payments, callbacks, webhooks, and audit data are removed.
Database schema history is preserved. Restarting `demo-merchant` clears its
in-memory setup and orders. Ops Dashboard therefore returns to first-admin
bootstrap state.

## Testing

Python `unittest` launches the real Bash script with fake Docker and curl
executables. Tests cover confirmation/environment guards, successful backup and
truncate sequencing, migration-table preservation, and restart-on-failure.
