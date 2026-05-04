# End-To-End Scenario Catalog

This file is the scenario index. Detailed end-to-end behavior is split into
small files by business group so each phase can update the scenarios it owns
without making one very large document harder to review.

## Status Legend

- `Implemented` - runnable through the current API.
- `Implemented with DB seed` - runnable today, but setup uses direct DB seed.
- `Automated E2E` - covered by route-level end-to-end tests.
- `Planned - phase NN` - target behavior owned by a later phase.

## Current Capability Snapshot

Implemented now:

- `/health`
- Merchant HMAC authentication.
- Merchant readiness checks for payment/refund service entry points.
- `POST /v1/payments`
- `GET /v1/payments/{transaction_id}`
- `GET /v1/payments/by-order/{order_id}`
- Payment persistence as `PENDING`.
- Duplicate pending payment reuse when the create request is semantically
  identical.
- Duplicate pending mismatch rejection.
- Success-order duplicate rejection at service level.
- `POST /v1/provider/callbacks/payment`
- Provider payment callback evidence logging.
- Payment callback transitions from `PENDING` to `SUCCESS` or `FAILED`.
- Payment expiration service for overdue `PENDING` payments.
- Reconciliation evidence creation for amount mismatch or late success after
  expiration.
- `POST /v1/refunds`
- `GET /v1/refunds/{refund_transaction_id}`
- `GET /v1/refunds/by-refund-id/{refund_id}`
- `POST /v1/provider/callbacks/refund`
- Refund callback evidence logging.
- Refund callback transitions from `REFUND_PENDING` to `REFUNDED` or
  `REFUND_FAILED`.
- Refund reconciliation evidence creation for amount mismatch or final-state
  conflict.
- Webhook event creation for final payment/refund states when merchant has
  `webhook_url`.
- Signed webhook delivery with persisted delivery attempts.
- Webhook retry state for HTTP failure, timeout, and network error.
- `POST /v1/ops/webhooks/{event_id}/retry` for internal manual retry of failed
  webhook events.
- `POST /v1/ops/merchants` for internal merchant registration.
- `PUT /v1/ops/merchants/{merchant_id}/onboarding-case`.
- `POST /v1/ops/merchants/{merchant_id}/onboarding-case/approve` and
  `/reject`.
- `POST /v1/ops/merchants/{merchant_id}/credentials` and
  `/credentials/rotate`.
- `POST /v1/ops/merchants/{merchant_id}/activate`, `/suspend`, and `/disable`.
- `GET /v1/ops/reconciliation`, `GET /v1/ops/reconciliation/{record_id}`, and
  `POST /v1/ops/reconciliation/{record_id}/resolve`.
- Audit logging for ops merchant actions, credential operations,
  reconciliation resolution, and optional webhook manual retry actor context.
- Automated E2E tests for:
  - ops onboarding -> active credential -> payment success -> payment webhook ->
    full refund -> refund webhook;
  - duplicate pending payment replay with fixed `expire_at`, bad HMAC failure,
    pending mismatch, and success-order rejection;
  - late success callback reconciliation and ops resolution;
  - webhook retry exhaustion, manual retry audit, and suspended merchant
    payment/refund rejection.

Not implemented yet:

- Full internal auth/JWT/RBAC for ops users.
- Production settlement, disputes, analytics, multi-provider routing, and
  partial refunds.

## Scenario Files

| File | Scenario Groups | Owned Phases |
| --- | --- | --- |
| `scenarios/happy-path.md` | E2E-01 to E2E-04 target journeys | Phase 08 |
| `scenarios/auth.md` | AUTH-01 to AUTH-05 merchant authentication failures | Phase 02 |
| `scenarios/merchant.md` | MER-01 to MER-02, ONB-01 to ONB-04 merchant readiness and onboarding | Phase 02, Phase 07 |
| `scenarios/payment.md` | PAY-01 to PAY-10 payment creation, query, duplicate, and ownership cases | Phase 03 |
| `scenarios/callback.md` | CB-01 to CB-04 and EXP-01 provider callback and expiration cases | Phase 04 |
| `scenarios/refund.md` | REF-01 to REF-09 refund creation, query, callback, and rejection cases | Phase 05 |
| `scenarios/webhook.md` | WH-01 to WH-10 webhook event, delivery, retry, and manual retry cases | Phase 06 |
| `scenarios/ops.md` | OPS-01 to OPS-03 and AUD-01 to AUD-02 ops and audit cases | Phase 07 |
| `scenarios/reconciliation.md` | REC-01 to REC-05 reconciliation mismatch and resolution cases | Phase 04, Phase 07 |
| `matrix.md` | Coverage mapping from scenario IDs to test targets | Phase 03.5, Phase 08 |

## Scenario Matrix

| Scenario | Main Actor | Detail File | APIs | Tables | Current Status | Owning Phase |
| --- | --- | --- | --- | --- | --- | --- |
| AUTH-01 Missing auth header fails | Merchant backend | `scenarios/auth.md` | any merchant API | no business table change | Implemented | Phase 02 |
| AUTH-02 Invalid HMAC signature fails | Merchant backend | `scenarios/auth.md` | any merchant API | no business table change | Implemented | Phase 02 |
| AUTH-03 Expired timestamp fails | Merchant backend | `scenarios/auth.md` | any merchant API | no business table change | Implemented | Phase 02 |
| AUTH-04 Unknown merchant fails | Merchant backend | `scenarios/auth.md` | any merchant API | no business table change | Implemented | Phase 02 |
| AUTH-05 Inactive credential fails | Merchant backend | `scenarios/auth.md` | any merchant API | no business table change | Implemented | Phase 02 |
| MER-01 Active merchant can use payment/refund entry points | Merchant backend | `scenarios/merchant.md` | service entry points | `merchants`, `merchant_credentials` | Implemented | Phase 02 |
| MER-02 Non-active merchant cannot use payment/refund entry points | Merchant backend | `scenarios/merchant.md` | service entry points | no payment/refund insert | Implemented | Phase 02 |
| ONB-01 Ops registers merchant | Ops | `scenarios/merchant.md` | `/v1/ops/merchants` | `merchants`, `audit_logs` | Implemented | Phase 07 |
| ONB-02 Ops submits onboarding case | Ops | `scenarios/merchant.md` | `/v1/ops/merchants/{merchant_id}/onboarding-case` | `merchant_onboarding_cases`, `audit_logs` | Implemented | Phase 07 |
| ONB-03 Ops approves onboarding case | Ops | `scenarios/merchant.md` | `/v1/ops/merchants/{merchant_id}/onboarding-case/approve` | `merchant_onboarding_cases`, `audit_logs` | Implemented | Phase 07 |
| ONB-04 Ops activates merchant | Ops | `scenarios/merchant.md` | credential and activation APIs | `merchants`, `merchant_credentials`, `audit_logs` | Implemented | Phase 07 |
| PAY-01 Active merchant creates payment | Merchant backend | `scenarios/payment.md` | `POST /v1/payments` | `order_references`, `payment_transactions` | Implemented with DB seed | Phase 03 |
| PAY-02 Merchant queries payment by transaction id | Merchant backend | `scenarios/payment.md` | `GET /v1/payments/{transaction_id}` | `payment_transactions` | Implemented with DB seed | Phase 03 |
| PAY-03 Merchant queries payment by order id | Merchant backend | `scenarios/payment.md` | `GET /v1/payments/by-order/{order_id}` | `payment_transactions`, `order_references` | Implemented with DB seed | Phase 03 |
| PAY-04 Duplicate pending identical request | Merchant backend | `scenarios/payment.md` | `POST /v1/payments` | `payment_transactions` | Implemented | Phase 03 |
| PAY-05 Duplicate pending mismatch | Merchant backend | `scenarios/payment.md` | `POST /v1/payments` | no new payment insert | Implemented | Phase 03 |
| PAY-06 Previous failed payment allows new attempt | Merchant backend | `scenarios/payment.md` | `POST /v1/payments` | `payment_transactions`, `order_references` | Implemented at service level | Phase 03 |
| PAY-07 Previous expired payment allows new attempt | Merchant backend | `scenarios/payment.md` | `POST /v1/payments` | `payment_transactions`, `order_references` | Implemented at service level | Phase 03 |
| PAY-08 Previous success payment rejects new attempt | Merchant backend | `scenarios/payment.md` | `POST /v1/payments` | no new payment insert | Implemented at service level | Phase 03 |
| PAY-09 Merchant cannot read another merchant payment | Merchant backend | `scenarios/payment.md` | payment query APIs | no business table change | Implemented at service level | Phase 03 |
| PAY-10 Non-active merchant cannot create payment | Merchant backend | `scenarios/payment.md` | `POST /v1/payments` | no payment insert | Implemented at service level | Phase 02, Phase 03 |
| CB-01 Payment success callback | Provider simulator | `scenarios/callback.md` | `POST /v1/provider/callbacks/payment` | `bank_callback_logs`, `payment_transactions`, `webhook_events` | Implemented with DB seed | Phase 04, Phase 06 |
| CB-02 Payment failed callback | Provider simulator | `scenarios/callback.md` | `POST /v1/provider/callbacks/payment` | `bank_callback_logs`, `payment_transactions`, `webhook_events` | Implemented | Phase 04, Phase 06 |
| CB-03 Unknown transaction callback | Provider simulator | `scenarios/callback.md` | `POST /v1/provider/callbacks/payment` | `bank_callback_logs` | Implemented | Phase 04 |
| CB-04 Duplicate provider callback | Provider simulator | `scenarios/callback.md` | `POST /v1/provider/callbacks/payment` | `bank_callback_logs`, `payment_transactions` | Implemented | Phase 04 |
| EXP-01 Expire overdue payment | System | `scenarios/callback.md` | scheduled service or internal command | `payment_transactions`, `webhook_events` | Implemented at service level | Phase 04, Phase 06 |
| REC-01 Late success after expiration | Provider simulator, Ops | `scenarios/reconciliation.md` | callback API, ops reconciliation API | `bank_callback_logs`, `reconciliation_records`, `audit_logs` | Implemented | Phase 04, Phase 07 |
| REC-02 Callback amount mismatch | Provider simulator, Ops | `scenarios/reconciliation.md` | callback API, ops reconciliation API | `bank_callback_logs`, `reconciliation_records`, `audit_logs` | Implemented | Phase 04, Phase 07 |
| REF-01 Merchant creates full refund | Merchant backend | `scenarios/refund.md` | `POST /v1/refunds` | `refund_transactions` | Implemented with DB seed | Phase 05 |
| REF-02 Merchant queries refund by transaction id | Merchant backend | `scenarios/refund.md` | `GET /v1/refunds/{refund_transaction_id}` | `refund_transactions` | Implemented with DB seed | Phase 05 |
| REF-03 Merchant queries refund by merchant refund id | Merchant backend | `scenarios/refund.md` | `GET /v1/refunds/by-refund-id/{refund_id}` | `refund_transactions` | Implemented with DB seed | Phase 05 |
| REF-04 Provider marks refund success | Provider simulator | `scenarios/refund.md` | `POST /v1/provider/callbacks/refund` | `bank_callback_logs`, `refund_transactions`, `webhook_events` | Implemented with DB seed | Phase 05, Phase 06 |
| REF-05 Provider marks refund failed | Provider simulator | `scenarios/refund.md` | `POST /v1/provider/callbacks/refund` | `bank_callback_logs`, `refund_transactions`, `webhook_events` | Implemented | Phase 05, Phase 06 |
| WH-01 Payment success creates webhook event | Gateway worker | `scenarios/webhook.md` | internal event factory | `webhook_events` | Implemented | Phase 06 |
| WH-05 HTTP 2xx marks webhook delivered | Gateway worker | `scenarios/webhook.md` | merchant webhook URL | `webhook_events`, `webhook_delivery_attempts` | Implemented with DB seed | Phase 06 |
| WH-10 Ops manual retry sends failed event again | Gateway worker, Ops | `scenarios/webhook.md` | `POST /v1/ops/webhooks/{event_id}/retry` | `webhook_events`, `webhook_delivery_attempts`, `audit_logs` | Implemented | Phase 06, Phase 07 |
| OPS-01 Ops suspends merchant | Ops | `scenarios/ops.md` | suspend API | `merchants`, `audit_logs` | Implemented | Phase 07 |
| OPS-02 Ops disables merchant | Ops | `scenarios/ops.md` | disable API | `merchants`, `audit_logs` | Implemented | Phase 07 |
| OPS-03 Credential rotation | Ops | `scenarios/ops.md` | `/v1/ops/merchants/{merchant_id}/credentials/rotate` | `merchant_credentials`, `audit_logs` | Implemented | Phase 07 |
| REC-05 Resolve reconciliation record | Ops | `scenarios/reconciliation.md` | `POST /v1/ops/reconciliation/{record_id}/resolve` | `reconciliation_records`, `audit_logs` | Implemented | Phase 07 |
| E2E-01 Merchant onboarding to successful payment and refund | Ops, Merchant backend, Provider simulator, Gateway worker | `scenarios/happy-path.md` | ops, payment, callback, refund, webhook APIs | `merchants`, `merchant_credentials`, `payment_transactions`, `refund_transactions`, `webhook_events`, `webhook_delivery_attempts`, `audit_logs` | Automated E2E | Phase 08 |
| E2E-02 Duplicate and idempotency path | Merchant backend | `scenarios/happy-path.md` | `POST /v1/payments` | `payment_transactions` | Automated E2E | Phase 08 |
| E2E-03 Late callback reconciliation path | Provider simulator, Ops | `scenarios/happy-path.md` | callback API, ops reconciliation API | `payment_transactions`, `bank_callback_logs`, `reconciliation_records`, `audit_logs` | Automated E2E | Phase 08 |
| E2E-04 Webhook retry and manual retry path | Gateway worker, Ops | `scenarios/happy-path.md` | webhook retry API, suspend API, merchant APIs | `webhook_events`, `webhook_delivery_attempts`, `audit_logs`, `merchants` | Automated E2E | Phase 08 |

## Runnable Verification

The route-level E2E test uses the phase 07 ops APIs instead of DB seed:

```bash
cd backend
python -m unittest tests.test_e2e_payment_refund_webhook -v
```

The smoke scripts still provide runnable slices for payment creation, callbacks,
refunds, webhooks, and ops reconciliation:

```bash
cd backend
python scripts/smoke_payment_api.py
python scripts/smoke_provider_callback_api.py
python scripts/smoke_refund_api.py
python scripts/smoke_webhook_api.py
python scripts/smoke_ops_reconciliation_api.py
```

See `scenarios/payment.md`, `scenarios/callback.md`, `scenarios/refund.md`, `scenarios/webhook.md`, `scenarios/merchant.md`, `scenarios/ops.md`,
and `scenarios/reconciliation.md` for the API and DB effects of these runnable slices.
