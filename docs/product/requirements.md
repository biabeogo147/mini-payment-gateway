# 1. Business requirements

## Merchant lifecycle

Canonical merchant status enum:

* `PENDING_REVIEW`
* `ACTIVE`
* `REJECTED`
* `SUSPENDED`
* `DISABLED`

Canonical onboarding case status enum:

* `DRAFT`
* `PENDING_REVIEW`
* `APPROVED`
* `REJECTED`

Approval belongs to onboarding case. Merchant status is operational only.

## Payment rules

* one active payment per `merchant_id + order_id`
* active payment means `PENDING`
* payment states are `PENDING | SUCCESS | FAILED | EXPIRED`
* `INITIATED` is not a persisted DB state
* expired payment does not revive
* duplicate create-payment for current `PENDING` order returns existing transaction
* new payment for same order is allowed only after prior payment is `FAILED` or `EXPIRED`
* new payment for same order is rejected after prior payment is `SUCCESS`

## Refund rules

* refund states are `REFUND_PENDING | REFUNDED | REFUND_FAILED`
* full refund only
* refund window = 7 days from `paid_at`
* unique refund by `merchant_id + refund_id`
* no more than one `REFUNDED` refund per payment

## Webhook rules

* HTTP 2xx means success
* retry schedule: 1 minute, 5 minutes, 15 minutes after initial attempt
* total attempts = 4
* manual retry is internal-only

---

# 2. Technical requirements

## Auth

* `X-Merchant-Id`
* `X-Access-Key`
* `X-Signature`
* `X-Timestamp`
* HMAC-SHA256 verification
* timestamp validity window = 5 minutes
* internal Ops users authenticate with an HttpOnly session cookie
* merchant portal users authenticate with a separate HttpOnly session cookie
* merchant portal data scope is resolved from the logged-in `MerchantUser`
* merchant portal users do not use merchant API HMAC credentials

## Idempotency

* business idempotency for payment: `merchant_id + order_id`
* business idempotency for refund: `merchant_id + refund_id`
* optional technical idempotency header: `X-Idempotency-Key`

## DB strictness

Important invariants should be enforced in DB where practical:

* one active credential per merchant
* one active payment per `merchant_id + order_id`
* one logical refund per `merchant_id + refund_id`
* one `REFUNDED` refund per payment
* positive payment amount
* positive refund amount
* non-negative webhook attempt count

## Persistence decisions

* `OrderReference` is required
* `MerchantOnboardingCase` is a first-class entity
* merchant approval metadata is not denormalized on `Merchant`
* schema is optimized for greenfield correctness, not backward compatibility with old dev data

---

# 3. Operational requirements

* ops/admin owns merchant review, merchant state changes, and manual webhook retry
* internal `ADMIN` and `OPS` users can create, update, deactivate/reactivate,
  and reset passwords for merchant portal users
* `OPS` users cannot manage internal users, rotate merchant credentials, or
  disable merchants
* Merchant Dashboard is read-only except for local password change
* audit log must support entity-specific events for at least `MERCHANT`, `MERCHANT_CREDENTIAL`, `ONBOARDING_CASE`, `PAYMENT`, `REFUND`, `WEBHOOK_EVENT`, `RECONCILIATION`, `INTERNAL_USER`, and `MERCHANT_USER`
* support and ops must be able to search payment by both `order_id` and `transaction_id`
* delayed callback after payment expiration goes to reconciliation/manual review path, not to automatic revive
