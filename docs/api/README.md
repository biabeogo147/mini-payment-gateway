# API Contract

These documents are the canonical API contract until generated OpenAPI docs are
introduced. Implementation must follow these contracts unless a later plan file
explicitly changes the behavior.

## Documents

- `merchant.md` - merchant-facing payment and refund APIs.
- `ops.md` - internal ops/admin APIs.
- `provider-callback.md` - bank/provider/simulator callback APIs.
- `webhook.md` - outbound merchant webhook contract.
- `errors.md` - shared error response shape and error codes.

## Endpoint Ownership

- Merchant-facing endpoints are authenticated with merchant HMAC headers.
- Provider callback endpoints are accepted from the bank/provider/simulator side.
  For the MVP simulator, transport trust can be environment-local until provider
  signing is introduced.
- Ops endpoints are internal-only and are not part of the merchant-facing API.

## Versioning

All MVP endpoints use the `/v1` prefix. Breaking contract changes require a plan
update before implementation.
