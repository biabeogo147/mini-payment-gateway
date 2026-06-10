# Local Setup

## Prerequisites

- Docker Desktop.
- Python 3.13 or a compatible Python executable available as:
  `python`.
- Node.js 20 with npm for dashboard development.
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

If you are using the repository `.venv` on Windows, run the same commands with
the virtualenv interpreter:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip install -e .
```

## Apply Migrations

```bash
cd backend
python -m alembic upgrade head
```

Windows `.venv` equivalent:

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
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

Windows `.venv` equivalent:

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

For the full MVP demo path:

```bash
cd backend
python -m unittest tests.test_e2e_payment_refund_webhook -v
```

## Start Dashboards

From the repository root:

```bash
npm install
npm run ops-dashboard:dev
npm run merchant-dashboard:dev
```

Default local ports:

- Ops Dashboard: `http://127.0.0.1:4173`
- Merchant Dashboard: `http://127.0.0.1:4174`

Both Vite apps proxy `/api` to `http://127.0.0.1:8000`.

## Seed Dashboard Demo Data

Run this only when you want a local/sandbox walkthrough dataset:

```bash
cd backend
python scripts/seed_dashboard_demo.py
```

The script is idempotent and creates a demo merchant, merchant portal user,
credential metadata, payments, refunds, webhook events, delivery attempts, and
callback evidence.

Default local demo portal values created by the script:

- Merchant id: `m_demo_dashboard`
- Portal user: `merchant.demo@example.com`
- Portal password: `MerchantDemo123!`

Override these with `DASHBOARD_DEMO_MERCHANT_ID`,
`DASHBOARD_DEMO_MERCHANT_EMAIL`, and `DASHBOARD_DEMO_MERCHANT_PASSWORD` when
needed. Do not commit live sandbox secrets to docs or source control.

## Frontend Regression Commands

Run these from the repository root before opening a review:

```bash
npm run merchant-dashboard:typecheck
npm run merchant-dashboard:test
npm run merchant-dashboard:build
npm run ops-dashboard:typecheck
npm run ops-dashboard:build
```

## Dashboard Browser Smoke Checklist

Use local URLs unless you are intentionally testing sandbox.

Ops Dashboard at `http://127.0.0.1:4173`:

- login or bootstrap a local internal admin session;
- open merchant list/detail;
- create a throwaway merchant;
- run merchant lifecycle actions and confirm status badges update without
  overflow;
- create, reset password for, deactivate, and reactivate a merchant portal
  user from merchant detail;
- check active session card remains fixed in the topbar and does not move while
  navigating.

Merchant Dashboard at `http://127.0.0.1:4174`:

- login with the seeded demo merchant portal user;
- open Overview and confirm compact charts render with no horizontal overflow;
- open Analytics and switch `7d`, `30d`, `90d`;
- use `View data` on analytics cards to confirm exact values are readable;
- open Payments, Refunds, Webhooks, Profile, and Credentials;
- use lookup and analytics drill-down query params where applicable;
- open change password form, then cancel or use a local throwaway user;
- sign out and confirm the session returns to login.

For mobile smoke, manually narrow the browser/app window and confirm dashboard
charts stack into one column, status badges stay inside list items, and card
text does not overlap.
