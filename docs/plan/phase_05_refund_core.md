# Refund Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement full refund creation, refund status query, and provider refund result callbacks.

**Architecture:** Refund controllers authenticate the merchant and call a refund service. The refund service validates original payment eligibility, enforces refund idempotency, creates `RefundTransaction`, and delegates provider result transitions to a refund state machine. Provider refund callbacks reuse the phase 04 callback evidence and reconciliation pattern.

**Tech Stack:** FastAPI, SQLAlchemy, existing payment/refund models, existing HMAC auth dependency, standard `unittest` test suite.

---

## Implementation Status

Ready for implementation. No phase 05 application code has been added yet.
Models, enums, migrations, merchant auth, payment core, provider payment
callbacks, callback evidence logging, and payment reconciliation evidence are
already in place.

Use the current repository checkout directly. Do not create a branch or
worktree unless the user asks for one. Commit only when requested.

## Scope

Implement:

- `POST /v1/refunds`
- `GET /v1/refunds/by-refund-id/{refund_id}`
- `GET /v1/refunds/{refund_transaction_id}`
- `POST /v1/provider/callbacks/refund`
- refund callback evidence logging.
- refund reconciliation evidence for amount mismatch or final-state conflict.
- smoke script that runs the merchant payment-to-refund path against the API and
  verifies DB effects.

Do not implement:

- partial refunds.
- settlement, ledger, dispute, payout, or multi-provider routing.
- webhook event creation/delivery; phase 06 owns webhook events for refund final
  states.
- ops reconciliation review/resolution APIs; phase 07 owns review workflows.
- provider-grade callback signing; trusted simulator/provider traffic remains
  acceptable for MVP.

## Scenario References

Use `docs/scenarios/refund.md` as the behavior source for:

- `REF-01 Full Refund Request For Successful Payment`
- `REF-02 Refund Query By Transaction Id`
- `REF-03 Refund Query By Merchant Refund Id`
- `REF-04 Provider Refund Success Callback`
- `REF-05 Provider Refund Failed Callback`
- `REF-06 Partial Refund Rejects`
- `REF-07 Refund After 7-Day Window Rejects`
- `REF-08 Duplicate Refund Id Returns Existing Refund`
- `REF-09 Refund Against Non-Success Payment Rejects`

Use `docs/scenarios/reconciliation.md` for refund callback mismatch behavior by
extending the same evidence-first pattern already used by phase 04.

Use `docs/scenarios/testing_matrix.md` to keep the phase 05 test names aligned
with the scenario IDs.

## Current Code Map

Existing source that phase 05 should build on:

- `backend/app/controllers/payment_controller.py` shows the thin controller and
  dependency wiring style for merchant-authenticated APIs.
- `backend/app/controllers/provider_callback_controller.py` already exposes
  `POST /v1/provider/callbacks/payment`; extend this controller with refund
  callback routing.
- `backend/app/services/payment_service.py` shows service-layer business rule
  style, idempotency checks, repository usage, and `AppError` usage.
- `backend/app/services/provider_callback_service.py` already handles callback
  evidence, duplicate callbacks, amount mismatch, and final-state conflicts for
  payments. Extend it with refund callback behavior without moving payment
  rules into controllers.
- `backend/app/services/merchant_readiness_service.py` already has
  `assert_can_create_refund(merchant)`.
- `backend/app/repositories/payment_repository.py` already supports payment
  lookup by transaction id and latest merchant order.
- `backend/app/repositories/bank_callback_repository.py` currently has
  `create_payment_callback_log(...)`; add a refund-specific log helper using
  `CallbackType.REFUND_RESULT`.
- `backend/app/repositories/reconciliation_repository.py` currently has
  `create_payment_reconciliation_record(...)`; add a refund-specific helper
  using `EntityType.REFUND`.
- `backend/app/models/refund_transaction.py` already has:
  - unique `refund_transaction_id`;
  - unique `merchant_db_id + refund_id`;
  - partial unique index for one `REFUNDED` row per payment;
  - `external_reference`, `processed_at`, and failed reason fields.
- `backend/app/models/enums.py` already has `RefundStatus`,
  `CallbackType.REFUND_RESULT`, `CallbackProcessingResult`, and
  `EntityType.REFUND`.
- Alembic migrations already create `refund_transactions`; no migration is
  expected unless implementation discovers a model/schema mismatch.

## Implementation Decisions

- Merchant refund endpoints require the existing HMAC auth dependency.
- `CreateRefundRequest` accepts exactly one original payment selector:
  `original_transaction_id` or `order_id`.
- `order_id` resolution uses the latest payment for the authenticated merchant
  order and requires that payment to be `SUCCESS`.
- Original payment must belong to the authenticated merchant.
- Original payment must be `SUCCESS` and must have `paid_at`; otherwise reject
  with `PAYMENT_NOT_REFUNDABLE`.
- Refund window is inclusive: a refund is allowed when
  `now <= payment.paid_at + 7 days`.
- Full refund only: `refund_amount` must equal `payment.amount`; otherwise
  reject with `REFUND_AMOUNT_NOT_FULL`.
- Duplicate `merchant_db_id + refund_id` with the same semantic request returns
  the existing refund.
- A conflicting duplicate `merchant_db_id + refund_id` rejects with
  `REFUND_NOT_ALLOWED`.
- For semantic duplicate checks, compare original payment id, refund amount, and
  reason. The optional `X-Idempotency-Key` is stored but is not the business
  uniqueness key.
- A payment can have only one active/successful refund attempt. Reject a new
  refund for the same payment if an existing refund is `REFUND_PENDING` or
  `REFUNDED`.
- A prior `REFUND_FAILED` row does not block a new refund request with a new
  `refund_id`.
- Payment status remains `SUCCESS` after a refund is `REFUNDED`.
- Refund route order must register `/by-refund-id/{refund_id}` before
  `/{refund_transaction_id}` so the static route is not shadowed.
- Provider refund callback request status values are `SUCCESS` and `FAILED`.
  The service maps them to `REFUNDED` and `REFUND_FAILED`.
- Provider refund callback request field for the internal refund id is
  `refund_transaction_id`; the callback log stores this value in
  `BankCallbackLog.transaction_reference`.
- Successful refund callbacks require `processed_at`. Failed refund callbacks may
  omit it and use service `now`.
- Every refund callback that reaches the service writes a `bank_callback_logs`
  row, including unknown refund, duplicate, mismatch, and conflict cases.
- Unknown refund callbacks return `processing_result=PENDING_REVIEW` with no
  refund status and no reconciliation record.
- Amount mismatch creates refund reconciliation evidence and does not mutate the
  refund.
- Callback conflict against a final refund state creates refund reconciliation
  evidence and does not mutate the refund.
- Duplicate same-state callback logs `IGNORED` and returns the current refund
  status.
- All service methods should accept optional `now` for deterministic tests.

## API Contracts

### Create Refund

Request:

```json
{
  "original_transaction_id": "pay_...",
  "refund_id": "REF-1001",
  "refund_amount": "100000.00",
  "reason": "Customer requested refund"
}
```

Alternative selector:

```json
{
  "order_id": "ORDER-1001",
  "refund_id": "REF-1001",
  "refund_amount": "100000.00",
  "reason": "Customer requested refund"
}
```

Response:

```json
{
  "refund_transaction_id": "rfnd_...",
  "original_transaction_id": "pay_...",
  "refund_id": "REF-1001",
  "refund_amount": "100000.00",
  "refund_status": "REFUND_PENDING"
}
```

### Refund Callback

Success request:

```json
{
  "external_reference": "bank_ref_refund_1001",
  "refund_transaction_id": "rfnd_...",
  "status": "SUCCESS",
  "amount": "100000.00",
  "processed_at": "2026-04-29T10:05:00Z",
  "source_type": "SIMULATOR",
  "raw_payload": {
    "provider_status": "00"
  }
}
```

Failed request:

```json
{
  "external_reference": "bank_ref_refund_1001",
  "refund_transaction_id": "rfnd_...",
  "status": "FAILED",
  "amount": "100000.00",
  "failed_reason_code": "BANK_REJECTED",
  "failed_reason_message": "Bank rejected refund.",
  "raw_payload": {
    "provider_status": "05"
  }
}
```

Processed response:

```json
{
  "refund_transaction_id": "rfnd_...",
  "refund_status": "REFUNDED",
  "processing_result": "PROCESSED",
  "reconciliation_record_id": null
}
```

Unknown refund response:

```json
{
  "refund_transaction_id": null,
  "refund_status": null,
  "processing_result": "PENDING_REVIEW",
  "reconciliation_record_id": null
}
```

Mismatch or conflict response:

```json
{
  "refund_transaction_id": "rfnd_...",
  "refund_status": "REFUND_PENDING",
  "processing_result": "PENDING_REVIEW",
  "reconciliation_record_id": "rec_..."
}
```

## Files

- Create: `backend/app/controllers/refund_controller.py`
- Create: `backend/app/repositories/refund_repository.py`
- Create: `backend/app/schemas/refund.py`
- Create: `backend/app/services/refund_service.py`
- Create: `backend/app/services/refund_state_machine.py`
- Create: `backend/scripts/smoke_refund_api.py`
- Modify: `backend/app/controllers/provider_callback_controller.py`
- Modify: `backend/app/repositories/bank_callback_repository.py`
- Modify: `backend/app/repositories/payment_repository.py`
- Modify: `backend/app/repositories/reconciliation_repository.py`
- Modify: `backend/app/schemas/provider_callback.py`
- Modify: `backend/app/services/provider_callback_service.py`
- Modify: `backend/app/main.py`
- Modify: `docs/api/error_catalog.md`
- Modify: `docs/api/merchant_api.md`
- Modify: `docs/api/provider_callback_api.md`
- Modify: `docs/plan/README.md`
- Modify: `docs/scenarios/refund.md`
- Modify: `docs/scenarios/reconciliation.md`
- Modify: `docs/scenarios/testing_matrix.md`
- Create: `docs/plan/phase_05_completion.md`
- Test: `backend/tests/test_refund_state_machine.py`
- Test: `backend/tests/test_refund_service.py`
- Test: `backend/tests/test_refund_routes.py`
- Test: `backend/tests/test_provider_callback_service.py`
- Test: `backend/tests/test_provider_callback_routes.py`

## Tasks

### Task 0: Baseline Check

- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

- [ ] Expected: existing phase 0-4 tests pass before phase 05 edits.

### Task 1: Add Refund State Machine Tests

- [ ] Create `backend/tests/test_refund_state_machine.py`.
- [ ] Test `mark_refunded(refund, processed_at, external_reference)`:
  - starts from `REFUND_PENDING`;
  - sets `status=REFUNDED`;
  - sets `processed_at`;
  - sets `external_reference`.
- [ ] Test `mark_refund_failed(refund, reason_code, reason_message, external_reference, processed_at)`:
  - starts from `REFUND_PENDING`;
  - sets `status=REFUND_FAILED`;
  - sets failed reason fields;
  - sets `processed_at`;
  - sets `external_reference`.
- [ ] Test rejected transitions raise `AppError`:
  - `REFUNDED -> REFUND_FAILED`;
  - `REFUND_FAILED -> REFUNDED`;
  - `REFUNDED -> REFUNDED` through mutation helper.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_refund_state_machine -v
```

- [ ] Expected: FAIL before state machine exists.

### Task 2: Implement Refund State Machine

- [ ] Create `backend/app/services/refund_state_machine.py`.
- [ ] Implement:
  - `assert_refund_transition_allowed(current_status, target_status)`;
  - `mark_refunded(refund, processed_at, external_reference=None)`;
  - `mark_refund_failed(refund, reason_code, reason_message=None, external_reference=None, processed_at=None)`.
- [ ] Use `AppError(error_code="REFUND_INVALID_STATE_TRANSITION", status_code=409)`
  for rejected transitions.
- [ ] Run state machine tests.
- [ ] Expected: PASS.

### Task 3: Define Refund Schemas And Tests

- [ ] Create or add schema tests in `backend/tests/test_refund_service.py`.
- [ ] Test `CreateRefundRequest`:
  - accepts `original_transaction_id`;
  - accepts `order_id`;
  - rejects both selectors together;
  - rejects neither selector;
  - normalizes `refund_amount` as `Decimal`.
- [ ] Create `backend/app/schemas/refund.py`.
- [ ] Define:
  - `CreateRefundRequest`;
  - `RefundResponse`;
  - `RefundStatusResponse`.
- [ ] Request fields:
  - `original_transaction_id: str | None`;
  - `order_id: str | None`;
  - `refund_id: str`;
  - `refund_amount: Decimal`;
  - `reason: str`.
- [ ] Response fields:
  - `refund_transaction_id`;
  - `original_transaction_id`;
  - `refund_id`;
  - `refund_amount`;
  - `refund_status`.
- [ ] Add `from_refund(refund, original_payment)` helper to mirror payment
  response construction.

### Task 4: Add Refund Repository

- [ ] Create repository tests in `backend/tests/test_refund_service.py`.
- [ ] Create `backend/app/repositories/refund_repository.py`.
- [ ] Implement:
  - `get_by_refund_transaction_id(db, refund_transaction_id)`;
  - `get_by_merchant_refund_id(db, merchant_db_id, refund_id)`;
  - `get_by_payment_and_statuses(db, payment_transaction_id, statuses)`;
  - `create(db, refund_transaction_id, merchant_db_id, payment_transaction_id, refund_id, refund_amount, reason, idempotency_key=None)`;
  - `save(db, refund)`.
- [ ] Repository `create()` should set `status=RefundStatus.REFUND_PENDING`.
- [ ] Tests should verify fake DB `add()` and `flush()` are called.

### Task 5: Add Payment Repository Helper

- [ ] Modify `backend/app/repositories/payment_repository.py`.
- [ ] Add:
  - `get_success_by_merchant_order(db, merchant_db_id, order_id)`.
- [ ] This helper should return the latest `SUCCESS` payment for that merchant
  order, ordered by `created_at desc`, then `transaction_id desc`.
- [ ] Add a unit-level fake store/service test that proves `order_id` refund
  resolution does not return non-success payments.

### Task 6: Write Refund Service Tests

- [ ] Create `backend/tests/test_refund_service.py`.
- [ ] Test `REF-01`: successful payment can create `REFUND_PENDING`.
- [ ] Test `REF-01`: request by `order_id` resolves the merchant successful
  payment.
- [ ] Test `REF-06`: partial amount rejects with `REFUND_AMOUNT_NOT_FULL`.
- [ ] Test `REF-07`: after the 7-day window rejects with
  `REFUND_WINDOW_EXPIRED`.
- [ ] Test `REF-08`: duplicate `merchant_db_id + refund_id` with same semantic
  content returns existing refund and does not create a new row.
- [ ] Test `REF-08`: conflicting duplicate refund id rejects with
  `REFUND_NOT_ALLOWED`.
- [ ] Test `REF-09`: `PENDING`, `FAILED`, and `EXPIRED` payments reject with
  `PAYMENT_NOT_REFUNDABLE`.
- [ ] Test a `SUCCESS` payment with missing `paid_at` rejects with
  `PAYMENT_NOT_REFUNDABLE`.
- [ ] Test an existing `REFUND_PENDING` or `REFUNDED` refund for the same payment
  blocks a new refund id.
- [ ] Test a prior `REFUND_FAILED` refund does not block a new refund id.
- [ ] Test `REF-02`: query by refund transaction id returns only owned refunds.
- [ ] Test `REF-03`: query by merchant refund id returns only owned refunds.
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_refund_service -v
```

- [ ] Expected: FAIL before service exists.

### Task 7: Implement Refund Service

- [ ] Create `backend/app/services/refund_service.py`.
- [ ] Implement:
  - `create_refund(db, authenticated_merchant, request, idempotency_key, now=None)`;
  - `get_refund_by_transaction_id(db, authenticated_merchant, refund_transaction_id)`;
  - `get_refund_by_refund_id(db, authenticated_merchant, refund_id)`.
- [ ] Reuse `assert_can_create_refund(authenticated_merchant.merchant)`.
- [ ] Resolve original payment by `original_transaction_id` or `order_id`.
- [ ] Use `_new_refund_transaction_id()` that returns `rfnd_{uuid4().hex}`.
- [ ] Use `AppError` consistently:
  - `PAYMENT_NOT_FOUND` for missing original payment selector target;
  - `PAYMENT_NOT_REFUNDABLE` for non-success or missing `paid_at`;
  - `REFUND_AMOUNT_NOT_FULL` for non-full refund;
  - `REFUND_WINDOW_EXPIRED` for window failure;
  - `REFUND_NOT_ALLOWED` for duplicate conflict or active refund conflict;
  - `REFUND_NOT_FOUND` for missing/foreign refund queries.
- [ ] Commit DB transaction after creating a new refund.
- [ ] Return schema responses from model helpers.
- [ ] Run refund service tests.
- [ ] Expected: PASS.

### Task 8: Add Refund Controller And Routes

- [ ] Create `backend/tests/test_refund_routes.py`.
- [ ] Test `POST /v1/refunds` calls `refund_service.create_refund(...)` with:
  - `db`;
  - authenticated merchant;
  - parsed request;
  - `X-Idempotency-Key`.
- [ ] Test `GET /v1/refunds/by-refund-id/{refund_id}` calls the correct service
  method and is not shadowed by transaction lookup.
- [ ] Test `GET /v1/refunds/{refund_transaction_id}` calls transaction lookup.
- [ ] Create `backend/app/controllers/refund_controller.py`.
- [ ] Register routes in this order:
  - `POST /v1/refunds`;
  - `GET /v1/refunds/by-refund-id/{refund_id}`;
  - `GET /v1/refunds/{refund_transaction_id}`.
- [ ] Register router in `backend/app/main.py`.
- [ ] Run route tests.
- [ ] Expected: PASS.

### Task 9: Add Refund Callback Schemas And Tests

- [ ] Extend `backend/tests/test_provider_callback_service.py`.
- [ ] Test `RefundCallbackRequest`:
  - supports `SUCCESS` and `FAILED`;
  - rejects unsupported statuses;
  - success callback requires `processed_at`;
  - defaults `source_type=SIMULATOR`.
- [ ] Extend `backend/app/schemas/provider_callback.py`.
- [ ] Define:
  - `RefundCallbackStatus`: `SUCCESS`, `FAILED`;
  - `RefundCallbackRequest`;
  - `RefundCallbackResponse`.
- [ ] Response fields:
  - `refund_transaction_id: str | None`;
  - `refund_status: RefundStatus | None`;
  - `processing_result: CallbackProcessingResult`;
  - `reconciliation_record_id: str | None`.
- [ ] Run provider callback schema tests.

### Task 10: Extend Callback And Reconciliation Repositories

- [ ] Extend `backend/app/repositories/bank_callback_repository.py`.
- [ ] Add `create_refund_callback_log(...)` with the same shape as payment
  callback logging but `callback_type=CallbackType.REFUND_RESULT`.
- [ ] Extend `backend/app/repositories/reconciliation_repository.py`.
- [ ] Add `create_refund_reconciliation_record(...)` using:
  - `entity_type=EntityType.REFUND`;
  - `entity_id=refund.id`;
  - internal/external status;
  - internal/external amount;
  - match result;
  - mismatch reason code/message.
- [ ] Add repository fake-DB tests for both helpers.

### Task 11: Implement Refund Provider Callback Service

- [ ] Extend `backend/tests/test_provider_callback_service.py`.
- [ ] Test `REF-04`: success callback moves `REFUND_PENDING -> REFUNDED`,
  sets `processed_at`, sets `external_reference`, logs `PROCESSED`.
- [ ] Test `REF-05`: failed callback moves `REFUND_PENDING -> REFUND_FAILED`,
  sets failed reason fields, logs `PROCESSED`.
- [ ] Test unknown refund logs `PENDING_REVIEW` and returns null refund fields.
- [ ] Test duplicate same-state callback logs `IGNORED` and does not mutate.
- [ ] Test amount mismatch creates refund reconciliation evidence and does not
  mutate.
- [ ] Test final-state conflict creates refund reconciliation evidence and does
  not mutate.
- [ ] Extend `backend/app/services/provider_callback_service.py`.
- [ ] Implement `process_refund_callback(db, request, now=None)`.
- [ ] Reuse `refund_state_machine` for state mutation.
- [ ] Persist with `refund_repository.save(db, refund)`.
- [ ] Log every callback through `create_refund_callback_log(...)`.
- [ ] Return the refund callback result contract.
- [ ] Run provider callback service tests.

### Task 12: Add Refund Callback Route

- [ ] Extend `backend/tests/test_provider_callback_routes.py`.
- [ ] Test `POST /v1/provider/callbacks/refund` calls
  `provider_callback_service.process_refund_callback(...)` with `db` and parsed
  request.
- [ ] Extend `backend/app/controllers/provider_callback_controller.py`.
- [ ] Add:
  - `POST /v1/provider/callbacks/refund`.
- [ ] Run provider callback route tests.

### Task 13: API And DB Smoke

- [ ] Create `backend/scripts/smoke_refund_api.py`.
- [ ] The script should run against real Postgres and an in-process uvicorn
  server, following the phase 04 smoke style.
- [ ] Flow:
  - seed an active merchant and credential;
  - create a payment through `POST /v1/payments`;
  - send payment success callback through `POST /v1/provider/callbacks/payment`;
  - create a refund through `POST /v1/refunds`;
  - send refund success callback through `POST /v1/provider/callbacks/refund`;
  - query refund by transaction id;
  - query refund by merchant refund id;
  - verify `payment_transactions.status` remains `SUCCESS`;
  - verify `refund_transactions.status=REFUNDED`;
  - verify a `bank_callback_logs` row exists with `callback_type=REFUND_RESULT`;
  - print compact JSON evidence.
- [ ] Run after migrations:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m alembic upgrade head
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_refund_api.py
```

- [ ] Expected: JSON output proves API responses and DB rows agree.

### Task 14: Documentation Updates

- [ ] Update `docs/api/merchant_api.md` if implementation fields differ from
  the contract above.
- [ ] Update `docs/api/provider_callback_api.md` so refund callback docs use
  `refund_transaction_id`, request status `SUCCESS`/`FAILED`, and response
  `refund_status`.
- [ ] Update `docs/api/error_catalog.md` with
  `REFUND_INVALID_STATE_TRANSITION`.
- [ ] Update `docs/scenarios/refund.md` statuses for implemented refund
  scenarios.
- [ ] Update `docs/scenarios/reconciliation.md` with refund callback mismatch
  evidence if implemented.
- [ ] Update `docs/scenarios/testing_matrix.md` phase 05 rows from `Planned` to
  implemented coverage.
- [ ] Update `docs/plan/README.md` standard verification commands with
  `scripts\smoke_refund_api.py`.
- [ ] Create `docs/plan/phase_05_completion.md` with:
  - completed scope;
  - tests run;
  - smoke output;
  - remaining phase 06/07 notes.

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

- [ ] Only if the user asks for a commit, stage refund files and commit.
- [ ] Commit message suggestion:

```text
feat: add full refund flow
```

## Acceptance Criteria

- Merchant can create and query full refunds.
- Refund rules match `docs/3_requirement.md` and `docs/scenarios/refund.md`.
- Refund creation is idempotent by `merchant_db_id + refund_id`.
- Partial refunds are rejected.
- Refunds outside the 7-day paid window are rejected.
- Only successful payments can be refunded.
- Provider refund callbacks update only `REFUND_PENDING` refunds.
- Duplicate refund callbacks are logged and ignored.
- Refund amount mismatch and final-state conflicts produce reviewable
  reconciliation evidence.
- Payment state remains `SUCCESS` after refund succeeds.
- API docs, scenario docs, testing matrix, and completion docs are updated after
  implementation.
