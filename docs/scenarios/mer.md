# Merchant Scenarios

Merchant scenarios cover readiness checks that exist today and the target ops
onboarding flow planned for phase 07.

## MER-01 Active Merchant Can Use Payment Or Refund Entry Points

Implementation Status: Implemented - phase 02.

Actor: Merchant backend.

APIs:

- `POST /v1/payments`
- Future `POST /v1/refunds`

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
- Future `POST /v1/refunds`

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

Implementation Status: Planned - phase 07.

Actor: Ops.

API:

```http
POST /v1/ops/merchants
```

Request:

```json
{
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
  "status": "PENDING_REVIEW"
}
```

DB Effects:

- `merchants`: insert merchant row with `status=PENDING_REVIEW`.
- `audit_logs`: insert merchant creation event.

State Transition: none to merchant `PENDING_REVIEW`.

Expected Assertions:

- Merchant exists by public `merchant_id`.
- Merchant cannot create payment yet.

## ONB-02 Ops Submits Onboarding Case

Implementation Status: Planned - phase 07.

Actor: Ops.

API:

```http
POST /v1/ops/merchants/{merchant_id}/onboarding-case
```

Request:

```json
{
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
  "case_id": "case_...",
  "merchant_id": "m_demo",
  "status": "PENDING_REVIEW"
}
```

DB Effects:

- `merchant_onboarding_cases`: insert or update case row.
- `audit_logs`: insert onboarding case submitted event.

State Transition: onboarding case `DRAFT -> PENDING_REVIEW`.

Expected Assertions:

- One onboarding case exists for the merchant in MVP.
- Merchant remains `PENDING_REVIEW`.

## ONB-03 Ops Approves Onboarding Case

Implementation Status: Planned - phase 07.

Actor: Ops.

API:

```http
POST /v1/ops/onboarding-cases/{case_id}/approve
```

Request:

```json
{
  "reviewed_by": "ops_admin",
  "decision_note": "Documents verified for demo."
}
```

Response:

```json
{
  "case_id": "case_...",
  "status": "APPROVED",
  "reviewed_by": "ops_admin",
  "reviewed_at": "2026-04-29T10:00:00Z"
}
```

DB Effects:

- `merchant_onboarding_cases`: update status, reviewer, reviewed timestamp, and note.
- `audit_logs`: insert onboarding approval event.

State Transition: onboarding case `PENDING_REVIEW -> APPROVED`.

Expected Assertions:

- Onboarding case is approved.
- Merchant is not active until active credential/config exists.

## ONB-04 Ops Activates Merchant With Approved Onboarding And Active Credential

Implementation Status: Planned - phase 07.

Actor: Ops.

APIs:

```http
POST /v1/ops/merchants/{merchant_id}/credentials
POST /v1/ops/merchants/{merchant_id}/activate
```

Credential Request:

```json
{
  "access_key": "ak_demo",
  "secret_key": "super-secret"
}
```

Activation Request:

```json
{
  "reason": "Onboarding approved and credential created."
}
```

Response:

```json
{
  "merchant_id": "m_demo",
  "status": "ACTIVE"
}
```

DB Effects:

- `merchant_credentials`: insert active credential.
- `merchants`: update status to `ACTIVE`.
- `audit_logs`: insert credential creation and merchant activation events.

State Transition: merchant `PENDING_REVIEW -> ACTIVE`.

Expected Assertions:

- Exactly one active credential exists for the merchant.
- Merchant activation requires approved onboarding and active credential.
- Merchant APIs can authenticate after activation.

Current Workaround:

- Use direct DB seed through `backend/scripts/smoke_payment_api.py` until ops APIs
  exist.
