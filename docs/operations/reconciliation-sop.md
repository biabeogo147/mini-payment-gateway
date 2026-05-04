# Reconciliation SOP

This SOP covers internal review of provider evidence that conflicts with the
gateway state. Request and response examples are in `docs/api/ops.md`.

## List Open Cases

Use:

```text
GET /v1/ops/reconciliation?match_result=PENDING_REVIEW
```

Useful filters:

- `match_result=PENDING_REVIEW`
- `match_result=MISMATCHED`
- `entity_type=PAYMENT`
- `entity_type=REFUND`
- `entity_id={payment_or_refund_uuid}`

## Inspect A Case

Use:

```text
GET /v1/ops/reconciliation/{record_id}
```

Review:

- `entity_type` and `entity_id`;
- `internal_status` vs `external_status`;
- `internal_amount` vs `external_amount`;
- `mismatch_reason_code` and `mismatch_reason_message`;
- callback evidence in `bank_callback_logs`.

## Resolve A Case

Use:

```text
POST /v1/ops/reconciliation/{record_id}/resolve
```

Body:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": "00000000-0000-0000-0000-000000000000",
    "reason": "Accepted provider late success after review"
  },
  "reviewed_by": "00000000-0000-0000-0000-000000000000",
  "review_note": "Accepted provider evidence"
}
```

Expected result: `match_result` becomes `RESOLVED`, `reviewed_by` and
`review_note` are stored, and `RECONCILIATION_RESOLVED` is written to
`audit_logs`.

## Resolution Guidance

- Late success after expiration uses `LATE_SUCCESS_AFTER_EXPIRATION`.
- Amount mismatch uses `AMOUNT_MISMATCH`.
- Final-state conflicts use `STATUS_CONFLICT`.
- Resolution in the MVP records the ops decision; it does not perform settlement,
  ledger correction, or merchant notification.
