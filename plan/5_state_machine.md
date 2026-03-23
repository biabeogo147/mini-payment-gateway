# 1. Payment state machine

## Persisted payment states

* `PENDING`
* `SUCCESS`
* `FAILED`
* `EXPIRED`

`INITIATED` is not persisted.

## Valid transitions

* `PENDING -> SUCCESS`
* `PENDING -> FAILED`
* `PENDING -> EXPIRED`

## Final states

* `SUCCESS`
* `FAILED`
* `EXPIRED`

## Rules

* one active payment means one `PENDING` payment per `merchant_id + order_id`
* expired payment does not revive
* callback arriving after `EXPIRED` must be handled through reconciliation/manual review, not by automatic `EXPIRED -> SUCCESS`
* only `SUCCESS` payment can be refunded

## Create-payment rule

If create-payment fails before a usable transaction exists:

* return API error
* do not persist a partial transaction row

---

# 2. Refund state machine

## Persisted refund states

* `REFUND_PENDING`
* `REFUNDED`
* `REFUND_FAILED`

## Valid transitions

* `REFUND_PENDING -> REFUNDED`
* `REFUND_PENDING -> REFUND_FAILED`

## Final states

* `REFUNDED`
* `REFUND_FAILED`

## Rules

* refund is separate from payment state machine
* payment remains `SUCCESS` even after refund succeeds
* one payment can have multiple refund attempts historically, but at most one `REFUNDED` row
* refund window = 7 days from `paid_at`

---

# 3. Merchant lifecycle split

## Merchant operational status

* `PENDING_REVIEW`
* `ACTIVE`
* `REJECTED`
* `SUSPENDED`
* `DISABLED`

## Onboarding case status

* `DRAFT`
* `PENDING_REVIEW`
* `APPROVED`
* `REJECTED`

Rules:

* onboarding approval is recorded on `MerchantOnboardingCase`
* merchant moves to `ACTIVE` only when onboarding is approved and credentials/config are ready
* merchant approval is not modeled as a separate operational merchant state
