# Ops API

Ops APIs are internal-only. They are used by `ADMIN` and `OPS` users and are
not exposed as merchant-facing endpoints.

Phase 10 adds internal authentication, session cookies, RBAC, and read/search
APIs for the Ops dashboard.

## Internal Auth And RBAC

Internal users authenticate through `/v1/internal/auth/*`.

Available auth routes:

- `GET /v1/internal/auth/bootstrap-status`
- `POST /v1/internal/auth/bootstrap`
- `POST /v1/internal/auth/login`
- `POST /v1/internal/auth/logout`
- `GET /v1/internal/auth/me`
- `POST /v1/internal/auth/change-password`

Internal user administration is `ADMIN`-only:

- `GET /v1/internal/users`
- `POST /v1/internal/users`
- `PATCH /v1/internal/users/{user_id}`
- `POST /v1/internal/users/{user_id}/reset-password`

Role model:

- `ADMIN`: full access, including internal user management, merchant disable,
  and credential rotation.
- `OPS`: standard operating access for onboarding, payment/refund/webhook
  support, reconciliation resolution, and merchant lifecycle actions short of
  the admin-only actions above.

Ops write routes still require an `actor` object in the request body because
the user-supplied `reason` remains part of the audit trail. `actor_type` and
`actor_id` are normalized from the authenticated internal session on the
server, not trusted from the request body.

Merchant and reconciliation ops bodies therefore still use a nested actor
object:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Operator note"
  }
}
```

`actor_type` is one of `SYSTEM`, `ADMIN`, or `OPS`. `actor_id` is optional in
the request body and is ignored by the phase 10 controller layer for
authenticated Ops/Admin actions.

## Dashboard Read APIs

Phase 10 adds read/search/stat routes that back the Ops dashboard.

Dashboard summary and charts:

- `GET /v1/ops/dashboard/summary`
- `GET /v1/ops/dashboard/charts`

Merchant read APIs:

- `GET /v1/ops/merchants`
- `GET /v1/ops/merchants/{merchant_id}`
- `GET /v1/ops/merchants/{merchant_id}/onboarding-case`
- `GET /v1/ops/merchants/{merchant_id}/credentials`

Payment read APIs:

- `GET /v1/ops/payments`
- `GET /v1/ops/payments/{transaction_id}`

Refund read APIs:

- `GET /v1/ops/refunds`
- `GET /v1/ops/refunds/{refund_transaction_id}`

Webhook read APIs:

- `GET /v1/ops/webhooks`
- `GET /v1/ops/webhooks/{event_id}`
- `GET /v1/ops/webhooks/{event_id}/attempts`

Audit and reconciliation:

- `GET /v1/ops/audit-logs`
- `GET /v1/ops/reconciliation`
- `GET /v1/ops/reconciliation/{record_id}`

## Merchant Management

### Create Merchant

`POST /v1/ops/merchants`

Creates a merchant with status `PENDING_REVIEW` and writes
`MERCHANT_CREATED`.

Request:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Register merchant."
  },
  "merchant_id": "m_demo",
  "merchant_name": "Demo Merchant",
  "legal_name": "Demo Merchant LLC",
  "contact_name": "Demo Ops",
  "contact_email": "ops@example.com",
  "contact_phone": "+84000000000",
  "webhook_url": "https://merchant.example.com/webhooks/payment-gateway",
  "settlement_account_name": "Demo Merchant LLC",
  "settlement_account_number": "123456789",
  "settlement_bank_code": "DEMO"
}
```

Response:

```json
{
  "merchant_id": "m_demo",
  "merchant_name": "Demo Merchant",
  "status": "PENDING_REVIEW"
}
```

Errors:

- `MERCHANT_ALREADY_EXISTS` with HTTP 409.

### Create Or Update Onboarding Case

`PUT /v1/ops/merchants/{merchant_id}/onboarding-case`

Creates or updates the merchant's single MVP onboarding case, sets it to
`PENDING_REVIEW`, and writes `ONBOARDING_CASE_SUBMITTED`.

Request:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Submit onboarding case."
  },
  "domain_or_app_name": "Demo Shop",
  "submitted_profile_json": {
    "business_type": "online_shop"
  },
  "documents_json": {
    "business_license": "demo-license.pdf"
  },
  "review_checks_json": {
    "risk_level": "LOW"
  }
}
```

Response:

```json
{
  "case_id": "case-uuid",
  "merchant_id": "m_demo",
  "status": "PENDING_REVIEW",
  "domain_or_app_name": "Demo Shop",
  "reviewed_by": null,
  "reviewed_at": null,
  "decision_note": null
}
```

Errors:

- `MERCHANT_NOT_FOUND` with HTTP 404.
- `ONBOARDING_CASE_FINAL` with HTTP 409 for approved/rejected cases.

### Approve Onboarding

`POST /v1/ops/merchants/{merchant_id}/onboarding-case/approve`

Approves the pending onboarding case and writes
`ONBOARDING_CASE_APPROVED`.

Request:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Approve onboarding."
  },
  "reviewed_by": null,
  "decision_note": "Documents verified for demo."
}
```

`reviewed_by` is optional. If omitted, the service uses `actor.actor_id`.

### Reject Onboarding

`POST /v1/ops/merchants/{merchant_id}/onboarding-case/reject`

Rejects the pending onboarding case and writes
`ONBOARDING_CASE_REJECTED`.

Request shape matches approval.

Errors for approve/reject:

- `MERCHANT_NOT_FOUND` with HTTP 404.
- `ONBOARDING_CASE_NOT_FOUND` with HTTP 404.
- `ONBOARDING_CASE_FINAL` with HTTP 409 when the case is not pending review.

### Activate Merchant

`POST /v1/ops/merchants/{merchant_id}/activate`

Allowed only when onboarding is `APPROVED` and an active credential exists.
Writes `MERCHANT_ACTIVATED`.

Request:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Onboarding approved and credential created."
  }
}
```

Response:

```json
{
  "merchant_id": "m_demo",
  "merchant_name": "Demo Merchant",
  "status": "ACTIVE"
}
```

Errors:

- `MERCHANT_NOT_FOUND` with HTTP 404.
- `ONBOARDING_CASE_NOT_APPROVED` with HTTP 409.
- `ACTIVE_CREDENTIAL_REQUIRED` with HTTP 409.

### Suspend Or Disable Merchant

`POST /v1/ops/merchants/{merchant_id}/suspend`

`POST /v1/ops/merchants/{merchant_id}/disable`

Both routes accept `OpsReasonRequest` with an `actor` object. Suspended and
disabled merchants remain inspectable but cannot create new payments or refunds
because merchant readiness accepts only `ACTIVE`. `disable` is `ADMIN`-only in
phase 10. Disable does not revoke credentials automatically.

Audit events:

- `MERCHANT_SUSPENDED`
- `MERCHANT_DISABLED`

## Credentials

### Create Credential

`POST /v1/ops/merchants/{merchant_id}/credentials`

Creates one active credential for the merchant and writes
`CREDENTIAL_CREATED`. The MVP stores `secret_key_encrypted` as plaintext to
match existing auth behavior, but responses and audit rows never expose the raw
secret.

Request:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Create first active credential."
  },
  "access_key": "ak_demo",
  "secret_key": "super-secret"
}
```

Response:

```json
{
  "credential_id": "credential-uuid",
  "merchant_id": "m_demo",
  "access_key": "ak_demo",
  "secret_key_last4": "cret",
  "status": "ACTIVE",
  "expired_at": null,
  "rotated_at": null
}
```

Errors:

- `MERCHANT_NOT_FOUND` with HTTP 404.
- `ACTIVE_CREDENTIAL_EXISTS` with HTTP 409.

### Rotate Credential

`POST /v1/ops/merchants/{merchant_id}/credentials/rotate`

Marks the prior active credential `ROTATED`, sets `rotated_at` and
`expired_at`, creates a new active credential, and writes
`CREDENTIAL_ROTATED`. This route is `ADMIN`-only in phase 10.

Request and response shape match credential creation.

Errors:

- `MERCHANT_NOT_FOUND` with HTTP 404.
- `ACTIVE_CREDENTIAL_NOT_FOUND` with HTTP 404.

## Reconciliation

### List Reconciliation Records

`GET /v1/ops/reconciliation`

Optional query params:

- `match_result`: `MATCHED`, `MISMATCHED`, `PENDING_REVIEW`, or `RESOLVED`.
- `entity_type`: `PAYMENT` or `REFUND`.
- `entity_id`: entity UUID.
- `limit`: 1 to 500, default 100.

Response:

```json
{
  "records": [
    {
      "record_id": "record-uuid",
      "entity_type": "PAYMENT",
      "entity_id": "payment-row-uuid",
      "internal_status": "PENDING",
      "external_status": "SUCCESS",
      "internal_amount": "100000.00",
      "external_amount": "99999.00",
      "match_result": "MISMATCHED",
      "mismatch_reason_code": "AMOUNT_MISMATCH",
      "mismatch_reason_message": "External payment amount does not match internal amount.",
      "reviewed_by": null,
      "review_note": null,
      "created_at": "2026-05-01T10:00:00Z",
      "updated_at": "2026-05-01T10:00:00Z"
    }
  ]
}
```

### Get Reconciliation Record

`GET /v1/ops/reconciliation/{record_id}`

Returns one `ReconciliationRecordResponse`.

### Resolve Reconciliation Record

`POST /v1/ops/reconciliation/{record_id}/resolve`

Sets `match_result=RESOLVED`, writes `reviewed_by` and `review_note`, uses
`updated_at` as the resolution timestamp, and writes
`RECONCILIATION_RESOLVED`.

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

Errors:

- `RECONCILIATION_NOT_FOUND` with HTTP 404.
- `RECONCILIATION_ALREADY_RESOLVED` with HTTP 409.

## Webhook Retry

`POST /v1/ops/webhooks/{event_id}/retry`

Manual retry remains internal-only and only accepts webhook events with
`status=FAILED`. Phase 10 requires an authenticated internal session and still
accepts optional audit metadata so the operator can record why the retry was
triggered.

Optional audit body:

```json
{
  "actor_type": "OPS",
  "actor_id": null,
  "reason": "Retry after merchant endpoint recovered."
}
```

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

When the optional body is supplied, the service writes `WEBHOOK_MANUAL_RETRY`
with before/after webhook event state.

## Audit

Phase 07 writes audit rows for:

- `MERCHANT_CREATED`
- `ONBOARDING_CASE_SUBMITTED`
- `ONBOARDING_CASE_APPROVED`
- `ONBOARDING_CASE_REJECTED`
- `MERCHANT_ACTIVATED`
- `MERCHANT_SUSPENDED`
- `MERCHANT_DISABLED`
- `CREDENTIAL_CREATED`
- `CREDENTIAL_ROTATED`
- `RECONCILIATION_RESOLVED`
- `WEBHOOK_MANUAL_RETRY`

Audit state sanitization masks keys named `secret_key` and
`secret_key_encrypted` recursively.
