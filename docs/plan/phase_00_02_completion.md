# Phase 00-02 Completion Summary

Completed on branch `codex-phase-0-2`.

## Completed Scope

### Phase 00: API Contract

- Created API contract docs in `docs/api/`.
- Documented merchant auth headers, merchant payment API, merchant refund API,
  provider callbacks, ops APIs, webhook payloads, retry behavior, and standard
  error shape.
- Updated `docs/6_necessary_document.md` to point at the new API docs.

### Phase 01: Backend Foundation

- Added the initial HTTP package and health router. Phase 2.5 later migrated
  these HTTP concerns into `backend/app/controllers/`.
- Added `get_db()` dependency.
- Added `AppError` and FastAPI error handler.
- Added timezone-aware `utc_now()`.
- Added package boundaries for `repositories`, `schemas`, and `services`.
- Added `httpx` dependency because FastAPI `TestClient` requires it.

### Phase 02: Merchant Auth And Readiness

- Added HMAC-SHA256 helpers.
- Added merchant and credential repository lookups.
- Added `AuthenticatedMerchant` context.
- Added merchant request authentication service.
- Added FastAPI `get_authenticated_merchant` dependency.
- Added merchant readiness guards for create payment and refund.

## Verification Evidence

### Unit Tests

Run from `backend/`:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

Result:

```text
Ran 25 tests in 0.070s
OK
```

### API Smoke

Uvicorn was started locally and `/health` was called.

Result:

```json
{
  "Health": "{\"status\":\"ok\"}",
  "Title": "Mini Payment Gateway",
  "Version": "0.1.0"
}
```

### Database Smoke

Postgres was started with Docker Compose, Alembic migrations were applied, and
`backend/scripts/smoke_verify_db.py` was run.

Result:

```text
Smoke verification passed.
```

Seeded verification counts:

```text
merchants: 1
merchant_credentials: 1
payment_transactions: 1
refund_transactions: 2
webhook_events: 1
audit_logs: 1
```

## Notes

- The DB smoke script cleanup order was fixed by clearing
  `order_references.latest_payment_transaction_id` before deleting
  `payment_transactions`.
- Phase 01 and phase 02 commit tasks remain unchecked in their phase files
  because no git commit was requested or created during implementation.

## Superseded Next Phase

Phase 2.5 has now been completed. See
`docs/plan/phase_02_5_completion.md`.

That slice reorganized the backend package shape:

- move HTTP routers, dependencies, and FastAPI error handling into
  `backend/app/controllers/`;
- rename merchant readiness into a consistently named service module;
- update tests and docs so phase 03 can add payment endpoints under the MVC
  structure.

Proceed to `docs/plan/phase_03_payment_core.md`.

Phase 03 should implement:

- payment schemas.
- deterministic MVP QR payload generation.
- order reference and payment repositories.
- payment service rules for duplicate orders and idempotency.
- merchant payment controller:
  - `POST /v1/payments`
  - `GET /v1/payments/{transaction_id}`
  - `GET /v1/payments/by-order/{order_id}`
