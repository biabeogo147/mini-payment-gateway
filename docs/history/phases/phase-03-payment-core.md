# Payment Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement create dynamic QR payment and get payment status for merchant backends.

**Architecture:** Payment controllers authenticate the merchant, validate request schemas, and call a payment service. The service enforces business idempotency, creates or reuses `OrderReference`, creates `PaymentTransaction` in `PENDING`, generates QR content, and exposes status query methods.

**Tech Stack:** FastAPI, SQLAlchemy repositories, Pydantic schemas, existing payment/order models.

---

## Implementation Status

Completed. The implementation added payment schemas, deterministic QR content,
order/payment repositories, payment service rules, merchant payment controller,
and route/service tests.

Verification commands used:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_payment_service -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_payment_routes -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_payment_api.py
```

## Scope

Implement the first working merchant-facing payment slice:

- `POST /v1/payments`
- `GET /v1/payments/{transaction_id}`
- `GET /v1/payments/by-order/{order_id}`

No provider callback or webhook delivery in this phase.

## Files

- Create: `backend/app/controllers/payment_controller.py`
- Create: `backend/app/repositories/order_reference_repository.py`
- Create: `backend/app/repositories/payment_repository.py`
- Create: `backend/app/schemas/payment.py`
- Create: `backend/app/services/payment_service.py`
- Create: `backend/app/services/qr_service.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_payment_service.py`
- Test: `backend/tests/test_payment_routes.py`

## Business Rules

- Create payment requires authenticated active merchant.
- `INITIATED` is never persisted.
- New transaction starts directly as `PENDING`.
- One active payment means one `PENDING` payment per `merchant_id + order_id`.
- Duplicate create-payment for the current `PENDING` order returns existing transaction if semantically identical.
- New payment for same order is allowed only after prior payment is `FAILED` or `EXPIRED`.
- New payment for same order is rejected after prior payment is `SUCCESS`.

## Tasks

### Task 1: Define Payment Schemas

- [x] Write failing schema tests in `backend/tests/test_payment_service.py`.
- [x] Create `backend/app/schemas/payment.py`.
- [x] Define:
  - `CreatePaymentRequest`
  - `PaymentResponse`
  - `PaymentStatusResponse`
- [x] Required request fields:
  - `order_id`
  - `amount`
  - `description`
  - either `expire_at` or `ttl_seconds`
  - optional `metadata`
- [x] Response fields:
  - `transaction_id`
  - `order_id`
  - `merchant_id`
  - `qr_content`
  - `qr_image_url`
  - `qr_image_base64`
  - `status`
  - `expire_at`
- [x] Run schema tests.

### Task 2: Add QR Service

- [x] Create `backend/app/services/qr_service.py`.
- [x] Implement deterministic MVP QR content:

```text
MINI_GATEWAY|merchant_id={merchant_id}|transaction_id={transaction_id}|amount={amount}|currency={currency}
```

- [x] Add tests that assert QR contains merchant id, transaction id, amount, and currency.

### Task 3: Add Repositories

- [x] Create `backend/app/repositories/order_reference_repository.py`.
- [x] Add:
  - `get_by_merchant_and_order(db, merchant_db_id, order_id)`
  - `create(db, merchant_db_id, order_id)`
  - `set_latest_payment(db, order_reference, payment_transaction_id)`
- [x] Create `backend/app/repositories/payment_repository.py`.
- [x] Add:
  - `get_by_transaction_id(db, transaction_id)`
  - `get_latest_by_merchant_order(db, merchant_db_id, order_id)`
  - `get_pending_by_merchant_order(db, merchant_db_id, order_id)`
  - `create(db, ...)`
- [x] Add repository tests where practical.

### Task 4: Implement Payment Service Tests

- [x] Add tests in `backend/tests/test_payment_service.py`:
  - create payment creates order reference and pending transaction.
  - duplicate pending semantically identical returns existing transaction.
  - duplicate pending with different amount/description/expire rejects.
  - previous `FAILED` allows new attempt.
  - previous `EXPIRED` allows new attempt.
  - previous `SUCCESS` rejects new attempt.
  - query by transaction id works.
  - query by order id works.
- [x] Run:

```powershell
cd backend
python -m unittest tests.test_payment_service -v
```

- [x] Expected: FAIL before service exists.

### Task 5: Implement Payment Service

- [x] Create `backend/app/services/payment_service.py`.
- [x] Implement `create_payment(db, authenticated_merchant, request, idempotency_key)`.
- [x] Implement `get_payment_by_transaction_id(db, authenticated_merchant, transaction_id)`.
- [x] Implement `get_payment_by_order_id(db, authenticated_merchant, order_id)`.
- [x] Ensure service validates merchant ownership on reads.
- [x] Run service tests.
- [x] Expected: PASS.

### Task 6: Add Payment Controller

- [x] Create `backend/app/controllers/payment_controller.py`.
- [x] Add:
  - `POST /v1/payments`
  - `GET /v1/payments/{transaction_id}`
  - `GET /v1/payments/by-order/{order_id}`
- [x] Use `get_authenticated_merchant` dependency.
- [x] Modify `backend/app/main.py` to include the router.
- [x] Add route tests in `backend/tests/test_payment_routes.py`.

### Task 7: Verification

- [x] Run:

```powershell
cd backend
python -m unittest discover tests -v
```

- [x] Expected: all tests pass.
- [x] Optional manual smoke:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_payment_api.py
```

### Task 8: Commit

- [ ] Stage payment files.
- [ ] Commit message suggestion:

```text
feat: add merchant payment core
```

## Acceptance Criteria

- Merchant can create a dynamic QR payment.
- Payment state starts as `PENDING`.
- Idempotency and duplicate order rules match `plan/3_requirement.md`.
- Merchant can query by transaction id and order id.
- No webhook event is required yet in this phase.
