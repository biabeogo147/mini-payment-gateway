# 1. Product scope

## Problem statement

Build a simple QR payment gateway for internal demo and small-scale merchant integration. The MVP must prove that:

* merchant onboarding can be operated internally
* payment flow works end-to-end
* transaction lifecycle is explicit and traceable
* webhook delivery has retry and auditability
* refund is a separate flow with separate tracking

## Actors

### Admin/Ops

Internal operator who can:

* create merchant records
* review onboarding cases
* activate, suspend, reject, or disable merchants
* rotate credentials
* inspect payment, refund, webhook, and reconciliation data
* retry failed webhook delivery manually

### Merchant backend

API consumer that can:

* create payment
* get payment status
* create refund
* get refund status
* receive webhook callbacks

### Customer/Payer

End user who scans the QR code and pays through a banking app.

### Bank/Provider/Simulator

External side that returns payment or refund results. In MVP this can be a simulator or mock integration.

## MVP in scope

* manual merchant onboarding through internal ops flow
* merchant profile + credential management
* single active credential per merchant
* dynamic QR payment only
* payment status tracking: `PENDING | SUCCESS | FAILED | EXPIRED`
* refund status tracking: `REFUND_PENDING | REFUNDED | REFUND_FAILED`
* one active payment per `merchant_id + order_id`
* full refund only
* refund window = 7 days from `paid_at`
* webhook retry policy with operator retry support
* reconciliation records and audit trail
* onboarding case stored in DB as a first-class entity

## Out of scope

* self-service merchant onboarding portal
* eKYC or real legal verification automation
* multi-store and multi-endpoint webhook config
* static QR per store
* multi-currency
* chargeback, dispute, or settlement engine
* accounting ledger
* advanced analytics dashboard
* multiple provider routing engine
* merchant-facing portal beyond API usage

## Canonical lifecycle split

Merchant operational lifecycle:

* `PENDING_REVIEW`
* `ACTIVE`
* `REJECTED`
* `SUSPENDED`
* `DISABLED`

Merchant onboarding case lifecycle:

* `DRAFT`
* `PENDING_REVIEW`
* `APPROVED`
* `REJECTED`

Approval belongs to onboarding case. Merchant status reflects operational readiness only.
