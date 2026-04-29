# Provider Callback And Expiration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement provider/simulator callbacks, raw callback logging, payment state transitions, and expiration handling.

**Architecture:** Provider callback routes call a callback service that stores `BankCallbackLog`, normalizes provider status, and delegates payment state updates to the payment service. Expiration is a separate service operation that moves overdue pending payments to `EXPIRED`.

**Tech Stack:** FastAPI, SQLAlchemy, existing `BankCallbackLog`, `PaymentTransaction`, and `ReconciliationRecord` models.

---

## Scope

Implement:

- `POST /v1/provider/callbacks/payment`
- callback evidence logging.
- payment transitions:
  - `PENDING -> SUCCESS`
  - `PENDING -> FAILED`
  - `PENDING -> EXPIRED`
- late callback after expiration goes to reconciliation/manual review path.
- no automatic webhook delivery yet; create an extension point for phase 06.

## Files

- Create: `backend/app/api/routes/provider_callbacks.py`
- Create: `backend/app/repositories/bank_callback_repository.py`
- Create: `backend/app/repositories/reconciliation_repository.py`
- Create: `backend/app/schemas/provider_callback.py`
- Create: `backend/app/services/provider_callback_service.py`
- Create: `backend/app/services/payment_state_machine.py`
- Create: `backend/app/services/expiration_service.py`
- Modify: `backend/app/repositories/payment_repository.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_payment_state_machine.py`
- Test: `backend/tests/test_provider_callback_service.py`
- Test: `backend/tests/test_expiration_service.py`

## Tasks

### Task 1: Add Payment State Machine Tests

- [ ] Create `backend/tests/test_payment_state_machine.py`.
- [ ] Test allowed transitions:
  - `PENDING -> SUCCESS`
  - `PENDING -> FAILED`
  - `PENDING -> EXPIRED`
- [ ] Test rejected transitions:
  - `EXPIRED -> SUCCESS`
  - `SUCCESS -> FAILED`
  - `FAILED -> SUCCESS`
- [ ] Run:

```powershell
cd backend
python -m unittest tests.test_payment_state_machine -v
```

- [ ] Expected: FAIL before state machine exists.

### Task 2: Implement Payment State Machine

- [ ] Create `backend/app/services/payment_state_machine.py`.
- [ ] Implement:
  - `assert_payment_transition_allowed(current_status, target_status)`
  - `mark_success(payment, paid_at)`
  - `mark_failed(payment, reason_code, reason_message)`
  - `mark_expired(payment)`
- [ ] Run state machine tests.
- [ ] Expected: PASS.

### Task 3: Define Provider Callback Schema

- [ ] Create `backend/app/schemas/provider_callback.py`.
- [ ] Define payment callback request:
  - `external_reference`
  - `transaction_reference`
  - `status`
  - `amount`
  - `paid_at`
  - `raw_payload`
- [ ] Define normalized statuses:
  - `SUCCESS`
  - `FAILED`
  - `PENDING_REVIEW`
- [ ] Add schema tests for required fields.

### Task 4: Implement Callback Logging Repository

- [ ] Create `backend/app/repositories/bank_callback_repository.py`.
- [ ] Implement create method for `BankCallbackLog`.
- [ ] Ensure raw payload is persisted.

### Task 5: Implement Provider Callback Service

- [ ] Create `backend/tests/test_provider_callback_service.py`.
- [ ] Test:
  - success callback marks pending payment success and sets `paid_at`.
  - failed callback marks pending payment failed.
  - unknown transaction creates callback log with failed or pending review result.
  - callback after payment expired creates reconciliation record and does not revive.
- [ ] Create `backend/app/services/provider_callback_service.py`.
- [ ] Implement service behavior.
- [ ] Run callback tests.

### Task 6: Implement Expiration Service

- [ ] Create `backend/tests/test_expiration_service.py`.
- [ ] Test overdue pending payments become `EXPIRED`.
- [ ] Test non-overdue pending payments stay pending.
- [ ] Create `backend/app/services/expiration_service.py`.
- [ ] Add repository method to find pending payments with `expire_at <= now`.
- [ ] Run expiration tests.

### Task 7: Add Provider Callback Route

- [ ] Create `backend/app/api/routes/provider_callbacks.py`.
- [ ] Add `POST /v1/provider/callbacks/payment`.
- [ ] Register route in `backend/app/main.py`.
- [ ] Keep provider auth simple for MVP; document simulator trust clearly.

### Task 8: Verification

- [ ] Run:

```powershell
cd backend
python -m unittest discover tests -v
```

- [ ] Expected: all tests pass.

### Task 9: Commit

- [ ] Stage callback and expiration files.
- [ ] Commit message suggestion:

```text
feat: add provider callback and payment expiration
```

## Acceptance Criteria

- Provider callback logs raw evidence.
- Valid callbacks update only `PENDING` payments.
- Expired payments do not revive on late success callback.
- Late/ambiguous callback creates reconciliation evidence.
- Webhook dispatch is not required until phase 06.
