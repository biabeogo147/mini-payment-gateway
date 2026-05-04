# Provider Callback And Expiration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement provider/simulator callbacks, raw callback logging, payment state transitions, and expiration handling.

**Architecture:** Provider callback controllers call a callback service that stores `BankCallbackLog`, normalizes provider status, and delegates payment state updates to the payment service. Expiration is a separate service operation that moves overdue pending payments to `EXPIRED`.

**Tech Stack:** FastAPI, SQLAlchemy, existing `BankCallbackLog`, `PaymentTransaction`, and `ReconciliationRecord` models.

---

## Implementation Status

Completed. The implementation added provider payment callbacks, callback log
persistence, payment state transitions, expiration service behavior, and phase
04 reconciliation evidence creation. Webhook event creation and ops
reconciliation review remain in later phases.

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

Do not implement:

- refund callbacks; they belong to phase 05.
- webhook event creation/delivery; phase 04 should only leave a clear service
  extension point for phase 06.
- ops review APIs; reconciliation review and resolution belong to phase 07.
- provider authentication beyond a simple trusted simulator endpoint.

## Scenario References

Use `docs/testing/scenarios/callback.md` as the behavior source for:

- `CB-01 Payment Success Callback`
- `CB-02 Payment Failed Callback`
- `CB-03 Unknown Transaction Callback`
- `CB-04 Duplicate Provider Callback`
- `EXP-01 Expire Overdue Payment`

Use `docs/testing/scenarios/reconciliation.md` as the behavior source for:

- `REC-01 Late Success Callback After Expiration`
- `REC-02 Callback Amount Mismatch`

Use `docs/testing/matrix.md` to keep the phase 04 test names aligned
with the scenario IDs.

## Current Code Map

Existing source that phase 04 should build on:

- `backend/app/controllers/payment_controller.py` shows the current thin
  controller pattern and dependency wiring.
- `backend/app/services/payment_service.py` owns create/query payment behavior.
  Phase 04 should not put callback state transition rules here; use a dedicated
  payment state machine.
- `backend/app/repositories/payment_repository.py` currently supports payment
  create/query. Phase 04 needs update helpers and an overdue-pending lookup.
- `backend/app/models/payment_transaction.py` already has `status`, `paid_at`,
  `external_reference`, `failed_reason_code`, and `failed_reason_message`.
- `backend/app/models/bank_callback_log.py` already supports raw callback
  evidence and processing result.
- `backend/app/models/reconciliation_record.py` already supports mismatch and
  pending-review evidence.
- `backend/app/models/enums.py` already contains:
  - `PaymentStatus`: `PENDING`, `SUCCESS`, `FAILED`, `EXPIRED`
  - `CallbackSourceType`: `BANK`, `NAPAS`, `SIMULATOR`, `QR_PROVIDER`
  - `CallbackType`: `PAYMENT_RESULT`, `REFUND_RESULT`
  - `CallbackProcessingResult`: `PROCESSED`, `IGNORED`, `FAILED`, `PENDING_REVIEW`
  - `ReconciliationStatus`: `MATCHED`, `MISMATCHED`, `PENDING_REVIEW`, `RESOLVED`
  - `EntityType.PAYMENT`
- Alembic migrations already create the phase 04 tables; no migration is
  expected unless implementation discovers a model/schema mismatch.

## Implementation Decisions

- Callback endpoint path: `POST /v1/provider/callbacks/payment`.
- Request status values accepted by the API: `SUCCESS`, `FAILED`.
- Provider source defaults to `SIMULATOR` for MVP if the request does not pass a
  source field.
- A callback log must be written for every callback request that reaches the
  service, including unknown transaction, duplicate, mismatch, and late callback
  cases.
- Only `PENDING` payments can transition to `SUCCESS`, `FAILED`, or `EXPIRED`.
- Duplicate callback with the same already-final state should return the current
  payment status and log `processing_result=IGNORED`.
- Callback amount mismatch must create a reconciliation record and must not mark
  the payment successful.
- Late success after `EXPIRED` must create a reconciliation record and must not
  revive the payment.
- Expiration service should be callable from tests or future scheduler code as
  `expire_overdue_payments(db, now)`.
- All service methods should accept optional `now` for deterministic tests.

## Callback Result Contract

Phase 04 should return a compact result shape:

```json
{
  "transaction_id": "pay_...",
  "status": "SUCCESS",
  "processing_result": "PROCESSED",
  "reconciliation_record_id": null
}
```

Unknown transaction response:

```json
{
  "transaction_id": null,
  "status": null,
  "processing_result": "PENDING_REVIEW",
  "reconciliation_record_id": null
}
```

Amount mismatch or late callback response:

```json
{
  "transaction_id": "pay_...",
  "status": "PENDING",
  "processing_result": "PENDING_REVIEW",
  "reconciliation_record_id": "rec_..."
}
```

Use existing `AppError` only for invalid API shape or unsupported provider
status. Business ambiguity should be persisted and returned as
`PENDING_REVIEW`, not raised as a server error.

## Files

- Create: `backend/app/controllers/provider_callback_controller.py`
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
- Test: `backend/tests/test_provider_callback_routes.py`

## Tasks

### Task 1: Add Payment State Machine Tests

- [ ] Create `backend/tests/test_payment_state_machine.py`.
- [ ] Test `mark_success(payment, paid_at, external_reference)`:
  - starts from `PENDING`;
  - sets `status=SUCCESS`;
  - sets `paid_at`;
  - sets `external_reference`.
- [ ] Test `mark_failed(payment, reason_code, reason_message, external_reference)`:
  - starts from `PENDING`;
  - sets `status=FAILED`;
  - sets failed reason fields;
  - sets `external_reference`.
- [ ] Test `mark_expired(payment)`:
  - starts from `PENDING`;
  - sets `status=EXPIRED`.
- [ ] Test rejected transitions raise `AppError`:
  - `EXPIRED -> SUCCESS`
  - `SUCCESS -> FAILED`
  - `FAILED -> SUCCESS`
- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_payment_state_machine -v
```

- [ ] Expected: FAIL before state machine exists.

### Task 2: Implement Payment State Machine

- [ ] Create `backend/app/services/payment_state_machine.py`.
- [ ] Implement:
  - `assert_payment_transition_allowed(current_status, target_status)`
  - `mark_success(payment, paid_at, external_reference=None)`
  - `mark_failed(payment, reason_code, reason_message, external_reference=None)`
  - `mark_expired(payment)`
- [ ] Use `AppError(error_code="PAYMENT_INVALID_STATE_TRANSITION", status_code=409)`
  for rejected transitions.
- [ ] Run state machine tests.
- [ ] Expected: PASS.

### Task 3: Define Provider Callback Schema

- [ ] Create `backend/app/schemas/provider_callback.py`.
- [ ] Define `PaymentCallbackStatus` enum:
  - `SUCCESS`
  - `FAILED`
- [ ] Define `PaymentCallbackRequest`:
  - `external_reference`
  - `transaction_reference`
  - `status`
  - `amount`
  - `paid_at` for success callbacks
  - `failed_reason_code` for failed callbacks
  - `failed_reason_message` for failed callbacks
  - `raw_payload`
  - optional `source_type`, default `SIMULATOR`
- [ ] Define `PaymentCallbackResponse` using the result contract above.
- [ ] Add schema tests in `backend/tests/test_provider_callback_service.py` or
  a separate schema test section:
  - unsupported status rejects;
  - success callback requires `paid_at`;
  - failed callback accepts failed reason fields.

### Task 4: Implement Callback Logging Repository

- [ ] Create `backend/app/repositories/bank_callback_repository.py`.
- [ ] Implement `create_payment_callback_log(...)` for `BankCallbackLog`.
- [ ] Accept source type, external reference, transaction reference, raw payload,
  normalized status, received timestamp, processed timestamp, processing result,
  and optional error message.
- [ ] Ensure raw payload is persisted.
- [ ] Add a small repository unit test with fake DB to verify `add()` and
  `flush()` are called.

### Task 5: Implement Reconciliation Repository

- [ ] Create `backend/app/repositories/reconciliation_repository.py`.
- [ ] Implement `create_payment_reconciliation_record(...)`.
- [ ] Persist:
  - `entity_type=PAYMENT`
  - `entity_id=payment.id`
  - internal/external status
  - internal/external amount
  - `match_result`
  - mismatch reason code/message.
- [ ] Add a small repository unit test with fake DB to verify `add()` and
  `flush()` are called.

### Task 6: Implement Provider Callback Service

- [ ] Create `backend/tests/test_provider_callback_service.py`.
- [ ] Test:
  - success callback marks pending payment success and sets `paid_at`.
  - failed callback marks pending payment failed.
  - unknown transaction creates callback log with `PENDING_REVIEW`.
  - duplicate same-state callback logs `IGNORED` and does not mutate payment.
  - amount mismatch creates reconciliation record and does not mark success.
  - callback after payment expired creates reconciliation record and does not revive.
- [ ] Create `backend/app/services/provider_callback_service.py`.
- [ ] Implement service behavior.
- [ ] Run callback tests.

### Task 7: Implement Expiration Service

- [ ] Create `backend/tests/test_expiration_service.py`.
- [ ] Test overdue pending payments become `EXPIRED`.
- [ ] Test non-overdue pending payments stay pending.
- [ ] Test final-state payments stay unchanged.
- [ ] Test running expiration twice is repeat-safe.
- [ ] Create `backend/app/services/expiration_service.py`.
- [ ] Add repository method to find pending payments with `expire_at <= now`.
- [ ] Add repository method to persist mutated payment rows if needed.
- [ ] Run expiration tests.

### Task 8: Add Provider Callback Controller

- [ ] Create `backend/app/controllers/provider_callback_controller.py`.
- [ ] Add `POST /v1/provider/callbacks/payment`.
- [ ] Register controller router in `backend/app/main.py`.
- [ ] Keep provider auth simple for MVP; document simulator trust clearly.
- [ ] Create `backend/tests/test_provider_callback_routes.py`.
- [ ] Test the route calls `provider_callback_service.process_payment_callback`
  with `db` and parsed request.
- [ ] Test response JSON contains `transaction_id`, `status`,
  `processing_result`, and `reconciliation_record_id`.

### Task 9: API And DB Smoke Preparation

- [ ] Decide during implementation whether to add
  `backend/scripts/smoke_provider_callback_api.py`.
- [ ] If added, the smoke script should:
  - seed an active merchant and credential.
  - create a payment through `POST /v1/payments`.
  - call `POST /v1/provider/callbacks/payment` with `SUCCESS`.
  - query the payment and verify `status=SUCCESS`.
  - query `bank_callback_logs` and verify callback evidence exists.
- [ ] If not added in phase 04, document that phase 08 owns full E2E smoke.

### Task 10: Documentation Updates

- [ ] Update `docs/testing/scenarios/callback.md` statuses for implemented callback and
  expiration behavior.
- [ ] Update `docs/testing/scenarios/reconciliation.md` for phase 04-owned
  reconciliation evidence creation.
- [ ] Update `docs/testing/matrix.md` phase 04 rows from `Planned` to
  the exact implemented coverage.
- [ ] Create `docs/history/completions/phase-04.md` after implementation.

### Task 11: Verification

- [ ] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

- [ ] Expected: all tests pass.

### Task 12: Commit

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
