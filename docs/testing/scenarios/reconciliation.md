# Reconciliation Scenarios

Reconciliation scenarios cover ambiguous or mismatched provider evidence and ops
resolution. Callback phases create evidence for real provider callbacks; phase
07 adds reusable evidence helpers and ops review APIs.

## REC-01 Late Success Callback After Expiration

Implementation Status: Evidence creation implemented - phase 04. Ops review and
resolution implemented - phase 07.

Actors:

- Provider simulator.
- Ops.

APIs:

```http
POST /v1/provider/callbacks/payment
GET /v1/ops/reconciliation
POST /v1/ops/reconciliation/{record_id}/resolve
```

DB Effects:

- `bank_callback_logs`: insert late callback evidence.
- `payment_transactions`: remains `EXPIRED`.
- `reconciliation_records`: insert `PENDING_REVIEW` evidence with
  `mismatch_reason_code=LATE_SUCCESS_AFTER_EXPIRATION`.
- `audit_logs`: insert `RECONCILIATION_RESOLVED` when ops resolves.

Expected Assertions:

- Expired payment does not revive automatically.
- Ops can inspect and resolve the reconciliation later.

## REC-02 Callback Amount Mismatch

Implementation Status: Evidence creation implemented - phases 04/05. Ops review
and resolution implemented - phase 07.

DB Effects:

- `bank_callback_logs`: insert callback evidence.
- `reconciliation_records`: insert `MISMATCHED` or `PENDING_REVIEW`.
- `payment_transactions` or `refund_transactions`: no final success update
  until reviewed when callback evidence conflicts.

Expected Assertions:

- Provider amount must match internal payment/refund amount.
- Mismatch is visible to ops through `GET /v1/ops/reconciliation`.

## REC-02R Refund Callback Amount Mismatch

Implementation Status: Evidence creation implemented - phase 05. Ops review and
resolution implemented - phase 07.

DB Effects:

- `bank_callback_logs`: insert refund callback evidence.
- `reconciliation_records`: insert `MISMATCHED` evidence with
  `entity_type=REFUND`.
- `refund_transactions`: remains in its current state.

Expected Assertions:

- Provider amount must match internal refund amount.
- Mismatch is visible to ops.

## REC-03 Matching Provider Evidence

Implementation Status: Implemented - phase 07.

Service:

- `reconciliation_service.create_payment_evidence(...)`
- `reconciliation_service.create_refund_evidence(...)`

DB Effects:

- `reconciliation_records`: insert `MATCHED` when internal status and amount
  align with external evidence.

Expected Assertions:

- Matching payment status and amount can be recorded without manual resolution.
- Matching refund evidence maps external `SUCCESS` to internal `REFUNDED` and
  external `FAILED` to internal `REFUND_FAILED`.

## REC-04 Mismatch Evidence

Implementation Status: Implemented - phase 07.

Mismatch Types:

- Payment/refund amount mismatch -> `MISMATCHED`, `AMOUNT_MISMATCH`.
- Payment status mismatch -> `MISMATCHED`, `STATUS_MISMATCH`.
- Late success after expired payment -> `PENDING_REVIEW`,
  `LATE_SUCCESS_AFTER_EXPIRATION`.
- Refund status conflict -> `PENDING_REVIEW`, `STATUS_CONFLICT`.

DB Effects:

- `reconciliation_records`: insert `MISMATCHED` or `PENDING_REVIEW`.

## REC-05 Resolve Reconciliation Record

Implementation Status: Implemented - phase 07.

Actor: Ops.

API:

```http
POST /v1/ops/reconciliation/{record_id}/resolve
```

Request:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Provider evidence reviewed."
  },
  "reviewed_by": null,
  "review_note": "Provider evidence reviewed and accepted."
}
```

DB Effects:

- `reconciliation_records`: update `match_result=RESOLVED`.
- `reconciliation_records`: set `reviewed_by` and `review_note`.
- `reconciliation_records.updated_at`: acts as the resolution timestamp.
- `audit_logs`: insert `RECONCILIATION_RESOLVED`.

Expected Assertions:

- Resolution includes actor, note, and timestamp.
- Already resolved records return `RECONCILIATION_ALREADY_RESOLVED`.
- Missing records return `RECONCILIATION_NOT_FOUND`.
- Record remains traceable after resolution.
