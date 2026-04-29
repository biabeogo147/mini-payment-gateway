# E2E Scenario Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a shared end-to-end scenario catalog that explains how the mini payment gateway should be operated and tested from merchant onboarding through payment, refund, webhook, reconciliation, and ops actions.

**Architecture:** This is a documentation-first phase. It does not implement new backend behavior; it makes the target workflows explicit so phase 04-08 can develop against the same scenario language, API sequence, DB effects, and acceptance assertions.

**Tech Stack:** Markdown docs, Mermaid diagrams, existing API contract docs, existing SQLAlchemy model docs, phase roadmap docs.

---

## Implementation Status

Completed. The implementation created `docs/scenarios/README.md`,
`docs/scenarios/e2e_scenarios.md` as an index, grouped scenario files
(`happy_path.md`, `auth.md`, `mer.md`, `pay.md`, `callback.md`, `refund.md`,
`webhook.md`, `ops.md`, `reconciliation.md`), and
`docs/scenarios/testing_matrix.md`; linked phase 04-08 back to the grouped
catalog; and updated the roadmap so provider callback work starts after the
shared scenarios are visible.

Verification commands used:

```powershell
$fence = [char]96 + [char]96 + [char]96; $files = (Get-ChildItem docs\scenarios -Filter *.md).FullName + @('docs\plan\phase_03_5_e2e_scenario_catalog.md'); foreach ($file in $files) { $count = (Select-String -Path $file -Pattern $fence).Count; if ($count % 2 -ne 0) { Write-Output "ODD $file $count" } }
rg -n "[ \t]+$" docs\scenarios docs\plan
rg -n "auth.md|mer.md|pay.md|callback.md|refund.md|webhook.md|ops.md|reconciliation.md|happy_path.md|testing_matrix|phase_03_5" docs\plan docs\scenarios
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

- Create: `docs/scenarios/README.md`
- Create: `docs/scenarios/e2e_scenarios.md` as the index
- Create: `docs/scenarios/happy_path.md`
- Create: `docs/scenarios/auth.md`
- Create: `docs/scenarios/mer.md`
- Create: `docs/scenarios/pay.md`
- Create: `docs/scenarios/callback.md`
- Create: `docs/scenarios/refund.md`
- Create: `docs/scenarios/webhook.md`
- Create: `docs/scenarios/ops.md`
- Create: `docs/scenarios/reconciliation.md`
- Create: `docs/scenarios/testing_matrix.md`
- Modify: `docs/plan/README.md`
- Modify: `docs/plan/phase_03_completion.md`
- Modify: `docs/plan/phase_04_provider_callback_and_expiration.md`
- Modify: `docs/plan/phase_05_refund_core.md`
- Modify: `docs/plan/phase_06_webhook_delivery.md`
- Modify: `docs/plan/phase_07_reconciliation_and_ops_audit.md`
- Modify: `docs/plan/phase_08_readiness_docs_and_e2e.md`

## Output Document Shape

`docs/scenarios/e2e_scenarios.md` should be an index and use this structure:

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

- `docs/scenarios/happy_path.md` - target E2E journeys.
- `docs/scenarios/auth.md` - merchant HMAC scenarios.
- `docs/scenarios/mer.md` - merchant readiness and onboarding scenarios.
- `docs/scenarios/pay.md` - payment scenarios.
- `docs/scenarios/callback.md` - provider callback and expiration scenarios.
- `docs/scenarios/refund.md` - refund scenarios.
- `docs/scenarios/webhook.md` - webhook scenarios.
- `docs/scenarios/ops.md` - ops and audit scenarios.
- `docs/scenarios/reconciliation.md` - reconciliation scenarios.

`docs/scenarios/testing_matrix.md` should be shorter and QA-focused:

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

- [ ] Create `docs/scenarios/README.md`.
- [ ] Create `docs/scenarios/e2e_scenarios.md` as the index.
- [ ] Create grouped scenario files:
  - `docs/scenarios/happy_path.md`
  - `docs/scenarios/auth.md`
  - `docs/scenarios/mer.md`
  - `docs/scenarios/pay.md`
  - `docs/scenarios/callback.md`
  - `docs/scenarios/refund.md`
  - `docs/scenarios/webhook.md`
  - `docs/scenarios/ops.md`
  - `docs/scenarios/reconciliation.md`
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

- [ ] In `docs/scenarios/pay.md`, fully document the currently runnable flow:
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

- [ ] Create `docs/scenarios/testing_matrix.md`.
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

- [ ] Modify `docs/plan/README.md`:
  - add the grouped `docs/scenarios/*.md` files and `docs/scenarios/testing_matrix.md` to source docs.
  - insert phase 3.5 between phase 03 and phase 04.
  - mark phase 04 as after scenario catalog.
- [ ] Modify `docs/plan/phase_03_completion.md`:
  - next phase should be phase 3.5 before phase 04.
- [ ] Modify `docs/plan/phase_04_provider_callback_and_expiration.md`:
  - reference provider callback scenarios from `docs/scenarios/callback.md` and reconciliation cases from `docs/scenarios/reconciliation.md`.
- [ ] Modify `docs/plan/phase_05_refund_core.md`:
  - reference refund scenarios from `docs/scenarios/refund.md`.
- [ ] Modify `docs/plan/phase_06_webhook_delivery.md`:
  - reference webhook scenarios from `docs/scenarios/webhook.md`.
- [ ] Modify `docs/plan/phase_07_reconciliation_and_ops_audit.md`:
  - reference merchant, ops, audit, and reconciliation scenarios.
- [ ] Modify `docs/plan/phase_08_readiness_docs_and_e2e.md`:
  - avoid duplicating the catalog; phase 08 should convert selected scenarios into automated E2E tests and runbooks.

### Task 9: Verification

- [ ] Check Markdown code fences:

```powershell
$fence = [char]96 + [char]96 + [char]96; $files = (Get-ChildItem docs\scenarios -Filter *.md).FullName + @('docs\plan\phase_03_5_e2e_scenario_catalog.md'); foreach ($file in $files) { $count = (Select-String -Path $file -Pattern $fence).Count; if ($count % 2 -ne 0) { Write-Output "ODD $file $count" } }
```

- [ ] Check for trailing whitespace:

```powershell
rg -n "[ \t]+$" docs\scenarios docs\plan
```

- [ ] Check scenario docs are discoverable:

```powershell
rg -n "auth.md|mer.md|pay.md|callback.md|refund.md|webhook.md|ops.md|reconciliation.md|happy_path.md|testing_matrix|phase_03_5" docs\plan docs\scenarios
```

### Task 10: Commit

- [ ] Stage docs-only phase 3.5 files.
- [ ] Commit message suggestion:

```text
docs: add e2e scenario catalog plan
```

## Acceptance Criteria

- Team members can read `docs/scenarios/e2e_scenarios.md` as the index and the
  grouped scenario files to understand the intended full lifecycle before all
  APIs are implemented.
- Each scenario says what is runnable now versus planned later.
- Each scenario names API calls, sample request/response shape, DB table effects,
  state transitions, and owning phase.
- `docs/scenarios/testing_matrix.md` maps scenarios to current and future tests.
- Phase 04-08 plans refer back to grouped scenario files instead of inventing
  disconnected behavior.
- No backend behavior is changed in this docs-only phase.
