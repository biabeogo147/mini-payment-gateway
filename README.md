# Mini Payment Gateway

Mini Payment Gateway is a FastAPI backend MVP for merchant onboarding, HMAC
merchant APIs, QR-style payment creation, provider callbacks, full refunds,
webhook delivery, ops reconciliation, and audit trails.

## Backend

The application lives under `backend/` and uses SQLAlchemy, Alembic, PostgreSQL,
and standard `unittest` tests.

Quick start:

```powershell
docker compose up -d postgres
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m pip install -e .
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m alembic upgrade head
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run tests:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_e2e_payment_refund_webhook -v
```

Smoke scripts:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_payment_api.py
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_provider_callback_api.py
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_refund_api.py
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_webhook_api.py
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' scripts\smoke_ops_reconciliation_api.py
```

## Docs

- `docs/README.md` - docs map by reader goal.
- `docs/getting-started/runbook.md` - setup, verification, smoke, and demo operations.
- `docs/api/README.md` - API contract index.
- `docs/testing/e2e.md` - scenario catalog and coverage snapshot.
- `docs/architecture/backend.md` - backend architecture and layer responsibilities.
- `docs/operations/` - operator SOPs for onboarding, webhook retry, and reconciliation.
