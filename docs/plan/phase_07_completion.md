# Phase 07 Completion

Phase 07 implements the internal ops layer for merchant onboarding and state
changes, credential operations, audit logging, reconciliation review/resolution,
and optional webhook manual retry audit.

## Completed Scope

- Added audit repository/service with recursive masking for `secret_key` and
  `secret_key_encrypted`.
- Added ops actor context DTOs and merchant ops schemas.
- Added merchant ops service and routes:
  - `POST /v1/ops/merchants`
  - `PUT /v1/ops/merchants/{merchant_id}/onboarding-case`
  - `POST /v1/ops/merchants/{merchant_id}/onboarding-case/approve`
  - `POST /v1/ops/merchants/{merchant_id}/onboarding-case/reject`
  - `POST /v1/ops/merchants/{merchant_id}/credentials`
  - `POST /v1/ops/merchants/{merchant_id}/credentials/rotate`
  - `POST /v1/ops/merchants/{merchant_id}/activate`
  - `POST /v1/ops/merchants/{merchant_id}/suspend`
  - `POST /v1/ops/merchants/{merchant_id}/disable`
- Added onboarding repository and merchant/credential repository write helpers.
- Added reconciliation service, schemas, repository query helpers, and routes:
  - `GET /v1/ops/reconciliation`
  - `GET /v1/ops/reconciliation/{record_id}`
  - `POST /v1/ops/reconciliation/{record_id}/resolve`
- Added matched, mismatched, pending-review, and resolved reconciliation service
  behavior for payment/refund evidence.
- Added optional audit context to `POST /v1/ops/webhooks/{event_id}/retry` while
  keeping no-body phase 06 retry calls compatible.
- Added `backend/scripts/smoke_ops_reconciliation_api.py`.
- Updated ops API docs, architecture docs, scenario docs, testing matrix, plan
  README, and phase 07 plan status.

## Verification

Baseline before phase 07 edits:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

Result: 116 tests passed.

Focused phase 07 checks run during implementation:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_audit_service -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_merchant_ops_routes tests.test_merchant_ops_service -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_reconciliation_routes tests.test_reconciliation_service -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_webhook_delivery_service tests.test_webhook_ops_routes -v
```

Full unit suite after implementation:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

Result: 141 tests passed.

DB migration check:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m alembic upgrade head
```

Result: Alembic reported PostgreSQL context and no pending migration failures.

Phase 07 smoke:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_ops_reconciliation_api.py
```

Output:

```json
{"activation_status": "ACTIVE", "approval_status": "APPROVED", "audit_events": ["CREDENTIAL_CREATED", "MERCHANT_ACTIVATED", "MERCHANT_CREATED", "ONBOARDING_CASE_APPROVED", "ONBOARDING_CASE_SUBMITTED", "RECONCILIATION_RESOLVED"], "callback_processing_result": "PENDING_REVIEW", "credential_access_key": "ak_phase7_16f7889b", "db_reconciliation_status": "RESOLVED", "listed_reconciliation_count": 1, "merchant_id": "m_phase7_16f7889b", "onboarding_status": "PENDING_REVIEW", "payment_transaction_id": "pay_1112aabc1b2c437b97fafd5ccd3179e2", "port": 56197, "reconciliation_record_id": "a1a2fc2a-988c-4d55-90f1-ff58b40954b4", "resolution_status": "RESOLVED"}
```

## Remaining Phase 08 Notes

- Add automated full E2E tests around onboarding -> payment -> refund ->
  callback -> webhook -> reconciliation journeys.
- Add runbooks/readiness docs for operating the smoke scripts and manual ops
  flows.
- Keep internal authentication/RBAC out of phase 07; phase 08 can document the
  intended production hardening path without adding it to the mini MVP unless
  scope changes.
- Settlement, disputes, analytics, multi-provider routing, and partial refunds
  remain out of scope.
