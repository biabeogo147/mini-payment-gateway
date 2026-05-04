# End-To-End Scenario Catalog

This file is the scenario index. Detailed end-to-end behavior is split into
small files by business group so each phase can update the scenarios it owns
without making one very large document harder to review.

## Status Legend

- `Implemented` - runnable through the current API.
- `Implemented with DB seed` - runnable today, but setup uses direct DB seed.
- `Planned - phase NN` - target behavior owned by a later phase.
- `Future E2E` - should be automated in phase 08.

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

Not implemented yet:

- Ops merchant onboarding APIs.
- Ops reconciliation review and audit services.
- Automated full E2E test.

## Scenario Files

| File | Scenario Groups | Owned Phases |
| --- | --- | --- |
| `happy_path.md` | E2E-01 to E2E-04 target journeys | Phase 08 |
| `auth.md` | AUTH-01 to AUTH-05 merchant authentication failures | Phase 02 |
| `mer.md` | MER-01 to MER-02, ONB-01 to ONB-04 merchant readiness and onboarding | Phase 02, Phase 07 |
| `pay.md` | PAY-01 to PAY-10 payment creation, query, duplicate, and ownership cases | Phase 03 |
| `callback.md` | CB-01 to CB-04 and EXP-01 provider callback and expiration cases | Phase 04 |
| `refund.md` | REF-01 to REF-09 refund creation, query, callback, and rejection cases | Phase 05 |
| `webhook.md` | WH-01 to WH-10 webhook event, delivery, retry, and manual retry cases | Phase 06 |
| `ops.md` | OPS-01 to OPS-03 and AUD-01 to AUD-02 ops and audit cases | Phase 07 |
| `reconciliation.md` | REC-01 to REC-05 reconciliation mismatch and resolution cases | Phase 04, Phase 07 |
| `testing_matrix.md` | Coverage mapping from scenario IDs to test targets | Phase 03.5, Phase 08 |

## Scenario Matrix

| Scenario | Main Actor | Detail File | APIs | Tables | Current Status | Owning Phase |
| --- | --- | --- | --- | --- | --- | --- |
| AUTH-01 Missing auth header fails | Merchant backend | `auth.md` | any merchant API | no business table change | Implemented | Phase 02 |
| AUTH-02 Invalid HMAC signature fails | Merchant backend | `auth.md` | any merchant API | no business table change | Implemented | Phase 02 |
| AUTH-03 Expired timestamp fails | Merchant backend | `auth.md` | any merchant API | no business table change | Implemented | Phase 02 |
| AUTH-04 Unknown merchant fails | Merchant backend | `auth.md` | any merchant API | no business table change | Implemented | Phase 02 |
| AUTH-05 Inactive credential fails | Merchant backend | `auth.md` | any merchant API | no business table change | Implemented | Phase 02 |
| MER-01 Active merchant can use payment/refund entry points | Merchant backend | `mer.md` | service entry points | `merchants`, `merchant_credentials` | Implemented | Phase 02 |
| MER-02 Non-active merchant cannot use payment/refund entry points | Merchant backend | `mer.md` | service entry points | no payment/refund insert | Implemented | Phase 02 |
| ONB-01 Ops registers merchant | Ops | `mer.md` | `/v1/ops/merchants` | `merchants`, `audit_logs` | Planned - phase 07 | Phase 07 |
| ONB-02 Ops submits onboarding case | Ops | `mer.md` | `/v1/ops/merchants/{merchant_id}/onboarding-case` | `merchant_onboarding_cases`, `audit_logs` | Planned - phase 07 | Phase 07 |
| ONB-03 Ops approves onboarding case | Ops | `mer.md` | `/v1/ops/onboarding-cases/{case_id}/approve` | `merchant_onboarding_cases`, `audit_logs` | Planned - phase 07 | Phase 07 |
| ONB-04 Ops activates merchant | Ops | `mer.md` | credential and activation APIs | `merchants`, `merchant_credentials`, `audit_logs` | Planned - phase 07 | Phase 07 |
| PAY-01 Active merchant creates payment | Merchant backend | `pay.md` | `POST /v1/payments` | `order_references`, `payment_transactions` | Implemented with DB seed | Phase 03 |
| PAY-02 Merchant queries payment by transaction id | Merchant backend | `pay.md` | `GET /v1/payments/{transaction_id}` | `payment_transactions` | Implemented with DB seed | Phase 03 |
| PAY-03 Merchant queries payment by order id | Merchant backend | `pay.md` | `GET /v1/payments/by-order/{order_id}` | `payment_transactions`, `order_references` | Implemented with DB seed | Phase 03 |
| PAY-04 Duplicate pending identical request | Merchant backend | `pay.md` | `POST /v1/payments` | `payment_transactions` | Implemented | Phase 03 |
| PAY-05 Duplicate pending mismatch | Merchant backend | `pay.md` | `POST /v1/payments` | no new payment insert | Implemented | Phase 03 |
| PAY-06 Previous failed payment allows new attempt | Merchant backend | `pay.md` | `POST /v1/payments` | `payment_transactions`, `order_references` | Implemented at service level | Phase 03 |
| PAY-07 Previous expired payment allows new attempt | Merchant backend | `pay.md` | `POST /v1/payments` | `payment_transactions`, `order_references` | Implemented at service level | Phase 03 |
| PAY-08 Previous success payment rejects new attempt | Merchant backend | `pay.md` | `POST /v1/payments` | no new payment insert | Implemented at service level | Phase 03 |
| PAY-09 Merchant cannot read another merchant payment | Merchant backend | `pay.md` | payment query APIs | no business table change | Implemented at service level | Phase 03 |
| PAY-10 Non-active merchant cannot create payment | Merchant backend | `pay.md` | `POST /v1/payments` | no payment insert | Implemented at service level | Phase 02, Phase 03 |
| CB-01 Payment success callback | Provider simulator | `callback.md` | `POST /v1/provider/callbacks/payment` | `bank_callback_logs`, `payment_transactions`, `webhook_events` | Implemented with DB seed | Phase 04, Phase 06 |
| CB-02 Payment failed callback | Provider simulator | `callback.md` | `POST /v1/provider/callbacks/payment` | `bank_callback_logs`, `payment_transactions`, `webhook_events` | Implemented | Phase 04, Phase 06 |
| CB-03 Unknown transaction callback | Provider simulator | `callback.md` | `POST /v1/provider/callbacks/payment` | `bank_callback_logs` | Implemented | Phase 04 |
| CB-04 Duplicate provider callback | Provider simulator | `callback.md` | `POST /v1/provider/callbacks/payment` | `bank_callback_logs`, `payment_transactions` | Implemented | Phase 04 |
| EXP-01 Expire overdue payment | System | `callback.md` | scheduled service or internal command | `payment_transactions`, `webhook_events` | Implemented at service level | Phase 04, Phase 06 |
| REC-01 Late success after expiration | Provider simulator, Ops | `reconciliation.md` | callback API, ops reconciliation API | `bank_callback_logs`, `reconciliation_records` | Evidence creation implemented; ops review planned | Phase 04, Phase 07 |
| REC-02 Callback amount mismatch | Provider simulator, Ops | `reconciliation.md` | callback API, ops reconciliation API | `bank_callback_logs`, `reconciliation_records` | Evidence creation implemented; ops review planned | Phase 04, Phase 07 |
| REF-01 Merchant creates full refund | Merchant backend | `refund.md` | `POST /v1/refunds` | `refund_transactions` | Implemented with DB seed | Phase 05 |
| REF-02 Merchant queries refund by transaction id | Merchant backend | `refund.md` | `GET /v1/refunds/{refund_transaction_id}` | `refund_transactions` | Implemented with DB seed | Phase 05 |
| REF-03 Merchant queries refund by merchant refund id | Merchant backend | `refund.md` | `GET /v1/refunds/by-refund-id/{refund_id}` | `refund_transactions` | Implemented with DB seed | Phase 05 |
| REF-04 Provider marks refund success | Provider simulator | `refund.md` | `POST /v1/provider/callbacks/refund` | `bank_callback_logs`, `refund_transactions`, `webhook_events` | Implemented with DB seed | Phase 05, Phase 06 |
| REF-05 Provider marks refund failed | Provider simulator | `refund.md` | `POST /v1/provider/callbacks/refund` | `bank_callback_logs`, `refund_transactions`, `webhook_events` | Implemented | Phase 05, Phase 06 |
| WH-01 Payment success creates webhook event | Gateway worker | `webhook.md` | internal event factory | `webhook_events` | Implemented | Phase 06 |
| WH-05 HTTP 2xx marks webhook delivered | Gateway worker | `webhook.md` | merchant webhook URL | `webhook_events`, `webhook_delivery_attempts` | Implemented with DB seed | Phase 06 |
| WH-10 Ops manual retry sends failed event again | Gateway worker, Ops | `webhook.md` | `POST /v1/ops/webhooks/{event_id}/retry` | `webhook_events`, `webhook_delivery_attempts` | Implemented without ops audit | Phase 06 |
| OPS-01 Ops suspends merchant | Ops | `ops.md` | suspend API | `merchants`, `audit_logs` | Planned - phase 07 | Phase 07 |
| OPS-02 Ops disables merchant | Ops | `ops.md` | disable API | `merchants`, `audit_logs` | Planned - phase 07 | Phase 07 |
| OPS-03 Credential rotation | Ops | `ops.md` | `/v1/ops/merchants/{merchant_id}/credentials/rotate` | `merchant_credentials`, `audit_logs` | Planned - phase 07 | Phase 07 |
| REC-05 Resolve reconciliation record | Ops | `reconciliation.md` | `POST /v1/ops/reconciliation/{record_id}/resolve` | `reconciliation_records`, `audit_logs` | Planned - phase 07 | Phase 07 |

## Runnable Smoke

The currently runnable end-to-end slices use DB seed for merchant setup, then
exercise payment creation, payment callbacks, refund creation, refund callbacks,
and reads:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_payment_api.py
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_provider_callback_api.py
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_refund_api.py
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_webhook_api.py
```

See `pay.md`, `callback.md`, `refund.md`, and `webhook.md` for the API and DB
effects of these runnable slices.
