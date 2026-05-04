# Webhook Scenarios

Webhook scenarios cover event creation, signed delivery, retry behavior, and
manual retry. Payment/refund finalization must not depend on successful webhook
delivery.

## WH-01 Payment Success Creates Webhook Event

Implementation Status: Implemented - phase 06.

Trigger: payment `PENDING -> SUCCESS`.

DB Effects:

- `webhook_events`: insert `payment.succeeded`.

Expected Assertions:

- Event creation is repeat-safe.
- Payment success does not depend on HTTP delivery success.
- Merchants without `webhook_url` do not receive a queued event.

## WH-02 Payment Failure Creates Webhook Event

Implementation Status: Implemented - phase 06.

Trigger: payment `PENDING -> FAILED`.

DB Effects:

- `webhook_events`: insert `payment.failed`.

## WH-03 Payment Expiration Creates Webhook Event

Implementation Status: Implemented - phase 06.

Trigger: payment `PENDING -> EXPIRED`.

DB Effects:

- `webhook_events`: insert `payment.expired`.

## WH-04 Refund Success Creates Webhook Event

Implementation Status: Implemented - phase 06.

Trigger: refund `REFUND_PENDING -> REFUNDED`.

DB Effects:

- `webhook_events`: insert `refund.succeeded`.

Companion behavior: refund `REFUND_PENDING -> REFUND_FAILED` creates
`refund.failed`.

## WH-05 HTTP 2xx Marks Webhook Delivered

Implementation Status: Implemented - phase 06.

Target:

```http
POST {merchant.webhook_url}
```

Payload:

```json
{
  "event_id": "evt_...",
  "event_type": "payment.succeeded",
  "merchant_id": "m_demo",
  "entity_type": "PAYMENT",
  "entity_id": "payment-row-uuid",
  "created_at": "2026-04-29T10:05:01Z",
  "data": {
    "transaction_id": "pay_...",
    "order_id": "ORDER-1001",
    "status": "SUCCESS",
    "amount": "100000.00"
  }
}
```

DB Effects:

- `webhook_delivery_attempts`: insert attempt with `SUCCESS`.
- `webhook_events`: update status to `DELIVERED`.

State Transition: webhook event `PENDING -> DELIVERED`.

## WH-06 HTTP 500 Schedules Retry

Implementation Status: Implemented - phase 06.

DB Effects:

- `webhook_delivery_attempts`: insert failed attempt.
- `webhook_events`: increment attempt count and set `next_retry_at`.

Expected Assertions:

- Event remains retryable until attempt limit is reached.
- Attempt 1 schedules `next_retry_at = now + 1 minute`.

## WH-07 Timeout Schedules Retry

Implementation Status: Implemented - phase 06.

DB Effects:

- `webhook_delivery_attempts`: insert timeout attempt.
- `webhook_events`: increment attempt count and set `next_retry_at`.

## WH-08 Network Error Schedules Retry

Implementation Status: Implemented - phase 06.

DB Effects:

- `webhook_delivery_attempts`: insert network-error attempt.
- `webhook_events`: increment attempt count and set `next_retry_at`.

## WH-09 Attempt 4 Exhaustion Marks Failed

Implementation Status: Implemented - phase 06.

Retry Schedule:

- Attempt 1 schedules retry after 1 minute.
- Attempt 2 schedules retry after 5 minutes.
- Attempt 3 schedules retry after 15 minutes.
- Attempt 4 has no next retry and marks the event `FAILED`.

DB Effects:

- `webhook_events`: update status to `FAILED`.
- `webhook_delivery_attempts`: keep the final failed attempt.

## WH-10 Ops Manual Retry Sends Failed Event Again

Implementation Status: Implemented - phase 06. Optional audit context
implemented - phase 07.

Actor: Ops.

API:

```http
POST /v1/ops/webhooks/{event_id}/retry
```

Optional Audit Request:

```json
{
  "actor_type": "OPS",
  "actor_id": null,
  "reason": "Retry after merchant endpoint recovered."
}
```

DB Effects:

- `webhook_delivery_attempts`: insert manual retry attempt.
- `webhook_events`: update delivery status.
- `audit_logs`: insert `WEBHOOK_MANUAL_RETRY` when optional audit context is
  supplied.

Expected Assertions:

- Manual retry is auditable when optional actor context is supplied.
- No-body manual retry remains backward-compatible with phase 06.
- Manual retry does not mutate payment/refund final state.
- Manual retry rejects missing events and events that are not `FAILED`.
