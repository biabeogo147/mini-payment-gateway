# Payment Scenarios

Payment scenarios cover the currently runnable merchant payment APIs.

## Runnable Smoke

```bash
cd backend
python scripts/smoke_payment_api.py
```

The smoke script seeds an active merchant and credential, creates a payment,
queries it by transaction id, queries it by order id, and verifies PostgreSQL
state.

## PAY-01 Active Merchant Creates Payment

Implementation Status: Implemented with DB seed - phase 03.

Actor: Merchant backend.

API:

```http
POST /v1/payments
```

Headers:

```http
X-Merchant-Id: m_demo
X-Access-Key: ak_demo
X-Timestamp: 2026-04-29T10:00:00Z
X-Signature: <hmac_sha256>
X-Idempotency-Key: idem-1001
```

Request:

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

Response:

```json
{
  "transaction_id": "pay_...",
  "order_id": "ORDER-1001",
  "merchant_id": "m_demo",
  "qr_content": "MINI_GATEWAY|merchant_id=m_demo|transaction_id=pay_...|amount=100000.00|currency=VND",
  "qr_image_url": null,
  "qr_image_base64": null,
  "status": "PENDING",
  "expire_at": "2026-04-29T10:15:00Z"
}
```

DB Effects:

- `order_references`: insert row if this merchant order does not exist.
- `payment_transactions`: insert row with `status=PENDING`.
- `order_references`: set `latest_payment_transaction_id`.

State Transition: none to payment `PENDING`.

Expected Assertions:

- `INITIATED` is never persisted.
- One active pending payment exists for `merchant_db_id + order_id`.
- QR content includes merchant id, transaction id, amount, and currency.

## PAY-02 Merchant Queries Payment By Transaction Id

Implementation Status: Implemented with DB seed - phase 03.

API:

```http
GET /v1/payments/{transaction_id}
```

Response:

```json
{
  "transaction_id": "pay_...",
  "order_id": "ORDER-1001",
  "merchant_id": "m_demo",
  "qr_content": "MINI_GATEWAY|...",
  "qr_image_url": null,
  "qr_image_base64": null,
  "status": "PENDING",
  "expire_at": "2026-04-29T10:15:00Z"
}
```

DB Effects:

- `payment_transactions`: read.

Expected Assertions:

- Merchant can only read owned payments.
- Unknown or other-merchant transaction id returns `PAYMENT_NOT_FOUND`.

## PAY-03 Merchant Queries Payment By Order Id

Implementation Status: Implemented with DB seed - phase 03.

API:

```http
GET /v1/payments/by-order/{order_id}
```

DB Effects:

- `order_references`: read.
- `payment_transactions`: read latest payment attempt.

Expected Assertions:

- Query by order returns the latest payment attempt for that merchant order.
- Merchant cannot query another merchant's order.

## PAY-04 Duplicate Pending Payment With Identical Request

Implementation Status: Implemented - phase 03.

API:

```http
POST /v1/payments
```

DB Effects:

- No second `payment_transactions` row is inserted.

Expected Assertions:

- Response returns the existing `transaction_id`.
- Request must match amount, currency, description, and expiration.

## PAY-05 Duplicate Pending Payment With Different Amount, Description, Or Expiration

Implementation Status: Implemented - phase 03.

Expected Response:

```json
{
  "error_code": "PAYMENT_PENDING_EXISTS",
  "message": "A pending payment already exists for this order.",
  "details": {
    "order_id": "ORDER-1001",
    "transaction_id": "pay_..."
  }
}
```

DB Effects:

- No second `payment_transactions` row is inserted.

## PAY-06 Previous Failed Payment Allows New Attempt

Implementation Status: Implemented at service level - phase 03.

DB Effects:

- New `payment_transactions` row is inserted.
- `order_references.latest_payment_transaction_id` points to the new attempt.

## PAY-07 Previous Expired Payment Allows New Attempt

Implementation Status: Implemented at service level - phase 03.

DB Effects:

- New `payment_transactions` row is inserted.
- `order_references.latest_payment_transaction_id` points to the new attempt.

## PAY-08 Previous Successful Payment Rejects New Attempt

Implementation Status: Implemented at service level - phase 03.

Expected Response:

```json
{
  "error_code": "PAYMENT_ALREADY_SUCCESS",
  "message": "A successful payment already exists for this order.",
  "details": {
    "order_id": "ORDER-1001",
    "transaction_id": "pay_..."
  }
}
```

DB Effects:

- No new payment row is inserted.

## PAY-09 Query Another Merchant's Payment

Implementation Status: Implemented at service level - phase 03.

Expected Response:

```json
{
  "error_code": "PAYMENT_NOT_FOUND",
  "message": "Payment not found.",
  "details": {
    "transaction_id": "pay_..."
  }
}
```

## PAY-10 Non-Active Merchant Cannot Create Payment

Implementation Status: Implemented at service level - phase 02 and phase 03.

DB Effects:

- No `payment_transactions` row is inserted.

Expected Response:

```json
{
  "error_code": "MERCHANT_NOT_ACTIVE",
  "message": "Merchant is not active.",
  "details": {
    "merchant_status": "SUSPENDED"
  }
}
```
