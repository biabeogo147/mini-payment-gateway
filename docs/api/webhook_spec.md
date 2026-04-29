# Webhook Spec

Webhook delivery notifies merchant backends about final payment and refund
states. Payment and refund state changes do not depend on webhook delivery
success.

## Event Types

- `payment.succeeded`
- `payment.failed`
- `payment.expired`
- `refund.succeeded`
- `refund.failed`

## Payload Envelope

```json
{
  "event_id": "evt_...",
  "event_type": "payment.succeeded",
  "merchant_id": "m_demo",
  "entity_type": "PAYMENT",
  "entity_id": "uuid",
  "created_at": "2026-04-29T00:00:00Z",
  "data": {}
}
```

## Payment Data Example

```json
{
  "transaction_id": "pay_...",
  "order_id": "ORDER-1001",
  "amount": "100000.00",
  "currency": "VND",
  "status": "SUCCESS",
  "paid_at": "2026-04-29T10:00:00Z"
}
```

## Refund Data Example

```json
{
  "refund_transaction_id": "rfnd_...",
  "original_transaction_id": "pay_...",
  "refund_id": "REF-1001",
  "refund_amount": "100000.00",
  "status": "REFUNDED",
  "processed_at": "2026-04-29T10:05:00Z"
}
```

## Signing

Webhook payloads are signed with the active merchant credential secret. The
signature is sent in:

- `X-Webhook-Event-Id`
- `X-Webhook-Timestamp`
- `X-Webhook-Signature`

Canonical signing string:

```text
{timestamp}.{event_id}.{body_sha256_hex}
```

## Delivery Rules

- HTTP 2xx means success.
- Non-2xx, timeout, and network errors are failed attempts.
- Retry schedule after the first failed attempt:
  - 1 minute
  - 5 minutes
  - 15 minutes
- Total attempts: 4.
- Manual retry is internal-only.
- Every attempt is stored as `WebhookDeliveryAttempt`.
