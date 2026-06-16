# Phase 12 Completion

Phase 12 adds the background worker that automatically expires overdue
payments and delivers due webhook retries.

## Completed Scope

- Added `python -m app.worker.main` as the worker entrypoint.
- Added worker config for enable flags, loop interval, batch limits, log level,
  and optional heartbeat path.
- Added PostgreSQL advisory locks for payment expiration and webhook delivery.
- Wired payment expiration and due webhook delivery into bounded worker cycles.
- Added local and sandbox `worker` services to Docker Compose.
- Updated sandbox deploy to build, start, and log the worker.
- Updated runbook, backend architecture, sandbox deployment, and DevOps docs.

## Verification

Local verification in this branch:

```bash
cd backend
python -m alembic upgrade head
python -m unittest discover tests -v
```

Result: 194 backend tests passed.

Frontend verification:

```bash
npm run typecheck --workspace @mini-payment-gateway/ops-dashboard
npm run typecheck --workspace @mini-payment-gateway/merchant-dashboard
```

Result: both typecheck commands completed successfully.

## Remaining Notes

- Sandbox deployment is wired but still needs to be run from `main` after merge.
- The worker intentionally stays simple: one process, direct service reuse,
  polling intervals, batch limits, and advisory locks rather than a queue
  platform.
