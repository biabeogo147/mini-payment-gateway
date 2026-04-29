# Ops And Audit Scenarios

Ops scenarios cover administrative state changes and auditability. These APIs are
planned for phase 07.

## OPS-01 Ops Suspends Merchant

Implementation Status: Planned - phase 07.

API:

```http
POST /v1/ops/merchants/{merchant_id}/suspend
```

DB Effects:

- `merchants`: update to `SUSPENDED`.
- `audit_logs`: insert suspend event.

Expected Assertions:

- Suspended merchant cannot create payment or refund.
- Ops can still inspect historical records.

## OPS-02 Ops Disables Merchant

Implementation Status: Planned - phase 07.

API:

```http
POST /v1/ops/merchants/{merchant_id}/disable
```

DB Effects:

- `merchants`: update to `DISABLED`.
- `audit_logs`: insert disable event.

Expected Assertions:

- Disabled merchant cannot create payment or refund.
- Disabled merchant's old credentials no longer authenticate if the phase
  chooses to revoke them.

## OPS-03 Credential Rotation

Implementation Status: Planned - phase 07.

API:

```http
POST /v1/ops/merchants/{merchant_id}/credentials/rotate
```

DB Effects:

- `merchant_credentials`: old credential becomes `ROTATED`.
- `merchant_credentials`: new credential becomes `ACTIVE`.
- `audit_logs`: insert credential rotation event.

Expected Assertions:

- Exactly one active credential remains.
- Old credential can no longer authenticate.

## AUD-01 Ops Merchant Action Writes Audit Log

Implementation Status: Planned - phase 07.

DB Effects:

- `audit_logs`: insert event with actor, entity type, entity id, before state,
  after state, reason, and timestamp.

Expected Assertions:

- Every merchant state change is traceable.

## AUD-02 Credential Rotation Writes Audit Log

Implementation Status: Planned - phase 07.

DB Effects:

- `audit_logs`: insert credential rotation event.

Expected Assertions:

- Audit row does not expose plaintext secret key.
