# Phase Roadmap

This directory breaks the mini payment gateway plan into implementation phases.
Each phase is intended to produce a small, testable slice of the product without
pulling in out-of-scope features.

## Source Plans

- `docs/1_product_scope.md`
- `docs/2_bussiness_flow.md`
- `docs/3_requirement.md`
- `docs/4_module_and_core_entity.md`
- `docs/5_state_machine.md`
- `docs/6_necessary_document.md`
- `docs/7_usecase_diagram.md`
- `docs/architecture.md`
- `docs/scenarios/README.md`
- `docs/scenarios/e2e_scenarios.md` (scenario index)
- `docs/scenarios/happy_path.md`
- `docs/scenarios/auth.md`
- `docs/scenarios/mer.md`
- `docs/scenarios/pay.md`
- `docs/scenarios/callback.md`
- `docs/scenarios/refund.md`
- `docs/scenarios/webhook.md`
- `docs/scenarios/ops.md`
- `docs/scenarios/reconciliation.md`
- `docs/scenarios/testing_matrix.md`
- `docs/usecase_diagram.puml`

## Current Baseline

- Database models and Alembic migrations exist.
- API contract docs exist in `docs/api/`.
- Backend foundation exists with MVC-style `controllers/`, health controller,
  database dependency, standard `AppError`, and UTC time helper.
- Merchant auth foundation exists with HMAC helpers, merchant/credential
  repositories, auth service, auth dependency, and merchant readiness guards.
- Phase 2.5 completed the structural cleanup from `app.api` to
  `app.controllers`.
- Payment core exists with create payment, status query, order query, QR content,
  duplicate pending reuse, retry-after-failure/expiration, and success rejection
  rules.
- Phase 3.5 added the shared scenario catalog, split by business group, and
  testing matrix in `docs/scenarios/`.
- Provider callback and payment expiration exist with callback evidence logging,
  payment final-state transitions, and reconciliation evidence creation for
  ambiguous callbacks.
- Phase 05 refund core has an execution-ready plan covering refund service,
  refund callbacks, reconciliation evidence, smoke verification, and docs
  updates.
- Refund, webhook delivery, ops reconciliation review, audit workflows, and full
  simulator finalization flow are still pending.
- Existing tests cover schema contract, smoke verification, backend foundation,
  merchant auth, merchant readiness, payment core, provider callbacks, and
  expiration.

## Implementation Order

1. `phase_00_api_contract.md` - freeze API and webhook contracts before code. Completed.
2. `phase_01_backend_foundation.md` - create backend structure, dependency
   injection, error shape, and test scaffolding. Completed.
3. `phase_02_auth_and_merchant_readiness.md` - implement merchant HMAC auth and
   merchant operational readiness checks. Completed.
4. `phase_02_5_mvc_refactor.md` - reorganize backend into lightweight MVC
   layers before feature growth. Completed.
5. `phase_03_payment_core.md` - implement create payment and get payment status. Completed.
6. `phase_03_5_e2e_scenario_catalog.md` - document E2E operating and testing
   scenarios before continuing feature work. Completed.
7. `phase_04_provider_callback_and_expiration.md` - implement provider callback,
   callback logging, and expiration behavior. Completed.
8. `phase_05_refund_core.md` - implement full refund and refund status query.
9. `phase_06_webhook_delivery.md` - implement webhook events, signing, retry, and
   manual retry.
10. `phase_07_reconciliation_and_ops_audit.md` - implement reconciliation records
   and audit trail for internal actions.
11. `phase_08_readiness_docs_and_e2e.md` - finish docs, runbooks, and end-to-end
   demo tests.

## Dependency Map

```text
[done] API contract
  -> [done] backend foundation
  -> [done] merchant auth/readiness
  -> [done] MVC refactor
  -> [done] payment core
  -> [done] E2E scenario catalog
  -> [done] provider callback/expiration
  -> [next] refund core
  -> webhook delivery
  -> reconciliation/audit
  -> readiness docs/e2e
```

## Phase Rules

- Use TDD for implementation phases: write failing tests first, then implement.
- Keep controllers thin; business rules belong in services.
- Keep data access behind repositories or focused query helpers.
- Keep new HTTP files under `backend/app/controllers/` after phase 2.5.
- Do not add self-service merchant UI, settlement, dispute, multi-provider
  routing, partial refund, or analytics.
- Commit after each phase or after each independently testable task.

## Standard Verification Commands

Run from `backend/` unless noted otherwise.

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

When pytest is added:

```powershell
python -m pytest tests -q
```

When FastAPI controllers are implemented:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m uvicorn app.main:app --reload
```

When payment API smoke verification is needed:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_payment_api.py
```

When provider callback smoke verification is needed:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_provider_callback_api.py
```

## Latest Completion Record

- `phase_00_02_completion.md` records what changed, what was verified, and what
  remains for phase 2.5 and phase 03.
- `phase_02_5_completion.md` records the MVC refactor verification and the
  remaining phase 03 entry point.
- `phase_03_completion.md` records the payment core implementation and the next
  provider callback/expiration phase.
- `phase_03_5_completion.md` records the grouped scenario catalog and testing
  matrix added before provider callback work.
- `phase_04_completion.md` records provider callback, expiration, and
  reconciliation evidence implementation.
