# API Contract

These documents are the canonical API contract until generated OpenAPI docs are
introduced. Implementation must follow these contracts unless a later plan file
explicitly changes the behavior.

## Documents

- `merchant.md` - merchant-facing payment and refund APIs.
- `merchant-portal.md` - merchant dashboard session auth and read-only portal
  APIs.
- `ops.md` - internal ops/admin APIs.
- `provider-callback.md` - bank/provider/simulator callback APIs.
- `webhook.md` - outbound merchant webhook contract.
- `errors.md` - shared error response shape and error codes.

## Endpoint Ownership

- Merchant-facing payment/refund endpoints are authenticated with merchant HMAC
  headers.
- Merchant Portal endpoints are authenticated with a separate HttpOnly session
  cookie. Portal users are scoped to one merchant and are provisioned by
  internal `ADMIN` users from Ops.
- Provider callback endpoints are accepted from the bank/provider/simulator side
  with `X-Provider-Id`, `X-Provider-Timestamp`, and
  `X-Provider-Signature` HMAC headers.
- Ops endpoints are internal-only, authenticated with internal session cookies
  in phase 10, and are not part of the merchant-facing API.

## Actor And Auth Matrix

| Actor | API surface | Auth mechanism | Scope source | Example routes |
| --- | --- | --- | --- | --- |
| Merchant backend | Merchant API | `X-Merchant-Id`, `X-Access-Key`, `X-Timestamp`, `X-Signature` HMAC headers | Authenticated merchant credential | `/v1/payments`, `/v1/refunds` |
| Admin/Ops user | Ops API | Internal HttpOnly session cookie | Internal user role `ADMIN` or `OPS` | `/v1/ops/merchants`, `/v1/ops/reconciliation` |
| Admin/Ops user | Ops portal-user API | Internal HttpOnly session cookie | Internal user role `ADMIN` or `OPS` | `/v1/ops/merchants/{merchant_id}/portal-users` |
| Merchant portal user | Merchant Portal API | Merchant HttpOnly session cookie | `merchant_users.merchant_db_id` | `/v1/merchant-portal/dashboard/summary`, `/v1/merchant-portal/analytics` |
| Provider simulator | Provider callback API | Provider HMAC headers using `PROVIDER_CALLBACK_SECRETS` | Callback payload references | `/v1/provider/callbacks/payment`, `/v1/provider/callbacks/refund` |

Merchant Portal endpoints never accept a client-supplied `merchant_id` for data
scope. The backend resolves scope from the session user to avoid cross-merchant
read leaks.

## Versioning

All MVP endpoints use the `/v1` prefix. Breaking contract changes require a plan
update before implementation.
