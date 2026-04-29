# API Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the merchant, ops, provider callback, and webhook contracts before implementing backend behavior.

**Architecture:** API contracts live as Markdown docs first, then become FastAPI schemas and route tests in later phases. This phase deliberately avoids implementation code so business behavior is clear before service design.

**Tech Stack:** Markdown, OpenAPI terminology, FastAPI/Pydantic concepts.

---

## Scope

Create API and webhook documentation that covers the MVP:

- Merchant auth headers.
- Merchant payment API.
- Merchant refund API.
- Provider/simulator callback API.
- Internal ops API.
- Merchant webhook payloads and retry behavior.
- Standard error shape and idempotency semantics.

## Files

- Create: `plan/api/README.md`
- Create: `plan/api/merchant_api.md`
- Create: `plan/api/ops_api.md`
- Create: `plan/api/provider_callback_api.md`
- Create: `plan/api/webhook_spec.md`
- Create: `plan/api/error_catalog.md`
- Modify: `plan/6_necessary_document.md`

## Tasks

### Task 1: Create API Documentation Index

- [ ] Create `plan/api/README.md`.
- [ ] Link every API spec file.
- [ ] Add endpoint ownership:
  - Merchant-facing endpoints are authenticated with merchant HMAC.
  - Provider callback endpoints use provider/simulator trust rules.
  - Ops endpoints are internal-only.
- [ ] Add a short rule: API docs are canonical until OpenAPI generation is added.

### Task 2: Define Standard Error Shape

- [ ] Create `plan/api/error_catalog.md`.
- [ ] Define response shape:

```json
{
  "error_code": "PAYMENT_ALREADY_SUCCESS",
  "message": "Payment already succeeded for this order.",
  "request_id": "req_...",
  "details": {}
}
```

- [ ] Include error categories:
  - `AUTH_INVALID_SIGNATURE`
  - `AUTH_TIMESTAMP_EXPIRED`
  - `MERCHANT_NOT_ACTIVE`
  - `PAYMENT_PENDING_EXISTS`
  - `PAYMENT_ALREADY_SUCCESS`
  - `PAYMENT_NOT_FOUND`
  - `REFUND_NOT_ALLOWED`
  - `REFUND_WINDOW_EXPIRED`
  - `REFUND_AMOUNT_NOT_FULL`
  - `WEBHOOK_EVENT_NOT_FOUND`
  - `VALIDATION_ERROR`

### Task 3: Define Merchant Payment API

- [ ] Create `plan/api/merchant_api.md`.
- [ ] Document headers:
  - `X-Merchant-Id`
  - `X-Access-Key`
  - `X-Signature`
  - `X-Timestamp`
  - optional `X-Idempotency-Key`
- [ ] Document `POST /v1/payments`.
- [ ] Document `GET /v1/payments/{transaction_id}`.
- [ ] Document query fallback by order id:
  - `GET /v1/payments/by-order/{order_id}`
- [ ] Document duplicate create-payment behavior:
  - current `PENDING` and semantically identical request returns existing transaction.
  - prior `FAILED` or `EXPIRED` allows a new payment attempt.
  - prior `SUCCESS` rejects the new payment.

### Task 4: Define Merchant Refund API

- [ ] In `plan/api/merchant_api.md`, document `POST /v1/refunds`.
- [ ] Document `GET /v1/refunds/{refund_transaction_id}`.
- [ ] Document query by merchant refund id:
  - `GET /v1/refunds/by-refund-id/{refund_id}`
- [ ] Document refund rules:
  - original payment must be `SUCCESS`.
  - full refund only.
  - refund window is 7 days from `paid_at`.
  - duplicate `merchant_id + refund_id` returns existing refund.

### Task 5: Define Provider Callback API

- [ ] Create `plan/api/provider_callback_api.md`.
- [ ] Document `POST /v1/provider/callbacks/payment`.
- [ ] Document `POST /v1/provider/callbacks/refund`.
- [ ] Include raw payload persistence requirement in `BankCallbackLog`.
- [ ] Include late callback rule:
  - if payment is already `EXPIRED`, do not revive it.
  - create reconciliation evidence instead.

### Task 6: Define Ops API

- [ ] Create `plan/api/ops_api.md`.
- [ ] Document internal endpoints:
  - create merchant.
  - create/update onboarding case.
  - approve/reject onboarding.
  - activate/suspend/disable merchant.
  - rotate credential.
  - inspect payment/refund/webhook/reconciliation.
  - retry webhook manually.
- [ ] Mark auth as internal-only for this MVP.
- [ ] Mark UI as out of scope.

### Task 7: Define Webhook Spec

- [ ] Create `plan/api/webhook_spec.md`.
- [ ] Define event types:
  - `payment.succeeded`
  - `payment.failed`
  - `payment.expired`
  - `refund.succeeded`
  - `refund.failed`
- [ ] Define payload envelope:

```json
{
  "event_id": "evt_...",
  "event_type": "payment.succeeded",
  "merchant_id": "m_...",
  "entity_type": "PAYMENT",
  "entity_id": "uuid",
  "created_at": "2026-04-29T00:00:00Z",
  "data": {}
}
```

- [ ] Define delivery behavior:
  - HTTP 2xx means delivered.
  - retry schedule is 1 minute, 5 minutes, 15 minutes.
  - total attempts is 4.
  - manual retry is internal-only.

### Task 8: Verification

- [ ] Check that all planned MVP APIs are documented.
- [ ] Check that no out-of-scope endpoint was introduced.
- [ ] Run:

```powershell
rg -n "POST /v1/payments|POST /v1/refunds|provider/callbacks|payment.succeeded|AUTH_INVALID_SIGNATURE" plan/api
```

- [ ] Expected: all key API terms are found.

## Acceptance Criteria

- API docs cover every in-scope actor interaction from `plan/7_usecase_diagram.md`.
- Payment, refund, callback, webhook, and ops behavior is documented before code.
- The error catalog is reusable by route and service tests.
- No implementation code is added in this phase.
