# Phase Roadmap

This directory breaks the mini payment gateway plan into implementation phases.
Each phase is intended to produce a small, testable slice of the product without
pulling in out-of-scope features.

## Source Plans

- `plan/1_product_scope.md`
- `plan/2_bussiness_flow.md`
- `plan/3_requirement.md`
- `plan/4_module_and_core_entity.md`
- `plan/5_state_machine.md`
- `plan/6_necessary_document.md`
- `plan/7_usecase_diagram.md`
- `plan/usecase_diagram.puml`

## Current Baseline

- Database models and Alembic migrations exist.
- The backend exposes only a FastAPI healthcheck.
- No service layer, route layer, schema layer, auth layer, webhook worker, or
  simulator flow exists yet.
- Existing tests focus on schema contract and smoke verification.

## Implementation Order

1. `phase_00_api_contract.md` - freeze API and webhook contracts before code.
2. `phase_01_backend_foundation.md` - create backend structure, dependency
   injection, error shape, and test scaffolding.
3. `phase_02_auth_and_merchant_readiness.md` - implement merchant HMAC auth and
   merchant operational readiness checks.
4. `phase_03_payment_core.md` - implement create payment and get payment status.
5. `phase_04_provider_callback_and_expiration.md` - implement provider callback,
   callback logging, and expiration behavior.
6. `phase_05_refund_core.md` - implement full refund and refund status query.
7. `phase_06_webhook_delivery.md` - implement webhook events, signing, retry, and
   manual retry.
8. `phase_07_reconciliation_and_ops_audit.md` - implement reconciliation records
   and audit trail for internal actions.
9. `phase_08_readiness_docs_and_e2e.md` - finish docs, runbooks, and end-to-end
   demo tests.

## Dependency Map

```text
API contract
  -> backend foundation
  -> merchant auth/readiness
  -> payment core
  -> provider callback/expiration
  -> refund core
  -> webhook delivery
  -> reconciliation/audit
  -> readiness docs/e2e
```

## Phase Rules

- Use TDD for implementation phases: write failing tests first, then implement.
- Keep route handlers thin; business rules belong in services.
- Keep data access behind repositories or focused query helpers.
- Do not add self-service merchant UI, settlement, dispute, multi-provider
  routing, partial refund, or analytics.
- Commit after each phase or after each independently testable task.

## Standard Verification Commands

Run from `backend/` unless noted otherwise.

```powershell
python -m unittest discover tests -v
```

When pytest is added:

```powershell
python -m pytest tests -q
```

When FastAPI routes are implemented:

```powershell
python -m uvicorn app.main:app --reload
```
