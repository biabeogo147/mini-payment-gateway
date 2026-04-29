# Happy Path Scenarios

Happy path scenarios describe target full journeys. Some steps are runnable
today with DB seed; the complete journey becomes a phase 08 E2E test after
provider callback, refund, webhook, ops, and reconciliation phases exist.

## E2E-01 Merchant Onboarding To Successful Payment And Refund

Implementation Status: Future E2E - phase 08.

Purpose: show the target lifecycle from merchant onboarding through successful
payment, successful refund, webhook delivery, and final ops visibility.

Preconditions:

- Database migrations are applied.
- The API is running.
- Ops actor exists, or internal ops authentication is bypassed for MVP.
- Provider is a simulator or trusted test caller.

### Step 1: Ops Registers Merchant

Detail: `mer.md` / `ONB-01`.

DB Effects:

- `merchants`: insert `PENDING_REVIEW`.
- `audit_logs`: insert merchant creation event.

### Step 2: Ops Submits And Approves Onboarding

Detail: `mer.md` / `ONB-02`, `ONB-03`.

DB Effects:

- `merchant_onboarding_cases`: insert/update and approve case.
- `audit_logs`: insert onboarding submission and approval events.

### Step 3: Ops Creates Credential And Activates Merchant

Detail: `mer.md` / `ONB-04`.

DB Effects:

- `merchant_credentials`: insert active credential.
- `merchants`: update `PENDING_REVIEW -> ACTIVE`.
- `audit_logs`: insert credential and activation events.

Current Workaround:

- Use direct DB seed through `backend/scripts/smoke_payment_api.py` until ops APIs
  exist.

### Step 4: Merchant Creates Payment

Detail: `pay.md` / `PAY-01`.

DB Effects:

- `order_references`: insert merchant order reference.
- `payment_transactions`: insert `PENDING` payment.

### Step 5: Provider Marks Payment Success

Detail: `callback.md` / `CB-01`.

DB Effects:

- `bank_callback_logs`: insert callback evidence.
- `payment_transactions`: update `PENDING -> SUCCESS`.
- `webhook_events`: create `payment.succeeded` in phase 06.

### Step 6: Merchant Queries Payment

Detail: `pay.md` / `PAY-02`, `PAY-03`.

DB Effects:

- `payment_transactions`: read.
- `order_references`: read for order query.

### Step 7: Gateway Delivers Payment Webhook

Detail: `webhook.md` / `WH-01`, `WH-05`.

DB Effects:

- `webhook_events`: update `PENDING -> DELIVERED`.
- `webhook_delivery_attempts`: insert delivery attempt.

### Step 8: Merchant Creates Full Refund

Detail: `refund.md` / `REF-01`.

DB Effects:

- `refund_transactions`: insert `REFUND_PENDING`.

### Step 9: Provider Marks Refund Success

Detail: `refund.md` / `REF-04`.

DB Effects:

- `bank_callback_logs`: insert callback evidence.
- `refund_transactions`: update `REFUND_PENDING -> REFUNDED`.
- `webhook_events`: create `refund.succeeded` in phase 06.

### Step 10: Gateway Delivers Refund Webhook

Detail: `webhook.md` / `WH-04`, `WH-05`.

DB Effects:

- `webhook_events`: update `PENDING -> DELIVERED`.
- `webhook_delivery_attempts`: insert delivery attempt.

### Step 11: Ops Reviews Audit And Reconciliation Evidence

Detail: `ops.md`, `reconciliation.md`.

DB Effects:

- `audit_logs`: read.
- `reconciliation_records`: read or resolve if mismatch evidence exists.

## E2E-02 Duplicate And Idempotency Path

Implementation Status: Future E2E - phase 08.

Steps:

- Seed or create an active merchant.
- Create a payment.
- Retry the same create request and expect the same pending transaction.
- Retry with a different amount or description and expect rejection.
- Mark payment success.
- Retry create for the same order and expect success-order rejection.

Scenario Details:

- `pay.md` / `PAY-04`
- `pay.md` / `PAY-05`
- `pay.md` / `PAY-08`

## E2E-03 Late Callback Reconciliation Path

Implementation Status: Future E2E - phase 08.

Steps:

- Create a payment.
- Expire the payment.
- Send a late success callback.
- Verify payment remains expired.
- Verify reconciliation evidence is created.
- Resolve the reconciliation record through ops.

Scenario Details:

- `callback.md` / `EXP-01`
- `reconciliation.md` / `REC-01`
- `reconciliation.md` / `REC-05`

## E2E-04 Webhook Retry And Manual Retry Path

Implementation Status: Future E2E - phase 08.

Steps:

- Finalize payment or refund.
- Create webhook event.
- Simulate HTTP 500, timeout, or network error.
- Verify retry schedule.
- Exhaust retries or use manual retry.
- Verify delivery attempts remain auditable.

Scenario Details:

- `webhook.md` / `WH-06`
- `webhook.md` / `WH-07`
- `webhook.md` / `WH-08`
- `webhook.md` / `WH-09`
- `webhook.md` / `WH-10`
