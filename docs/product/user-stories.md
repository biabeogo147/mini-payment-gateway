# User Stories

This document lists user stories that are implemented in the current MVP. It
does not include future-only stories.

## Admin

| ID | Story | Acceptance criteria |
| --- | --- | --- |
| US-ADMIN-01 | As an Admin, I want to create and review merchants so that only approved merchants can use the gateway. | Admin can create a merchant, submit/review onboarding evidence, create credentials, and activate the merchant. |
| US-ADMIN-02 | As an Admin, I want to manage internal users so that operations access can be controlled. | Admin can list, create, update, deactivate/reactivate, and reset internal user passwords. |
| US-ADMIN-03 | As an Admin, I want to provision merchant dashboard users so that merchants can inspect their own gateway data. | Admin can create, update, deactivate/reactivate, and reset merchant portal users from merchant detail. Generated passwords are shown once. |
| US-ADMIN-04 | As an Admin, I want to inspect audit and reconciliation evidence so that operational changes are traceable. | Admin can open audit logs and reconciliation records, then resolve reconciliation items with a reason. |

## Ops

| ID | Story | Acceptance criteria |
| --- | --- | --- |
| US-OPS-01 | As an Ops user, I want to monitor operational queues so that failed or pending work can be handled quickly. | Ops can login, view dashboard metrics/charts, and navigate to payments, refunds, webhooks, and reconciliation. |
| US-OPS-02 | As an Ops user, I want to manage merchant lifecycle states so that merchants can be activated, suspended, or disabled safely. | Ops can perform allowed lifecycle actions with a required reason and audit trail. |
| US-OPS-03 | As an Ops user, I want to inspect webhook attempts so that failed merchant notifications can be retried or explained. | Ops can open webhook detail, see attempts, and retry failed webhook events where allowed. |
| US-OPS-04 | As an Ops user, I want RBAC to block admin-only actions so that password management remains controlled. | Ops cannot create/reset merchant portal users or manage internal users. |

## Merchant Operator

| ID | Story | Acceptance criteria |
| --- | --- | --- |
| US-MERCHANT-01 | As a merchant operator, I want to login to a dashboard so that I can see my payment gateway activity without API credentials. | Merchant user logs in with `merchant_id`, email, and password. The session is separate from HMAC API credentials. |
| US-MERCHANT-02 | As a merchant operator, I want to see overview metrics so that I can quickly understand current payment/refund/webhook health. | Overview shows summary cards and compact charts using only the logged-in merchant's data. |
| US-MERCHANT-03 | As a merchant operator, I want interactive analytics so that I can read exact amounts, counts, rates, and attention items. | Analytics supports 7/30/90-day ranges, tooltips, data tables, and drill-down links. |
| US-MERCHANT-04 | As a merchant operator, I want to inspect payments, refunds, and webhooks so that I can answer customer support questions. | Explorer pages list and show detail for only the logged-in merchant's records. Records from another merchant return `404`. |
| US-MERCHANT-05 | As a merchant operator, I want to change my password so that I can secure my portal account after receiving an initial password. | Change-password requires the current password, sets the new password hash, and refreshes the session. |

## Merchant Business Viewer

| ID | Story | Acceptance criteria |
| --- | --- | --- |
| US-VIEWER-01 | As a merchant business viewer, I want to view revenue and success-rate trends so that I can understand gateway performance. | Viewer can open Overview and Analytics, read exact chart values, and switch date ranges. |
| US-VIEWER-02 | As a merchant business viewer, I want read-only credential metadata so that I can identify the active access key without seeing secrets. | Credentials page shows access key, last four secret characters, status, and timestamps only. |
| US-VIEWER-03 | As a merchant business viewer, I want read-only profile data so that I can confirm merchant identity and webhook configuration. | Profile page shows merchant identity, status, contact, and integration metadata without mutation controls. |

## Excluded Stories

The current MVP does not implement self-service merchant onboarding, merchant
profile editing, credential rotation by merchants, CSV export, realtime
analytics polling, settlement, disputes, multi-provider routing, or partial
refunds.
