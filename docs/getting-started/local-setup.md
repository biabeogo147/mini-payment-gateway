# Local Setup

## Prerequisites

- Docker Desktop.
- Python environment:
  `D:\Anaconda\envs\mini-payment-gateway\python.exe`.
- Repository root: `D:\DS-AI\mini-payment-gateway`.

## Start PostgreSQL

```powershell
docker compose up -d postgres
```

## Install Backend

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m pip install -e .
```

## Apply Migrations

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m alembic upgrade head
```

## Start API

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check:

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/docs`

## Run Tests

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

For the full MVP demo path:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_e2e_payment_refund_webhook -v
```
