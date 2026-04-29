# Scenario Docs

This directory keeps the shared operating and testing scenarios for the mini
payment gateway.

The goal is alignment: product, backend, QA, and ops should be able to read the
same scenario and understand which API is called, which request and response are
expected, which tables change, and which phase owns the implementation.

## Files

- `e2e_scenarios.md` - scenario index and current capability snapshot.
- `happy_path.md` - target full journeys from merchant onboarding through
  payment, refund, webhook delivery, and reconciliation.
- `auth.md` - merchant HMAC authentication scenarios.
- `mer.md` - merchant readiness and onboarding scenarios.
- `pay.md` - payment creation, query, duplicate, and ownership scenarios.
- `callback.md` - provider payment callback and expiration scenarios.
- `refund.md` - full refund and refund callback scenarios.
- `webhook.md` - webhook event, delivery, retry, and manual retry scenarios.
- `ops.md` - ops state changes and audit scenarios.
- `reconciliation.md` - mismatch evidence and reconciliation resolution
  scenarios.
- `testing_matrix.md` - compact QA matrix mapping each scenario to current or
  future automated coverage.

## Status Legend

- `Implemented` - runnable in the current codebase.
- `Implemented with DB seed` - runnable today, but setup still uses direct DB
  seed because the ops API does not exist yet.
- `Planned - phase NN` - target behavior for a later phase.
- `Future E2E` - should become an automated end-to-end test in phase 08 after
  the underlying APIs exist.

## Current Runnable Slice

The current source can run merchant HMAC auth and payment intake:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_payment_api.py
```

That script seeds an active merchant and credential, calls the payment API,
queries the payment by transaction id and order id, and verifies the payment row
in PostgreSQL.

## Development Rule

When a later phase adds or changes behavior, update these scenario docs in the
same phase. The grouped scenario files are the shared contract; implementation
plans should point back here instead of redefining business behavior in
isolation.
