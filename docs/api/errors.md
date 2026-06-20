# Error Catalog

All API errors use the same response shape.

```json
{
  "error_code": "PAYMENT_ALREADY_SUCCESS",
  "message": "Payment already succeeded for this order.",
  "request_id": "req_...",
  "details": {}
}
```

## Common Fields

- `error_code`: stable machine-readable code.
- `message`: human-readable message suitable for logs and API clients.
- `request_id`: gateway request correlation id when available.
- `details`: structured details such as invalid fields or current resource state.

## Error Codes

| Code | HTTP | Meaning |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | Request shape or field validation failed. |
| `AUTH_MISSING_HEADER` | 401 | Required merchant auth header is missing. |
| `AUTH_INVALID_MERCHANT` | 401 | `X-Merchant-Id` does not identify a known merchant. |
| `AUTH_INVALID_CREDENTIAL` | 401 | `X-Access-Key` is not active for the merchant. |
| `AUTH_TIMESTAMP_EXPIRED` | 401 | `X-Timestamp` is outside the 5 minute validity window. |
| `AUTH_INVALID_SIGNATURE` | 401 | `X-Signature` does not match the canonical request signature. |
| `PROVIDER_AUTH_MISSING_HEADER` | 401 | Required provider callback auth header is missing. |
| `PROVIDER_AUTH_UNKNOWN_PROVIDER` | 401 | `X-Provider-Id` has no configured callback secret. |
| `PROVIDER_AUTH_TIMESTAMP_EXPIRED` | 401 | `X-Provider-Timestamp` is invalid or outside the 5 minute window. |
| `PROVIDER_AUTH_INVALID_SIGNATURE` | 401 | `X-Provider-Signature` does not match the callback body. |
| `MERCHANT_NOT_ACTIVE` | 403 | Merchant is not allowed to create payment or refund. |
| `ACTIVE_QR_ACCOUNT_REQUIRED` | 409 | Active merchant has no active QR receiving account for the pilot provider. |
| `VIETQR_REQUIRES_WHOLE_VND` | 422 | Pilot VietQR payment requires `VND` and a whole-VND amount. |
| `PAYMENT_PENDING_EXISTS` | 409 | A non-identical pending payment already exists for the order. |
| `PAYMENT_ALREADY_SUCCESS` | 409 | The order already has a successful payment. |
| `PAYMENT_NOT_FOUND` | 404 | Payment cannot be found for this merchant. |
| `PAYMENT_INVALID_STATE_TRANSITION` | 409 | Requested payment state transition is not allowed. |
| `PAYMENT_NOT_REFUNDABLE` | 409 | Payment is not in a refundable state. |
| `REFUND_NOT_ALLOWED` | 409 | Refund request violates refund business rules. |
| `REFUND_WINDOW_EXPIRED` | 409 | Refund is outside the 7 day window from `paid_at`. |
| `REFUND_AMOUNT_NOT_FULL` | 409 | Refund amount does not match the original payment amount. |
| `REFUND_INVALID_STATE_TRANSITION` | 409 | Requested refund state transition is not allowed. |
| `REFUND_NOT_FOUND` | 404 | Refund cannot be found for this merchant. |
| `WEBHOOK_EVENT_NOT_FOUND` | 404 | Webhook event cannot be found for manual retry. |
| `WEBHOOK_RETRY_NOT_ALLOWED` | 409 | Webhook event is not eligible for retry. |
