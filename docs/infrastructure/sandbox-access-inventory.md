# Sandbox Access Inventory

This document is the internal handoff inventory for sandbox CI/CD access,
runtime secret locations, and the `github-runner` deployment account.

Use it when you need to answer:

- which Linux account owns the sandbox deploy flow;
- where the self-hosted runner lives;
- where runtime secrets are stored;
- which secret names and ports currently exist on the sandbox host;
- how to inspect the current values directly on the server.

This is an inventory and retrieval guide.
It intentionally does **not** commit raw secret values into Git history.

## Current Host Inventory

- Host: `192.168.1.199`
- Repository checkout: `/opt/mini-payment-gateway`
- Deploy branch: `main`
- Runtime env file: `/opt/mini-payment-gateway/.env`
- Runner account: `github-runner`
- Runner home: `/home/github-runner`
- Runner install directory: `/home/github-runner/actions-runner`
- Runner name: `sandbox-runner-01`
- Runner labels: `self-hosted`, `linux`, `sandbox`, `deploy`
- Runner service:
  `actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service`

## `github-runner` Account

The sandbox deploy model uses a dedicated non-root Linux account:

- username: `github-runner`
- primary role: own the checkout and execute deploy jobs
- Docker access: yes, through membership in the `docker` group
- systemd runner service owner: `github-runner`

Why it matters:

- automated deploys run as this user;
- manual recovery should also be executed as this user;
- anyone with effective control of this account plus Docker access has
  privileged control of the sandbox host.

## Current Published Service Endpoints

The sandbox currently publishes all runtime services on the host LAN IP:

- PostgreSQL: `192.168.1.199:5432`
- Backend API: `192.168.1.199:8000`
- Ops Dashboard: `192.168.1.199:4173`
- Merchant Dashboard: `192.168.1.199:4174`

## Secret And Runtime Variable Inventory

The current sandbox `.env` is expected to contain at least these important
values.

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

Published port and bind controls:

- `POSTGRES_BIND_ADDR`
- `POSTGRES_PORT`
- `BACKEND_BIND_ADDR`
- `BACKEND_PORT`
- `OPS_DASHBOARD_BIND_ADDR`
- `OPS_DASHBOARD_PORT`
- `MERCHANT_DASHBOARD_BIND_ADDR`
- `MERCHANT_DASHBOARD_PORT`

## Current Secret Storage Model

The current sandbox topology does **not** use GitHub SSH deploy keys or cloud
secret managers for deploy execution.

Important notes:

- deployment is direct self-hosted runner execution on the target host;
- runtime secrets live in `/opt/mini-payment-gateway/.env`;
- GitHub Actions only needs repository access and runner registration;
- the workflow does not require SSH secrets because GitHub does not SSH into
  the host.

## Retrieve The Current Values On The Host

Inspect the current `.env` directly on the sandbox host:

```bash
sudo -u github-runner bash -lc '
  cd /opt/mini-payment-gateway &&
  grep -E "^(POSTGRES_|DATABASE_URL=|APP_ENV=|INTERNAL_AUTH_|MERCHANT_AUTH_|BACKEND_|OPS_DASHBOARD_|MERCHANT_DASHBOARD_)" .env
'
```

Inspect account and runner details:

```bash
id github-runner
systemctl status actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git rev-parse --short HEAD'
```

Inspect current container publish state:

```bash
sudo -u github-runner bash -lc '
  cd /opt/mini-payment-gateway &&
  docker compose -f docker-compose.sandbox.yml ps
'
```

## Why Raw Secret Values Are Not In Git Docs

This repository is still Git history, so once a raw password or secret is
committed it becomes much harder to rotate and clean up safely later.

The chosen compromise for this internal environment is:

- document the host, account, paths, secret names, and retrieval commands in
  Git;
- keep the raw secret values server-local in `/opt/mini-payment-gateway/.env`.

That gives DevOps a complete handoff without turning Git history into the
secret store itself.
