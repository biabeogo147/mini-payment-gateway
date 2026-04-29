# Webhook Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement merchant webhook event creation, payload signing, delivery attempts, retry schedule, and manual retry.

**Architecture:** Payment/refund state changes create `WebhookEvent` rows. A webhook service signs payloads, sends HTTP requests, writes `WebhookDeliveryAttempt`, updates event status and retry schedule, and exposes an internal manual retry operation.

**Tech Stack:** FastAPI, SQLAlchemy, standard-library HMAC, HTTP client dependency to be chosen (`httpx` recommended if added).

---

## Scope

Implement:

- webhook event creation for payment/refund final states.
- webhook payload signing.
- HTTP delivery attempt persistence.
- retry schedule: 1 minute, 5 minutes, 15 minutes.
- total attempts: 4.
- manual retry internal endpoint.

## Scenario References

Use `docs/scenarios/webhook.md` as the behavior source for:

- `WH-01 Payment Success Creates Webhook Event`
- `WH-02 Payment Failure Creates Webhook Event`
- `WH-03 Payment Expiration Creates Webhook Event`
- `WH-04 Refund Success Creates Webhook Event`
- `WH-05 HTTP 2xx Marks Webhook Delivered`
- `WH-06 HTTP 500 Schedules Retry`
- `WH-07 Timeout Schedules Retry`
- `WH-08 Network Error Schedules Retry`
- `WH-09 Attempt 4 Exhaustion Marks Failed`
- `WH-10 Ops Manual Retry Sends Failed Event Again`

Use `docs/scenarios/testing_matrix.md` to keep the phase 06 test names aligned
with the scenario IDs.

## Files

- Create: `backend/app/controllers/webhook_ops_controller.py`
- Create: `backend/app/repositories/webhook_repository.py`
- Create: `backend/app/schemas/webhook.py`
- Create: `backend/app/services/webhook_event_factory.py`
- Create: `backend/app/services/webhook_delivery_service.py`
- Create: `backend/app/services/webhook_retry_policy.py`
- Modify: `backend/app/services/payment_state_machine.py`
- Modify: `backend/app/services/refund_state_machine.py`
- Modify: `backend/app/services/provider_callback_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/pyproject.toml` if adding `httpx`.
- Test: `backend/tests/test_webhook_retry_policy.py`
- Test: `backend/tests/test_webhook_event_factory.py`
- Test: `backend/tests/test_webhook_delivery_service.py`

## Event Types

- `payment.succeeded`
- `payment.failed`
- `payment.expired`
- `refund.succeeded`
- `refund.failed`

## Tasks

### Task 1: Add Retry Policy Tests

- [ ] Create `backend/tests/test_webhook_retry_policy.py`.
- [ ] Test:
  - attempt 1 schedules +1 minute.
  - attempt 2 schedules +5 minutes.
  - attempt 3 schedules +15 minutes.
  - attempt 4 has no next retry and marks failure if not delivered.
- [ ] Run:

```powershell
cd backend
python -m unittest tests.test_webhook_retry_policy -v
```

- [ ] Expected: FAIL before policy exists.

### Task 2: Implement Retry Policy

- [ ] Create `backend/app/services/webhook_retry_policy.py`.
- [ ] Implement:
  - `next_retry_at(attempt_count, now)`
  - `has_attempts_remaining(attempt_count)`
  - `MAX_ATTEMPTS = 4`
- [ ] Run retry policy tests.
- [ ] Expected: PASS.

### Task 3: Implement Webhook Repository

- [ ] Create `backend/app/repositories/webhook_repository.py`.
- [ ] Add methods:
  - create event.
  - get event by event id.
  - get event by internal id.
  - create delivery attempt.
  - find due pending/failed events.
  - update status, count, last attempt, next retry.

### Task 4: Implement Event Factory

- [ ] Create `backend/tests/test_webhook_event_factory.py`.
- [ ] Test event payloads for payment and refund final states.
- [ ] Create `backend/app/services/webhook_event_factory.py`.
- [ ] Build event envelope:

```json
{
  "event_id": "evt_...",
  "event_type": "payment.succeeded",
  "merchant_id": "m_...",
  "entity_type": "PAYMENT",
  "entity_id": "uuid",
  "created_at": "iso-8601",
  "data": {}
}
```

- [ ] Run event factory tests.

### Task 5: Implement Delivery Service

- [ ] Create `backend/tests/test_webhook_delivery_service.py`.
- [ ] Use a fake HTTP client in tests.
- [ ] Test:
  - HTTP 2xx marks event `DELIVERED`.
  - HTTP 500 records failed attempt and schedules retry.
  - timeout records `TIMEOUT`.
  - network error records `NETWORK_ERROR`.
  - after 4 attempts status becomes `FAILED`.
- [ ] Create `backend/app/services/webhook_delivery_service.py`.
- [ ] Add payload signing with merchant credential secret.
- [ ] Write `WebhookDeliveryAttempt` on every send.
- [ ] Run delivery tests.

### Task 6: Hook Webhook Creation Into Payment/Refund Finalization

- [ ] Modify provider callback service so payment success/failure creates webhook event.
- [ ] Modify expiration service so payment expiration creates webhook event.
- [ ] Modify refund provider callback so refund success/failure creates webhook event.
- [ ] Keep delivery separate; event creation should not require successful HTTP delivery.

### Task 7: Add Manual Retry Controller

- [ ] Create `backend/app/controllers/webhook_ops_controller.py`.
- [ ] Add internal endpoint:
  - `POST /v1/ops/webhooks/{event_id}/retry`
- [ ] Register route in `backend/app/main.py`.
- [ ] Add route test that calls manual retry with a fake delivery service.

### Task 8: Verification

- [ ] Run:

```powershell
cd backend
python -m unittest discover tests -v
```

- [ ] Expected: all tests pass.

### Task 9: Commit

- [ ] Stage webhook files.
- [ ] Commit message suggestion:

```text
feat: add webhook delivery retry flow
```

## Acceptance Criteria

- Webhook events are created for final payment/refund states.
- Delivery attempts are auditable.
- Retry schedule matches plan.
- Manual retry is internal-only.
- Payment/refund success does not depend on webhook delivery success.
