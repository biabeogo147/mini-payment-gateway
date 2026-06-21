# Merchant API

Merchant APIs are consumed by merchant backends and require HMAC authentication.

## Authentication Headers

Every merchant request must include:

- `X-Merchant-Id`: public merchant id.
- `X-Access-Key`: active credential access key.
- `X-Signature`: HMAC-SHA256 signature.
- `X-Timestamp`: request timestamp; valid for 5 minutes.
- `X-Idempotency-Key`: optional technical idempotency key.

Canonical signing string:

```text
{timestamp}.{method}.{path}.{body_sha256_hex}
```

Signature:

```text
hex(hmac_sha256(secret_key, signing_string))
```

## Verify Credential

`GET /v1/merchant/auth/verify`

This side-effect-free endpoint verifies the same merchant HMAC used by payment
requests. A successful response confirms that the merchant id, active access
key, secret, timestamp, and signature are valid:

```json
{
  "authenticated": true,
  "merchant_id": "m_demo"
}
```

Demo Merchant calls this endpoint before retaining a submitted credential, so
an invalid credential is rejected during setup instead of during payment
creation.

## Create Payment

`POST /v1/payments`

### Request

```json
{
  "order_id": "ORDER-1001",
  "amount": "100000.00",
  "description": "Demo QR payment",
  "ttl_seconds": 900,
  "metadata": {
    "customer_ref": "CUST-1"
  }
}
```

`expire_at` may be sent instead of `ttl_seconds`.

### Response

```json
{
  "transaction_id": "pay_...",
  "order_id": "ORDER-1001",
  "merchant_id": "m_demo",
  "qr_reference": "PABC123456789",
  "qr_content": "000201...",
  "qr_image_url": null,
  "qr_image_base64": "data:image/png;base64,...",
  "status": "PENDING",
  "expire_at": "2026-04-29T10:00:00Z"
}
```

### Rules

- Merchant must be `ACTIVE`.
- Merchant must have one active Ops-managed VietQR receiving account.
- Pilot payments accept only `currency=VND` and whole-VND amounts.
- `qr_reference` is a gateway transfer reference, maximum 13 ASCII characters,
  and is used as the VietQR transfer purpose.
- `qr_content` is the merchant-presented VietQR/EMV payload. `qr_image_base64`
  is a PNG data URL suitable for direct rendering in merchant apps.
- A usable transaction is persisted directly as `PENDING`; `INITIATED` is never
  stored.
- One active payment means one `PENDING` payment per `merchant_id + order_id`.
- Duplicate create-payment for the current `PENDING` order returns the existing
  transaction when the request is semantically identical.
- Duplicate create-payment for the current `PENDING` order with different amount,
  description, or expiration is rejected with `PAYMENT_PENDING_EXISTS`.
- A new payment for the same order is allowed after a prior payment is `FAILED`
  or `EXPIRED`.
- A new payment for the same order is rejected after a prior payment is `SUCCESS`
  with `PAYMENT_ALREADY_SUCCESS`.

## Get Payment Status

`GET /v1/payments/{transaction_id}`

Returns the payment owned by the authenticated merchant.

## Get Payment By Order

`GET /v1/payments/by-order/{order_id}`

Returns the latest payment attempt for the merchant order.

## Create Refund

`POST /v1/refunds`

### Request

```json
{
  "original_transaction_id": "pay_...",
  "refund_id": "REF-1001",
  "refund_amount": "100000.00",
  "reason": "Customer requested refund"
}
```

`order_id` may be used instead of `original_transaction_id` when resolving the
original successful payment by merchant order.

### Response

```json
{
  "refund_transaction_id": "rfnd_...",
  "original_transaction_id": "pay_...",
  "refund_id": "REF-1001",
  "refund_amount": "100000.00",
  "refund_status": "REFUND_PENDING"
}
```

### Rules

- Merchant must be `ACTIVE`.
- Original payment must be `SUCCESS`.
- Full refund only; `refund_amount` must equal the original payment amount.
- Refund window is 7 days from `paid_at`.
- Duplicate `merchant_id + refund_id` returns the existing refund.
- Existing `REFUND_PENDING` or `REFUNDED` refund blocks a new refund id for the
  same payment.
- A prior `REFUND_FAILED` refund does not block a new refund id.

## Get Refund Status

`GET /v1/refunds/{refund_transaction_id}`

Returns the refund owned by the authenticated merchant.

## Get Refund By Merchant Refund Id

`GET /v1/refunds/by-refund-id/{refund_id}`

Returns the refund for the authenticated merchant and merchant-provided
`refund_id`.
