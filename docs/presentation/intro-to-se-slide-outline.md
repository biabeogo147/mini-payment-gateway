# Intro To Software Engineering Slide Outline

This outline matches the final presentation requirements. It only includes
implemented functionality.

## Slide 1 - System Use Cases Implemented

Show the implemented actor map:

- Admin: internal privileged user for merchant onboarding/lifecycle,
  operational evidence, internal user management, and merchant portal user
  provisioning.
- Ops: internal day-to-day operations user for merchant lifecycle and
  operational evidence, including merchant portal user provisioning and support.
- Merchant backend: create/query payments and refunds through HMAC APIs.
- Provider simulator: payment/refund result callbacks.
- Scheduler/Timer: expiration and webhook retry triggers.
- Merchant portal user: read overview, analytics, payments, refunds, webhooks,
  profile, credentials, and change password.

Use `docs/product/use-cases.md` as the source.

## Slide 2 - Storyline Walkthrough

Demo flow:

1. Admin bootstraps the system and creates an Ops user.
2. Ops onboards the merchant and provisions its merchant portal user.
3. Merchant user logs into Merchant Dashboard.
4. Merchant reviews Overview and Analytics.
5. Merchant drills into Payments, Refunds, and Webhooks.
6. Ops shows audit/reconciliation or webhook recovery if time remains.

Avoid demoing settlement, disputes, export CSV, or merchant self-service
onboarding because they are not implemented.

## Slide 3 - System Architecture

Show the context diagram from `docs/architecture/system.md`:

- Ops Dashboard on `4173`
- Merchant Dashboard on `4174`
- FastAPI backend on `8000`
- PostgreSQL database
- Merchant backend, Provider simulator, Scheduler/Timer

Emphasize auth boundaries:

- Merchant API: HMAC
- Ops API: internal HttpOnly session
- Merchant Portal API: merchant HttpOnly session

## Slide 4 - Component Architecture And Design

Show backend layers:

- Controllers
- Schemas
- Services
- Repositories
- Models
- PostgreSQL/Alembic

Explain why the dashboards are separate apps:

- internal operations and merchant users have different permissions;
- Merchant Dashboard is read-only and scoped by session;
- Ops Dashboard owns internal provisioning and recovery actions, with RBAC
  retaining Admin-only internal-user and high-risk merchant controls.

## Slide 5 - Database Design

Use the ERD from `backend/app/models/README.md`.

Highlight:

- `merchants`
- `merchant_credentials`
- `merchant_users`
- `merchant_onboarding_cases`
- `payment_transactions`
- `refund_transactions`
- `webhook_events`
- `webhook_delivery_attempts`
- `bank_callback_logs`
- `reconciliation_records`
- `audit_logs`

Key constraints:

- one active credential per merchant;
- one pending payment per merchant/order;
- one refunded refund per payment;
- merchant portal users unique by merchant/email;
- analytics indexes on merchant/date fields.

## Slide 6 - API Design

Use `docs/api/README.md` as the source.

Explain API surfaces:

- Merchant API: payment/refund with HMAC headers.
- Provider callback API: simulator result ingestion.
- Ops API: internal authenticated operational routes.
- Merchant Portal API: merchant-scoped read-only dashboard routes.

Highlight scope isolation:

- Merchant Portal never accepts `merchant_id` from the client for data scope.
- Detail records outside the logged-in merchant return `404`.
- Raw secrets are never returned.

## Slide 7 - Component Implementation

Backend implementation points:

- FastAPI route modules define each API surface.
- Services enforce state transitions, RBAC, audit, and scope rules.
- Repositories hold query and analytics aggregation logic.
- Alembic migration `20260609_0007_merchant_portal.py` adds merchant portal
  database support.

Frontend implementation points:

- Ops Dashboard: React, Vite, TypeScript, TanStack Query.
- Merchant Dashboard: React, Vite, TypeScript, TanStack Query, Recharts.
- Analytics is lazy-loaded so Recharts is not part of the initial route bundle.

## Slide 8 - Testing And Evaluation

Show verification categories:

- backend unit/route/E2E tests;
- merchant portal auth/scope/analytics tests;
- frontend typecheck/build tests;
- Merchant Dashboard component tests;
- browser smoke on both dashboards;
- Docker Compose config validation.

Suggested commands:

```bash
& "C:\Download Apps\PyCharm\Projects\mini-payment-gateway\.venv\Scripts\python.exe" -m unittest discover tests -v
npm run merchant-dashboard:test
npm run merchant-dashboard:build
npm run ops-dashboard:build
```

## Slide 9 - Product Demonstration

Demo with seeded local/sandbox data:

- Ops Dashboard: `http://127.0.0.1:4173`
- Merchant Dashboard: `http://127.0.0.1:4174`
- Backend: `http://127.0.0.1:8000`

Keep the demo sequence short and evidence-driven. Show one example of RBAC or
merchant-scope isolation if time allows.
