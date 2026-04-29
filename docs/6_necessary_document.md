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

* architecture diagram: `docs/architecture.md`
* sequence diagrams
* API spec: `docs/api/merchant_api.md`, `docs/api/provider_callback_api.md`, `docs/api/ops_api.md`
* webhook spec: `docs/api/webhook_spec.md`
* error catalog: `docs/api/error_catalog.md`
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
