# Merchant Onboarding SOP

This SOP covers the internal MVP merchant lifecycle. Detailed request and
response examples are in `docs/api/ops.md`.

## Register Merchant

Use `POST /v1/ops/merchants` with:

- nested `actor` context;
- stable `merchant_id`;
- `merchant_name` and `contact_email`;
- optional `webhook_url`;
- optional settlement fields.

Expected result: merchant is `PENDING_REVIEW` and `MERCHANT_CREATED` is written
to `audit_logs`.

## Submit Onboarding Case

Use `PUT /v1/ops/merchants/{merchant_id}/onboarding-case` with:

- nested `actor` context;
- `submitted_profile_json`;
- `documents_json`;
- optional `review_checks_json`.

Expected result: onboarding case is `PENDING_REVIEW` and
`ONBOARDING_CASE_SUBMITTED` is audited.

## Approve Or Reject

Approve with:

```text
POST /v1/ops/merchants/{merchant_id}/onboarding-case/approve
```

Reject with:

```text
POST /v1/ops/merchants/{merchant_id}/onboarding-case/reject
```

Include `actor`, `reviewed_by`, and `decision_note`. Approval writes
`ONBOARDING_CASE_APPROVED`; rejection writes `ONBOARDING_CASE_REJECTED`.

## Create Credential And Activate

Create an active credential:

```text
POST /v1/ops/merchants/{merchant_id}/credentials
```

Then activate:

```text
POST /v1/ops/merchants/{merchant_id}/activate
```

Activation requires an approved onboarding case and an active credential. The
merchant becomes `ACTIVE`, and merchant APIs can create payments/refunds with
valid HMAC headers.

## Suspend, Disable, Or Rotate

- Suspend with `POST /v1/ops/merchants/{merchant_id}/suspend`.
- Disable with `POST /v1/ops/merchants/{merchant_id}/disable`.
- Rotate credential with
  `POST /v1/ops/merchants/{merchant_id}/credentials/rotate`.

Suspended and disabled merchants cannot create new payments or refunds.
Credential rotation deactivates the previous active credential and audits both
before/after credential state.
