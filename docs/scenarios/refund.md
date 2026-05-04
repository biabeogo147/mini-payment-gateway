# Refund Scenarios

Refund scenarios cover full refund creation, refund lookup, provider refund
callbacks, and rejection rules. Mini gateway scope does not include partial
refunds.

## REF-01 Full Refund Request For Successful Payment

Implementation Status: Implemented - phase 05.

Actor: Merchant backend.

API:

```http
POST /v1/refunds
```

Request:

```json
{
  "original_transaction_id": "pay_...",
  "refund_id": "REF-1001",
  "refund_amount": "100000.00",
  "reason": "Customer requested refund"
}
```

Response:

```json
{
  "refund_transaction_id": "rfnd_...",
  "original_transaction_id": "pay_...",
  "refund_id": "REF-1001",
  "refund_amount": "100000.00",
  "refund_status": "REFUND_PENDING"
}
```

DB Effects:

- `refund_transactions`: insert row with `status=REFUND_PENDING`.

State Transition: none to refund `REFUND_PENDING`.

Expected Assertions:

- Original payment must be `SUCCESS`.
- Refund amount must equal original payment amount.
- Refund must be within 7 days from `paid_at`.
- Refund is unique by `merchant_db_id + refund_id`.

## REF-02 Refund Query By Transaction Id

Implementation Status: Implemented - phase 05.

API:

```http
GET /v1/refunds/{refund_transaction_id}
```

DB Effects:

- `refund_transactions`: read.

Expected Assertions:

- Merchant can only read owned refunds.
- Unknown or other-merchant refund returns not found.

## REF-03 Refund Query By Merchant Refund Id

Implementation Status: Implemented - phase 05.

API:

```http
GET /v1/refunds/by-refund-id/{refund_id}
```

DB Effects:

- `refund_transactions`: read by `merchant_db_id + refund_id`.

Expected Assertions:

- Merchant can only read owned refunds.
- Query returns the merchant-visible refund id mapping.

## REF-04 Provider Refund Success Callback

Implementation Status: Implemented - phase 05.

Actor: Provider simulator.

API:

```http
POST /v1/provider/callbacks/refund
```

Request:

```json
{
  "external_reference": "bank-refund-1001",
  "refund_transaction_id": "rfnd_...",
  "status": "SUCCESS",
  "amount": "100000.00",
  "processed_at": "2026-04-29T10:10:00Z",
  "raw_payload": {
    "provider": "SIMULATOR",
    "trace_id": "refund-trace-1001"
  }
}
```

Response:

```json
{
  "refund_transaction_id": "rfnd_...",
  "refund_status": "REFUNDED",
  "processing_result": "PROCESSED"
}
```

DB Effects:

- `bank_callback_logs`: insert raw callback evidence.
- `refund_transactions`: update `REFUND_PENDING -> REFUNDED`.
- `webhook_events`: create `refund.succeeded` in phase 06.

Expected Assertions:

- Payment remains `SUCCESS` after refund succeeds.
- At most one `REFUNDED` refund exists per payment.

## REF-05 Provider Refund Failed Callback

Implementation Status: Implemented - phase 05.

DB Effects:

- `bank_callback_logs`: insert callback evidence.
- `refund_transactions`: update `REFUND_PENDING -> REFUND_FAILED`.
- `webhook_events`: create `refund.failed` in phase 06.

## REF-06 Partial Refund Rejects

Implementation Status: Implemented - phase 05.

DB Effects:

- No invalid `refund_transactions` row is inserted.

Expected Assertions:

- `refund_amount` must equal the original payment amount.

## REF-07 Refund After 7-Day Window Rejects

Implementation Status: Implemented - phase 05.

DB Effects:

- No invalid refund row is inserted.

Expected Assertions:

- Refund window is calculated from payment `paid_at`.

## REF-08 Duplicate Refund Id Returns Existing Refund

Implementation Status: Implemented - phase 05.

DB Effects:

- No duplicate refund row is inserted for the same `merchant_db_id + refund_id`.

Expected Assertions:

- Duplicate request with the same semantic content returns the existing refund.
- Conflicting duplicate refund request is rejected.

## REF-09 Refund Against Non-Success Payment Rejects

Implementation Status: Implemented - phase 05.

DB Effects:

- No invalid `refund_transactions` row is inserted.

Expected Assertions:

- `PENDING`, `FAILED`, and `EXPIRED` payments cannot be refunded.
