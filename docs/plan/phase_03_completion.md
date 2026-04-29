# Phase 03 Completion Summary

Completed on branch `codex-phase-0-2`.

## Completed Scope

- Added payment request/response schemas in `backend/app/schemas/payment.py`.
- Added deterministic MVP QR payload generation in
  `backend/app/services/qr_service.py`.
- Added order reference and payment repositories.
- Added payment service for:
  - create payment;
  - duplicate pending payment reuse;
  - duplicate pending mismatch rejection;
  - retry after `FAILED` or `EXPIRED`;
  - rejection after `SUCCESS`;
  - query by transaction id;
  - query by merchant order id.
- Added `backend/app/controllers/payment_controller.py` with:
  - `POST /v1/payments`;
  - `GET /v1/payments/{transaction_id}`;
  - `GET /v1/payments/by-order/{order_id}`.
- Registered the payment controller in `backend/app/main.py`.
- Added `backend/scripts/smoke_payment_api.py` for real HTTP + PostgreSQL
  smoke verification of the payment API.

## Verification Evidence

### TDD Red Checks

Schema and QR tests first failed because the modules did not exist:

```text
ModuleNotFoundError: No module named 'app.schemas.payment'
ModuleNotFoundError: No module named 'app.services.qr_service'
```

Payment service tests first failed because repositories and service did not
exist:

```text
ModuleNotFoundError: No module named 'app.repositories.order_reference_repository'
ModuleNotFoundError: No module named 'app.repositories.payment_repository'
ModuleNotFoundError: No module named 'app.services.payment_service'
```

Route tests first failed because the controller did not exist:

```text
ImportError: cannot import name 'payment_controller' from 'app.controllers'
```

### Unit Tests

Run from `backend/`:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

Result:

```text
Ran 42 tests
OK
```

### API And DB Smoke

Run from `backend/` with Docker Postgres healthy:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_payment_api.py
```

Result:

```json
{
  "created_transaction": "pay_d82be2e9c28844888b17b38e3509b074",
  "created_status": "PENDING",
  "by_transaction_status": "PENDING",
  "by_order_transaction": "pay_d82be2e9c28844888b17b38e3509b074",
  "db_status": "PENDING",
  "db_amount": "12345.00",
  "db_qr_has_transaction_id": true,
  "merchant_id": "m_phase3_c6e753dc"
}
```

## Implemented Business Rules

- Create payment requires an authenticated active merchant.
- Payment is persisted directly as `PENDING`; no `INITIATED` state is used.
- Current `PENDING` payment for the same merchant order is returned when the
  request is semantically identical.
- Current `PENDING` payment with different amount, description, currency, or
  expiration is rejected with `PAYMENT_PENDING_EXISTS`.
- Previous `FAILED` or `EXPIRED` payment allows a new attempt.
- Previous `SUCCESS` payment rejects a new attempt with `PAYMENT_ALREADY_SUCCESS`.
- Payment lookup by transaction id validates merchant ownership.

## Notes

- No provider callback, expiration worker, refund, or webhook event creation was
  added in this phase.
- No commit was created because no commit was requested.
- The smoke script intentionally leaves its unique test merchant/payment in the
  local database so the DB update can be inspected after the run.

## Superseded Next Phase

Phase 3.5 has now been completed. See
`docs/plan/phase_03_5_completion.md`.

That slice documented the grouped end-to-end scenario catalog in
`docs/scenarios/`, including APIs, requests, responses, DB effects, state
transitions, and owning phases for merchant onboarding, payment, callback,
refund, webhook, reconciliation, and ops workflows.
