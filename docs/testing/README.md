# Testing Docs

This folder maps business scenarios to automated checks.

## Start Here

- `e2e.md` - scenario index and current capability snapshot.
- `matrix.md` - compact QA matrix from scenario ID to automated coverage.
- `postman.md` - Postman import and execution guide for QA/QC, including one collection per file under `scenarios/`.
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

Dashboard verification from the repository root:

```bash
npm run merchant-dashboard:typecheck
npm run merchant-dashboard:test
npm run merchant-dashboard:build
npm run ops-dashboard:typecheck
npm run ops-dashboard:build
```

Compose validation from the repository root:

```bash
docker compose -f docker-compose.yml config --quiet
docker compose --env-file .env.sandbox.example -f docker-compose.sandbox.yml config --quiet
```

The sandbox compose file intentionally fails without required secret/database
environment variables. For local config validation, use `.env.sandbox.example`
or a real uncommitted sandbox `.env`.

## Dashboard Browser Smoke Checklist

Run this after migrations and demo seeding when a local or sandbox browser is
available.

Ops Dashboard:

- login as an internal Admin user;
- open Overview and confirm metrics/charts render without horizontal overflow;
- open Merchants, select a merchant, and inspect status, onboarding,
  credentials, and portal users;
- create or reset a merchant portal user and confirm the generated password is
  shown only in the immediate response;
- verify `OPS` users cannot manage internal users or merchant portal passwords;
- open Payments, Refunds, Webhooks, Reconciliation, and Audit detail pages.

Merchant Dashboard:

- login as the seeded merchant portal user;
- open Overview and confirm compact charts render;
- open Analytics, switch `7d`, `30d`, and `90d`, and read exact values through
  tooltips or `View data`;
- use an Analytics drill-down link and confirm the explorer receives query
  params;
- open Payments, Refunds, Webhooks, Profile, and Credentials;
- confirm profile/credentials are read-only and raw secrets are not exposed;
- change password and login again with the new password;
- resize to mobile width and confirm cards, badges, charts, and session/status
  panels do not overlap.
