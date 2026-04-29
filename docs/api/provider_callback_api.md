# Provider Callback API

Provider callback APIs receive payment and refund results from the bank,
provider, or simulator. In the MVP, the simulator can call these endpoints from
the local environment without provider-grade signing.

## Payment Callback

`POST /v1/provider/callbacks/payment`

### Request

```json
{
  "external_reference": "bank_ref_1001",
  "transaction_reference": "pay_...",
  "status": "SUCCESS",
  "amount": "100000.00",
  "paid_at": "2026-04-29T10:00:00Z",
  "raw_payload": {
    "provider_status": "00"
  }
}
```

### Behavior

- Store raw and normalized callback evidence in `BankCallbackLog`.
- If payment is `PENDING`, move it to `SUCCESS` or `FAILED`.
- If payment is already `EXPIRED`, do not move it to `SUCCESS`.
- Late success after expiration creates reconciliation evidence for manual review.
- Final payment updates emit webhook events in the webhook phase.

## Refund Callback

`POST /v1/provider/callbacks/refund`

### Request

```json
{
  "external_reference": "bank_ref_refund_1001",
  "transaction_reference": "rfnd_...",
  "status": "REFUNDED",
  "amount": "100000.00",
  "processed_at": "2026-04-29T10:05:00Z",
  "raw_payload": {
    "provider_status": "00"
  }
}
```

### Behavior

- Store raw and normalized callback evidence in `BankCallbackLog`.
- If refund is `REFUND_PENDING`, move it to `REFUNDED` or `REFUND_FAILED`.
- Final refund updates emit webhook events in the webhook phase.

## Normalized Processing Results

- `PROCESSED`: callback was applied to an internal transaction.
- `IGNORED`: duplicate or irrelevant callback did not change state.
- `FAILED`: callback could not be processed.
- `PENDING_REVIEW`: callback requires reconciliation/manual review.
