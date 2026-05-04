# Ops API

Ops APIs are internal-only. They are used by Admin/Ops users and are not exposed
as merchant-facing endpoints in the MVP. A full internal identity layer can be
added later; this contract defines the business actions only.

Phase 07 keeps internal authentication out of scope. Mutating ops endpoints use
a lightweight actor context in the request body for audit rows:

```json
{
  "actor_type": "OPS",
  "actor_id": null,
  "reason": "Operator note"
}
```

## Merchant Management

### Create Merchant

`POST /v1/ops/merchants`

Creates a merchant with status `PENDING_REVIEW`.

Implementation status: planned - phase 07.

### Create Or Update Onboarding Case

`PUT /v1/ops/merchants/{merchant_id}/onboarding-case`

Stores onboarding payload, documents, review checklist data, settlement details,
webhook URL, allowed IP list, and domain/app name.

Implementation status: planned - phase 07.

### Approve Onboarding

`POST /v1/ops/merchants/{merchant_id}/onboarding-case/approve`

Stores decision metadata on `MerchantOnboardingCase`, not on `Merchant`.

Implementation status: planned - phase 07.

### Reject Onboarding

`POST /v1/ops/merchants/{merchant_id}/onboarding-case/reject`

Stores rejection note and moves the onboarding case to `REJECTED`.

Implementation status: planned - phase 07.

### Activate Merchant

`POST /v1/ops/merchants/{merchant_id}/activate`

Allowed only when onboarding is `APPROVED` and an active credential exists.

Implementation status: planned - phase 07.

### Suspend Or Disable Merchant

`POST /v1/ops/merchants/{merchant_id}/suspend`

`POST /v1/ops/merchants/{merchant_id}/disable`

Suspended and disabled merchants remain inspectable but cannot create new
payments or refunds.

Implementation status: planned - phase 07.

## Credentials

### Rotate Credential

`POST /v1/ops/merchants/{merchant_id}/credentials/rotate`

Creates a new active credential and marks the prior active credential as rotated
or inactive. The database must keep only one `ACTIVE` credential per merchant.

Implementation status: planned - phase 07.

## Inspection

`GET /v1/ops/payments`

Searchable by `transaction_id`, `order_id`, `merchant_id`, and status.

`GET /v1/ops/refunds`

Searchable by `refund_transaction_id`, `refund_id`, `merchant_id`, and status.

`GET /v1/ops/webhooks`

Searchable by `event_id`, `merchant_id`, status, and next retry time.

`GET /v1/ops/reconciliation`

Searchable by match result, entity type, and entity id.

Implementation status: planned - phase 07.

## Webhook Retry

`POST /v1/ops/webhooks/{event_id}/retry`

Implementation status: implemented in phase 06 without ops authentication.

Manual retry is internal-only and only accepts webhook events with
`status=FAILED`. It sends the stored event payload again, creates a new
`webhook_delivery_attempts` row, and updates the `webhook_events` delivery
status.

Response:

```json
{
  "event_id": "evt_...",
  "status": "DELIVERED",
  "attempt_count": 5,
  "last_attempt_result": "SUCCESS",
  "next_retry_at": null
}
```

Manual retry audit logging is intentionally deferred to phase 07.

## Audit

Ops actions write `AuditLog` entries for at least:

- `MERCHANT`
- `MERCHANT_CREDENTIAL`
- `ONBOARDING_CASE`
- `PAYMENT`
- `REFUND`
- `WEBHOOK_EVENT`
- `RECONCILIATION`
