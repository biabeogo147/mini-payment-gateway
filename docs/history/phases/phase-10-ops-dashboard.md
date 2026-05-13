# Ops Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an internal Ops dashboard so Admin/Ops users can operate the mini
payment gateway without Postman or direct database access.

**Architecture:** Phase 10 adds one internal web app for Admin/Ops plus the
backend read/search/stat/auth APIs required to operate the existing money
movement engine. The current FastAPI backend remains the system of record for
merchant, payment, refund, webhook, reconciliation, and audit data. The new UI
is an internal console, not a public product surface.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, existing models and services,
internal auth/session layer, React + Vite + TypeScript, React Router, TanStack
Query, and a lightweight charting library for operational metrics.

---

## Implementation Status

Completed. Phase 10 now ships the internal Ops dashboard, internal session
auth, RBAC, read/search/stat APIs, and sandbox runtime integration for the
dashboard container.

First live application deployment for this phase was verified on May 13, 2026
(Asia/Saigon) against sandbox host `192.168.1.199`. See
`docs/history/completions/phase-10.md` for the rollout evidence, verification,
and remaining notes.

This plan assumes:

- the current repository already contains the phase 02-09 backend and sandbox
  CI/CD foundation;
- `InternalUser` exists as the canonical internal operator model;
- phase 10 owns only the internal Ops dashboard;
- merchant-facing dashboard work will move to phase 11;
- worker/scheduler automation will move to a later dedicated phase.

This phase was implemented directly in the main repository checkout without a
separate branch or worktree, matching the explicit operator instruction at the
time of rollout.

## Scope

Implement:

- internal operator authentication for `InternalUser`;
- role-based access control for `ADMIN` and `OPS`;
- an internal Ops web app;
- dashboard summary/stat APIs for operational overview cards and charts;
- read/search/detail APIs for merchants, payments, refunds, webhooks, audit
  logs, and reconciliation records;
- UI flows for merchant onboarding, credential management, activation,
  suspension, disablement, webhook retry, and reconciliation resolution;
- internal user management for `ADMIN`;
- docs updates for the new internal UI and auth model.

Do not implement:

- merchant dashboard or merchant portal;
- settlement, disputes, ledger, accounting, or advanced finance reporting;
- public-facing UI;
- mobile-first design;
- worker/scheduler automation for expiration or webhook retry;
- provider hardening beyond what is needed to support the Ops console;
- large BI/analytics modules.

## Product Intent

This phase turns the current API-first MVP into an operable internal product.

The desired operator outcome is:

- an `OPS` user can log in and process merchant onboarding end-to-end;
- an `OPS` user can search payments, refunds, webhook failures, and
  reconciliation cases quickly;
- an `ADMIN` user can manage internal users and high-risk actions;
- normal day-to-day operations can be performed from a browser UI instead of
  Postman.

The dashboard is intentionally small and operational. It should optimize for:

- clarity;
- speed of lookup;
- low-click workflows;
- dense information display suitable for an internal console.

## Design Decisions

- Build the Ops dashboard as a separate internal frontend app, recommended path:
  `apps/ops-dashboard/`.
- Use one shared backend instead of a separate BFF service.
- Use server-backed internal auth with secure session cookies rather than
  storing access tokens in browser storage.
- Keep role design small:
  - `ADMIN`
  - `OPS`
- Put all money movement state mutation behind existing or expanded `/v1/ops/*`
  APIs so the dashboard never writes directly to the database.
- Add read/search APIs that match operator workflows instead of forcing the UI
  to stitch together many merchant-facing endpoints.
- Prefer list/detail pages with strong filtering over heavy multi-panel
  dashboards.
- Keep charts lightweight and operational, not BI-grade.

## Role Matrix

### `ADMIN`

Can:

- access every Ops dashboard page;
- create, activate, deactivate, and change roles for internal users;
- create merchants;
- approve/reject onboarding;
- create or rotate credentials;
- activate, suspend, or disable merchants;
- retry failed webhooks manually;
- resolve reconciliation records;
- view full audit logs.

### `OPS`

Can:

- access dashboard home and operational explorer pages;
- create merchants;
- submit onboarding cases;
- approve/reject onboarding;
- create initial credentials;
- activate or suspend merchants;
- retry failed webhooks manually;
- resolve reconciliation records;
- view audit logs.

Cannot:

- manage internal users;
- disable merchants;
- rotate credentials in the initial phase unless later policy changes;
- access admin-only controls.

## Information Architecture

Recommended primary navigation:

- `Overview`
- `Merchants`
- `Onboarding`
- `Payments`
- `Refunds`
- `Webhooks`
- `Reconciliation`
- `Audit`
- `Internal Users` (`ADMIN` only)

Global header features:

- current user menu;
- logout;
- environment badge;
- global lookup field for fast entity search.

## Screens

### 1. Login

Required features:

- email + password sign-in;
- invalid credential feedback;
- session expiry handling;
- logout from the current session.

Not required in phase 10:

- SSO;
- forgot-password email flow;
- MFA.

### 2. Overview Dashboard

Required cards:

- merchants pending review;
- merchants active;
- payments in last 24 hours;
- total successful payment amount in last 24 hours;
- refunds in last 24 hours;
- failed webhook events open;
- reconciliation records pending review.

Required queue widgets:

- newest onboarding items waiting for review;
- newest failed webhooks;
- newest reconciliation items waiting for action.

Required charts:

- payment count by status over the last 7 days;
- refund count over the last 7 days;
- webhook delivery outcomes over the last 7 days;
- reconciliation created vs resolved over the last 7 days.

### 3. Merchants

Merchant list must support:

- search by `merchant_id`;
- search by merchant name;
- search by contact email;
- filter by merchant status;
- filter by onboarding case status;
- sort by created/updated time.

Merchant detail must show:

- merchant profile fields;
- operational status;
- onboarding case summary;
- credential metadata;
- recent payments;
- recent refunds;
- recent webhook failures;
- recent audit entries.

Merchant actions from the detail page:

- submit/update onboarding case;
- approve onboarding;
- reject onboarding;
- create credential;
- rotate credential (`ADMIN` only by default);
- activate merchant;
- suspend merchant;
- disable merchant (`ADMIN` only).

### 4. Onboarding Queue

Required features:

- list merchants with onboarding case `PENDING_REVIEW`;
- show key profile data and review note context;
- open merchant detail directly;
- approve/reject with reason.

### 5. Payments Explorer

Required features:

- search by `transaction_id`;
- search by `order_id`;
- filter by merchant;
- filter by payment status;
- filter by date range.

Payment detail must show:

- payment metadata;
- amount, status, and timestamps;
- QR payload snapshot;
- callback evidence summary;
- linked reconciliation record when present;
- linked refunds when present.

### 6. Refunds Explorer

Required features:

- search by `refund_transaction_id`;
- search by `refund_id`;
- filter by merchant;
- filter by refund status;
- filter by date range.

Refund detail must show:

- original payment reference;
- refund amount, reason, and status;
- refund callback evidence summary;
- linked reconciliation record when present.

### 7. Webhooks Explorer

Required features:

- list webhook events;
- filter by event type;
- filter by delivery status;
- filter by merchant;
- filter by date range.

Webhook detail must show:

- event payload;
- event metadata;
- delivery attempt history;
- latest failure reason;
- manual retry action when the event is eligible.

### 8. Reconciliation Queue

Required features:

- filter by `MATCHED`, `MISMATCHED`, `PENDING_REVIEW`, `RESOLVED`;
- filter by entity type;
- filter by date range.

Reconciliation detail must show:

- internal status/amount;
- external status/amount;
- mismatch reason;
- review note;
- actor/reviewer metadata;
- resolve action with note.

### 9. Audit Log

Required features:

- filter by actor type;
- filter by entity type;
- filter by entity id;
- filter by event type;
- filter by date range.

Audit detail must show:

- before state;
- after state;
- masked secrets;
- reason;
- actor;
- timestamp.

### 10. Internal Users (`ADMIN` only)

Required features:

- list internal users;
- create internal user;
- assign role `ADMIN` or `OPS`;
- activate/deactivate internal user;
- reset password.

## Global Lookup

Add a compact global search in the top bar for high-frequency operator lookup.

Expected shortcuts:

- `m_...` -> merchant detail;
- `pay_...` -> payment detail;
- `rfnd_...` -> refund detail;
- `evt_...` -> webhook detail;
- `ORDER-...` -> payment search seeded with `order_id`.

This should be implemented as a thin UI convenience over existing or new
read/search APIs, not as direct DB querying from the browser.

## Backend Additions

### Internal Auth APIs

Create:

- `POST /v1/internal/auth/login`
- `POST /v1/internal/auth/logout`
- `GET /v1/internal/auth/me`
- `POST /v1/internal/auth/change-password`

Recommended session model:

- secure HttpOnly cookie;
- server-side session lookup or signed session token;
- role and user status enforced on every request.

### Internal User Management APIs

Create:

- `GET /v1/internal/users`
- `POST /v1/internal/users`
- `PATCH /v1/internal/users/{id}`
- `POST /v1/internal/users/{id}/reset-password`

### Dashboard Summary APIs

Create:

- `GET /v1/ops/dashboard/summary`
- `GET /v1/ops/dashboard/charts`

### Merchant Read APIs

Create:

- `GET /v1/ops/merchants`
- `GET /v1/ops/merchants/{merchant_id}`
- `GET /v1/ops/merchants/{merchant_id}/onboarding-case`
- `GET /v1/ops/merchants/{merchant_id}/credentials`

### Payment Read APIs

Create:

- `GET /v1/ops/payments`
- `GET /v1/ops/payments/{transaction_id}`

### Refund Read APIs

Create:

- `GET /v1/ops/refunds`
- `GET /v1/ops/refunds/{refund_transaction_id}`

### Webhook Read APIs

Create:

- `GET /v1/ops/webhooks`
- `GET /v1/ops/webhooks/{event_id}`
- `GET /v1/ops/webhooks/{event_id}/attempts`

### Audit Read APIs

Create:

- `GET /v1/ops/audit-logs`

### Reconciliation APIs

Reuse existing reconciliation list/detail/resolve routes. Add missing filters
only if the current route shape is not enough for the UI.

## Frontend Structure

Recommended app structure:

```text
apps/ops-dashboard/
  src/
    app/
    routes/
    pages/
    components/
    features/
      auth/
      dashboard/
      merchants/
      payments/
      refunds/
      webhooks/
      reconciliation/
      audit/
      internal-users/
```

Recommended frontend concerns:

- route guards by auth state;
- permission guards by role;
- TanStack Query for API state;
- table/filter state persisted in the URL where practical;
- shared status badges and formatting helpers;
- confirmation modal for destructive or high-risk actions.

## Visual Direction

This is an internal operator console, not a marketing product.

UI should feel:

- dense but readable;
- fast to scan;
- neutral and trustworthy;
- desktop-first.

Recommended visual rules:

- strong tabular layout;
- persistent filters on explorer pages;
- color-coded state badges;
- low-friction drill-down from queue widget -> list -> detail;
- avoid oversized hero layouts or decorative empty space.

## Files

### Frontend

- Create: `apps/ops-dashboard/package.json`
- Create: `apps/ops-dashboard/vite.config.ts`
- Create: `apps/ops-dashboard/tsconfig.json`
- Create: `apps/ops-dashboard/src/main.tsx`
- Create: `apps/ops-dashboard/src/app/router.tsx`
- Create: `apps/ops-dashboard/src/app/layout.tsx`
- Create: `apps/ops-dashboard/src/features/auth/*`
- Create: `apps/ops-dashboard/src/features/dashboard/*`
- Create: `apps/ops-dashboard/src/features/merchants/*`
- Create: `apps/ops-dashboard/src/features/payments/*`
- Create: `apps/ops-dashboard/src/features/refunds/*`
- Create: `apps/ops-dashboard/src/features/webhooks/*`
- Create: `apps/ops-dashboard/src/features/reconciliation/*`
- Create: `apps/ops-dashboard/src/features/audit/*`
- Create: `apps/ops-dashboard/src/features/internal-users/*`

### Backend

- Create: internal auth controller/service/schema/repository files as needed
- Create: internal user admin controller/service/schema/repository files as needed
- Create: Ops read/search controllers/services/schemas/repositories as needed
- Modify: `backend/app/main.py`
- Modify: `backend/app/controllers/deps.py`
- Modify: `docs/api/ops.md`
- Modify: `docs/architecture/backend.md`
- Modify: `README.md`
- Modify: `docs/history/README.md`

## Tasks

### Task 0: Baseline And App Skeleton Decision

- [ ] Confirm frontend app location as `apps/ops-dashboard/`.
- [ ] Confirm internal auth model:
  - secure session cookie;
  - `InternalUser` as auth principal.
- [ ] Confirm role policy:
  - `ADMIN`
  - `OPS`
- [ ] Run current backend test baseline:

```bash
cd backend
python -m unittest discover tests -v
```

- [ ] Expected: current tests pass before phase 10 work starts.

### Task 1: Internal Auth Backend

- [ ] Add password hash storage for `InternalUser`.
- [ ] Add login/logout/me/change-password APIs.
- [ ] Add backend auth dependency for internal routes.
- [ ] Reject inactive internal users.
- [ ] Write unit and route tests for:
  - valid login;
  - invalid login;
  - inactive user rejection;
  - logout;
  - password change.

### Task 2: Role-Based Access Control

- [ ] Add reusable permission checks for `ADMIN` and `OPS`.
- [ ] Protect admin-only routes:
  - internal user management;
  - high-risk merchant actions if policy requires it.
- [ ] Write tests for allowed and forbidden access.

### Task 3: Internal User Management

- [ ] Add list/create/update/reset-password endpoints.
- [ ] Add bootstrap path for first admin user.
- [ ] Add audit behavior for internal user management if appropriate.
- [ ] Write tests for:
  - user creation;
  - role update;
  - deactivate/reactivate;
  - reset password.

### Task 4: Ops Read/Search APIs

- [ ] Add merchant list/detail APIs.
- [ ] Add onboarding case read APIs.
- [ ] Add credential metadata read APIs.
- [ ] Add payment explorer APIs.
- [ ] Add refund explorer APIs.
- [ ] Add webhook explorer APIs.
- [ ] Add audit log explorer API.
- [ ] Reuse existing reconciliation routes where possible.
- [ ] Add pagination/filter/query tests.

### Task 5: Dashboard Summary APIs

- [ ] Add summary endpoint for top-level cards.
- [ ] Add chart endpoint for 7-day operational metrics.
- [ ] Keep aggregation logic simple and Postgres-friendly.
- [ ] Add tests for summary counts and chart buckets.

### Task 6: Frontend Scaffold

- [ ] Scaffold `apps/ops-dashboard/`.
- [ ] Add router, layout, auth guard, and role guard.
- [ ] Add shared UI primitives:
  - sidebar;
  - top bar;
  - global search;
  - tables;
  - filters;
  - badges;
  - confirm dialogs.
- [ ] Add API client and query configuration.

### Task 7: Core Ops Pages

- [ ] Implement Login page.
- [ ] Implement Overview page.
- [ ] Implement Merchant list/detail pages.
- [ ] Implement Onboarding queue page.
- [ ] Implement merchant action flows:
  - submit onboarding;
  - approve/reject;
  - create credential;
  - activate/suspend/disable;
  - rotate credential if role policy allows it.

### Task 8: Explorer Pages

- [ ] Implement Payments explorer + detail.
- [ ] Implement Refunds explorer + detail.
- [ ] Implement Webhooks explorer + detail + manual retry.
- [ ] Implement Reconciliation queue + detail + resolve.
- [ ] Implement Audit log explorer.

### Task 9: Internal User UI

- [ ] Implement Internal Users page for `ADMIN`.
- [ ] Add create/edit/deactivate/reset-password flows.
- [ ] Hide the page completely for `OPS`.

### Task 10: Verification And Documentation

- [ ] Add backend tests for all new auth/RBAC/read APIs.
- [ ] Add frontend smoke or component/integration tests where practical.
- [ ] Update `docs/api/ops.md` with auth and read/search endpoints.
- [ ] Update architecture docs to describe the internal console surface.
- [ ] Update root README and history index.
- [ ] Write completion record only after the feature is implemented and verified.

## Acceptance Criteria

- An internal `ADMIN` user can log in from the browser.
- An internal `OPS` user can log in from the browser.
- Unauthenticated users cannot access Ops dashboard pages or Ops APIs.
- Role restrictions are enforced on both backend and frontend.
- Ops can complete merchant onboarding through the UI.
- Ops can search and inspect payments by `transaction_id` and `order_id`.
- Ops can search and inspect refunds.
- Ops can inspect webhook failures and manually retry eligible events.
- Ops can inspect and resolve reconciliation records.
- Admin can manage internal users.
- Dashboard overview cards and charts render from real backend data.
- Existing audit behavior remains intact for merchant ops, webhook retry, and
  reconciliation resolution.

## Recommended Next Phase After Phase 10

Proceed to the separate merchant-facing dashboard phase. Do not mix merchant
user login or merchant portal concerns into this phase unless scope changes
explicitly.
