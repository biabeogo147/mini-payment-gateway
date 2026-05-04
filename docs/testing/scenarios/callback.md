# Provider Callback And Expiration Scenarios

Provider callback scenarios cover provider/simulator payment result updates,
raw callback evidence, and payment expiration.

## CB-01 Payment Success Callback

Implementation Status: Implemented with DB seed - phase 04. Webhook event
creation implemented in phase 06.

Actor: Provider simulator.

API:

```http
POST /v1/provider/callbacks/payment
```

Request:

```json
{
  "external_reference": "bank-ref-1001",
  "transaction_reference": "pay_...",
  "status": "SUCCESS",
  "amount": "100000.00",
  "paid_at": "2026-04-29T10:05:00Z",
  "raw_payload": {
    "provider": "SIMULATOR",
    "trace_id": "trace-1001"
  }
}
```

Response:

```json
{
  "transaction_id": "pay_...",
  "status": "SUCCESS",
  "processing_result": "PROCESSED"
}
```

DB Effects:

- `bank_callback_logs`: insert raw callback evidence.
- `payment_transactions`: update `PENDING -> SUCCESS`, set `paid_at`, and
  store external reference.
- `webhook_events`: create `payment.succeeded` when merchant has `webhook_url`.

Expected Assertions:

- Only `PENDING` payment can move to `SUCCESS`.
- Duplicate callback does not corrupt state.
- Callback amount must match payment amount, otherwise reconciliation is needed.

## CB-02 Payment Failed Callback

Implementation Status: Implemented with DB seed - phase 04. Webhook event
creation implemented in phase 06.

DB Effects:

- `bank_callback_logs`: insert raw callback evidence.
- `payment_transactions`: update `PENDING -> FAILED`, set failure code/message.
- `webhook_events`: create `payment.failed` when merchant has `webhook_url`.

Expected Assertions:

- Only `PENDING` payment can move to `FAILED`.
- Duplicate failed callback is safely logged or ignored.

## CB-03 Unknown Transaction Callback

Implementation Status: Implemented - phase 04.

DB Effects:

- `bank_callback_logs`: insert row with failed or pending-review processing
  result.
- No payment row is updated.

Expected Assertions:

- Unknown callback evidence is retained for investigation.
- The API should return a controlled response, not a server error.

## CB-04 Duplicate Provider Callback

Implementation Status: Implemented - phase 04.

DB Effects:

- `bank_callback_logs`: insert callback evidence for the duplicate call.
- `payment_transactions`: final state remains unchanged.

Expected Assertions:

- Replayed success after success is safe.
- Replayed failed after failed is safe.
- Conflicting final-state callback creates reconciliation evidence.

## EXP-01 Expire Overdue Payment

Implementation Status: Implemented at service level - phase 04. Webhook event
creation implemented in phase 06.

Actor: System.

API:

```http
scheduled service or internal command
```

DB Effects:

- `payment_transactions`: update `PENDING -> EXPIRED` when `expire_at <= now`.
- `webhook_events`: create `payment.expired` when merchant has `webhook_url`.

Expected Assertions:

- Non-overdue pending payments stay pending.
- Final-state payments do not change.
- Expiration is repeat-safe.

## Runnable Smoke

The provider callback smoke script starts the API, seeds an active merchant,
creates a payment, sends a provider success callback, and verifies both
`payment_transactions` and `bank_callback_logs` in PostgreSQL:

```bash
cd backend
python scripts/smoke_provider_callback_api.py
```
