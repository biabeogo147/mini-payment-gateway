# Webhook Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement merchant webhook event creation, payload signing, delivery attempts, retry schedule, and manual retry.

**Architecture:** Payment/refund finalization creates durable `WebhookEvent` rows for merchants with a configured `webhook_url`. A separate webhook delivery service signs payloads, sends HTTP requests, writes `WebhookDeliveryAttempt`, updates retry state, and exposes an internal manual retry endpoint. Delivery is intentionally separated from payment/refund finalization so business state changes do not depend on outbound HTTP success.

**Tech Stack:** FastAPI, SQLAlchemy, existing webhook models, standard-library HMAC helpers, existing `httpx` dependency, standard `unittest` test suite.

---

## Implementation Status

Completed on 2026-05-04. Phase 06 application code now creates webhook events
from final payment/refund transitions, signs and delivers stored payloads,
persists delivery attempts, schedules retries, exposes internal manual retry,
and includes unit tests plus a DB/API smoke script.

Use the current repository checkout directly. Do not create a branch or
worktree unless the user asks for one. Commit only when requested.

Completion record: `docs/history/completions/phase-06.md`.

## Scope

Implement:

- webhook event creation for configured merchant payment/refund final states.
- webhook event payload construction for:
  - `payment.succeeded`;
  - `payment.failed`;
  - `payment.expired`;
  - `refund.succeeded`;
  - `refund.failed`.
- payload signing using the active merchant credential secret.
- HTTP delivery through an injectable `httpx`-compatible client.
- delivery attempt persistence.
- retry schedule:
  - attempt 1 failure schedules retry after 1 minute;
  - attempt 2 failure schedules retry after 5 minutes;
  - attempt 3 failure schedules retry after 15 minutes;
  - attempt 4 failure marks the event `FAILED`.
- due-event delivery service operation for future worker/scheduler use.
- internal manual retry endpoint:
  - `POST /v1/ops/webhooks/{event_id}/retry`.
- smoke script that proves callback-driven event creation and delivery against a
  local webhook receiver.

Do not implement:

- background scheduler or long-running worker process.
- merchant-facing webhook configuration API.
- ops authentication/authorization.
- audit log writes for manual retry; phase 07 owns ops audit.
- event delivery for merchants without `webhook_url`.
- encryption/key-management changes for merchant credentials.
- exactly-once external delivery guarantees. Phase 06 provides durable attempts,
  idempotent event creation, and retry state only.

## Scenario References

Use `docs/testing/scenarios/webhook.md` as the behavior source for:

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

Use `docs/api/webhook.md` as the outbound webhook contract source.

Use `docs/testing/matrix.md` to keep the phase 06 test names aligned
with the scenario IDs.

## Current Code Map

Existing source that phase 06 should build on:

- `backend/app/models/webhook_event.py` already contains:
  - `event_id`;
  - `merchant_db_id`;
  - `event_type`;
  - `entity_type`;
  - `entity_id`;
  - `payload_json`;
  - `signature`;
  - `status`;
  - `next_retry_at`;
  - `attempt_count`;
  - `last_attempt_at`.
- `backend/app/models/webhook_delivery_attempt.py` already contains outbound
  request/response diagnostics and `DeliveryAttemptResult`.
- `backend/app/models/enums.py` already contains:
  - `WebhookEventStatus`: `PENDING`, `DELIVERED`, `FAILED`;
  - `DeliveryAttemptResult`: `SUCCESS`, `FAILED`, `TIMEOUT`, `NETWORK_ERROR`;
  - `EntityType.PAYMENT`, `EntityType.REFUND`, `EntityType.WEBHOOK_EVENT`.
- `backend/app/models/merchant.py` already has `webhook_url`.
- `backend/app/models/merchant_credential.py` stores the active credential
  secret in `secret_key_encrypted`. Current auth treats this value as plaintext
  through `_decrypt_secret`; phase 06 should follow that MVP convention.
- `backend/app/core/security.py` already has `sha256_hex(...)` and
  `sign_hmac_sha256(...)`.
- `backend/app/services/provider_callback_service.py` finalizes payment and
  refund callbacks. Phase 06 should hook event creation only after a successful
  state transition was processed.
- `backend/app/services/expiration_service.py` finalizes expired payments.
- `backend/app/repositories/merchant_repository.py` currently needs a
  `get_by_id(...)` helper.
- `backend/app/repositories/credential_repository.py` currently needs a
  `get_active_by_merchant(...)` helper.
- `backend/pyproject.toml` already includes `httpx`, so no dependency change is
  expected.
- Alembic migrations already create webhook tables; no migration is expected
  unless implementation discovers a model/schema mismatch.

## Implementation Decisions

- Event creation is service-level idempotent by:
  - `merchant_db_id`;
  - `event_type`;
  - `entity_type`;
  - `entity_id`.
- No database unique constraint is added in phase 06; use repository lookup
  before insert.
- `event_id` format is `evt_{uuid4().hex}`.
- Event creation should no-op when the merchant has no `webhook_url`. This keeps
  the mini gateway from accumulating permanently undeliverable events for
  merchants that did not configure webhooks.
- Event creation should not perform HTTP delivery.
- New events start with:
  - `status=PENDING`;
  - `attempt_count=0`;
  - `next_retry_at=now`.
- Payload is created and stored at event creation time as a stable snapshot.
- Payload envelope:

```json
{
  "event_id": "evt_...",
  "event_type": "payment.succeeded",
  "merchant_id": "m_demo",
  "entity_type": "PAYMENT",
  "entity_id": "uuid",
  "created_at": "2026-04-29T10:05:01Z",
  "data": {}
}
```

- Payment payload data should include:
  - `transaction_id`;
  - `order_id`;
  - `amount`;
  - `currency`;
  - `status`;
  - `paid_at`;
  - `expire_at`;
  - `failed_reason_code`;
  - `failed_reason_message`.
- Refund payload data should include:
  - `refund_transaction_id`;
  - `original_transaction_id`;
  - `refund_id`;
  - `refund_amount`;
  - `status`;
  - `processed_at`;
  - `failed_reason_code`;
  - `failed_reason_message`.
- Payload signing happens at delivery time using the current active merchant
  credential.
- The canonical webhook signing string is:

```text
{timestamp}.{event_id}.{body_sha256_hex}
```

- Delivery headers:
  - `Content-Type: application/json`;
  - `X-Webhook-Event-Id`;
  - `X-Webhook-Timestamp`;
  - `X-Webhook-Signature`.
- Store the latest outbound signature on `WebhookEvent.signature` for
  inspection. Store exact outbound headers and body on every
  `WebhookDeliveryAttempt`.
- Attempt number is `event.attempt_count + 1`.
- HTTP `2xx` marks the attempt `SUCCESS` and the event `DELIVERED`.
- HTTP non-`2xx` marks the attempt `FAILED` and either schedules the next retry
  or marks the event `FAILED`.
- `httpx.TimeoutException` maps to `TIMEOUT`.
- `httpx.RequestError` maps to `NETWORK_ERROR`.
- Missing merchant, missing `webhook_url`, or missing active credential during
  delivery should mark the event `FAILED` and record a `FAILED` attempt when a
  request URL can be determined. Missing URL can mark event `FAILED` without an
  attempt if no request URL exists.
- Manual retry is allowed only for `FAILED` events. A successful manual retry
  moves the event to `DELIVERED`; a failed manual retry keeps it `FAILED`.
- Manual retry attempt number may exceed the automatic `MAX_ATTEMPTS` because it
  is operator-initiated.
- Payment/refund final state must not depend on webhook HTTP delivery success.

## Files

- Create: `backend/app/controllers/webhook_ops_controller.py`
- Create: `backend/app/repositories/webhook_repository.py`
- Create: `backend/app/schemas/webhook.py`
- Create: `backend/app/services/webhook_delivery_service.py`
- Create: `backend/app/services/webhook_event_factory.py`
- Create: `backend/app/services/webhook_retry_policy.py`
- Create: `backend/scripts/smoke_webhook_api.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/repositories/credential_repository.py`
- Modify: `backend/app/repositories/merchant_repository.py`
- Modify: `backend/app/services/expiration_service.py`
- Modify: `backend/app/services/provider_callback_service.py`
- Modify: `docs/api/ops.md`
- Modify: `docs/api/webhook.md`
- Modify: `docs/history/README.md`
- Modify: `docs/testing/scenarios/callback.md`
- Modify: `docs/testing/e2e.md`
- Modify: `docs/testing/scenarios/happy-path.md`
- Modify: `docs/testing/scenarios/refund.md`
- Modify: `docs/testing/matrix.md`
- Modify: `docs/testing/scenarios/webhook.md`
- Create: `docs/history/completions/phase-06.md`
- Test: `backend/tests/test_webhook_retry_policy.py`
- Test: `backend/tests/test_webhook_event_factory.py`
- Test: `backend/tests/test_webhook_delivery_service.py`
- Test: `backend/tests/test_webhook_hooks.py`
- Test: `backend/tests/test_webhook_ops_routes.py`

## Tasks

### Task 0: Baseline Check

- [ ] Run:

```bash
cd backend
python -m unittest discover tests -v
```

- [ ] Expected: existing phase 0-5 tests pass before phase 06 edits.

### Task 1: Add Retry Policy Tests

- [ ] Create `backend/tests/test_webhook_retry_policy.py`.
- [ ] Test `next_retry_at(attempt_no, now)`:
  - attempt 1 returns `now + 1 minute`;
  - attempt 2 returns `now + 5 minutes`;
  - attempt 3 returns `now + 15 minutes`;
  - attempt 4 returns `None`.
- [ ] Test `has_automatic_attempts_remaining(attempt_no)`:
  - true for attempts 1, 2, and 3 after failure;
  - false for attempt 4.
- [ ] Run:

```bash
cd backend
python -m unittest tests.test_webhook_retry_policy -v
```

- [ ] Expected: FAIL before policy exists.

### Task 2: Implement Retry Policy

- [ ] Create `backend/app/services/webhook_retry_policy.py`.
- [ ] Implement:
  - `MAX_AUTOMATIC_ATTEMPTS = 4`;
  - `next_retry_at(attempt_no, now)`;
  - `has_automatic_attempts_remaining(attempt_no)`.
- [ ] Keep the schedule as constants near the functions for readability.
- [ ] Run retry policy tests.
- [ ] Expected: PASS.

### Task 3: Add Repository Helper Tests

- [ ] Add repository tests in `backend/tests/test_webhook_event_factory.py` or a
  separate repository test section.
- [ ] Test `webhook_repository.create_event(...)`:
  - adds a `WebhookEvent`;
  - flushes;
  - sets `status=PENDING`;
  - sets `attempt_count=0`.
- [ ] Test `webhook_repository.create_delivery_attempt(...)`:
  - adds a `WebhookDeliveryAttempt`;
  - flushes;
  - stores request headers/body and result.
- [ ] Test fake repository helper expectations for:
  - get existing event by entity/event type;
  - find due pending events.

### Task 4: Implement Repository Helpers

- [ ] Create `backend/app/repositories/webhook_repository.py`.
- [ ] Implement:
  - `get_by_event_id(db, event_id)`;
  - `get_existing_event(db, merchant_db_id, event_type, entity_type, entity_id)`;
  - `create_event(db, event_id, merchant_db_id, event_type, entity_type, entity_id, payload_json, next_retry_at)`;
  - `find_due_events(db, now, limit=100)`;
  - `save_event(db, event)`;
  - `create_delivery_attempt(db, webhook_event_id, attempt_no, request_url, request_headers_json, request_body_json, response_status_code, response_body_snippet, error_message, started_at, finished_at, result)`.
- [ ] Modify `backend/app/repositories/merchant_repository.py`:
  - add `get_by_id(db, merchant_db_id)`.
- [ ] Modify `backend/app/repositories/credential_repository.py`:
  - add `get_active_by_merchant(db, merchant_db_id)`.
- [ ] Run repository-related tests.

### Task 5: Add Event Factory Tests

- [ ] Create `backend/tests/test_webhook_event_factory.py`.
- [ ] Test payment event creation:
  - `SUCCESS` creates `payment.succeeded`;
  - `FAILED` creates `payment.failed`;
  - `EXPIRED` creates `payment.expired`.
- [ ] Test refund event creation:
  - `REFUNDED` creates `refund.succeeded`;
  - `REFUND_FAILED` creates `refund.failed`.
- [ ] Test merchant without `webhook_url` returns `None` and does not insert.
- [ ] Test duplicate entity/event type returns the existing event and does not
  insert.
- [ ] Test stored payload includes envelope fields and relevant data fields.
- [ ] Run:

```bash
cd backend
python -m unittest tests.test_webhook_event_factory -v
```

- [ ] Expected: FAIL before factory exists.

### Task 6: Implement Event Factory

- [ ] Create `backend/app/services/webhook_event_factory.py`.
- [ ] Implement:
  - `create_payment_event_if_needed(db, payment, now=None)`;
  - `create_refund_event_if_needed(db, refund, now=None)`.
- [ ] Resolve merchant through `merchant_repository.get_by_id(...)`.
- [ ] Resolve original payment for refund payload through
  `payment_repository.get_by_id(...)`.
- [ ] Map event types:
  - `PaymentStatus.SUCCESS -> payment.succeeded`;
  - `PaymentStatus.FAILED -> payment.failed`;
  - `PaymentStatus.EXPIRED -> payment.expired`;
  - `RefundStatus.REFUNDED -> refund.succeeded`;
  - `RefundStatus.REFUND_FAILED -> refund.failed`.
- [ ] Return `None` for non-final states or missing webhook configuration.
- [ ] Use `webhook_repository.get_existing_event(...)` before insert.
- [ ] Use `event_id=evt_{uuid4().hex}`.
- [ ] Use `next_retry_at=now` for newly created events.
- [ ] Run event factory tests.
- [ ] Expected: PASS.

### Task 7: Add Delivery Service Tests

- [ ] Create `backend/tests/test_webhook_delivery_service.py`.
- [ ] Use a fake HTTP client object with a `post(...)` method.
- [ ] Use fake repository/merchant/credential stores rather than real DB.
- [ ] Test:
  - HTTP 2xx records a `SUCCESS` attempt and marks event `DELIVERED`;
  - HTTP 500 records a `FAILED` attempt and schedules attempt 2 for +1 minute;
  - attempt 2 failure schedules +5 minutes;
  - attempt 3 failure schedules +15 minutes;
  - attempt 4 failure marks event `FAILED`;
  - timeout records `TIMEOUT` and schedules retry;
  - network error records `NETWORK_ERROR` and schedules retry;
  - missing active credential marks event `FAILED`;
  - `deliver_due_webhooks(db, now, limit, http_client)` delivers only due
    `PENDING` events;
  - `manual_retry(db, event_id, now, http_client)` rejects missing event and
    delivered event.
- [ ] Assert signing headers are present and `X-Webhook-Signature` matches the
  canonical string in `docs/api/webhook.md`.
- [ ] Run:

```bash
cd backend
python -m unittest tests.test_webhook_delivery_service -v
```

- [ ] Expected: FAIL before service exists.

### Task 8: Implement Delivery Service

- [ ] Create `backend/app/services/webhook_delivery_service.py`.
- [ ] Implement:
  - `deliver_event(db, event, now=None, http_client=None, manual=False)`;
  - `deliver_due_webhooks(db, now=None, limit=100, http_client=None)`;
  - `manual_retry(db, event_id, now=None, http_client=None)`.
- [ ] Use default `httpx.Client()` only when no client is injected.
- [ ] Build request body from `event.payload_json`.
- [ ] Sign body with:
  - timestamp from `now`;
  - event id;
  - `sha256_hex(body_bytes)`;
  - `sign_hmac_sha256(active_credential.secret_key_encrypted, signing_string)`.
- [ ] Create a `WebhookDeliveryAttempt` for each actual send.
- [ ] Update event:
  - increment `attempt_count`;
  - set `last_attempt_at`;
  - set `signature`;
  - set `status`;
  - set `next_retry_at`.
- [ ] Use `AppError("WEBHOOK_EVENT_NOT_FOUND", 404)` for missing manual retry
  event.
- [ ] Use `AppError("WEBHOOK_RETRY_NOT_ALLOWED", 409)` for delivered or nonfailed
  manual retry targets.
- [ ] Run delivery tests.
- [ ] Expected: PASS.

### Task 9: Add Webhook Hook Tests

- [ ] Create `backend/tests/test_webhook_hooks.py` or extend existing callback
  and expiration tests.
- [ ] Test payment success callback creates `payment.succeeded` event.
- [ ] Test payment failed callback creates `payment.failed` event.
- [ ] Test payment duplicate/ignored callback does not create a new event.
- [ ] Test payment mismatch or pending-review callback does not create an event.
- [ ] Test expiration service creates `payment.expired` events for expired
  payments.
- [ ] Test refund success callback creates `refund.succeeded` event.
- [ ] Test refund failed callback creates `refund.failed` event.
- [ ] Run hook tests.
- [ ] Expected: FAIL before services are wired.

### Task 10: Wire Event Creation Hooks

- [ ] Modify `backend/app/services/provider_callback_service.py`.
- [ ] After a payment transition is processed and saved, call
  `webhook_event_factory.create_payment_event_if_needed(...)`.
- [ ] After a refund transition is processed and saved, call
  `webhook_event_factory.create_refund_event_if_needed(...)`.
- [ ] Do not create events for:
  - unknown callbacks;
  - amount mismatch callbacks;
  - duplicate same-state callbacks;
  - final-state conflict callbacks.
- [ ] Modify `backend/app/services/expiration_service.py`.
- [ ] After each payment is marked `EXPIRED` and saved, call
  `webhook_event_factory.create_payment_event_if_needed(...)`.
- [ ] Keep delivery out of these hooks.
- [ ] Run hook tests and existing callback/expiration tests.
- [ ] Expected: PASS.

### Task 11: Add Manual Retry Route Tests

- [ ] Create `backend/tests/test_webhook_ops_routes.py`.
- [ ] Test `POST /v1/ops/webhooks/{event_id}/retry` calls
  `webhook_delivery_service.manual_retry(...)` with db and event id.
- [ ] Test response serializes:
  - `event_id`;
  - `status`;
  - `attempt_count`;
  - `last_attempt_result`;
  - `next_retry_at`.
- [ ] Run route tests.
- [ ] Expected: FAIL before controller exists.

### Task 12: Implement Manual Retry Controller

- [ ] Create `backend/app/schemas/webhook.py`.
- [ ] Define `WebhookRetryResponse`:
  - `event_id`;
  - `status`;
  - `attempt_count`;
  - `last_attempt_result`;
  - `next_retry_at`.
- [ ] Create `backend/app/controllers/webhook_ops_controller.py`.
- [ ] Add:
  - `POST /v1/ops/webhooks/{event_id}/retry`.
- [ ] Keep it internal-only for MVP; do not add auth yet.
- [ ] Register the router in `backend/app/main.py`.
- [ ] Run route tests.
- [ ] Expected: PASS.

### Task 13: API And DB Smoke

- [ ] Create `backend/scripts/smoke_webhook_api.py`.
- [ ] The script should:
  - start a local merchant webhook receiver using Python standard library HTTP
    server on a free port;
  - seed an active merchant with `webhook_url` pointing to that receiver;
  - create a payment through `POST /v1/payments`;
  - mark payment success through `POST /v1/provider/callbacks/payment`;
  - verify a `webhook_events` row exists with `event_type=payment.succeeded`;
  - call `webhook_delivery_service.deliver_due_webhooks(...)`;
  - verify the receiver got one signed request;
  - verify `webhook_delivery_attempts` has a `SUCCESS` attempt;
  - verify the event status is `DELIVERED`;
  - print compact JSON evidence.
- [ ] Optionally include a second local receiver mode that returns HTTP 500 and
  verify retry scheduling.
- [ ] Run:

```bash
cd backend
python -m alembic upgrade head
python scripts/smoke_webhook_api.py
```

- [ ] Expected: JSON output proves event creation, signed delivery, attempt
  persistence, and DB event status agree.

### Task 14: Documentation Updates

- [ ] Update `docs/api/webhook.md` if implementation fields differ from
  the contract above.
- [ ] Update `docs/api/ops.md` to note manual retry audit is phase 07.
- [ ] Update `docs/testing/scenarios/webhook.md` statuses for implemented webhook
  scenarios.
- [ ] Update `docs/testing/scenarios/callback.md` for phase 06 webhook event creation on
  payment success/failure/expiration.
- [ ] Update `docs/testing/scenarios/refund.md` for phase 06 webhook event creation on
  refund success/failure.
- [ ] Update `docs/testing/scenarios/happy-path.md` where webhook delivery steps become
  implemented with DB seed.
- [ ] Update `docs/testing/e2e.md` current capability snapshot.
- [ ] Update `docs/testing/matrix.md` phase 06 rows from `Planned` to
  implemented coverage.
- [ ] Update `docs/history/README.md` standard verification commands with
  `scripts/smoke_webhook_api.py`.
- [ ] Create `docs/history/completions/phase-06.md` with:
  - completed scope;
  - tests run;
  - smoke output;
  - remaining phase 07/08 notes.

### Task 15: Full Verification

- [ ] Run:

```bash
cd backend
python -m unittest discover tests -v
```

- [ ] Expected: all tests pass.

- [ ] Run:

```bash
git diff --check
```

- [ ] Expected: no whitespace errors.

### Task 16: Commit

- [ ] Only if the user asks for a commit, stage webhook files and commit.
- [ ] Commit message suggestion:

```text
feat: add webhook delivery retry flow
```

## Acceptance Criteria

- Webhook events are created for configured merchants when payment/refund rows
  reach final states.
- Event creation is repeat-safe for duplicate callbacks.
- Event creation does not perform HTTP delivery.
- HTTP delivery signs payloads using the active merchant credential.
- Every delivery attempt is persisted with request/response diagnostics.
- HTTP 2xx marks webhook event `DELIVERED`.
- HTTP non-2xx, timeout, and network errors schedule retries according to the
  phase 06 retry policy.
- Attempt 4 failure marks webhook event `FAILED`.
- Manual retry can resend failed events and does not mutate payment/refund final
  state.
- Payment/refund finalization does not depend on webhook HTTP delivery success.
- API docs, scenario docs, testing matrix, and completion docs are updated after
  implementation.
