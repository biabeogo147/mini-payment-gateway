# Sandbox Access Inventory

This file is the single source of truth for current sandbox host facts.

Use it when you need:

- the sandbox host and checkout path
- the CI/CD runner account and service details
- the published service endpoints
- the canonical runtime key inventory
- commands to inspect current values directly on the host

This file owns live facts only. It does **not** own setup steps, deploy
procedure, or rollout history.

## Current Host Facts

- sandbox host: `192.168.1.199`
- app checkout: `/opt/mini-payment-gateway`
- runtime env file: `/opt/mini-payment-gateway/.env`
- compose file: `docker-compose.sandbox.yml`
- deploy branch: `main`

## CI/CD Runner Facts

- deployment account: `github-runner`
- runner home: `/home/github-runner`
- runner install directory: `/home/github-runner/actions-runner`
- runner name: `sandbox-runner-01`
- runner labels: `self-hosted`, `linux`, `sandbox`, `deploy`
- runner service:
  `actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service`

## Published Endpoints

- PostgreSQL: `192.168.1.199:5432`
- Backend API: `192.168.1.199:8000`
- Ops Dashboard: `192.168.1.199:4173`
- Merchant Dashboard: `192.168.1.199:4174`

## Runtime Key Inventory

Database and runtime:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `APP_ENV`

Internal auth:

- `INTERNAL_AUTH_SECRET`
- `INTERNAL_AUTH_COOKIE_NAME`
- `INTERNAL_AUTH_TTL_SECONDS`
- `INTERNAL_AUTH_COOKIE_SECURE`

Merchant auth:

- `MERCHANT_AUTH_SECRET`
- `MERCHANT_AUTH_COOKIE_NAME`
- `MERCHANT_AUTH_TTL_SECONDS`
- `MERCHANT_AUTH_COOKIE_SECURE`

Published bind and port controls:

- `POSTGRES_BIND_ADDR`
- `POSTGRES_PORT`
- `BACKEND_BIND_ADDR`
- `BACKEND_PORT`
- `OPS_DASHBOARD_BIND_ADDR`
- `OPS_DASHBOARD_PORT`
- `MERCHANT_DASHBOARD_BIND_ADDR`
- `MERCHANT_DASHBOARD_PORT`

## Secret Storage Model

- runtime secrets live in `/opt/mini-payment-gateway/.env`
- deploy execution is direct self-hosted runner execution on the target host
- the workflow does not require SSH deploy secrets
- raw secret values are intentionally server-local and not committed to Git

## Inspect Commands

Inspect current runtime keys:

```bash
sudo -u github-runner bash -lc '
  cd /opt/mini-payment-gateway &&
  grep -E "^(POSTGRES_|DATABASE_URL=|APP_ENV=|INTERNAL_AUTH_|MERCHANT_AUTH_|BACKEND_|OPS_DASHBOARD_|MERCHANT_DASHBOARD_)" .env
'
```

Inspect runner and account details:

```bash
id github-runner
systemctl status actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service --no-pager
```

Inspect current host revision:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git rev-parse --short HEAD'
```

Inspect current published container state:

```bash
sudo -u github-runner bash -lc '
  cd /opt/mini-payment-gateway &&
  docker compose -f docker-compose.sandbox.yml ps
'
```
