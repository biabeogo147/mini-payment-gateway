# Reconciliation And Ops Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement reconciliation record creation, internal review actions, and audit logging for administrative changes.

**Architecture:** Reconciliation is a service that compares internal records with provider evidence and stores match or mismatch results. Audit logging is a shared service called by ops flows and manual interventions.

**Tech Stack:** FastAPI internal routes, SQLAlchemy, existing `ReconciliationRecord` and `AuditLog` models.

---

## Scope

Implement:

- reconciliation service for payment/refund mismatch evidence.
- ops review updates.
- audit log service.
- minimal internal merchant onboarding and credential operation endpoints if not already implemented.

## Files

- Create: `backend/app/api/routes/ops_merchants.py`
- Create: `backend/app/api/routes/ops_reconciliation.py`
- Create: `backend/app/repositories/audit_repository.py`
- Create: `backend/app/repositories/reconciliation_repository.py` if not created in phase 04.
- Create: `backend/app/schemas/ops.py`
- Create: `backend/app/schemas/reconciliation.py`
- Create: `backend/app/services/audit_service.py`
- Create: `backend/app/services/merchant_ops_service.py`
- Create: `backend/app/services/reconciliation_service.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_audit_service.py`
- Test: `backend/tests/test_merchant_ops_service.py`
- Test: `backend/tests/test_reconciliation_service.py`

## Tasks

### Task 1: Add Audit Service Tests

- [ ] Create `backend/tests/test_audit_service.py`.
- [ ] Test audit rows can be written for:
  - `MERCHANT`
  - `MERCHANT_CREDENTIAL`
  - `ONBOARDING_CASE`
  - `PAYMENT`
  - `REFUND`
  - `WEBHOOK_EVENT`
  - `RECONCILIATION`
- [ ] Test actor type and reason are persisted.
- [ ] Run:

```powershell
cd backend
python -m unittest tests.test_audit_service -v
```

- [ ] Expected: FAIL before audit service exists.

### Task 2: Implement Audit Service

- [ ] Create `backend/app/repositories/audit_repository.py`.
- [ ] Create `backend/app/services/audit_service.py`.
- [ ] Implement:
  - `record_event(db, event_type, entity_type, entity_id, actor_type, actor_id, before_state, after_state, reason)`
- [ ] Run audit tests.

### Task 3: Implement Merchant Ops Service

- [ ] Create `backend/tests/test_merchant_ops_service.py`.
- [ ] Test:
  - create merchant starts `PENDING_REVIEW`.
  - create/update onboarding case.
  - approve onboarding stores `reviewed_by`, `reviewed_at`, and note.
  - merchant can activate only when onboarding is approved and active credential exists.
  - suspend/disable blocks future merchant API creation flows.
  - credential rotation leaves one active credential.
- [ ] Create `backend/app/services/merchant_ops_service.py`.
- [ ] Create `backend/app/schemas/ops.py`.
- [ ] Create `backend/app/api/routes/ops_merchants.py`.
- [ ] Register ops merchant router.
- [ ] Ensure audit service is called for ops state changes.

### Task 4: Implement Reconciliation Service

- [ ] Create `backend/tests/test_reconciliation_service.py`.
- [ ] Test:
  - matching status and amount creates `MATCHED`.
  - status mismatch creates `MISMATCHED`.
  - amount mismatch creates `MISMATCHED`.
  - late success callback after expiration creates `PENDING_REVIEW`.
  - ops review can mark record `RESOLVED`.
- [ ] Create `backend/app/services/reconciliation_service.py`.
- [ ] Create `backend/app/schemas/reconciliation.py`.
- [ ] Reuse or create `backend/app/repositories/reconciliation_repository.py`.
- [ ] Run reconciliation tests.

### Task 5: Add Reconciliation Ops Routes

- [ ] Create `backend/app/api/routes/ops_reconciliation.py`.
- [ ] Add:
  - `GET /v1/ops/reconciliation`
  - `GET /v1/ops/reconciliation/{record_id}`
  - `POST /v1/ops/reconciliation/{record_id}/resolve`
- [ ] Register router in `backend/app/main.py`.
- [ ] Add route tests.

### Task 6: Verification

- [ ] Run:

```powershell
cd backend
python -m unittest discover tests -v
```

- [ ] Expected: all tests pass.

### Task 7: Commit

- [ ] Stage ops/audit/reconciliation files.
- [ ] Commit message suggestion:

```text
feat: add reconciliation and ops audit flows
```

## Acceptance Criteria

- Ops actions are auditable.
- Reconciliation records support match, mismatch, pending review, and resolved states.
- Merchant activation requires approved onboarding and credentials.
- Suspended/disabled merchants cannot create payment/refund.
