# Merchant Scenarios

Merchant scenarios cover readiness checks and the internal ops onboarding flow.

## MER-01 Active Merchant Can Use Payment Or Refund Entry Points

Implementation Status: Implemented - phase 02.

Actor: Merchant backend.

APIs:

- `POST /v1/payments`
- `POST /v1/refunds`

DB Reads:

- `merchants`
- `merchant_credentials`

Expected Assertions:

- Merchant status must be `ACTIVE`.
- The authenticated credential must be active.
- The service may continue to payment/refund business validation.

## MER-02 Non-Active Merchant Cannot Use Payment Or Refund Entry Points

Implementation Status: Implemented - phase 02.

Actor: Merchant backend.

APIs:

- `POST /v1/payments`
- `POST /v1/refunds`

DB Effects:

- No payment or refund row should be inserted.

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

Expected Assertions:

- `PENDING_REVIEW`, `SUSPENDED`, and `DISABLED` merchants cannot initiate money
  movement.
- Ops can still inspect historical records for non-active merchants.

## ONB-01 Ops Registers Merchant

Implementation Status: Implemented - phase 07.

Actor: Ops.

API:

```http
POST /v1/ops/merchants
```

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

DB Effects:

- `merchants`: insert merchant row with `status=PENDING_REVIEW`.
- `audit_logs`: insert `MERCHANT_CREATED`.

State Transition: none to merchant `PENDING_REVIEW`.

Expected Assertions:

- Merchant exists by public `merchant_id`.
- Duplicate public `merchant_id` returns `MERCHANT_ALREADY_EXISTS`.
- Merchant cannot create payment yet.

## ONB-02 Ops Submits Onboarding Case

Implementation Status: Implemented - phase 07.

Actor: Ops.

API:

```http
PUT /v1/ops/merchants/{merchant_id}/onboarding-case
```

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

DB Effects:

- `merchant_onboarding_cases`: insert or update the single merchant case.
- `audit_logs`: insert `ONBOARDING_CASE_SUBMITTED`.

State Transition: onboarding case `DRAFT -> PENDING_REVIEW` or non-final case
back to `PENDING_REVIEW`.

Expected Assertions:

- One onboarding case exists for the merchant in MVP.
- Approved or rejected cases are final in this phase and return
  `ONBOARDING_CASE_FINAL` on update.
- Merchant remains `PENDING_REVIEW`.

## ONB-03 Ops Approves Onboarding Case

Implementation Status: Implemented - phase 07.

Actor: Ops.

API:

```http
POST /v1/ops/merchants/{merchant_id}/onboarding-case/approve
```

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

Response:

```json
{
  "case_id": "case-uuid",
  "merchant_id": "m_demo",
  "status": "APPROVED",
  "domain_or_app_name": "Demo Shop",
  "reviewed_by": null,
  "reviewed_at": "2026-05-01T09:00:00Z",
  "decision_note": "Documents verified for demo."
}
```

DB Effects:

- `merchant_onboarding_cases`: update status, reviewer, reviewed timestamp, and note.
- `audit_logs`: insert `ONBOARDING_CASE_APPROVED`.

State Transition: onboarding case `PENDING_REVIEW -> APPROVED`.

Expected Assertions:

- Onboarding case is approved.
- Merchant is not active until active credential/config exists.
- Reject uses the same merchant-scoped path with `/reject` and writes
  `ONBOARDING_CASE_REJECTED`.

## ONB-04 Ops Activates Merchant With Approved Onboarding And Active Credential

Implementation Status: Implemented - phase 07.

Actor: Ops.

APIs:

```http
POST /v1/ops/merchants/{merchant_id}/credentials
POST /v1/ops/merchants/{merchant_id}/activate
```

Credential Request:

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

Activation Request:

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

DB Effects:

- `merchant_credentials`: insert active credential.
- `merchants`: update status to `ACTIVE`.
- `audit_logs`: insert `CREDENTIAL_CREATED` and `MERCHANT_ACTIVATED`.

State Transition: merchant `PENDING_REVIEW -> ACTIVE`.

Expected Assertions:

- Exactly one active credential exists for the merchant.
- Merchant activation requires approved onboarding and active credential.
- Credential responses do not expose plaintext `secret_key`.
- Merchant APIs can authenticate after activation.
