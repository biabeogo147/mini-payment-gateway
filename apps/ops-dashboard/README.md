# Ops Dashboard

Internal operations dashboard for Mini Payment Gateway.

## Scope

- Internal session login/bootstrap for `ADMIN` and `OPS`.
- Overview metrics, operational queues, and trend charts.
- Merchant onboarding and merchant lifecycle management.
- Merchant credential creation/rotation/status actions.
- Payment, refund, webhook, reconciliation, and audit explorers.
- Internal user management for `ADMIN`.
- Merchant portal user provisioning for `ADMIN`.

`OPS` can continue operational workflows, but only `ADMIN` can create merchant
portal users, update their status/role/name, or reset their passwords.

## Local Development

From the repository root:

```bash
npm install
npm run ops-dashboard:dev
```

The app runs on `http://127.0.0.1:4173` by default and proxies `/api` to
`http://127.0.0.1:8000`.

## Verification

```bash
npm run ops-dashboard:typecheck
npm run ops-dashboard:build
```
