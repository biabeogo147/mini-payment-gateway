# Ops And Audit Scenarios

Ops scenarios cover administrative state changes and auditability.

## OPS-01 Ops Suspends Merchant

Implementation Status: Implemented - phase 07.

API:

```http
POST /v1/ops/merchants/{merchant_id}/suspend
```

Request:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Temporarily pause payment activity."
  }
}
```

DB Effects:

- `merchants`: update to `SUSPENDED`.
- `audit_logs`: insert `MERCHANT_SUSPENDED`.

Expected Assertions:

- Suspended merchant cannot create payment or refund.
- Ops can still inspect historical records.

## OPS-02 Ops Disables Merchant

Implementation Status: Implemented - phase 07.

API:

```http
POST /v1/ops/merchants/{merchant_id}/disable
```

Request:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Disable merchant after offboarding."
  }
}
```

DB Effects:

- `merchants`: update to `DISABLED`.
- `audit_logs`: insert `MERCHANT_DISABLED`.

Expected Assertions:

- Disabled merchant cannot create payment or refund.
- Disable does not revoke credentials in phase 07.
- Credential rotation is the operation that makes the old access key unusable.

## OPS-03 Credential Rotation

Implementation Status: Implemented - phase 07.

API:

```http
POST /v1/ops/merchants/{merchant_id}/credentials/rotate
```

Request:

```json
{
  "actor": {
    "actor_type": "OPS",
    "actor_id": null,
    "reason": "Rotate compromised key."
  },
  "access_key": "ak_new",
  "secret_key": "new-secret"
}
```

DB Effects:

- `merchant_credentials`: old credential becomes `ROTATED`.
- `merchant_credentials`: old credential gets `rotated_at` and `expired_at`.
- `merchant_credentials`: new credential becomes `ACTIVE`.
- `audit_logs`: insert `CREDENTIAL_ROTATED`.

Expected Assertions:

- Exactly one active credential remains.
- Old credential can no longer authenticate because auth only accepts
  `CredentialStatus.ACTIVE`.

## AUD-01 Ops Merchant Action Writes Audit Log

Implementation Status: Implemented - phase 07.

DB Effects:

- `audit_logs`: insert event with actor, entity type, entity id, before state,
  after state, reason, and timestamp.

Covered events:

- `MERCHANT_CREATED`
- `MERCHANT_ACTIVATED`
- `MERCHANT_SUSPENDED`
- `MERCHANT_DISABLED`
- `ONBOARDING_CASE_SUBMITTED`
- `ONBOARDING_CASE_APPROVED`
- `ONBOARDING_CASE_REJECTED`

Expected Assertions:

- Every merchant and onboarding state change is traceable.

## AUD-02 Credential Rotation Writes Audit Log

Implementation Status: Implemented - phase 07.

DB Effects:

- `audit_logs`: insert `CREDENTIAL_CREATED` or `CREDENTIAL_ROTATED`.

Expected Assertions:

- Audit rows do not expose plaintext `secret_key`.
- Audit sanitization masks keys named `secret_key` and
  `secret_key_encrypted` recursively.
