# API Contract

These documents are the canonical API contract until generated OpenAPI docs are
introduced. Implementation must follow these contracts unless a later plan file
explicitly changes the behavior.

## Documents

- `merchant_api.md` - merchant-facing payment and refund APIs.
- `ops_api.md` - internal ops/admin APIs.
- `provider_callback_api.md` - bank/provider/simulator callback APIs.
- `webhook_spec.md` - outbound merchant webhook contract.
- `error_catalog.md` - shared error response shape and error codes.

## Endpoint Ownership

- Merchant-facing endpoints are authenticated with merchant HMAC headers.
- Provider callback endpoints are accepted from the bank/provider/simulator side.
  For the MVP simulator, transport trust can be environment-local until provider
  signing is introduced.
- Ops endpoints are internal-only and are not part of the merchant-facing API.

## Versioning

All MVP endpoints use the `/v1` prefix. Breaking contract changes require a plan
update before implementation.
