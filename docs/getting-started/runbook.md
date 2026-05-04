# Mini Payment Gateway Runbook

This runbook is the developer/operator entry point for the MVP backend. It
assumes commands are run from the repository root unless a step says `cd
backend`.

## Prerequisites

- Docker Desktop with the `postgres` service available through `docker compose`.
- Python 3.13 or a compatible Python executable available as:
  `python`.
- Backend dependencies installed in editable mode.
- PostgreSQL connection settings available through the existing project config.

## Setup

```bash
docker compose up -d postgres
cd backend
python -m pip install -e .
python -m alembic upgrade head
```

## Start The API

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health and OpenAPI checks:

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/docs`

## Test Commands

```bash
cd backend
python -m unittest discover tests -v
python -m unittest tests.test_e2e_payment_refund_webhook -v
```

## Smoke Commands

```bash
cd backend
python scripts/smoke_payment_api.py
python scripts/smoke_provider_callback_api.py
python scripts/smoke_refund_api.py
python scripts/smoke_webhook_api.py
python scripts/smoke_ops_reconciliation_api.py
```

Use `smoke_ops_reconciliation_api.py` for the fullest API demo slice. It starts
a temporary API server, creates and activates a merchant through ops APIs,
creates a signed payment, sends a late success callback, resolves the
reconciliation record, and prints a JSON summary.

## Demo Flow

1. Register merchant with `POST /v1/ops/merchants`.
2. Submit onboarding with
   `PUT /v1/ops/merchants/{merchant_id}/onboarding-case`.
3. Approve onboarding with
   `POST /v1/ops/merchants/{merchant_id}/onboarding-case/approve`.
4. Create credential with `POST /v1/ops/merchants/{merchant_id}/credentials`.
5. Activate merchant with `POST /v1/ops/merchants/{merchant_id}/activate`.
6. Create a signed payment with `POST /v1/payments`.
7. Mark payment success with `POST /v1/provider/callbacks/payment`.
8. Create a signed full refund with `POST /v1/refunds`.
9. Mark refund success with `POST /v1/provider/callbacks/refund`.
10. Deliver or retry webhook events through the webhook delivery service or
    `POST /v1/ops/webhooks/{event_id}/retry` for failed events.

Request/response details live in `docs/api/`.

## Inspecting Operations

- Webhook attempts: query `webhook_events` and `webhook_delivery_attempts`.
- Reconciliation cases: use `GET /v1/ops/reconciliation` with optional
  `match_result=PENDING_REVIEW`, `MISMATCHED`, `MATCHED`, or `RESOLVED`.
- Audit trail: query `audit_logs` for event codes such as
  `MERCHANT_CREATED`, `MERCHANT_ACTIVATED`, `RECONCILIATION_RESOLVED`, and
  `WEBHOOK_MANUAL_RETRY`.

## Related Docs

- `docs/api/README.md`
- `docs/testing/e2e.md`
- `docs/architecture/diagrams/payment-flow.puml`
- `docs/architecture/diagrams/refund-flow.puml`
- `docs/architecture/diagrams/webhook-retry-flow.puml`
- `docs/architecture/diagrams/reconciliation-flow.puml`
- `docs/operations/merchant-onboarding-sop.md`
- `docs/operations/webhook-retry-sop.md`
- `docs/operations/reconciliation-sop.md`
