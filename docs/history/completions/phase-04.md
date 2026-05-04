# Phase 04 Completion Summary

Completed on the current repository checkout.

## Completed Scope

- Added payment state machine helpers for:
  - `PENDING -> SUCCESS`;
  - `PENDING -> FAILED`;
  - `PENDING -> EXPIRED`;
  - invalid final-state transition rejection.
- Added provider payment callback schema and response contract.
- Added `POST /v1/provider/callbacks/payment`.
- Added callback evidence logging through `bank_callback_logs`.
- Added payment callback service behavior for:
  - success callback;
  - failed callback;
  - unknown transaction;
  - duplicate same-state callback;
  - amount mismatch;
  - late success after expiration.
- Added reconciliation evidence creation for amount mismatch and late callback
  cases.
- Added expiration service for overdue pending payments.
- Added provider callback smoke script:
  - `backend/scripts/smoke_provider_callback_api.py`.
- Updated provider callback API docs and phase 04 scenario coverage.

## Verification Evidence

### TDD Red Checks

The new state machine, callback service, expiration service, and route tests
first failed because the target modules did not exist.

### Unit Tests

Run from `backend/`:

```bash
python -m unittest discover tests -v
```

Latest result during implementation:

```text
Ran 62 tests
OK
```

### API And DB Smoke

Run from `backend/` with Docker Postgres healthy:

```bash
python scripts/smoke_provider_callback_api.py
```

This script seeds an active merchant, creates a payment, sends a provider
success callback, queries the payment, and verifies both `payment_transactions`
and `bank_callback_logs`.

Latest result:

```json
{
  "callback_processing_result": "PROCESSED",
  "callback_status": "SUCCESS",
  "db_callback_has_raw_payload": true,
  "db_callback_result": "PROCESSED",
  "db_payment_status": "SUCCESS",
  "merchant_id": "m_phase3_fe9c2726",
  "payment_query_status": "SUCCESS",
  "transaction_id": "pay_20126218753f473a845ce573ba073c29"
}
```

## Notes

- Phase 04 does not create webhook events. Phase 06 owns webhook event creation
  and delivery.
- Phase 04 creates reconciliation evidence only. Phase 07 owns ops review and
  resolution APIs.
- Refund callbacks remain phase 05 scope.
- No commit was created because no commit was requested.

## Next Phase

Proceed to `docs/history/phases/phase-05-refund-core.md`.
