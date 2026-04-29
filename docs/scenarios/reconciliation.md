# Reconciliation Scenarios

Reconciliation scenarios cover ambiguous or mismatched provider evidence and ops
resolution. Callback phases may create evidence first; phase 07 adds review and
resolution APIs.

## REC-01 Late Success Callback After Expiration

Implementation Status: Planned - phase 04 and phase 07.

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
- `reconciliation_records`: insert `PENDING_REVIEW` evidence.

Expected Assertions:

- Expired payment does not revive automatically.
- Ops can resolve the reconciliation later.

## REC-02 Callback Amount Mismatch

Implementation Status: Planned - phase 04 and phase 07.

DB Effects:

- `bank_callback_logs`: insert callback evidence.
- `reconciliation_records`: insert `MISMATCHED` or `PENDING_REVIEW`.
- `payment_transactions`: no final success update until reviewed.

Expected Assertions:

- Provider amount must match internal payment amount.
- Mismatch is visible to ops.

## REC-03 Matching Provider Evidence

Implementation Status: Planned - phase 07.

DB Effects:

- `reconciliation_records`: insert `MATCHED` or mark existing record matched.

Expected Assertions:

- Matching status and amount can be recorded without manual resolution.

## REC-04 Mismatch Evidence

Implementation Status: Planned - phase 07.

Mismatch Types:

- Status mismatch.
- Amount mismatch.
- Late success after expiration.

DB Effects:

- `reconciliation_records`: insert `MISMATCHED` or `PENDING_REVIEW`.

## REC-05 Resolve Reconciliation Record

Implementation Status: Planned - phase 07.

Actor: Ops.

API:

```http
POST /v1/ops/reconciliation/{record_id}/resolve
```

Request:

```json
{
  "resolved_by": "ops_admin",
  "resolution_note": "Provider evidence reviewed and accepted."
}
```

DB Effects:

- `reconciliation_records`: update `RESOLVED`.
- `audit_logs`: insert resolution event.

Expected Assertions:

- Resolution includes actor, note, and timestamp.
- Record remains traceable after resolution.
