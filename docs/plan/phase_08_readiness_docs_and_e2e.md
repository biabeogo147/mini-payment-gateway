# Readiness Docs And E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish demo readiness with end-to-end tests, runbooks, sequence diagrams, and verification docs.

**Architecture:** This phase validates that the implemented slices work together and that operators/developers can run the MVP without reading source code. It adds no major business scope.

**Tech Stack:** FastAPI test client, SQLAlchemy test database strategy, Markdown docs, PlantUML sequence diagrams.

---

## Scope

Create the documentation and tests needed for internal demo readiness:

- E2E happy path.
- E2E duplicate/idempotency behavior.
- E2E late callback reconciliation behavior.
- Runbook.
- Merchant onboarding SOP.
- Webhook retry SOP.
- Reconciliation SOP.
- Sequence diagrams.

## Files

- Create: `backend/tests/test_e2e_payment_refund_webhook.py`
- Create: `plan/sequence/payment_flow.puml`
- Create: `plan/sequence/refund_flow.puml`
- Create: `plan/sequence/webhook_retry_flow.puml`
- Create: `plan/sequence/reconciliation_flow.puml`
- Create: `docs/runbook.md`
- Create: `docs/merchant_onboarding_sop.md`
- Create: `docs/webhook_retry_sop.md`
- Create: `docs/reconciliation_sop.md`
- Create: `docs/testing_matrix.md`
- Modify: `README.md` if a root README exists; otherwise create it if useful.

## Tasks

### Task 1: Add E2E Test Matrix

- [ ] Create `docs/testing_matrix.md`.
- [ ] Cover:
  - happy-path payment.
  - auth/signature failure.
  - duplicate payment pending.
  - payment success then duplicate create rejected.
  - payment expired then callback success goes to reconciliation.
  - full refund success.
  - refund window expired.
  - webhook retry success after failure.
  - manual webhook retry.
  - merchant suspended cannot create payment/refund.

### Task 2: Add E2E Test

- [ ] Create `backend/tests/test_e2e_payment_refund_webhook.py`.
- [ ] Seed:
  - internal ops user.
  - active merchant.
  - active credential.
  - approved onboarding case.
- [ ] Execute:
  - create payment.
  - provider success callback.
  - webhook event created.
  - create full refund.
  - provider refund success callback.
  - webhook event created.
- [ ] Run:

```powershell
cd backend
python -m unittest tests.test_e2e_payment_refund_webhook -v
```

- [ ] Expected: PASS.

### Task 3: Add Sequence Diagrams

- [ ] Create `plan/sequence/payment_flow.puml`.
- [ ] Create `plan/sequence/refund_flow.puml`.
- [ ] Create `plan/sequence/webhook_retry_flow.puml`.
- [ ] Create `plan/sequence/reconciliation_flow.puml`.
- [ ] Use PlantUML `sequenceDiagram` style via `@startuml`.
- [ ] Keep each diagram aligned with the implemented routes.

### Task 4: Add Runbook

- [ ] Create `docs/runbook.md`.
- [ ] Include:
  - install dependencies.
  - run migrations.
  - start API.
  - run tests.
  - create demo merchant.
  - simulate payment callback.
  - inspect webhook attempts.

### Task 5: Add SOPs

- [ ] Create `docs/merchant_onboarding_sop.md`.
- [ ] Create `docs/webhook_retry_sop.md`.
- [ ] Create `docs/reconciliation_sop.md`.
- [ ] Keep SOPs operator-focused and short.

### Task 6: Full Verification

- [ ] Run:

```powershell
cd backend
python -m unittest discover tests -v
```

- [ ] If pytest has been adopted, also run:

```powershell
cd backend
python -m pytest tests -q
```

- [ ] Start server:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

- [ ] Manually verify `/health` and generated OpenAPI docs.

### Task 7: Commit

- [ ] Stage readiness files.
- [ ] Commit message suggestion:

```text
docs: add demo readiness docs and e2e coverage
```

## Acceptance Criteria

- MVP can be demonstrated end-to-end.
- Docs explain how to operate core flows.
- Sequence diagrams exist for payment, refund, webhook retry, and reconciliation.
- No out-of-scope features are added.
