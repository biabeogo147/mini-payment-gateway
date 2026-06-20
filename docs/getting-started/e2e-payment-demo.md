# End-To-End VietQR Payment Demo

This is the recommended instructor demo for the complete visible payment flow:
bootstrap an Admin, onboard a merchant, create a scannable VietQR payment,
simulate the bank result, deliver the gateway webhook, and let the merchant
checkout show the final status.

The gateway remains API-only. `backend/demo_merchant/` is a separate local
merchant backend and checkout used to show how a real merchant integrates the
gateway. The VietQR image can be scanned by a banking app; the two simulation
buttons replace only the provider/bank callback because this repository is not
connected to a real bank.

## Prerequisites

From the repository root, install dependencies and start only PostgreSQL with
Docker:

```powershell
docker compose up -d postgres
cd backend
..\.venv\Scripts\python.exe -m pip install -e .
..\.venv\Scripts\python.exe -m alembic upgrade head
cd ..
npm install
```

No backend, worker, dashboard, or demo merchant container is required for this
walkthrough.

## Reset To A Clean Demo

Stop the worker before resetting, then run:

```powershell
cd backend
$env:APP_ENV = "demo"
..\.venv\Scripts\python.exe scripts\reset_e2e_demo.py --confirm-reset
```

The script refuses to run unless the environment is `local`, `demo`, or `test`,
the database is PostgreSQL on `localhost`, `127.0.0.1`, or `::1`, and the
confirmation flag is present. It clears business tables, preserves
`alembic_version`, and resets the in-memory demo merchant when it is running.

## Start Five Terminals

Terminal 1, gateway API:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, expiration and webhook worker:

```powershell
cd backend
$env:WORKER_LOOP_INTERVAL_SECONDS = "1"
..\.venv\Scripts\python.exe -m app.worker.main
```

Terminal 3, demo merchant backend and customer checkout:

```powershell
cd backend
$env:DEMO_MODE = "true"
..\.venv\Scripts\python.exe -m uvicorn demo_merchant.main:app --host 127.0.0.1 --port 8100
```

Terminal 4, Ops Dashboard:

```powershell
npm run ops-dashboard:dev
```

Terminal 5, Merchant Dashboard:

```powershell
npm run merchant-dashboard:dev
```

Open these pages:

- Ops Dashboard: `http://127.0.0.1:4173`
- Merchant Dashboard: `http://127.0.0.1:4174`
- Gateway OpenAPI: `http://127.0.0.1:8000/docs`
- Demo merchant checkout: `http://127.0.0.1:8100`

## Demo Data

The reset leaves no users. On the Ops Dashboard bootstrap screen, create the
first Admin with values such as:

- Email: `demo.admin@example.com`
- Full name: `Demo Admin`
- Password: `DemoAdmin123!`

### 1. Admin creates an internal OPS user

After the bootstrap login, open **Internal users** and create the operator who
will perform the day-to-day merchant onboarding:

- Email: `demo.ops@example.com`
- Full name: `Demo Ops Operator`
- Role: `OPS`
- Status: `ACTIVE`
- Initial password: `DemoOps123!`

Internal user management is an `ADMIN`-only action. Log out of the Admin
session, then log in as `demo.ops@example.com` for the next steps.

### 2. OPS creates the merchant profile

Open **Merchants**, fill **Create merchant profile**, and submit these sample
values:

- Reason: `Create merchant for the E2E payment demo.`
- Merchant id: `m_e2e_demo`
- Merchant name: `E2E Demo Shop`
- Legal name: `E2E Demo Shop Company Limited`
- Contact name: `Demo Merchant Owner`
- Contact email: `merchant.owner@example.com`
- Contact phone: `0900000000`
- Webhook URL: `http://127.0.0.1:8100/webhooks/payment-gateway`
- Settlement account name: `E2E DEMO SHOP`
- Settlement account number: `9704000000000001`
- Settlement bank code: `VCB`

The new merchant starts in `PENDING_REVIEW`. Creating the merchant and the
following onboarding operations are deliberately available to `OPS`.

### 3. OPS submits and approves onboarding

Open **Onboarding** and enter:

- Merchant id: `m_e2e_demo`
- Reason: `Submit merchant for the E2E payment demo.`
- Domain or app: `E2E Demo Shop`
- Submitted profile JSON: `{"business_type":"online_shop"}`
- Documents JSON: `{"business_license":"demo-license.pdf"}`
- Review checks JSON: `{"risk_level":"LOW"}`

Click **Submit onboarding case**. Select the pending case, use decision reason
`Approve merchant for the E2E payment demo.`, decision note
`Demo documents and low-risk checks verified.`, then approve it.

### 4. OPS creates the API credential and VietQR account

Return to **Merchants**, select `m_e2e_demo`, and create its initial API
credential:

- Reason: `Issue the initial credential for the E2E payment demo.`
- Access key: `ak_e2e_demo`
- Secret key: `DemoMerchantSecret123!`

Record the secret key when entering it. The credential list only shows its last
four characters later.

In the same merchant detail, create the active VietQR receiving account:

- Reason: `Configure the VietQR account for the E2E payment demo.`
- Bank code: `VCB`
- Bank BIN: `970436`
- Account number: `9704000000000001`
- Account name: `E2E DEMO SHOP`
- Template: `compact`
- Initial status: `ACTIVE`

Use a real account owned by the team instead if the instructor will verify the
recipient name in a banking app. Do not complete a real transfer unless that is
intentional.

### 5. OPS activates the merchant

On the merchant detail page, enter action reason
`Onboarding approved and initial credential issued for demo.` and click
**Activate**. Activation requires approved onboarding and an active API
credential. An active VietQR account is additionally required when the merchant
creates a VietQR payment.

### 6. OPS creates the Merchant Dashboard user

Remain logged in as `demo.ops@example.com`. Open **Merchants**, select
`m_e2e_demo`, then create the merchant-facing portal user:

- Email: `merchant.admin@example.com`
- Full name: `Demo Merchant Admin`
- Role: `MERCHANT_ADMIN`
- Status: `ACTIVE`

Keep the generated temporary password shown once by the dashboard. This is not
the Merchant entity and not an internal OPS account; it is the human login for
`http://127.0.0.1:4174`. Both `ADMIN` and `OPS` can manage these portal users;
only `ADMIN` can manage internal users, rotate credentials, or disable merchants.

Finally, use `m_e2e_demo`, `ak_e2e_demo`, and
`DemoMerchantSecret123!` in the Setup form at `http://127.0.0.1:8100`. The
secret is kept only in the demo merchant server's memory and is never returned
to browser JavaScript after setup.

## Instructor Walkthrough

1. Create an order in the demo merchant checkout. Explain that its backend
   signs `POST /v1/payments` with merchant HMAC; browser JavaScript never sees
   the API secret.
2. Point out the amount, transfer content (`qr_reference`), transaction ID,
   countdown, and QR image. Scan the QR with a banking app to show that account,
   amount, and transfer content are encoded correctly. Do not confirm a real
   transfer unless real funds are intentionally being used.
3. Click **Thành công** under bank simulation. This sends only a signed provider
   callback. It does not directly change the checkout order.
4. Pause on the message saying that the bank responded and the merchant is
   waiting for the gateway webhook.
5. The gateway finalizes the payment and creates a webhook event. The worker
   locks the due-delivery job, signs the webhook, and sends it to the demo
   merchant.
6. The demo merchant verifies timestamp and HMAC, deduplicates the event ID,
   updates its in-memory order, and the polling checkout shows
   **Thanh toán thành công**.
7. Open the same transaction in Merchant Dashboard. In Ops Dashboard, show the
   callback log, webhook event, and successful delivery attempt as operational
   evidence.
8. Repeat with **Thất bại** to demonstrate the failure reason and failed final
   state.

The important boundary is: scanning the QR opens or fills the banking app; it
does not call the gateway. The bank/provider result callback is what informs
the gateway, and the signed gateway webhook is what informs the merchant.

## Automated HTTP Smoke

With all five terminals running, execute both outcomes:

```powershell
cd backend
$env:DEMO_ADMIN_EMAIL = "demo.admin@example.com"
$env:DEMO_ADMIN_PASSWORD = "DemoAdmin123!"
..\.venv\Scripts\python.exe scripts\smoke_e2e_demo.py --outcome success
..\.venv\Scripts\python.exe scripts\smoke_e2e_demo.py --outcome failed
```

Each command provisions a unique merchant through the real Ops API, creates a
real VietQR payment through merchant HMAC, sends a signed provider callback,
waits for the worker webhook, and verifies that Merchant Dashboard APIs expose
the same payment. Successful output contains `WEBHOOK_RECEIVED` and the expected
`SUCCESS` or `FAILED` status.

For the existing Postman/Newman pilot scenario and exact command, see
[`vietqr-pilot-demo.md`](vietqr-pilot-demo.md#postmannewman-demo).

## Troubleshooting

- `ModuleNotFoundError: qrcode`: run the editable install with the same
  `.venv` Python used to start the backend.
- Checkout remains on "waiting for gateway": confirm the worker terminal is
  running with a one-second interval and the merchant webhook URL points to
  `http://127.0.0.1:8100/webhooks/payment-gateway`.
- Provider callback is rejected: the gateway and demo merchant must use the
  same simulator secret from `PROVIDER_CALLBACK_SECRETS` and
  `DEMO_PROVIDER_CALLBACK_SECRET`.
- Webhook is rejected: configure the demo merchant with the exact API secret
  returned when the Ops credential was created.
