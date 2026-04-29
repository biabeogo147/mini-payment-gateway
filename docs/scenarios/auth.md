# Auth Scenarios

Authentication scenarios cover the merchant-facing HMAC contract. They apply to
every merchant API, including payment and refund APIs.

## Shared Request Headers

```http
X-Merchant-Id: m_demo
X-Access-Key: ak_demo
X-Timestamp: 2026-04-29T10:00:00Z
X-Signature: <hmac_sha256>
X-Idempotency-Key: idem-1001
```

DB Reads:

- `merchants`
- `merchant_credentials`

DB Effects:

- No business table is inserted or updated when authentication fails.

## AUTH-01 Missing Auth Header Fails

Implementation Status: Implemented - phase 02.

Actor: Merchant backend.

APIs:

- Any merchant API.

Expected Response:

```json
{
  "error_code": "AUTH_MISSING_HEADER",
  "message": "Missing required header: x-signature",
  "details": {
    "header": "x-signature"
  }
}
```

Expected Assertions:

- Request is rejected before business service execution.
- No `payment_transactions` or `refund_transactions` row is inserted.

## AUTH-02 Invalid HMAC Signature Fails

Implementation Status: Implemented - phase 02.

Expected Response:

```json
{
  "error_code": "AUTH_INVALID_SIGNATURE",
  "message": "Merchant authentication failed.",
  "details": {}
}
```

Expected Assertions:

- Signature comparison must use the stored active credential secret.
- No business table is changed.

## AUTH-03 Expired Timestamp Fails

Implementation Status: Implemented - phase 02.

Expected Response:

```json
{
  "error_code": "AUTH_TIMESTAMP_EXPIRED",
  "message": "Request timestamp is invalid or expired.",
  "details": {}
}
```

Expected Assertions:

- Timestamp skew outside the configured tolerance is rejected.
- No business table is changed.

## AUTH-04 Unknown Merchant Fails

Implementation Status: Implemented - phase 02.

Expected Response:

```json
{
  "error_code": "AUTH_INVALID_SIGNATURE",
  "message": "Merchant authentication failed.",
  "details": {}
}
```

Expected Assertions:

- Unknown merchant id does not reveal whether the merchant exists.
- No business table is changed.

## AUTH-05 Inactive Credential Fails

Implementation Status: Implemented - phase 02.

Expected Response:

```json
{
  "error_code": "AUTH_INVALID_SIGNATURE",
  "message": "Merchant authentication failed.",
  "details": {}
}
```

Expected Assertions:

- Rotated, disabled, or expired credentials cannot authenticate.
- Exactly one active credential should be used for request verification.
