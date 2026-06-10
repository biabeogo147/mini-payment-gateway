# Merchant Portal API

Merchant Portal APIs power the read-only Merchant Dashboard. They are separate
from merchant payment/refund APIs and do not use HMAC API credentials for
interactive dashboard login.

## Authentication

All routes use the `/v1/merchant-portal` prefix.

Session auth uses an HttpOnly merchant cookie. The backend resolves the merchant
scope from the session user, so clients must not send `merchant_id` to scope
portal data.

### POST `/auth/login`

Request:

```json
{
  "merchant_id": "m_...",
  "email": "merchant@example.com",
  "password": "temporary-or-user-password"
}
```

Response sets the merchant session cookie and returns:

```json
{
  "user": {
    "user_id": "uuid",
    "merchant_id": "m_...",
    "email": "merchant@example.com",
    "full_name": "Merchant Admin",
    "role": "MERCHANT_ADMIN",
    "status": "ACTIVE",
    "last_login_at": null,
    "created_at": "2026-06-09T00:00:00Z",
    "updated_at": "2026-06-09T00:00:00Z"
  }
}
```

Inactive users and invalid passwords return `401`.

### POST `/auth/logout`

Clears the merchant session cookie.

### GET `/auth/me`

Returns the current merchant portal user session or `401` when the session is
missing/invalid.

### POST `/auth/change-password`

Request:

```json
{
  "current_password": "old-password",
  "new_password": "new-password"
}
```

Returns the refreshed session user. Password changes invalidate older sessions.

## Dashboard

### GET `/dashboard/summary`

Returns merchant-scoped counters for the last 24 hours:

- `payments_last_24h`
- `successful_payment_amount_last_24h`
- `pending_payments`
- `refunds_last_24h`
- `open_webhook_events`

### GET `/dashboard/charts`

Returns merchant-scoped daily chart series for payment status, successful
payment amount, refund count, and webhook status.

## Analytics

### GET `/analytics?days=7|30|90`

Returns merchant-scoped analytics series for the interactive Merchant Dashboard
Analytics page. If `days` is omitted, the backend defaults to `30`.

Invalid ranges return `422`; the endpoint only accepts `7`, `30`, or `90`.
The backend resolves merchant scope from the session cookie and never accepts a
client-supplied `merchant_id`.

Response shape:

```json
{
  "range": {
    "days": 30,
    "start_date": "2026-05-12",
    "end_date": "2026-06-10"
  },
  "totals": {
    "payment_count": 0,
    "successful_payment_count": 0,
    "successful_payment_amount": "0",
    "success_rate": 0,
    "refund_count": 0,
    "refunded_amount": "0",
    "webhook_count": 0,
    "webhook_delivery_rate": 0
  },
  "series": {
    "payment_by_day": [
      {
        "date": "2026-06-10",
        "pending": 0,
        "success": 0,
        "failed": 0,
        "expired": 0,
        "total": 0,
        "successful_amount": "0",
        "success_rate": 0
      }
    ],
    "refund_by_day": [
      {
        "date": "2026-06-10",
        "pending": 0,
        "refunded": 0,
        "failed": 0,
        "count": 0,
        "amount": "0"
      }
    ],
    "webhook_by_day": [
      {
        "date": "2026-06-10",
        "pending": 0,
        "delivered": 0,
        "failed": 0,
        "total": 0,
        "delivery_rate": 0
      }
    ]
  },
  "attention": {
    "failed_or_expired_payments": 0,
    "refund_failures": 0,
    "open_webhooks": 0,
    "top_webhook_event_types": []
  }
}
```

Amount fields are decimal strings. Zero-activity days are still returned as
explicit zero buckets so charts and data tables can render stable ranges.
Attention data intentionally avoids internal reconciliation or audit workflow
state.

## Explorers

All explorer routes are scoped to the logged-in merchant.

- `GET /payments`
- `GET /payments/{transaction_id}`
- `GET /refunds`
- `GET /refunds/{refund_transaction_id}`
- `GET /webhooks`
- `GET /webhooks/{event_id}`

List routes support status/date/id filters and return only rows owned by the
session merchant. Detail routes return `404` when a record belongs to another
merchant, even if the id exists.

Payment and refund detail responses may include callback evidence and linked
records. They intentionally do not expose internal reconciliation workflow
state in the Merchant Dashboard MVP.

## Profile And Credentials

- `GET /profile` returns read-only merchant profile/config metadata.
- `GET /credentials` returns credential metadata only.

Credential responses include `access_key`, `secret_key_last4`, status, and
timestamps. Raw credential secrets are never returned.

## Ops Provisioning

Internal `ADMIN` users manage merchant portal users through Ops routes:

- `GET /v1/ops/merchants/{merchant_id}/portal-users`
- `POST /v1/ops/merchants/{merchant_id}/portal-users`
- `PATCH /v1/ops/merchants/{merchant_id}/portal-users/{user_id}`
- `POST /v1/ops/merchants/{merchant_id}/portal-users/{user_id}/reset-password`

Create/reset responses return the generated password once. Plaintext passwords
are never persisted or retrievable later.
