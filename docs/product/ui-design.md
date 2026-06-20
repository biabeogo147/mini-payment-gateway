# User Interface Design

This document describes the implemented dashboard UI design. It is intended for
presentation/report use, not as a pixel-perfect design spec.

## Design Split

The project uses two dashboard applications because the actors, permissions,
and workflows are different.

| UI | Audience | Purpose | Port |
| --- | --- | --- | --- |
| Ops Dashboard | Internal Admin/Ops users | Operate merchants, investigate evidence, manage users, and recover failed workflows. | `4173` |
| Merchant Dashboard | Merchant users | Read merchant-scoped payment, refund, webhook, profile, credential, and analytics data. | `4174` |

The split prevents merchant users from seeing internal audit/reconciliation
controls and keeps merchant portal user provisioning inside the internal Ops
surface.

## Ops Dashboard

Implemented pages:

| Page | Main tasks |
| --- | --- |
| Login/bootstrap | Start internal auth and create/login internal users. |
| Overview | Inspect operational metrics, charts, and work queues. |
| Merchants | Search merchants, inspect detail, manage lifecycle, credentials, onboarding, and merchant portal users. |
| Payments | Search payment transactions and inspect detail evidence. |
| Refunds | Search refund transactions and inspect linked payment/refund state. |
| Webhooks | Inspect webhook events, delivery attempts, and manual retry where allowed. |
| Reconciliation | Review mismatch evidence and resolve records. |
| Audit | Inspect operational audit trail. |
| Internal users | Admin-only internal user management. |

Key UI decisions:

- The left navigation is fixed for repeated operations work.
- Lists and details sit side-by-side on desktop to reduce context switching.
- Status badges use semantic colors for success, warning, danger, and muted
  states.
- Lifecycle and password actions require explicit buttons and backend RBAC.
- Merchant portal user controls appear inside merchant detail because portal
  users are scoped to a merchant.

## Merchant Dashboard

Implemented pages:

| Page | Main tasks |
| --- | --- |
| Login | Merchant user login with `merchant_id`, email, and password. |
| Overview | Read current summary cards and compact charts. |
| Analytics | Explore 7/30/90-day charts, exact values, and drill-down links. |
| Payments | Filter and inspect merchant-owned payment records. |
| Refunds | Filter and inspect merchant-owned refund records. |
| Webhooks | Filter and inspect merchant-owned webhook events and attempts. |
| Profile | Read merchant identity, contact, status, and integration metadata. |
| Credentials | Read active credential metadata without raw secrets. |

Key UI decisions:

- Merchant Dashboard is read-only except for local password change.
- The merchant status/session summary is anchored in layout so it does not jump
  between pages.
- Analytics uses Recharts for accessible axes, tooltips, responsive sizing, and
  mobile-friendly data tables.
- The Analytics page supports drill-down into explorer pages through query
  params, but the backend still enforces merchant scope.
- Credential cards intentionally show `access_key` and `secret_key_last4` only.

## Responsive And State Design

Implemented dashboard UI states:

- loading states for async queries;
- empty states for no data;
- error cards for API failures;
- responsive one-column mobile layout;
- stable status/session boxes;
- chart fallback data tables for exact values and accessibility;
- text wrapping for long merchant IDs, emails, webhook URLs, QR payloads, and
  JSON payload snippets.

## Demo Storyline

Recommended demo path:

1. Login to Ops Dashboard as Admin.
2. Open merchant detail and show status, onboarding, credentials, and portal
   users.
3. Create or reset a merchant portal user and explain the one-time password
   rule.
4. Login to Merchant Dashboard as that merchant user.
5. Show Overview and Analytics, including exact values from chart tooltips or
   data tables.
6. Drill down into Payments, Refunds, and Webhooks.
7. Show Profile and Credentials to demonstrate read-only merchant metadata.

This storyline matches implemented behavior and avoids demoing future-only
scope such as merchant self-service onboarding or settlement.
