# Postman Guide

This guide explains how QA and QC can use the Postman assets for the
mini-payment-gateway test scenarios.

## Files

There are now two Postman usage styles in the repo.

Shared imports:

- `postman/mini-payment-gateway.sandbox.environment.json`
- `postman/mini-payment-gateway.collection.json`

Scenario-specific collections:

- `postman/scenarios/auth.collection.json`
- `postman/scenarios/merchant.collection.json`
- `postman/scenarios/payment.collection.json`
- `postman/scenarios/callback.collection.json`
- `postman/scenarios/refund.collection.json`
- `postman/scenarios/webhook.collection.json`
- `postman/scenarios/ops.collection.json`
- `postman/scenarios/reconciliation.collection.json`
- `postman/scenarios/happy-path.collection.json`

## When To Use Which Collection

Use `postman/mini-payment-gateway.collection.json` when:

- you want one compact collection for general exploration
- you want the original sandbox smoke flow
- you are doing a broad end-to-end walkthrough

Use `postman/scenarios/*.collection.json` when:

- you are testing one scenario document in `docs/testing/scenarios/`
- you want QA/QC evidence grouped by business area
- you want negative cases and templates that do not belong in the compact
  master collection

## Scenario Mapping

Each file under `docs/testing/scenarios/` now has a matching Postman
collection.

- `scenarios/auth.md` -> `postman/scenarios/auth.collection.json`
- `scenarios/merchant.md` -> `postman/scenarios/merchant.collection.json`
- `scenarios/payment.md` -> `postman/scenarios/payment.collection.json`
- `scenarios/callback.md` -> `postman/scenarios/callback.collection.json`
- `scenarios/refund.md` -> `postman/scenarios/refund.collection.json`
- `scenarios/webhook.md` -> `postman/scenarios/webhook.collection.json`
- `scenarios/ops.md` -> `postman/scenarios/ops.collection.json`
- `scenarios/reconciliation.md` -> `postman/scenarios/reconciliation.collection.json`
- `scenarios/happy-path.md` -> `postman/scenarios/happy-path.collection.json`

The intention is:

- one scenario doc = one collection
- one shared environment = reused everywhere
- setup requests are included inside scenario collections when the scenario
  needs preconditions such as onboarding, activation, or a fresh payment

## Important Access Note

The current sandbox runtime binds the backend on:

```text
127.0.0.1:8000
```

That means QA/QC usually cannot call the sandbox directly from another machine
unless one of these is true:

1. they run Postman on the sandbox host itself
2. they use an SSH tunnel
3. the runtime is intentionally reconfigured to expose the backend on an
   internal interface

For the current default setup, use an SSH tunnel:

```bash
ssh -L 8000:127.0.0.1:8000 thanhlnp@192.168.1.199
```

Then keep:

```text
baseUrl = http://127.0.0.1:8000
```

## How To Import

For a scenario-specific test run:

1. Open Postman.
2. Click `Import`.
3. Import `postman/mini-payment-gateway.sandbox.environment.json`.
4. Import exactly the scenario collection you want from `postman/scenarios/`.
5. Select the environment `Mini Payment Gateway Sandbox`.

For a broad smoke run:

1. Import `postman/mini-payment-gateway.sandbox.environment.json`.
2. Import `postman/mini-payment-gateway.collection.json`.
3. Select the environment `Mini Payment Gateway Sandbox`.

You can import both the master collection and the scenario collections into the
same Postman workspace. They share the same environment.

## Environment Variables

Most important variables:

- `baseUrl`
- `internal_email`
- `internal_password`
- `merchant_id`
- `access_key`
- `merchant_secret`
- `order_id`
- `payment_transaction_id`
- `refund_id`
- `refund_transaction_id`
- `reconciliation_record_id`
- `webhook_event_id`

Additional scenario helpers that may be filled during runs:

- `inactive_access_key`
- `inactive_merchant_secret`
- `other_merchant_id`
- `other_access_key`
- `other_merchant_secret`
- `unknown_merchant_id`

### Auto-Generated Values

The shared pre-request script auto-generates missing values for the common
merchant and payment flow, including:

- `merchant_id`
- `access_key`
- `merchant_secret`
- `rotated_access_key`
- `rotated_merchant_secret`
- `order_id`
- `refund_id`
- `reconciliation_order_id`
- `idempotency_key`
- `now_iso`

Several scenario collections also set scenario-specific values on the fly, such
as a second merchant for ownership tests or preserved old credentials for
rotation tests.

### Values QA/QC May Want To Override

- `baseUrl`
- `webhook_url`
- `payment_amount`
- `payment_description`
- `refund_reason`
- `reconciliation_mismatch_amount`

## Internal Ops Authentication

Ops setup requests require an internal Admin/Ops session cookie. The
`happy-path` collection includes an `Internal Login` request before the E2E-01
Ops setup steps. Set these variables before running that folder:

- `internal_email`
- `internal_password`

Newman example:

```bash
npx --yes newman run postman/scenarios/happy-path.collection.json \
  -e postman/mini-payment-gateway.sandbox.environment.json \
  --folder "E2E-01 Merchant Onboarding To Successful Payment And Refund" \
  --env-var baseUrl=http://127.0.0.1:8000 \
  --env-var internal_email="<admin-email>" \
  --env-var internal_password="<admin-password>" \
  --env-var provider_id=simulator \
  --env-var provider_callback_secret=dev-insecure-provider-callback-secret-change-me
```

## Merchant HMAC Authentication

Merchant-facing payment and refund endpoints require HMAC headers.

The collections generate these headers automatically for:

- `/v1/payments...`
- `/v1/refunds...`

They fill:

- `X-Merchant-Id`
- `X-Access-Key`
- `X-Timestamp`
- `X-Signature`
- `X-Idempotency-Key`

QA/QC do not need to build the HMAC manually for normal runs.

Some scenario collections intentionally override these headers to test auth
failures, rotated credentials, and cross-merchant access checks.

## Provider Callback HMAC Authentication

Provider callback requests require:

- `X-Provider-Id`
- `X-Provider-Timestamp`
- `X-Provider-Signature`

The happy-path and callback collections generate these headers automatically
from `provider_id` and `provider_callback_secret`.

## Recommended Usage Pattern

For focused testing:

1. Pick one file from `docs/testing/scenarios/`.
2. Import the matching `postman/scenarios/*.collection.json`.
3. Run the folder for the scenario you want from top to bottom.
4. Record results against the scenario ids in `docs/testing/matrix.md`.

For a fresh merchant flow, clear these environment values before rerunning:

- `merchant_id`
- `access_key`
- `merchant_secret`
- `order_id`
- `payment_transaction_id`
- `refund_id`
- `refund_transaction_id`
- `reconciliation_order_id`
- `reconciliation_payment_transaction_id`
- `reconciliation_record_id`
- `other_merchant_id`
- `other_access_key`
- `other_merchant_secret`
- `inactive_access_key`
- `inactive_merchant_secret`

## Template-Only Cases

Some scenario ids are represented in Postman as templates or trigger flows,
because the current MVP does not expose every internal mechanism as a public
API.

### Expiration-Dependent Cases

These need the internal expiration worker or a prepared database fixture:

- `callback.md` / `EXP-01`
- `payment.md` / `PAY-07`
- `reconciliation.md` / `REC-01`
- `happy-path.md` / `E2E-03`
- `webhook.md` / `WH-03`

### Refund Window Expiry

`refund.md` / `REF-07` needs a payment whose `paid_at` is already older than 7
days. The collection includes the request template, but QA/QC still need a
pre-aged payment fixture.

### Webhook Delivery And Retry

`webhook.md` / `WH-05` through `WH-09` depend on what `webhook_url` points to.

Examples:

- 2xx receiver -> delivered path
- HTTP 500 receiver -> retry path
- timeout receiver -> retry path
- unreachable host -> network-error retry path

The collection triggers the gateway behavior, but the result depends on the
receiver you configure before merchant onboarding.

### Manual Retry

`webhook.md` / `WH-10` and `happy-path.md` / `E2E-04` need `webhook_event_id`.

The MVP does not expose a list-webhook-events API yet, so QA/QC must get the
event id from:

- application logs
- database inspection
- a future admin/helper tool

## What Each Collection Contains

High-level intent:

- `auth.collection.json` focuses on missing header, bad signature, expired
  timestamp, unknown merchant, and rotated credential cases.
- `merchant.collection.json` focuses on onboarding and merchant readiness.
- `payment.collection.json` focuses on create/query/duplicate/ownership paths.
- `callback.collection.json` focuses on provider payment callbacks and late
  callback templates.
- `refund.collection.json` focuses on full refund flow plus partial, duplicate,
  and non-refundable cases.
- `webhook.collection.json` focuses on event-triggering requests and manual
  retry.
- `ops.collection.json` focuses on suspend, disable, and credential rotation.
- `reconciliation.collection.json` focuses on mismatched callback evidence and
  resolution.
- `happy-path.collection.json` groups the major E2E journeys into one place.

## Relationship To The Testing Docs

Use the Postman assets together with:

- `docs/testing/e2e.md`
- `docs/testing/matrix.md`
- `docs/testing/scenarios/`

Suggested interpretation:

- Postman gives QA/QC executable requests
- `scenarios/*.md` explains the business meaning and assertions
- `matrix.md` helps map manual execution back to scenario coverage
