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
- Provider callback, refund, webhook delivery, reconciliation, ops workflows,
  and simulator finalization flow are still pending.
- Existing tests cover schema contract, smoke verification, backend foundation,
  merchant auth, and merchant readiness.

## Implementation Order

1. `phase_00_api_contract.md` - freeze API and webhook contracts before code. Completed.
2. `phase_01_backend_foundation.md` - create backend structure, dependency
   injection, error shape, and test scaffolding. Completed.
3. `phase_02_auth_and_merchant_readiness.md` - implement merchant HMAC auth and
   merchant operational readiness checks. Completed.
4. `phase_02_5_mvc_refactor.md` - reorganize backend into lightweight MVC
   layers before feature growth. Completed.
5. `phase_03_payment_core.md` - implement create payment and get payment status. Completed.
6. `phase_04_provider_callback_and_expiration.md` - implement provider callback,
   callback logging, and expiration behavior.
7. `phase_05_refund_core.md` - implement full refund and refund status query.
8. `phase_06_webhook_delivery.md` - implement webhook events, signing, retry, and
   manual retry.
9. `phase_07_reconciliation_and_ops_audit.md` - implement reconciliation records
   and audit trail for internal actions.
10. `phase_08_readiness_docs_and_e2e.md` - finish docs, runbooks, and end-to-end
   demo tests.

## Dependency Map

```text
[done] API contract
  -> [done] backend foundation
  -> [done] merchant auth/readiness
  -> [done] MVC refactor
  -> [done] payment core
  -> [next] provider callback/expiration
  -> refund core
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

## Latest Completion Record

- `phase_00_02_completion.md` records what changed, what was verified, and what
  remains for phase 2.5 and phase 03.
- `phase_02_5_completion.md` records the MVC refactor verification and the
  remaining phase 03 entry point.
- `phase_03_completion.md` records the payment core implementation and the next
  provider callback/expiration phase.
