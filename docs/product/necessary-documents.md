# Necessary documentation set

## Product docs

* PRD or product brief
* use case list
* user story list
* acceptance criteria

## Business analysis docs

* merchant onboarding flow
* payment flow
* refund flow
* reconciliation flow
* exception and failure handling flow

## System docs

* architecture diagram: `docs/architecture/backend.md`
* sequence diagrams
* API spec: `docs/api/merchant.md`, `docs/api/provider-callback.md`, `docs/api/ops.md`
* webhook spec: `docs/api/webhook.md`
* error catalog: `docs/api/errors.md`
* state transition diagram
* canonical DB schema
* enum catalog for merchant, onboarding case, payment, refund, webhook, and audit entities

## Testing docs

* happy-path cases
* auth and signature cases
* duplicate/idempotency cases
* timeout and retry cases
* refund-window and full-refund cases
* onboarding approval and activation cases
* DB constraint verification cases

## Operations docs

* runbook
* incident handling guide
* reconciliation SOP
* merchant onboarding SOP
* webhook retry SOP
