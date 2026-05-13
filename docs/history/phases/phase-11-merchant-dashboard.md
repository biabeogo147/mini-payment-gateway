# Merchant Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a merchant dashboard so merchant users can inspect payment,
refund, webhook, and integration health data without calling gateway APIs
manually for read-only workflows.

**Architecture:** Phase 11 adds a separate merchant-facing internal web app plus
merchant-scoped auth/read/search/stat APIs. The existing FastAPI backend remains
the system of record. Merchant dashboard traffic is strictly scoped to the
merchant's own data and does not expose internal ops-only state such as global
audit trails or other merchants' records.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, existing payment/refund/webhook
models and services, merchant-user auth/session layer, React + Vite +
TypeScript, React Router, TanStack Query, and a lightweight charting library.

---

## Implementation Status

Planning only. Do not implement this phase until the user explicitly requests
it.

This plan assumes:

- phase 10 owns the internal Ops dashboard and internal user auth surface;
- phase 11 owns only the merchant dashboard;
- worker/scheduler automation remains out of scope for this phase and moves to
  phase 12;
- the merchant dashboard is intentionally light and read-heavy, matching the
  mini gateway product scope.

Use the current repository checkout directly. Do not create a branch or worktree
unless the user asks for one. Commit only when requested.

## Scope

Implement:

- merchant user authentication;
- a merchant-scoped dashboard web app;
- dashboard summary/stat APIs for merchant-visible cards and charts;
- merchant-scoped payment, refund, and webhook read/search/detail APIs;
- merchant profile and integration read-only pages;
- merchant credential metadata read-only page;
- docs updates for the merchant dashboard and auth model.

Do not implement:

- self-service merchant onboarding;
- settlement, payout, ledger, dispute, or chargeback features;
- self-service rotate credential in the first phase unless later approved;
- merchant editing of sensitive config such as webhook URL or allowed IP list
  without a separate approval design;
- internal audit log access;
- public signup or invitation self-service flows;
- worker/scheduler automation.

## Product Intent

This phase gives the merchant a usable browser surface for everyday visibility,
without turning the mini gateway into a full merchant portal platform.

The desired merchant outcome is:

- a merchant user can log in;
- a merchant user can inspect payments, refunds, and webhook delivery history;
- a merchant user can understand recent volume and transaction outcomes;
- merchant support questions can be answered from the dashboard before falling
  back to raw API usage.

The dashboard should remain intentionally simple:

- read-heavy;
- operational;
- low-risk;
- tightly scoped to one merchant's own data.

## Design Decisions

- Build the merchant dashboard as a separate frontend app, recommended path:
  `apps/merchant-dashboard/`.
- Do not reuse `InternalUser`; add a dedicated merchant user model.
- Use secure session cookies for merchant user auth.
- Keep merchant roles small:
  - `MERCHANT_ADMIN`
  - `MERCHANT_VIEWER`
- Merchant users may view credential metadata, but raw secret values are never
  shown after creation.
- Merchant dashboard APIs must always resolve merchant scope from the logged-in
  merchant user, not from a user-supplied merchant id query parameter.
- Keep mutations minimal in this phase. The merchant dashboard is mainly for
  visibility, not administration of sensitive state.

## Role Matrix

### `MERCHANT_ADMIN`

Can:

- access all merchant dashboard pages for the merchant they belong to;
- view merchant profile and integration metadata;
- view credential metadata;
- view payments, refunds, webhook history, and dashboard charts.

Cannot:

- see data of any other merchant;
- manage internal ops-only functions;
- view internal audit logs;
- resolve reconciliation records directly;
- rotate credentials in the initial phase unless policy changes later.

### `MERCHANT_VIEWER`

Can:

- view dashboard home;
- view payments, refunds, and webhook history;
- view merchant profile summary.

Cannot:

- view admin-only integration controls if later added;
- manage merchant users in the initial phase;
- perform any sensitive operational action.

## Information Architecture

Recommended primary navigation:

- `Overview`
- `Payments`
- `Refunds`
- `Webhooks`
- `Profile`
- `Credentials`

Global header features:

- current user menu;
- logout;
- environment badge;
- merchant-scoped quick lookup.

## Screens

### 1. Login

Required features:

- email + password sign-in;
- invalid credential feedback;
- session expiry handling;
- logout from the current session;
- change own password.

Not required in phase 11:

- merchant self-signup;
- forgot-password email flow;
- MFA.

### 2. Overview Dashboard

Required cards:

- payments in last 24 hours;
- successful payment amount in last 24 hours;
- pending payments;
- refunds in last 24 hours;
- failed or open webhook events.

Required charts:

- payment count by status over the last 7 days;
- successful payment amount by day over the last 7 days;
- refund count over the last 7 days;
- webhook delivery outcomes over the last 7 days.

### 3. Payments Explorer

Required features:

- search by `transaction_id`;
- search by `order_id`;
- filter by payment status;
- filter by date range.

Payment detail must show:

- transaction id;
- order id;
- amount and currency;
- status and timestamps;
- QR payload snapshot;
- recent callback evidence summary if applicable;
- linked refunds if any.

### 4. Refunds Explorer

Required features:

- search by `refund_transaction_id`;
- search by `refund_id`;
- filter by refund status;
- filter by date range.

Refund detail must show:

- original payment reference;
- refund amount;
- refund reason;
- refund status and timestamps;
- callback evidence summary if applicable.

### 5. Webhooks Explorer

Required features:

- list merchant's webhook events;
- filter by event type;
- filter by delivery status;
- filter by date range.

Webhook detail must show:

- event metadata;
- payload snapshot;
- delivery attempt history;
- latest failure reason.

No manual retry action is exposed to merchant users in phase 11.

### 6. Profile

Required fields:

- merchant id;
- merchant name;
- legal name;
- contact name/email/phone;
- webhook URL;
- allowed IP list;
- merchant status.

This page is read-only in phase 11.

### 7. Credentials

Required fields:

- access key;
- secret suffix;
- credential status;
- created_at;
- rotated_at;
- expired_at.

The dashboard must never expose the raw secret value after credential creation.

## Global Lookup

Add a merchant-scoped lookup in the top bar.

Expected shortcuts:

- `pay_...` -> payment detail;
- `rfnd_...` -> refund detail;
- `ORDER-...` -> payment search seeded with `order_id`;
- `REF-...` -> refund search seeded with `refund_id`.

Lookup must never escape the current merchant's data scope.

## Backend Additions

### Merchant User Auth APIs

Create:

- `POST /v1/merchant-portal/auth/login`
- `POST /v1/merchant-portal/auth/logout`
- `GET /v1/merchant-portal/auth/me`
- `POST /v1/merchant-portal/auth/change-password`

Recommended session model:

- secure HttpOnly cookie;
- server-side session lookup or signed session token;
- merchant user status enforced on every request.

### Merchant Dashboard Summary APIs

Create:

- `GET /v1/merchant-portal/dashboard/summary`
- `GET /v1/merchant-portal/dashboard/charts`

### Merchant Payments APIs

Create:

- `GET /v1/merchant-portal/payments`
- `GET /v1/merchant-portal/payments/{transaction_id}`

### Merchant Refund APIs

Create:

- `GET /v1/merchant-portal/refunds`
- `GET /v1/merchant-portal/refunds/{refund_transaction_id}`

### Merchant Webhook APIs

Create:

- `GET /v1/merchant-portal/webhooks`
- `GET /v1/merchant-portal/webhooks/{event_id}`

### Merchant Profile APIs

Create:

- `GET /v1/merchant-portal/profile`
- `GET /v1/merchant-portal/credentials`

## Data Model Additions

Add a merchant user model, recommended shape:

- `MerchantUser`
  - id
  - merchant_db_id
  - email
  - full_name
  - role = `MERCHANT_ADMIN | MERCHANT_VIEWER`
  - status = `ACTIVE | INACTIVE`
  - password_hash
  - last_login_at
  - created_at
  - updated_at

Optional supporting model if using DB-backed sessions:

- `MerchantUserSession`

## Frontend Structure

Recommended app structure:

```text
apps/merchant-dashboard/
  src/
    app/
    routes/
    pages/
    components/
    features/
      auth/
      dashboard/
      payments/
      refunds/
      webhooks/
      profile/
      credentials/
```

Recommended frontend concerns:

- auth guard;
- merchant role guard;
- merchant-scoped lookup;
- URL-driven filters on explorer pages;
- shared formatting for statuses, timestamps, and amounts.

## Visual Direction

This is a merchant operations surface, not a marketing site.

UI should feel:

- simple;
- trustworthy;
- compact;
- merchant-readable.

Recommended visual rules:

- clean overview cards;
- strong list/detail layouts;
- simple trend charts;
- clear status badges;
- avoid dense internal-only ops clutter.

## Files

### Frontend

- Create: `apps/merchant-dashboard/package.json`
- Create: `apps/merchant-dashboard/vite.config.ts`
- Create: `apps/merchant-dashboard/tsconfig.json`
- Create: `apps/merchant-dashboard/src/main.tsx`
- Create: `apps/merchant-dashboard/src/app/router.tsx`
- Create: `apps/merchant-dashboard/src/app/layout.tsx`
- Create: `apps/merchant-dashboard/src/features/auth/*`
- Create: `apps/merchant-dashboard/src/features/dashboard/*`
- Create: `apps/merchant-dashboard/src/features/payments/*`
- Create: `apps/merchant-dashboard/src/features/refunds/*`
- Create: `apps/merchant-dashboard/src/features/webhooks/*`
- Create: `apps/merchant-dashboard/src/features/profile/*`
- Create: `apps/merchant-dashboard/src/features/credentials/*`

### Backend

- Create: merchant user controller/service/schema/repository files as needed
- Create: merchant portal controller/service/schema/repository files as needed
- Modify: `backend/app/main.py`
- Modify: `docs/api/merchant.md`
- Modify: `docs/architecture/backend.md`
- Modify: `README.md`
- Modify: `docs/history/README.md`

## Tasks

### Task 0: Baseline And App Skeleton Decision

- [ ] Confirm frontend app location as `apps/merchant-dashboard/`.
- [ ] Confirm merchant auth model:
  - secure session cookie;
  - dedicated `MerchantUser` auth principal.
- [ ] Confirm role policy:
  - `MERCHANT_ADMIN`
  - `MERCHANT_VIEWER`
- [ ] Run current backend test baseline:

```bash
cd backend
python -m unittest discover tests -v
```

- [ ] Expected: current tests pass before phase 11 work starts.

### Task 1: Merchant User Backend Foundation

- [ ] Add `MerchantUser` model and migration.
- [ ] Add password hash storage.
- [ ] Add merchant login/logout/me/change-password APIs.
- [ ] Reject inactive merchant users.
- [ ] Write backend tests for:
  - valid login;
  - invalid login;
  - inactive user rejection;
  - logout;
  - password change.

### Task 2: Merchant-Scoped Read APIs

- [ ] Add merchant dashboard summary endpoint.
- [ ] Add merchant chart endpoint.
- [ ] Add payments list/detail APIs.
- [ ] Add refunds list/detail APIs.
- [ ] Add webhooks list/detail APIs.
- [ ] Add profile and credential metadata APIs.
- [ ] Ensure all APIs are scoped from the logged-in merchant user only.
- [ ] Write tests for scope isolation and filters.

### Task 3: Frontend Scaffold

- [ ] Scaffold `apps/merchant-dashboard/`.
- [ ] Add router, layout, auth guard, and role guard.
- [ ] Add shared UI primitives:
  - header;
  - quick lookup;
  - tables;
  - filters;
  - badges.
- [ ] Add API client and query configuration.

### Task 4: Core Merchant Pages

- [ ] Implement Login page.
- [ ] Implement Overview page.
- [ ] Implement Payments explorer + detail.
- [ ] Implement Refunds explorer + detail.
- [ ] Implement Webhooks explorer + detail.
- [ ] Implement Profile page.
- [ ] Implement Credentials page.

### Task 5: Verification And Documentation

- [ ] Add backend tests for auth and merchant-scoped read APIs.
- [ ] Add frontend smoke or component/integration tests where practical.
- [ ] Update merchant API docs with portal/auth endpoints.
- [ ] Update architecture docs to describe the merchant dashboard surface.
- [ ] Update root README and history index.
- [ ] Write completion record only after the feature is implemented and verified.

## Acceptance Criteria

- A merchant user can log in from the browser.
- Unauthenticated users cannot access merchant dashboard pages or merchant
  portal APIs.
- Merchant users can view only their own merchant's data.
- Merchant users can search payments by `transaction_id` and `order_id`.
- Merchant users can search refunds by `refund_transaction_id` and `refund_id`.
- Merchant users can inspect webhook event history and delivery attempts.
- Merchant users can view merchant profile and credential metadata without
  seeing any raw secret value.
- Dashboard cards and charts render from real merchant-scoped backend data.

## Recommended Next Phase After Phase 11

Proceed to the worker/scheduler automation phase for expiration and due webhook
delivery. Do not fold scheduler logic or heavy merchant self-service config
mutation into this phase unless scope changes explicitly.
