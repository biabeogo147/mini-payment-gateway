# Reconciliation And Ops Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the mini gateway's internal ops layer for merchant onboarding/state changes, credential operations, reconciliation review, and audit logging.

**Architecture:** Keep the existing MVC shape: controllers expose internal ops endpoints, schemas define request/response contracts, services own business rules and audit orchestration, repositories hide SQLAlchemy queries, and models remain unchanged unless a real schema gap is found. Phase 07 intentionally keeps internal authentication out of scope; ops actions accept an explicit lightweight actor context in request bodies for auditability.

**Tech Stack:** FastAPI internal controllers, Pydantic schemas, SQLAlchemy repositories, existing `AuditLog`, `MerchantOnboardingCase`, `MerchantCredential`, and `ReconciliationRecord` models, standard `unittest`, and the existing PostgreSQL/Alembic setup.

---

## Implementation Status

Completed. Phase 07 application code, tests, smoke script, and documentation
updates have been added. See `docs/plan/phase_07_completion.md` for verification
evidence and remaining phase 08 notes.

Use the current repository checkout directly. Do not create a branch or worktree
unless the user asks for one. Commit only when requested.

## Scope

Implement:

- shared audit repository/service;
- internal actor context DTO used by ops requests;
- merchant creation, onboarding case upsert, onboarding approval/rejection,
  merchant activation, suspension, and disablement;
- active credential creation and rotation;
- reconciliation evidence creation helpers for matched/mismatched payment and
  refund evidence;
- reconciliation list/detail/resolve APIs;
- audit logging for ops merchant actions, credential actions, reconciliation
  resolution, and webhook manual retry;
- route tests, service tests, docs updates, and an API/DB smoke script.

Do not implement:

- full internal login/session/JWT auth;
- RBAC enforcement beyond accepting actor metadata;
- self-service merchant onboarding UI;
- settlement, dispute, analytics, or partial refund behavior;
- background reconciliation jobs;
- credential secret encryption/key-management changes;
- a new Alembic migration unless implementation discovers the current models
  cannot represent the required behavior.

## Design Decisions

- Ops endpoints are internal-only and unauthenticated in this mini phase.
- Every mutating ops request includes an actor context:

```json
{
  "actor_type": "OPS",
  "actor_id": null,
  "reason": "Operator note"
}
```

- `actor_type` is one of `SYSTEM`, `ADMIN`, or `OPS`.
- `actor_id` is optional because phase 07 does not implement internal user
  authentication. If supplied in real DB smoke tests, it must refer to an
  existing `internal_users.id` because `audit_logs.actor_id` has a foreign key.
- Audit event types are string codes, not a new enum, to keep the model stable:
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
- Onboarding is one case per merchant in the MVP.
- Onboarding upsert creates or updates the single case and sets it to
  `PENDING_REVIEW`.
- Approved or rejected onboarding cases are final for this phase; updating a
  final case returns a controlled conflict.
- Merchant activation requires:
  - merchant exists;
  - onboarding case is `APPROVED`;
  - at least one active credential exists.
- `SUSPENDED` and `DISABLED` merchants cannot create payments/refunds because
  the existing merchant readiness service already rejects non-`ACTIVE` statuses.
- Disable does not revoke credentials in phase 07. Credential rotation is the
  operation that makes the old access key unusable.
- Credential creation stores `secret_key_encrypted` as plaintext, matching the
  existing MVP auth convention.
- Credential responses must never return the plaintext secret.
- Reconciliation resolution uses `ReconciliationRecord.reviewed_by`,
  `review_note`, `match_result=RESOLVED`, and `updated_at` as the resolution
  timestamp. No new `resolved_at` column is required.
- Existing phase 04/05 callback mismatch evidence remains valid. Phase 07 adds
  a service wrapper and ops review APIs rather than changing callback final-state
  behavior.
- Webhook manual retry audit is added by extending the phase 06 manual retry
  path with optional audit context. Existing no-body retry behavior should
  continue to work for backwards compatibility.

## Scenario References

Use `docs/scenarios/mer.md` as the behavior source for:

- `ONB-01 Ops Registers Merchant`
- `ONB-02 Ops Submits Onboarding Case`
- `ONB-03 Ops Approves Onboarding Case`
- `ONB-04 Ops Activates Merchant With Approved Onboarding And Active Credential`

Use `docs/scenarios/ops.md` as the behavior source for:

- `OPS-01 Ops Suspends Merchant`
- `OPS-02 Ops Disables Merchant`
- `OPS-03 Credential Rotation`
- `AUD-01 Ops Merchant Action Writes Audit Log`
- `AUD-02 Credential Rotation Writes Audit Log`

Use `docs/scenarios/reconciliation.md` as the behavior source for:

- `REC-03 Matching Provider Evidence`
- `REC-04 Mismatch Evidence`
- `REC-05 Resolve Reconciliation Record`

Use `docs/scenarios/webhook.md` for the phase 06 manual retry behavior that
phase 07 will make auditable.

Use `docs/scenarios/testing_matrix.md` to keep phase 07 test names aligned with
scenario IDs.

## Current Code Map

Existing source that phase 07 should build on:

- `backend/app/models/audit_log.py`
  - `event_type`
  - `entity_type`
  - `entity_id`
  - `actor_type`
  - `actor_id`
  - `before_state_json`
  - `after_state_json`
  - `reason`
  - `created_at`
- `backend/app/models/reconciliation_record.py`
  - `entity_type`
  - `entity_id`
  - `internal_status`
  - `external_status`
  - `internal_amount`
  - `external_amount`
  - `match_result`
  - `mismatch_reason_code`
  - `mismatch_reason_message`
  - `reviewed_by`
  - `review_note`
  - timestamp mixin
- `backend/app/models/merchant_onboarding_case.py`
  - one onboarding case per merchant;
  - status, submitted profile/doc/check JSON, decision fields, reviewer fields.
- `backend/app/models/merchant_credential.py`
  - partial unique index for one active credential per merchant.
- `backend/app/models/internal_user.py`
  - optional FK target for audit actor IDs and onboarding reviewers.
- `backend/app/repositories/reconciliation_repository.py`
  - already creates payment/refund reconciliation rows for callback mismatch
    evidence; extend it instead of creating a duplicate repository.
- `backend/app/services/merchant_readiness_service.py`
  - already rejects non-`ACTIVE` merchants for payment/refund creation.
- `backend/app/controllers/webhook_ops_controller.py`
  - already exposes manual retry; phase 07 should add optional audit metadata.
- `backend/app/main.py`
  - registers all routers centrally.

## Files

- Create: `backend/app/controllers/ops_merchant_controller.py`
- Create: `backend/app/controllers/ops_reconciliation_controller.py`
- Create: `backend/app/repositories/audit_repository.py`
- Create: `backend/app/repositories/onboarding_repository.py`
- Create: `backend/app/schemas/ops.py`
- Create: `backend/app/schemas/reconciliation.py`
- Create: `backend/app/services/audit_service.py`
- Create: `backend/app/services/merchant_ops_service.py`
- Create: `backend/app/services/reconciliation_service.py`
- Create: `backend/scripts/smoke_ops_reconciliation_api.py`
- Modify: `backend/app/controllers/webhook_ops_controller.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/repositories/credential_repository.py`
- Modify: `backend/app/repositories/merchant_repository.py`
- Modify: `backend/app/repositories/reconciliation_repository.py`
- Modify: `backend/app/services/webhook_delivery_service.py`
- Modify: `backend/app/schemas/webhook.py`
- Modify: `docs/api/ops_api.md`
- Modify: `docs/scenarios/mer.md`
- Modify: `docs/scenarios/ops.md`
- Modify: `docs/scenarios/reconciliation.md`
- Modify: `docs/scenarios/testing_matrix.md`
- Modify: `docs/plan/README.md`
- Create: `docs/plan/phase_07_completion.md`
- Test: `backend/tests/test_audit_service.py`
- Test: `backend/tests/test_merchant_ops_service.py`
- Test: `backend/tests/test_merchant_ops_routes.py`
- Test: `backend/tests/test_reconciliation_service.py`
- Test: `backend/tests/test_reconciliation_routes.py`
- Test: extend `backend/tests/test_webhook_ops_routes.py`
- Test: extend `backend/tests/test_webhook_delivery_service.py`

## Tasks

### Task 0: Baseline Check

- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

- [ ] Expected: existing phase 0-6 tests pass before phase 07 edits.
- [ ] If this fails, stop and fix or document the pre-existing failure before
  writing phase 07 tests.

### Task 1: Add Audit Repository And Service Tests

- [ ] Create `backend/tests/test_audit_service.py`.
- [ ] Test `audit_repository.create(...)`:
  - adds an `AuditLog`;
  - flushes;
  - persists `event_type`, `entity_type`, `entity_id`, `actor_type`,
    `actor_id`, `before_state_json`, `after_state_json`, and `reason`.
- [ ] Test `audit_service.record_event(...)` for these entity types:
  - `MERCHANT`
  - `MERCHANT_CREDENTIAL`
  - `ONBOARDING_CASE`
  - `WEBHOOK_EVENT`
  - `RECONCILIATION`
- [ ] Test plaintext secret safety:
  - when `before_state` or `after_state` contains `secret_key` or
    `secret_key_encrypted`, the audit service masks the value before insert.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_audit_service -v
```

- [ ] Expected: FAIL before `audit_repository` and `audit_service` exist.

### Task 2: Implement Audit Repository And Service

- [ ] Create `backend/app/repositories/audit_repository.py`.
- [ ] Implement:
  - `create(db, event_type, entity_type, entity_id, actor_type, actor_id=None, before_state_json=None, after_state_json=None, reason=None)`.
- [ ] Create `backend/app/services/audit_service.py`.
- [ ] Implement:
  - `record_event(db, event_type, entity_type, entity_id, actor_type, actor_id=None, before_state=None, after_state=None, reason=None)`.
- [ ] Add helper:
  - `_sanitize_state(value)` recursively masks keys named `secret_key` and
    `secret_key_encrypted`.
- [ ] Do not call `db.commit()` inside `audit_service`; outer workflow services
  own transaction boundaries.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_audit_service -v
```

- [ ] Expected: PASS.

### Task 3: Add Merchant Ops Service Tests

- [ ] Create `backend/tests/test_merchant_ops_service.py`.
- [ ] Use fake repositories/stores like earlier service tests; do not require a
  real DB in unit tests.
- [ ] Test `create_merchant(...)`:
  - creates `MerchantStatus.PENDING_REVIEW`;
  - rejects duplicate public `merchant_id` with `MERCHANT_ALREADY_EXISTS`;
  - records `MERCHANT_CREATED` audit.
- [ ] Test `submit_onboarding_case(...)`:
  - creates a `PENDING_REVIEW` onboarding case when none exists;
  - updates the existing non-final case;
  - rejects `APPROVED` or `REJECTED` cases with `ONBOARDING_CASE_FINAL`;
  - records `ONBOARDING_CASE_SUBMITTED` audit.
- [ ] Test `approve_onboarding_case(...)`:
  - requires case status `PENDING_REVIEW`;
  - sets `APPROVED`, `reviewed_by`, `reviewed_at`, and `decision_note`;
  - records `ONBOARDING_CASE_APPROVED` audit.
- [ ] Test `reject_onboarding_case(...)`:
  - sets `REJECTED`, reviewer fields, and decision note;
  - records `ONBOARDING_CASE_REJECTED` audit.
- [ ] Test `create_credential(...)`:
  - requires merchant exists;
  - rejects if an active credential already exists;
  - stores `secret_key_encrypted` with current MVP plaintext convention;
  - stores `secret_key_last4`;
  - records `CREDENTIAL_CREATED` audit without plaintext secret.
- [ ] Test `activate_merchant(...)`:
  - requires approved onboarding case;
  - requires active credential;
  - changes merchant status to `ACTIVE`;
  - records `MERCHANT_ACTIVATED` audit.
- [ ] Test `suspend_merchant(...)` and `disable_merchant(...)`:
  - update status to `SUSPENDED` or `DISABLED`;
  - record audit rows.
- [ ] Test `rotate_credential(...)`:
  - marks old active credential `ROTATED`;
  - sets `rotated_at` and `expired_at`;
  - creates a new active credential;
  - records `CREDENTIAL_ROTATED` audit without plaintext secret.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_merchant_ops_service -v
```

- [ ] Expected: FAIL before merchant ops service exists.

### Task 4: Implement Merchant Ops Repositories And Service

- [ ] Create `backend/app/repositories/onboarding_repository.py`.
- [ ] Implement:
  - `get_by_merchant(db, merchant_db_id)`;
  - `get_by_id(db, case_id)`;
  - `create(db, merchant_db_id, status, domain_or_app_name, submitted_profile_json, documents_json, review_checks_json)`;
  - `save(db, onboarding_case)`.
- [ ] Modify `backend/app/repositories/merchant_repository.py`.
- [ ] Add:
  - `create(db, merchant_id, merchant_name, legal_name, contact_name, contact_email, contact_phone, webhook_url, settlement_account_name, settlement_account_number, settlement_bank_code)`;
  - `save(db, merchant)`.
- [ ] Modify `backend/app/repositories/credential_repository.py`.
- [ ] Add:
  - `create(db, merchant_db_id, access_key, secret_key, now=None)`;
  - `save(db, credential)`.
- [ ] Create `backend/app/services/merchant_ops_service.py`.
- [ ] Implement service functions:
  - `create_merchant(db, request, actor, now=None)`;
  - `submit_onboarding_case(db, merchant_id, request, actor, now=None)`;
  - `approve_onboarding_case(db, merchant_id, request, actor, now=None)`;
  - `reject_onboarding_case(db, merchant_id, request, actor, now=None)`;
  - `create_credential(db, merchant_id, request, actor, now=None)`;
  - `activate_merchant(db, merchant_id, request, actor, now=None)`;
  - `suspend_merchant(db, merchant_id, request, actor, now=None)`;
  - `disable_merchant(db, merchant_id, request, actor, now=None)`;
  - `rotate_credential(db, merchant_id, request, actor, now=None)`.
- [ ] Use `AppError` codes:
  - `MERCHANT_NOT_FOUND` with 404;
  - `MERCHANT_ALREADY_EXISTS` with 409;
  - `ONBOARDING_CASE_NOT_FOUND` with 404;
  - `ONBOARDING_CASE_FINAL` with 409;
  - `ONBOARDING_CASE_NOT_APPROVED` with 409;
  - `ACTIVE_CREDENTIAL_REQUIRED` with 409;
  - `ACTIVE_CREDENTIAL_EXISTS` with 409;
  - `ACTIVE_CREDENTIAL_NOT_FOUND` with 404.
- [ ] Each service function should write audit through `audit_service` before
  `db.commit()`.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_merchant_ops_service -v
```

- [ ] Expected: PASS.

### Task 5: Add Merchant Ops Schemas And Route Tests

- [ ] Create `backend/app/schemas/ops.py`.
- [ ] Define:
  - `OpsActorContext`;
  - `CreateMerchantRequest`;
  - `MerchantOpsResponse`;
  - `SubmitOnboardingCaseRequest`;
  - `OnboardingCaseResponse`;
  - `ReviewOnboardingCaseRequest`;
  - `CreateCredentialRequest`;
  - `RotateCredentialRequest`;
  - `CredentialOpsResponse`;
  - `OpsReasonRequest`.
- [ ] Ensure response schemas do not expose plaintext credential secrets.
- [ ] Create `backend/tests/test_merchant_ops_routes.py`.
- [ ] Test routes call service with parsed request, `db`, `merchant_id`, and
  actor context:
  - `POST /v1/ops/merchants`;
  - `PUT /v1/ops/merchants/{merchant_id}/onboarding-case`;
  - `POST /v1/ops/merchants/{merchant_id}/onboarding-case/approve`;
  - `POST /v1/ops/merchants/{merchant_id}/onboarding-case/reject`;
  - `POST /v1/ops/merchants/{merchant_id}/credentials`;
  - `POST /v1/ops/merchants/{merchant_id}/credentials/rotate`;
  - `POST /v1/ops/merchants/{merchant_id}/activate`;
  - `POST /v1/ops/merchants/{merchant_id}/suspend`;
  - `POST /v1/ops/merchants/{merchant_id}/disable`.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_merchant_ops_routes -v
```

- [ ] Expected: FAIL before controller exists.

### Task 6: Implement Merchant Ops Controller

- [ ] Create `backend/app/controllers/ops_merchant_controller.py`.
- [ ] Add `APIRouter(prefix="/v1/ops/merchants", tags=["ops-merchants"])`.
- [ ] Implement the routes from Task 5.
- [ ] Keep controllers thin; call `merchant_ops_service` only.
- [ ] Register router in `backend/app/main.py`.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_merchant_ops_routes tests.test_merchant_ops_service -v
```

- [ ] Expected: PASS.

### Task 7: Add Reconciliation Service Tests

- [ ] Create `backend/tests/test_reconciliation_service.py`.
- [ ] Test repository additions:
  - `get_by_id(db, record_id)`;
  - `find(db, match_result=None, entity_type=None, entity_id=None, limit=100)`;
  - `save(db, record)`.
- [ ] Test `create_payment_evidence(...)`:
  - matching internal status and amount creates `MATCHED`;
  - amount mismatch creates `MISMATCHED` with `AMOUNT_MISMATCH`;
  - status mismatch creates `MISMATCHED` with `STATUS_MISMATCH`;
  - late success after expired payment creates `PENDING_REVIEW` with
    `LATE_SUCCESS_AFTER_EXPIRATION`.
- [ ] Test `create_refund_evidence(...)`:
  - matching creates `MATCHED`;
  - amount mismatch creates `MISMATCHED`;
  - status conflict creates `PENDING_REVIEW` with `STATUS_CONFLICT`.
- [ ] Test `resolve_record(...)`:
  - missing record raises `RECONCILIATION_NOT_FOUND`;
  - already resolved record raises `RECONCILIATION_ALREADY_RESOLVED`;
  - pending/mismatched record becomes `RESOLVED`;
  - sets `reviewed_by` and `review_note`;
  - records `RECONCILIATION_RESOLVED` audit.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_reconciliation_service -v
```

- [ ] Expected: FAIL before service/repository additions exist.

### Task 8: Implement Reconciliation Repository And Service

- [ ] Modify `backend/app/repositories/reconciliation_repository.py`.
- [ ] Add:
  - `get_by_id(db, record_id)`;
  - `find(db, match_result=None, entity_type=None, entity_id=None, limit=100)`;
  - `save(db, record)`.
- [ ] Create `backend/app/services/reconciliation_service.py`.
- [ ] Implement:
  - `create_payment_evidence(db, payment, external_status, external_amount, now=None)`;
  - `create_refund_evidence(db, refund, external_status, external_amount, now=None)`;
  - `list_records(db, match_result=None, entity_type=None, entity_id=None, limit=100)`;
  - `get_record(db, record_id)`;
  - `resolve_record(db, record_id, request, actor, now=None)`.
- [ ] Keep existing direct callback repository functions intact for phase 04/05
  compatibility.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_reconciliation_service -v
```

- [ ] Expected: PASS.

### Task 9: Add Reconciliation Schemas And Route Tests

- [ ] Create `backend/app/schemas/reconciliation.py`.
- [ ] Define:
  - `ReconciliationRecordResponse`;
  - `ResolveReconciliationRequest`;
  - `ReconciliationListResponse` if needed.
- [ ] Create `backend/tests/test_reconciliation_routes.py`.
- [ ] Test:
  - `GET /v1/ops/reconciliation` passes filters to service;
  - `GET /v1/ops/reconciliation/{record_id}` calls detail service;
  - `POST /v1/ops/reconciliation/{record_id}/resolve` calls resolve service
    with request actor context.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_reconciliation_routes -v
```

- [ ] Expected: FAIL before controller/schema exists.

### Task 10: Implement Reconciliation Controller

- [ ] Create `backend/app/controllers/ops_reconciliation_controller.py`.
- [ ] Add `APIRouter(prefix="/v1/ops/reconciliation", tags=["ops-reconciliation"])`.
- [ ] Implement:
  - `GET /v1/ops/reconciliation`;
  - `GET /v1/ops/reconciliation/{record_id}`;
  - `POST /v1/ops/reconciliation/{record_id}/resolve`.
- [ ] Register router in `backend/app/main.py`.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_reconciliation_routes tests.test_reconciliation_service -v
```

- [ ] Expected: PASS.

### Task 11: Add Webhook Manual Retry Audit Tests

- [ ] Extend `backend/tests/test_webhook_delivery_service.py`.
- [ ] Test `manual_retry(..., audit_context=...)`:
  - captures before state;
  - retries delivery;
  - records `WEBHOOK_MANUAL_RETRY` audit with `EntityType.WEBHOOK_EVENT`;
  - records actor and reason;
  - keeps existing no-audit call behavior working.
- [ ] Extend `backend/tests/test_webhook_ops_routes.py`.
- [ ] Test route accepts optional body:

```json
{
  "actor_type": "OPS",
  "actor_id": null,
  "reason": "Retry after merchant endpoint recovered."
}
```

- [ ] Test route still works with no request body for phase 06 compatibility.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_webhook_delivery_service tests.test_webhook_ops_routes -v
```

- [ ] Expected: FAIL before audit wiring exists.

### Task 12: Implement Webhook Manual Retry Audit Wiring

- [ ] Modify `backend/app/schemas/webhook.py`.
- [ ] Add optional request schema, or reuse `OpsActorContext` from
  `backend/app/schemas/ops.py` if import direction stays clean.
- [ ] Modify `backend/app/services/webhook_delivery_service.py`.
- [ ] Extend `manual_retry(db, event_id, now=None, http_client=None, audit_context=None)`.
- [ ] When `audit_context` is provided:
  - snapshot event before retry;
  - call `deliver_event(...)`;
  - record `WEBHOOK_MANUAL_RETRY` audit with before/after state.
- [ ] Modify `backend/app/controllers/webhook_ops_controller.py`.
- [ ] Accept optional body and pass audit context to service.
- [ ] Run webhook route/service tests.
- [ ] Expected: PASS.

### Task 13: API And DB Smoke

- [ ] Create `backend/scripts/smoke_ops_reconciliation_api.py`.
- [ ] The script should:
  - start the FastAPI app on a free local port;
  - call `POST /v1/ops/merchants`;
  - call `PUT /v1/ops/merchants/{merchant_id}/onboarding-case`;
  - approve onboarding;
  - create an active credential;
  - activate merchant;
  - create a payment with merchant HMAC auth;
  - create a mismatched provider callback to produce a reconciliation record;
  - list reconciliation records;
  - resolve the record;
  - verify `audit_logs` contains merchant, credential, and reconciliation audit
    events;
  - print compact JSON evidence.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m alembic upgrade head
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_ops_reconciliation_api.py
```

- [ ] Expected: JSON output proves ops onboarding, credential creation,
  merchant activation, reconciliation resolution, and audit rows agree with DB.

### Task 14: Documentation Updates

- [ ] Update `docs/api/ops_api.md` with implemented request/response bodies.
- [ ] Update `docs/scenarios/mer.md`:
  - mark ONB-01 to ONB-04 implemented;
  - align onboarding upsert endpoint to `PUT /v1/ops/merchants/{merchant_id}/onboarding-case`;
  - align approval/rejection endpoints to merchant-scoped paths.
- [ ] Update `docs/scenarios/ops.md`:
  - mark OPS-01 to OPS-03 and AUD-01 to AUD-02 implemented;
  - note disable does not revoke credentials in this phase.
- [ ] Update `docs/scenarios/reconciliation.md`:
  - mark REC-03 to REC-05 implemented;
  - document `reviewed_by`, `review_note`, and audit behavior.
- [ ] Update `docs/scenarios/testing_matrix.md`:
  - phase 07 rows become `Covered` or `Covered with DB seed`.
- [ ] Update `docs/scenarios/e2e_scenarios.md` current capability snapshot.
- [ ] Update `docs/plan/README.md`:
  - mark phase 07 completed after implementation;
  - add smoke command.
- [ ] Create `docs/plan/phase_07_completion.md` with:
  - completed scope;
  - tests run;
  - smoke output;
  - remaining phase 08 notes.

### Task 15: Full Verification

- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

- [ ] Expected: all tests pass.

- [ ] Run:

```powershell
git diff --check
```

- [ ] Expected: no whitespace errors.

### Task 16: Commit

- [ ] Only if the user asks for a commit, stage phase 07 files and commit.
- [ ] Commit message suggestion:

```text
feat: add ops audit and reconciliation flows
```

## Acceptance Criteria

- Ops can create a merchant, submit/approve onboarding, create credentials, and
  activate the merchant.
- Ops can suspend and disable merchants, and existing payment/refund create
  readiness checks reject those merchant statuses.
- Credential creation and rotation leave at most one active credential per
  merchant.
- Credential rotation makes the old access key fail authentication because it is
  no longer `ACTIVE`.
- Ops actions create audit rows with entity, actor, before/after state, reason,
  and no plaintext secret leakage.
- Reconciliation service can create matched, mismatched, and pending-review
  evidence rows for payment/refund data.
- Ops can list, inspect, and resolve reconciliation records.
- Reconciliation resolution writes an audit row.
- Webhook manual retry can be audited while remaining backward-compatible with
  the phase 06 no-body retry endpoint.
- API docs, scenario docs, testing matrix, and completion docs are updated after
  implementation.
