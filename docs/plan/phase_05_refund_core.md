# Refund Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement full refund creation, refund status query, and refund provider result updates.

**Architecture:** Refund controllers authenticate the merchant and call a refund service. The refund service validates original payment eligibility, enforces `merchant_id + refund_id` idempotency, creates `RefundTransaction`, and applies refund state transitions.

**Tech Stack:** FastAPI, SQLAlchemy, existing payment/refund models, HMAC auth dependency.

---

## Scope

Implement:

- `POST /v1/refunds`
- `GET /v1/refunds/{refund_transaction_id}`
- `GET /v1/refunds/by-refund-id/{refund_id}`
- `POST /v1/provider/callbacks/refund`

No partial refunds. No settlement or ledger.

## Files

- Create: `backend/app/controllers/refund_controller.py`
- Create: `backend/app/repositories/refund_repository.py`
- Create: `backend/app/schemas/refund.py`
- Create: `backend/app/services/refund_service.py`
- Create: `backend/app/services/refund_state_machine.py`
- Modify: `backend/app/controllers/provider_callback_controller.py`
- Modify: `backend/app/schemas/provider_callback.py`
- Modify: `backend/app/services/provider_callback_service.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_refund_service.py`
- Test: `backend/tests/test_refund_routes.py`
- Test: `backend/tests/test_refund_state_machine.py`

## Business Rules

- Only `SUCCESS` payments can be refunded.
- Full refund only; `refund_amount` must equal payment amount.
- Refund window is 7 days from `paid_at`.
- Refund is unique by `merchant_id + refund_id`.
- More than one `REFUNDED` refund per payment is blocked by DB and service.
- Payment remains `SUCCESS` after refund succeeds.

## Tasks

### Task 1: Add Refund State Machine Tests

- [ ] Create `backend/tests/test_refund_state_machine.py`.
- [ ] Test allowed:
  - `REFUND_PENDING -> REFUNDED`
  - `REFUND_PENDING -> REFUND_FAILED`
- [ ] Test rejected:
  - `REFUNDED -> REFUND_FAILED`
  - `REFUND_FAILED -> REFUNDED`
- [ ] Run:

```powershell
cd backend
python -m unittest tests.test_refund_state_machine -v
```

- [ ] Expected: FAIL before state machine exists.

### Task 2: Implement Refund State Machine

- [ ] Create `backend/app/services/refund_state_machine.py`.
- [ ] Implement transition assertion and mutation helpers.
- [ ] Run state machine tests.
- [ ] Expected: PASS.

### Task 3: Define Refund Schemas

- [ ] Create `backend/app/schemas/refund.py`.
- [ ] Define:
  - `CreateRefundRequest`
  - `RefundResponse`
  - `RefundStatusResponse`
- [ ] Request fields:
  - `original_transaction_id` or `order_id`
  - `refund_id`
  - `refund_amount`
  - `reason`
- [ ] Response fields:
  - `refund_transaction_id`
  - `original_transaction_id`
  - `refund_id`
  - `refund_amount`
  - `refund_status`

### Task 4: Add Refund Repository

- [ ] Create `backend/app/repositories/refund_repository.py`.
- [ ] Add:
  - `get_by_refund_transaction_id(db, refund_transaction_id)`
  - `get_by_merchant_refund_id(db, merchant_db_id, refund_id)`
  - `get_refunded_by_payment(db, payment_transaction_id)`
  - `create(db, ...)`

### Task 5: Implement Refund Service Tests

- [ ] Create `backend/tests/test_refund_service.py`.
- [ ] Test:
  - successful payment can create refund pending.
  - non-success payment rejects refund.
  - partial amount rejects refund.
  - refund after 7-day window rejects.
  - duplicate `merchant_id + refund_id` returns existing refund.
  - existing `REFUNDED` row blocks another successful refund for same payment.
  - query by refund transaction id works.
  - query by refund id works.
- [ ] Run:

```powershell
cd backend
python -m unittest tests.test_refund_service -v
```

- [ ] Expected: FAIL before service exists.

### Task 6: Implement Refund Service

- [ ] Create `backend/app/services/refund_service.py`.
- [ ] Implement `create_refund(...)`.
- [ ] Implement query methods.
- [ ] Reuse merchant auth/readiness from phase 02.
- [ ] Run refund service tests.
- [ ] Expected: PASS.

### Task 7: Add Refund Controller

- [ ] Create `backend/app/controllers/refund_controller.py`.
- [ ] Add:
  - `POST /v1/refunds`
  - `GET /v1/refunds/{refund_transaction_id}`
  - `GET /v1/refunds/by-refund-id/{refund_id}`
- [ ] Register in `backend/app/main.py`.
- [ ] Add route tests.

### Task 8: Add Refund Provider Callback

- [ ] Extend `backend/app/schemas/provider_callback.py`.
- [ ] Extend `backend/app/controllers/provider_callback_controller.py` with:
  - `POST /v1/provider/callbacks/refund`
- [ ] Extend provider callback service to mark refund `REFUNDED` or `REFUND_FAILED`.
- [ ] Log callback evidence.
- [ ] Run tests.

### Task 9: Verification

- [ ] Run:

```powershell
cd backend
python -m unittest discover tests -v
```

- [ ] Expected: all tests pass.

### Task 10: Commit

- [ ] Stage refund files.
- [ ] Commit message suggestion:

```text
feat: add full refund flow
```

## Acceptance Criteria

- Merchant can create and query full refunds.
- Refund rules match `plan/3_requirement.md`.
- Provider refund callbacks update refund state.
- Payment state remains `SUCCESS` after refund succeeds.
