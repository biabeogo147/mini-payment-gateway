# Local Setup

## Prerequisites

- Docker Desktop.
- Python 3.13 or a compatible Python executable available as:
  `python`.
- Repository root: the directory created by `git clone`.

## Start PostgreSQL

```bash
docker compose up -d postgres
```

## Install Backend

```bash
cd backend
python -m pip install -e .
```

## Apply Migrations

```bash
cd backend
python -m alembic upgrade head
```

## Start API

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check:

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/docs`

## Run Tests

```bash
cd backend
python -m unittest discover tests -v
```

For the full MVP demo path:

```bash
cd backend
python -m unittest tests.test_e2e_payment_refund_webhook -v
```
