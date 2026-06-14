# Merchant Dashboard

Merchant-facing read-only portal for Mini Payment Gateway.

## Scope

- Merchant session login/logout with a separate HttpOnly cookie.
- Current user session and local password change.
- Overview summary and chart cards.
- Interactive analytics with 7/30/90 day ranges, tooltips, data tables, and
  drill-down links.
- Merchant-scoped payment, refund, and webhook explorers.
- Read-only merchant profile metadata.
- Read-only credential metadata: `access_key`, `secret_key_last4`, status, and
  timestamps only.

The dashboard never accepts `merchant_id` from the client for scoping. The
backend resolves merchant scope from the logged-in portal user.

## Out Of Scope

- Raw credential secrets.
- Internal audit logs.
- Reconciliation resolution state.
- Webhook retry controls.
- Merchant profile or credential mutation workflows.

## Local Development

From the repository root:

```bash
npm install
npm run merchant-dashboard:dev
```

The app runs on `http://127.0.0.1:4174` by default and proxies `/api` to
`http://127.0.0.1:8000`.

## Demo Data

After backend migrations, seed a walkthrough dataset explicitly:

```bash
cd backend
python scripts/seed_dashboard_demo.py
```

## Verification

```bash
npm run merchant-dashboard:typecheck
npm run merchant-dashboard:test
npm run merchant-dashboard:build
```
