# E2E Scenario Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a shared end-to-end scenario catalog that explains how the mini payment gateway should be operated and tested from merchant onboarding through payment, refund, webhook, reconciliation, and ops actions.

**Architecture:** This is a documentation-first phase. It does not implement new backend behavior; it makes the target workflows explicit so phase 04-08 can develop against the same scenario language, API sequence, DB effects, and acceptance assertions.

**Tech Stack:** Markdown docs, Mermaid diagrams, existing API contract docs, existing SQLAlchemy model docs, phase roadmap docs.

---

## Implementation Status

Completed. The implementation created `docs/testing/README.md`,
`docs/testing/e2e.md` as an index, grouped scenario files
(`scenarios/happy-path.md`, `scenarios/auth.md`, `scenarios/merchant.md`,
`scenarios/payment.md`, `scenarios/callback.md`, `scenarios/refund.md`,
`scenarios/webhook.md`, `scenarios/ops.md`, `scenarios/reconciliation.md`), and
`docs/testing/matrix.md`; linked phase 04-08 back to the grouped
catalog; and updated the roadmap so provider callback work starts after the
shared scenarios are visible.

Verification commands used:

```powershell
$fence = [char]96 + [char]96 + [char]96; $files = (Get-ChildItem docs\testing\scenarios -Filter *.md).FullName + @('docs\history\phases\phase-03-5-e2e-scenario-catalog.md'); foreach ($file in $files) { $count = (Select-String -Path $file -Pattern $fence).Count; if ($count % 2 -ne 0) { Write-Output "ODD $file $count" } }
rg -n "[ \t]+$" docs\testing docs\history
rg -n "scenarios/auth.md|scenarios/merchant.md|scenarios/payment.md|scenarios/callback.md|scenarios/refund.md|scenarios/webhook.md|scenarios/ops.md|scenarios/reconciliation.md|scenarios/happy-path.md|matrix.md|phase-03-5" docs\history docs\testing
```

Commit task remains unchecked because no commit was requested.

## Scope

Create a clear scenario catalog before building provider callbacks, refund,
webhooks, and ops APIs.

The catalog must answer, for each scenario:

- Which actor performs the step.
- Which API is called.
- What request is sent.
- What response is expected.
- Which database tables are inserted or updated.
- Which state transition is expected.
- Whether the step is implemented now or planned for a later phase.
- Which phase owns the implementation.

This phase should not add backend endpoints, services, models, migrations, or
automated E2E tests. Actual automated E2E tests remain in phase 08 after the
flows exist.

## Files

- Create: `docs/testing/README.md`
- Create: `docs/testing/e2e.md` as the index
- Create: `docs/testing/scenarios/happy-path.md`
- Create: `docs/testing/scenarios/auth.md`
- Create: `docs/testing/scenarios/merchant.md`
- Create: `docs/testing/scenarios/payment.md`
- Create: `docs/testing/scenarios/callback.md`
- Create: `docs/testing/scenarios/refund.md`
- Create: `docs/testing/scenarios/webhook.md`
- Create: `docs/testing/scenarios/ops.md`
- Create: `docs/testing/scenarios/reconciliation.md`
- Create: `docs/testing/matrix.md`
- Modify: `docs/history/README.md`
- Modify: `docs/history/completions/phase-03.md`
- Modify: `docs/history/phases/phase-04-provider-callback-and-expiration.md`
- Modify: `docs/history/phases/phase-05-refund-core.md`
- Modify: `docs/history/phases/phase-06-webhook-delivery.md`
- Modify: `docs/history/phases/phase-07-reconciliation-and-ops-audit.md`
- Modify: `docs/history/phases/phase-08-readiness-docs-and-e2e.md`

## Output Document Shape

`docs/testing/e2e.md` should be an index and use this structure:

```md
# End-To-End Scenario Catalog

## Status Legend

## Current Capability Snapshot

## Scenario Files

| File | Scenario Groups | Owned Phases |
| --- | --- | --- |

## Scenario Matrix

| Scenario | Main Actor | Detail File | APIs | Tables | Current Status | Owning Phase |
| --- | --- | --- | --- | --- | --- | --- |
```

Grouped scenario files should contain the detailed request/response, DB effect,
state transition, and acceptance assertions:

- `docs/testing/scenarios/happy-path.md` - target E2E journeys.
- `docs/testing/scenarios/auth.md` - merchant HMAC scenarios.
- `docs/testing/scenarios/merchant.md` - merchant readiness and onboarding scenarios.
- `docs/testing/scenarios/payment.md` - payment scenarios.
- `docs/testing/scenarios/callback.md` - provider callback and expiration scenarios.
- `docs/testing/scenarios/refund.md` - refund scenarios.
- `docs/testing/scenarios/webhook.md` - webhook scenarios.
- `docs/testing/scenarios/ops.md` - ops and audit scenarios.
- `docs/testing/scenarios/reconciliation.md` - reconciliation scenarios.

`docs/testing/matrix.md` should be shorter and QA-focused:

```md
# Testing Matrix

| Test Case | Type | Phase | APIs | Expected Result | Automatable |
| --- | --- | --- | --- | --- | --- |
```

## Scenario Catalog

### Core Happy Path

Include one complete target flow:

1. Ops registers merchant.
2. Ops submits onboarding case.
3. Ops approves onboarding case.
4. Ops creates/rotates active credential.
5. Ops activates merchant.
6. Merchant creates payment.
7. Provider sends payment success callback.
8. Merchant queries payment by transaction id.
9. Merchant queries payment by order id.
10. Gateway creates webhook event.
11. Gateway delivers webhook.
12. Merchant creates full refund.
13. Provider sends refund success callback.
14. Gateway creates refund webhook event.
15. Gateway delivers refund webhook.
16. Ops reviews audit/reconciliation evidence.

### Payment Scenarios

Document these scenarios:

- Active merchant creates payment successfully.
- Non-active merchant cannot create payment.
- Missing auth header fails.
- Invalid HMAC signature fails.
- Expired timestamp fails.
- Duplicate pending payment with identical request returns existing transaction.
- Duplicate pending payment with different amount rejects.
- Duplicate pending payment with different description rejects.
- Duplicate pending payment with different expiration rejects.
- Previous `FAILED` payment allows new attempt.
- Previous `EXPIRED` payment allows new attempt.
- Previous `SUCCESS` payment rejects new attempt.
- Query payment by transaction id.
- Query payment by order id.
- Query another merchant's payment returns not found.

### Provider Callback And Expiration Scenarios

Document these scenarios:

- Payment success callback marks payment `SUCCESS`.
- Payment failed callback marks payment `FAILED`.
- Duplicate provider callback is idempotent or safely ignored.
- Unknown transaction callback is logged and marked failed or pending review.
- Expired payment moves from `PENDING` to `EXPIRED`.
- Late success callback after expiration does not revive the payment.
- Late success callback creates reconciliation evidence.
- Callback amount mismatch creates reconciliation evidence.

### Refund Scenarios

Document these scenarios:

- Full refund request for successful payment creates `REFUND_PENDING`.
- Provider refund success callback marks refund `REFUNDED`.
- Provider refund failed callback marks refund `REFUND_FAILED`.
- Duplicate refund id returns existing refund.
- Refund against non-success payment rejects.
- Partial refund rejects.
- Refund after 7-day window rejects.
- More than one successful refund for the same payment is blocked.
- Merchant cannot query another merchant's refund.

### Webhook Scenarios

Document these scenarios:

- Payment success creates `payment.succeeded` webhook event.
- Payment failure creates `payment.failed` webhook event.
- Payment expiration creates `payment.expired` webhook event.
- Refund success creates `refund.succeeded` webhook event.
- Refund failure creates `refund.failed` webhook event.
- HTTP 2xx delivery marks event `DELIVERED`.
- HTTP 500 schedules retry.
- Timeout schedules retry.
- Network error schedules retry.
- Attempt 4 exhaustion marks event `FAILED`.
- Ops manual retry sends a failed event again.

### Ops And Audit Scenarios

Document these scenarios:

- Ops creates merchant.
- Ops updates onboarding case.
- Ops approves onboarding case.
- Ops rejects onboarding case.
- Ops activates merchant only after approved onboarding and active credential.
- Ops suspends merchant.
- Suspended merchant cannot create payment/refund.
- Ops disables merchant.
- Credential rotation leaves exactly one active credential.
- Old credential no longer authenticates.
- Every ops state change writes `audit_logs`.

### Reconciliation Scenarios

Document these scenarios:

- Matching provider evidence creates `MATCHED`.
- Status mismatch creates `MISMATCHED`.
- Amount mismatch creates `MISMATCHED`.
- Late success after expiration creates `PENDING_REVIEW`.
- Ops resolves reconciliation record.
- Resolution writes audit log.

## Tasks

### Task 1: Create Grouped Scenario Catalog Skeleton

- [ ] Create `docs/testing/README.md`.
- [ ] Create `docs/testing/e2e.md` as the index.
- [ ] Create grouped scenario files:
  - `docs/testing/scenarios/happy-path.md`
  - `docs/testing/scenarios/auth.md`
  - `docs/testing/scenarios/merchant.md`
  - `docs/testing/scenarios/payment.md`
  - `docs/testing/scenarios/callback.md`
  - `docs/testing/scenarios/refund.md`
  - `docs/testing/scenarios/webhook.md`
  - `docs/testing/scenarios/ops.md`
  - `docs/testing/scenarios/reconciliation.md`
- [ ] Add status legend.
- [ ] Add scenario matrix table.
- [ ] Add all scenario section headings listed above to the matching grouped
  file.
- [ ] Mark current implementation accurately:
  - health: implemented.
  - merchant HMAC auth: implemented.
  - payment creation/query: implemented.
  - merchant onboarding ops APIs: planned.
  - provider callbacks: planned.
  - refunds: planned.
  - webhook delivery: planned.
  - reconciliation and audit services: planned.

### Task 2: Document Current Implemented Payment Flow In Detail

- [ ] In `docs/testing/scenarios/payment.md`, fully document the currently runnable flow:
  - seed/create active merchant and credential.
  - call `POST /v1/payments`.
  - call `GET /v1/payments/{transaction_id}`.
  - call `GET /v1/payments/by-order/{order_id}`.
- [ ] Include concrete sample request/response bodies.
- [ ] Include HMAC header requirements.
- [ ] Include DB effects:
  - `merchants`
  - `merchant_credentials`
  - `order_references`
  - `payment_transactions`
- [ ] Reference the real smoke script:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_payment_api.py
```

### Task 3: Document Target Merchant Onboarding And Ops Flow

- [ ] Add the target ops APIs even if they are not implemented yet.
- [ ] Mark each API as `Planned - phase 07`.
- [ ] Include DB effects for:
  - `merchants`
  - `merchant_onboarding_cases`
  - `merchant_credentials`
  - `audit_logs`
- [ ] Make clear that current runnable smoke uses DB seed until ops APIs exist.

### Task 4: Document Target Payment Lifecycle Flow

- [ ] Add provider callback success and failure scenarios.
- [ ] Mark each API as `Planned - phase 04`.
- [ ] Include DB effects for:
  - `payment_transactions`
  - `bank_callback_logs`
  - `reconciliation_records`
  - later `webhook_events`
- [ ] Include state transitions:
  - `PENDING -> SUCCESS`
  - `PENDING -> FAILED`
  - `PENDING -> EXPIRED`
- [ ] Include late callback and mismatch handling expectations.

### Task 5: Document Target Refund Flow

- [ ] Add full refund request and provider refund callback scenarios.
- [ ] Mark merchant refund APIs as `Planned - phase 05`.
- [ ] Include DB effects for:
  - `refund_transactions`
  - `bank_callback_logs`
  - `webhook_events`
- [ ] Include rejection scenarios:
  - partial refund.
  - refund after 7 days.
  - refund for non-success payment.

### Task 6: Document Webhook, Reconciliation, And Audit Scenarios

- [ ] Mark webhook scenarios as `Planned - phase 06`.
- [ ] Mark reconciliation and audit scenarios as `Planned - phase 07`.
- [ ] Include retry schedule:
  - initial attempt.
  - retry after 1 minute.
  - retry after 5 minutes.
  - retry after 15 minutes.
  - total attempts: 4.
- [ ] Include DB effects for:
  - `webhook_events`
  - `webhook_delivery_attempts`
  - `reconciliation_records`
  - `audit_logs`

### Task 7: Create Testing Matrix

- [ ] Create `docs/testing/matrix.md`.
- [ ] Add one row per scenario.
- [ ] Add columns:
  - scenario id.
  - scenario name.
  - test type: unit, service, route, smoke, E2E.
  - owning phase.
  - current status.
  - automatable now.
  - target automated test file.
- [ ] Mark current automated coverage:
  - `backend/tests/test_auth_service.py`
  - `backend/tests/test_merchant_readiness.py`
  - `backend/tests/test_payment_service.py`
  - `backend/tests/test_payment_routes.py`
  - `backend/scripts/smoke_payment_api.py`

### Task 8: Link Scenario Catalog Back Into Phase Plans

- [ ] Modify `docs/history/README.md`:
  - add the grouped `docs/testing/scenarios/*.md` files and `docs/testing/matrix.md` to source docs.
  - insert phase 3.5 between phase 03 and phase 04.
  - mark phase 04 as after scenario catalog.
- [ ] Modify `docs/history/completions/phase-03.md`:
  - next phase should be phase 3.5 before phase 04.
- [ ] Modify `docs/history/phases/phase-04-provider-callback-and-expiration.md`:
  - reference provider callback scenarios from `docs/testing/scenarios/callback.md` and reconciliation cases from `docs/testing/scenarios/reconciliation.md`.
- [ ] Modify `docs/history/phases/phase-05-refund-core.md`:
  - reference refund scenarios from `docs/testing/scenarios/refund.md`.
- [ ] Modify `docs/history/phases/phase-06-webhook-delivery.md`:
  - reference webhook scenarios from `docs/testing/scenarios/webhook.md`.
- [ ] Modify `docs/history/phases/phase-07-reconciliation-and-ops-audit.md`:
  - reference merchant, ops, audit, and reconciliation scenarios.
- [ ] Modify `docs/history/phases/phase-08-readiness-docs-and-e2e.md`:
  - avoid duplicating the catalog; phase 08 should convert selected scenarios into automated E2E tests and runbooks.

### Task 9: Verification

- [ ] Check Markdown code fences:

```powershell
$fence = [char]96 + [char]96 + [char]96; $files = (Get-ChildItem docs\testing\scenarios -Filter *.md).FullName + @('docs\history\phases\phase-03-5-e2e-scenario-catalog.md'); foreach ($file in $files) { $count = (Select-String -Path $file -Pattern $fence).Count; if ($count % 2 -ne 0) { Write-Output "ODD $file $count" } }
```

- [ ] Check for trailing whitespace:

```powershell
rg -n "[ \t]+$" docs\testing docs\history
```

- [ ] Check scenario docs are discoverable:

```powershell
rg -n "scenarios/auth.md|scenarios/merchant.md|scenarios/payment.md|scenarios/callback.md|scenarios/refund.md|scenarios/webhook.md|scenarios/ops.md|scenarios/reconciliation.md|scenarios/happy-path.md|matrix.md|phase-03-5" docs\history docs\testing
```

### Task 10: Commit

- [ ] Stage docs-only phase 3.5 files.
- [ ] Commit message suggestion:

```text
docs: add e2e scenario catalog plan
```

## Acceptance Criteria

- Team members can read `docs/testing/e2e.md` as the index and the
  grouped scenario files to understand the intended full lifecycle before all
  APIs are implemented.
- Each scenario says what is runnable now versus planned later.
- Each scenario names API calls, sample request/response shape, DB table effects,
  state transitions, and owning phase.
- `docs/testing/matrix.md` maps scenarios to current and future tests.
- Phase 04-08 plans refer back to grouped scenario files instead of inventing
  disconnected behavior.
- No backend behavior is changed in this docs-only phase.
