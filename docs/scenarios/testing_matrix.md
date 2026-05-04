# Testing Matrix

This matrix maps scenario coverage to current and future automated checks.

Status values:

- `Covered` - automated coverage exists now.
- `Partially covered` - some service/route behavior exists, but full E2E waits
  for later phases.
- `Planned` - expected in a later phase.

## Scenario Group Files

| Scenario Prefix | Detail File |
| --- | --- |
| AUTH | `auth.md` |
| MER, ONB | `mer.md` |
| PAY | `pay.md` |
| CB, EXP | `callback.md` |
| REF | `refund.md` |
| WH | `webhook.md` |
| OPS, AUD | `ops.md` |
| REC | `reconciliation.md` |
| E2E | `happy_path.md` |

| Scenario ID | Scenario Name | Test Type | Owning Phase | Current Status | Automatable Now | Target Automated Test |
| --- | --- | --- | --- | --- | --- | --- |
| AUTH-01 | Missing auth header fails | Unit/service | Phase 02 | Covered | Yes | `backend/tests/test_auth_service.py` |
| AUTH-02 | Invalid HMAC signature fails | Unit/service | Phase 02 | Covered | Yes | `backend/tests/test_auth_service.py` |
| AUTH-03 | Expired timestamp fails | Unit/service | Phase 02 | Covered | Yes | `backend/tests/test_auth_service.py` |
| AUTH-04 | Unknown merchant fails | Unit/service | Phase 02 | Covered | Yes | `backend/tests/test_auth_service.py` |
| AUTH-05 | Inactive credential fails | Unit/service | Phase 02 | Covered | Yes | `backend/tests/test_auth_service.py` |
| MER-01 | Active merchant can create payment/refund | Unit/service | Phase 02 | Covered | Yes | `backend/tests/test_merchant_readiness.py` |
| MER-02 | Non-active merchant cannot create payment/refund | Unit/service | Phase 02 | Covered | Yes | `backend/tests/test_merchant_readiness.py` |
| PAY-01 | Active merchant creates payment | Service, route, smoke | Phase 03 | Covered with DB seed | Yes | `backend/tests/test_payment_service.py`, `backend/tests/test_payment_routes.py`, `backend/scripts/smoke_payment_api.py` |
| PAY-02 | Query payment by transaction id | Service, route, smoke | Phase 03 | Covered with DB seed | Yes | `backend/tests/test_payment_service.py`, `backend/tests/test_payment_routes.py`, `backend/scripts/smoke_payment_api.py` |
| PAY-03 | Query payment by order id | Service, route, smoke | Phase 03 | Covered with DB seed | Yes | `backend/tests/test_payment_service.py`, `backend/tests/test_payment_routes.py`, `backend/scripts/smoke_payment_api.py` |
| PAY-04 | Duplicate pending identical request returns existing transaction | Service | Phase 03 | Covered | Yes | `backend/tests/test_payment_service.py` |
| PAY-05 | Duplicate pending mismatch rejects | Service | Phase 03 | Covered | Yes | `backend/tests/test_payment_service.py` |
| PAY-06 | Previous failed payment allows new attempt | Service | Phase 03 | Covered | Yes | `backend/tests/test_payment_service.py` |
| PAY-07 | Previous expired payment allows new attempt | Service | Phase 03 | Covered | Yes | `backend/tests/test_payment_service.py` |
| PAY-08 | Previous success payment rejects new attempt | Service | Phase 03 | Covered | Yes | `backend/tests/test_payment_service.py` |
| PAY-09 | Query another merchant's payment returns not found | Service | Phase 03 | Covered | Yes | `backend/tests/test_payment_service.py` |
| PAY-10 | Non-active merchant cannot create payment | Service | Phase 02, Phase 03 | Covered | Yes | `backend/tests/test_merchant_readiness.py`, `backend/tests/test_payment_service.py` |
| ONB-01 | Ops registers merchant | Service, route, E2E | Phase 07 | Planned | No | `backend/tests/test_merchant_ops_service.py` |
| ONB-02 | Ops submits onboarding case | Service, route, E2E | Phase 07 | Planned | No | `backend/tests/test_merchant_ops_service.py` |
| ONB-03 | Ops approves onboarding case | Service, route, E2E | Phase 07 | Planned | No | `backend/tests/test_merchant_ops_service.py` |
| ONB-04 | Ops activates merchant with approved onboarding and active credential | Service, route, E2E | Phase 07 | Planned | No | `backend/tests/test_merchant_ops_service.py` |
| OPS-01 | Ops suspends merchant | Service, route, E2E | Phase 07 | Planned | No | `backend/tests/test_merchant_ops_service.py` |
| OPS-02 | Ops disables merchant | Service, route, E2E | Phase 07 | Planned | No | `backend/tests/test_merchant_ops_service.py` |
| OPS-03 | Credential rotation leaves one active credential | Service, route, E2E | Phase 07 | Planned | No | `backend/tests/test_merchant_ops_service.py` |
| CB-01 | Payment success callback marks payment success | Service, route, smoke | Phase 04 | Covered with DB seed | Yes | `backend/tests/test_provider_callback_service.py`, `backend/tests/test_provider_callback_routes.py`, `backend/scripts/smoke_provider_callback_api.py` |
| CB-02 | Payment failed callback marks payment failed | Service | Phase 04 | Covered | Yes | `backend/tests/test_provider_callback_service.py` |
| CB-03 | Unknown transaction callback is logged | Service | Phase 04 | Covered | Yes | `backend/tests/test_provider_callback_service.py` |
| CB-04 | Duplicate provider callback is safe | Service | Phase 04 | Covered | Yes | `backend/tests/test_provider_callback_service.py` |
| EXP-01 | Overdue pending payment expires | Service | Phase 04 | Covered | Yes | `backend/tests/test_expiration_service.py` |
| REC-01 | Late success after expiration creates reconciliation evidence | Service | Phase 04, Phase 07 | Partially covered | Yes | `backend/tests/test_provider_callback_service.py`, later `backend/tests/test_reconciliation_service.py` |
| REC-02 | Callback amount mismatch creates reconciliation evidence | Service | Phase 04, Phase 07 | Partially covered | Yes | `backend/tests/test_provider_callback_service.py`, later `backend/tests/test_reconciliation_service.py` |
| REF-01 | Successful payment can create full refund | Service, route, smoke | Phase 05 | Covered with DB seed | Yes | `backend/tests/test_refund_service.py`, `backend/tests/test_refund_routes.py`, `backend/scripts/smoke_refund_api.py` |
| REF-02 | Refund query by transaction id | Service, route, smoke | Phase 05 | Covered with DB seed | Yes | `backend/tests/test_refund_service.py`, `backend/tests/test_refund_routes.py`, `backend/scripts/smoke_refund_api.py` |
| REF-03 | Refund query by merchant refund id | Service, route, smoke | Phase 05 | Covered with DB seed | Yes | `backend/tests/test_refund_service.py`, `backend/tests/test_refund_routes.py`, `backend/scripts/smoke_refund_api.py` |
| REF-04 | Refund provider success callback marks refunded | Service, route, smoke | Phase 05 | Covered with DB seed | Yes | `backend/tests/test_refund_state_machine.py`, `backend/tests/test_provider_callback_service.py`, `backend/tests/test_provider_callback_routes.py`, `backend/scripts/smoke_refund_api.py` |
| REF-05 | Refund provider failed callback marks failed | Service, route | Phase 05 | Covered | Yes | `backend/tests/test_refund_state_machine.py`, `backend/tests/test_provider_callback_service.py`, `backend/tests/test_provider_callback_routes.py` |
| REF-06 | Partial refund rejects | Service | Phase 05 | Covered | Yes | `backend/tests/test_refund_service.py` |
| REF-07 | Refund after 7-day window rejects | Service | Phase 05 | Covered | Yes | `backend/tests/test_refund_service.py` |
| REF-08 | Duplicate refund id returns existing refund | Service | Phase 05 | Covered | Yes | `backend/tests/test_refund_service.py` |
| REF-09 | Refund against non-success payment rejects | Service | Phase 05 | Covered | Yes | `backend/tests/test_refund_service.py` |
| WH-01 | Payment success creates webhook event | Service, hook, smoke | Phase 06 | Covered with DB seed | Yes | `backend/tests/test_webhook_event_factory.py`, `backend/tests/test_webhook_hooks.py`, `backend/scripts/smoke_webhook_api.py` |
| WH-02 | Payment failure creates webhook event | Service, hook | Phase 06 | Covered | Yes | `backend/tests/test_webhook_event_factory.py`, `backend/tests/test_webhook_hooks.py` |
| WH-03 | Payment expiration creates webhook event | Service, hook | Phase 06 | Covered | Yes | `backend/tests/test_webhook_event_factory.py`, `backend/tests/test_webhook_hooks.py` |
| WH-04 | Refund success creates webhook event | Service, hook | Phase 06 | Covered | Yes | `backend/tests/test_webhook_event_factory.py`, `backend/tests/test_webhook_hooks.py` |
| WH-05 | HTTP 2xx marks webhook delivered | Service, smoke | Phase 06 | Covered with DB seed | Yes | `backend/tests/test_webhook_delivery_service.py`, `backend/scripts/smoke_webhook_api.py` |
| WH-06 | HTTP 500 schedules retry | Service | Phase 06 | Covered | Yes | `backend/tests/test_webhook_delivery_service.py` |
| WH-07 | Timeout schedules retry | Service | Phase 06 | Covered | Yes | `backend/tests/test_webhook_delivery_service.py` |
| WH-08 | Network error schedules retry | Service | Phase 06 | Covered | Yes | `backend/tests/test_webhook_delivery_service.py` |
| WH-09 | Attempt 4 exhaustion marks failed | Service | Phase 06 | Covered | Yes | `backend/tests/test_webhook_retry_policy.py`, `backend/tests/test_webhook_delivery_service.py` |
| WH-10 | Ops manual retry sends failed event again | Route, service | Phase 06 | Covered without ops audit | Yes | `backend/tests/test_webhook_delivery_service.py`, `backend/tests/test_webhook_ops_routes.py` |
| AUD-01 | Ops merchant action writes audit log | Service | Phase 07 | Planned | No | `backend/tests/test_audit_service.py` |
| AUD-02 | Credential rotation writes audit log | Service | Phase 07 | Planned | No | `backend/tests/test_audit_service.py` |
| REC-03 | Matching provider evidence creates matched record | Service | Phase 07 | Planned | No | `backend/tests/test_reconciliation_service.py` |
| REC-04 | Status or amount mismatch creates mismatched record | Service | Phase 07 | Planned | No | `backend/tests/test_reconciliation_service.py` |
| REC-05 | Ops resolves reconciliation record | Service, route | Phase 07 | Planned | No | `backend/tests/test_reconciliation_service.py` |
| E2E-01 | Merchant onboarding to successful payment and refund | E2E | Phase 08 | Planned | No | `backend/tests/test_e2e_payment_refund_webhook.py` |
| E2E-02 | Duplicate and idempotency path | E2E | Phase 08 | Planned | No | `backend/tests/test_e2e_payment_refund_webhook.py` |
| E2E-03 | Late callback reconciliation path | E2E | Phase 08 | Planned | No | `backend/tests/test_e2e_payment_refund_webhook.py` |
| E2E-04 | Webhook retry and manual retry path | E2E | Phase 08 | Planned | No | `backend/tests/test_e2e_payment_refund_webhook.py` |
