# Testing Docs

This folder maps business scenarios to automated checks.

## Start Here

- `e2e.md` - scenario index and current capability snapshot.
- `matrix.md` - compact QA matrix from scenario ID to automated coverage.
- `scenarios/` - detailed behavior by business area.

## Scenario Files

- `scenarios/auth.md` - merchant HMAC authentication.
- `scenarios/merchant.md` - merchant readiness and onboarding.
- `scenarios/payment.md` - payment creation, query, duplicate, and ownership.
- `scenarios/callback.md` - provider callbacks and expiration.
- `scenarios/refund.md` - full refund and refund callbacks.
- `scenarios/webhook.md` - webhook event, delivery, retry, and manual retry.
- `scenarios/ops.md` - ops state changes and audit behavior.
- `scenarios/reconciliation.md` - mismatch evidence and resolution.
- `scenarios/happy-path.md` - full E2E journeys.

## Verification Commands

```bash
cd backend
python -m unittest discover tests -v
python -m unittest tests.test_e2e_payment_refund_webhook -v
```
