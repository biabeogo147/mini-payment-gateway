# Webhook Retry SOP

This SOP covers internal handling for failed merchant webhooks. The outbound
webhook contract is in `docs/api/webhook.md`; the manual retry API is in
`docs/api/ops.md`.

## Identify Failed Events

Inspect `webhook_events` for:

- `status = FAILED`;
- `attempt_count >= 4` for automatic retry exhaustion;
- `event_id`, `event_type`, `merchant_db_id`, and `last_attempt_at`.

Inspect `webhook_delivery_attempts` for response status, error message, request
headers, and payload snapshots.

## Confirm Retry Eligibility

Manual retry is allowed only for failed events. A pending event should be picked
up by due-event delivery when `next_retry_at` arrives. A delivered event should
not be retried.

## Retry Manually

Call:

```text
POST /v1/ops/webhooks/{event_id}/retry
```

Use the public webhook `event_id`, not the internal UUID. Include optional audit
context:

```json
{
  "actor_type": "OPS",
  "actor_id": "00000000-0000-0000-0000-000000000000",
  "reason": "Merchant endpoint recovered after incident"
}
```

Expected success: response status is `DELIVERED`, `attempt_count` increases, a
new delivery attempt is stored, and `WEBHOOK_MANUAL_RETRY` is audited when
actor context is supplied.

## If Retry Fails

- Check merchant `webhook_url`.
- Check the active merchant credential used for webhook signing.
- Check the latest delivery attempt response or error message.
- Retry only after the merchant endpoint has been fixed.
