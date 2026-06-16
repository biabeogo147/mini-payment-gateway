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

Merchant read and portal user APIs:

- `GET /v1/ops/merchants`
- `GET /v1/ops/merchants/{merchant_id}`
- `GET /v1/ops/merchants/{merchant_id}/onboarding-case`
- `GET /v1/ops/merchants/{merchant_id}/credentials`
- `POST /v1/ops/merchants/{merchant_id}/qr-accounts`
- `PATCH /v1/ops/merchants/{merchant_id}/qr-accounts/{qr_account_id}`
- `POST /v1/ops/merchants/{merchant_id}/qr-accounts/{qr_account_id}/activate`
- `POST /v1/ops/merchants/{merchant_id}/qr-accounts/{qr_account_id}/deactivate`
- `GET /v1/ops/merchants/{merchant_id}/portal-users`
- `POST /v1/ops/merchants/{merchant_id}/portal-users`
- `PATCH /v1/ops/merchants/{merchant_id}/portal-users/{user_id}`
- `POST /v1/ops/merchants/{merchant_id}/portal-users/{user_id}/reset-password`

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
- `POST /v1/ops/reconciliation/{record_id}/resolve`

## Merchant Portal User Management

Merchant portal user management is `ADMIN`-only. `OPS` users can continue the
standard operational workflows, but they cannot create merchant dashboard users,
change portal roles/status, or reset merchant portal passwords.

### List Portal Users

`GET /v1/ops/merchants/{merchant_id}/portal-users`

Response:

```json
{
  "users": [
    {
      "user_id": "uuid",
      "merchant_id": "m_demo",
      "email": "merchant@example.com",
      "full_name": "Merchant Admin",
      "role": "MERCHANT_ADMIN",
      "status": "ACTIVE",
      "last_login_at": null,
      "created_at": "2026-06-09T00:00:00Z",
      "updated_at": "2026-06-09T00:00:00Z"
    }
  ]
}
```

### Create Portal User

`POST /v1/ops/merchants/{merchant_id}/portal-users`

Request:

```json
{
  "email": "merchant@example.com",
  "full_name": "Merchant Admin",
  "role": "MERCHANT_ADMIN",
  "status": "ACTIVE"
}
```

Response returns the generated password once:

```json
{
  "user": {
    "user_id": "uuid",
    "merchant_id": "m_demo",
    "email": "merchant@example.com",
    "full_name": "Merchant Admin",
    "role": "MERCHANT_ADMIN",
    "status": "ACTIVE",
    "last_login_at": null,
    "created_at": "2026-06-09T00:00:00Z",
    "updated_at": "2026-06-09T00:00:00Z"
  },
  "generated_password": "one-time-password"
}
```

### Update Portal User

`PATCH /v1/ops/merchants/{merchant_id}/portal-users/{user_id}`

Request fields are optional, but at least one should be supplied by the client:

```json
{
  "full_name": "Merchant Viewer",
  "role": "MERCHANT_VIEWER",
  "status": "INACTIVE"
}
```

### Reset Portal User Password

`POST /v1/ops/merchants/{merchant_id}/portal-users/{user_id}/reset-password`

Response shape matches create and returns the generated password once.
Plaintext passwords are not stored or retrievable later.

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

## QR Receiving Accounts

Ops manages merchant QR receiving accounts. Merchant self-service QR account
configuration is out of pilot scope.

### Create QR Account

`POST /v1/ops/merchants/{merchant_id}/qr-accounts`

Creates a VietQR receiving account and writes `MERCHANT_QR_ACCOUNT_CREATED`.
Only one active account per merchant and provider is allowed.

Request:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Configure VietQR receiving account."
  },
  "provider": "VIETQR",
  "bank_code": "VCB",
  "bank_bin": "970436",
  "account_number": "9704000000000001",
  "account_name": "DEMO MERCHANT",
  "template": "compact",
  "status": "ACTIVE"
}
```

Response:

```json
{
  "qr_account_id": "qr-account-uuid",
  "merchant_id": "m_demo",
  "provider": "VIETQR",
  "bank_code": "VCB",
  "bank_bin": "970436",
  "account_number": "9704000000000001",
  "account_name": "DEMO MERCHANT",
  "template": "compact",
  "status": "ACTIVE",
  "created_at": "2026-06-16T00:00:00Z",
  "updated_at": "2026-06-16T00:00:00Z"
}
```

### Update, Activate, Deactivate

- `PATCH /v1/ops/merchants/{merchant_id}/qr-accounts/{qr_account_id}` updates
  bank/account/template fields and writes `MERCHANT_QR_ACCOUNT_UPDATED`.
- `POST /v1/ops/merchants/{merchant_id}/qr-accounts/{qr_account_id}/activate`
  activates one account and deactivates the prior active account for the same
  provider.
- `POST /v1/ops/merchants/{merchant_id}/qr-accounts/{qr_account_id}/deactivate`
  marks the account inactive.

Errors:

- `MERCHANT_NOT_FOUND` with HTTP 404.
- `QR_ACCOUNT_NOT_FOUND` with HTTP 404.
- `ACTIVE_QR_ACCOUNT_EXISTS` with HTTP 409.

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
