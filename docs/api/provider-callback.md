# Provider Callback API

Provider callback APIs receive payment and refund results from the bank,
provider, or simulator. Pilot callbacks require provider HMAC headers.

## Authentication Headers

Every provider callback request must include:

- `X-Provider-Id`: provider id configured in `PROVIDER_CALLBACK_SECRETS`.
- `X-Provider-Timestamp`: request timestamp; valid for 5 minutes.
- `X-Provider-Signature`: HMAC-SHA256 signature.

Canonical signing string:

```text
{timestamp}.{method}.{path}.{body_sha256_hex}
```

Signature:

```text
hex(hmac_sha256(provider_secret, signing_string))
```

Local default:

```text
PROVIDER_CALLBACK_SECRETS=simulator=dev-insecure-provider-callback-secret-change-me
```

## Payment Callback

`POST /v1/provider/callbacks/payment`

Implementation status: implemented for signed simulator/provider callbacks.

### Request

```json
{
  "external_reference": "bank_ref_1001",
  "transaction_reference": "pay_...",
  "status": "SUCCESS",
  "amount": "100000.00",
  "paid_at": "2026-04-29T10:00:00Z",
  "source_type": "SIMULATOR",
  "raw_payload": {
    "provider_status": "00"
  }
}
```

For failed callbacks:

```json
{
  "external_reference": "bank_ref_1001",
  "transaction_reference": "pay_...",
  "status": "FAILED",
  "amount": "100000.00",
  "failed_reason_code": "BANK_REJECTED",
  "failed_reason_message": "Bank rejected payment.",
  "raw_payload": {
    "provider_status": "05"
  }
}
```

### Response

```json
{
  "transaction_id": "pay_...",
  "status": "SUCCESS",
  "processing_result": "PROCESSED",
  "reconciliation_record_id": null
}
```

Unknown transactions, amount mismatches, and late/conflicting callbacks return
`PENDING_REVIEW` with a callback log persisted. Mismatch and late-success cases
also return `reconciliation_record_id`.

### Behavior

- Store raw and normalized callback evidence in `BankCallbackLog`.
- If payment is `PENDING`, move it to `SUCCESS` or `FAILED`.
- If payment is already `EXPIRED`, do not move it to `SUCCESS`.
- Late success after expiration creates reconciliation evidence for manual review.
- Amount mismatch creates reconciliation evidence and does not mark the payment
  successful.
- Duplicate same-state callback is logged as `IGNORED` and does not mutate the
  payment.
- Final payment updates emit durable webhook events in phase 06 when the
  merchant has a configured `webhook_url`.

## Refund Callback

`POST /v1/provider/callbacks/refund`

Implementation status: implemented in phase 05 for refund callbacks.

The provider reports result status as `SUCCESS` or `FAILED`. The gateway maps
those provider statuses to internal refund states `REFUNDED` or
`REFUND_FAILED`.

### Request

```json
{
  "external_reference": "bank_ref_refund_1001",
  "refund_transaction_id": "rfnd_...",
  "status": "SUCCESS",
  "amount": "100000.00",
  "processed_at": "2026-04-29T10:05:00Z",
  "source_type": "SIMULATOR",
  "raw_payload": {
    "provider_status": "00"
  }
}
```

For failed callbacks:

```json
{
  "external_reference": "bank_ref_refund_1001",
  "refund_transaction_id": "rfnd_...",
  "status": "FAILED",
  "amount": "100000.00",
  "failed_reason_code": "BANK_REJECTED",
  "failed_reason_message": "Bank rejected refund.",
  "raw_payload": {
    "provider_status": "05"
  }
}
```

### Response

```json
{
  "refund_transaction_id": "rfnd_...",
  "refund_status": "REFUNDED",
  "processing_result": "PROCESSED",
  "reconciliation_record_id": null
}
```

### Behavior

- Store raw and normalized callback evidence in `BankCallbackLog`.
- If refund is `REFUND_PENDING`, move it to `REFUNDED` or `REFUND_FAILED`.
- Duplicate same-state callbacks are logged as `IGNORED`.
- Unknown refunds, amount mismatches, and final-state conflicts return
  `PENDING_REVIEW`; mismatch/conflict cases create reconciliation evidence.
- Final refund updates emit durable webhook events in phase 06 when the merchant
  has a configured `webhook_url`.

## Normalized Processing Results

- `PROCESSED`: callback was applied to an internal transaction.
- `IGNORED`: duplicate or irrelevant callback did not change state.
- `FAILED`: callback could not be processed.
- `PENDING_REVIEW`: callback requires reconciliation/manual review.
