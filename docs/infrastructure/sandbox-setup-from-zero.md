# Sandbox Setup From Zero

This is the day-0 provisioning guide for the sandbox host.

Use it when you are:

- building a brand-new sandbox host;
- rebuilding the host after replacement or loss;
- handing the first successful deploy to another DevOps operator.

This file owns setup from a fresh Ubuntu server to the first successful
workflow deploy. For current live host facts, use
`sandbox-access-inventory.md`. For day-2 operations, use
`sandbox-deployment.md`.

## What You Need Before Starting

- Ubuntu x64 host with SSH access
- a sudo-capable bootstrap user
- outbound HTTPS from the host to GitHub
- repository admin access to register a self-hosted runner
- runtime values for database, auth secrets, and published ports

Repository prerequisites already expected on `main`:

- `.github/workflows/sandbox-deploy.yml`
- `docker-compose.sandbox.yml`
- `deploy/sandbox_deploy.sh`
- `.env.sandbox.example`
- `apps/ops-dashboard/`
- `apps/merchant-dashboard/`

## Day-0 Outcome

When this guide is complete, you should have:

- Docker and Docker Compose installed
- a non-root deployment account named `github-runner`
- a sandbox checkout at `/opt/mini-payment-gateway`
- a server-local `.env` file with runtime values
- a registered self-hosted runner service
- a successful manual deploy
- a successful workflow deploy

## Setup Flow

```mermaid
flowchart TB
    A["Fresh Ubuntu host"] --> B["Verify access and outbound GitHub reachability"]
    B --> C["Install base packages and Docker"]
    C --> D["Create github-runner and app directory"]
    D --> E["Clone repo and create .env"]
    E --> F["Validate compose config"]
    F --> G["Run first manual deploy"]
    G --> H["Register self-hosted runner"]
    H --> I["Run first workflow deploy"]
    I --> J["Hand off to day-2 runbook + inventory"]
```

## Step 0: Verify The Starting Host

Why:

- confirm the machine is suitable before installing anything

Commands:

```bash
whoami
hostname
lsb_release -a
sudo -v
curl -I https://github.com
df -h
free -h
```

Success means:

- `sudo -v` works
- GitHub is reachable over HTTPS
- disk and memory are sufficient for Docker builds and PostgreSQL

## Step 1: Install Base Packages And Docker

Commands:

```bash
sudo apt update
sudo apt install -y git curl tar ca-certificates
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable docker
sudo systemctl start docker
```

Verify:

```bash
git --version
curl --version
docker version
docker compose version
sudo systemctl is-active docker
```

## Step 2: Create The Deployment Account

Commands:

```bash
sudo adduser github-runner
sudo usermod -aG docker github-runner
```

Verify:

```bash
id github-runner
```

Success means the account exists and includes the `docker` group.

## Step 3: Prepare The Application Directory

Commands:

```bash
sudo mkdir -p /opt/mini-payment-gateway
sudo chown -R github-runner:github-runner /opt/mini-payment-gateway
```

Verify:

```bash
ls -ld /opt/mini-payment-gateway
```

## Step 4: Clone The Repository

Run as `github-runner`:

```bash
sudo -u github-runner git clone --branch main https://github.com/biabeogo147/mini-payment-gateway.git /opt/mini-payment-gateway
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git status && git rev-parse --abbrev-ref HEAD'
```

Success means:

- the checkout is on `main`
- the working tree is clean

## Step 5: Create The Server-Only `.env`

Copy the example:

```bash
sudo -u github-runner cp /opt/mini-payment-gateway/.env.sandbox.example /opt/mini-payment-gateway/.env
sudo -u github-runner chmod 600 /opt/mini-payment-gateway/.env
sudo -u github-runner editor /opt/mini-payment-gateway/.env
```

Minimum categories that must be present:

- database:
  - `POSTGRES_DB`
  - `POSTGRES_USER`
  - `POSTGRES_PASSWORD`
  - `DATABASE_URL`
- internal auth:
  - `INTERNAL_AUTH_SECRET`
  - `INTERNAL_AUTH_COOKIE_NAME`
  - `INTERNAL_AUTH_TTL_SECONDS`
  - `INTERNAL_AUTH_COOKIE_SECURE`
- merchant auth:
  - `MERCHANT_AUTH_SECRET`
  - `MERCHANT_AUTH_COOKIE_NAME`
  - `MERCHANT_AUTH_TTL_SECONDS`
  - `MERCHANT_AUTH_COOKIE_SECURE`
- published bind/port values:
  - `POSTGRES_BIND_ADDR`
  - `POSTGRES_PORT`
  - `BACKEND_BIND_ADDR`
  - `BACKEND_PORT`
  - `OPS_DASHBOARD_BIND_ADDR`
  - `OPS_DASHBOARD_PORT`
  - `MERCHANT_DASHBOARD_BIND_ADDR`
  - `MERCHANT_DASHBOARD_PORT`

Minimum example:

```dotenv
APP_ENV=sandbox

POSTGRES_DB=mini_payment_gateway
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql+psycopg2://postgres:change-me@postgres:5432/mini_payment_gateway

INTERNAL_AUTH_SECRET=replace-with-a-long-random-secret
INTERNAL_AUTH_COOKIE_NAME=mini_payment_gateway_internal_session
INTERNAL_AUTH_TTL_SECONDS=43200
INTERNAL_AUTH_COOKIE_SECURE=false

MERCHANT_AUTH_SECRET=replace-with-a-different-long-random-secret
MERCHANT_AUTH_COOKIE_NAME=mini_payment_gateway_merchant_session
MERCHANT_AUTH_TTL_SECONDS=43200
MERCHANT_AUTH_COOKIE_SECURE=false

POSTGRES_BIND_ADDR=127.0.0.1
POSTGRES_PORT=5432
BACKEND_BIND_ADDR=127.0.0.1
BACKEND_PORT=8000
OPS_DASHBOARD_BIND_ADDR=127.0.0.1
OPS_DASHBOARD_PORT=4173
MERCHANT_DASHBOARD_BIND_ADDR=127.0.0.1
MERCHANT_DASHBOARD_PORT=4174
```

Important notes:

- keep `DATABASE_URL` pointed at the Docker service host `postgres`
- use different long random values for internal and merchant auth secrets
- use `127.0.0.1` for host-only publishing
- use the sandbox LAN IP when internal clients should connect directly
- do not commit the real `.env`

Verify:

```bash
sudo -u github-runner ls -l /opt/mini-payment-gateway/.env
```

## Step 6: Validate Compose Configuration

Command:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml config'
```

Success means the merged compose config renders without errors.

## Step 7: Run The First Manual Deploy

Command:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && bash deploy/sandbox_deploy.sh'
```

What this proves:

- checkout, Docker, database, and migrations all work on the host
- backend and both dashboards can start before GitHub Actions is involved

Verify using the configured published host and ports:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
curl -fsS http://<configured-host>:8000/health
curl -fsS http://<configured-host>:4173/
curl -fsS http://<configured-host>:4174/
curl -fsS http://<configured-host>:8000/v1/internal/auth/bootstrap-status
```

Success means:

- `postgres`, `backend`, `ops-dashboard`, and `merchant-dashboard` are up
- backend health returns `{"status":"ok"}`
- both dashboard roots return HTML

## Step 8: Register The Self-Hosted Runner

In GitHub:

```text
Repository -> Settings -> Actions -> Runners -> New self-hosted runner
```

Choose Linux x64, then run the GitHub-provided commands as `github-runner`.
Use the canonical runner name and labels from `sandbox-access-inventory.md`.

Typical flow:

```bash
sudo -u github-runner bash
cd /home/github-runner
mkdir -p actions-runner
cd actions-runner
curl -o actions-runner-linux-x64.tar.gz -L <github-provided-runner-url>
tar xzf actions-runner-linux-x64.tar.gz
./config.sh \
  --url https://github.com/biabeogo147/mini-payment-gateway \
  --token <runner-registration-token> \
  --name <runner-name> \
  --labels <comma-separated-runner-labels>
exit
```

Install the service:

```bash
cd /home/github-runner/actions-runner
sudo ./svc.sh install github-runner
sudo ./svc.sh start
sudo ./svc.sh status
```

Verify:

- the runner appears `Online` in GitHub
- the service is running on the host

## Step 9: Configure Optional GitHub Environment Values

Recommended environment:

```text
Environment name: sandbox
```

Recommended variables:

| Variable | Value |
| --- | --- |
| `SANDBOX_APP_DIR` | `/opt/mini-payment-gateway` |
| `SANDBOX_COMPOSE_FILE` | `docker-compose.sandbox.yml` |
| `SANDBOX_HEALTH_URL` | optional override; leave unset to derive from `.env` |
| `SANDBOX_OPS_DASHBOARD_URL` | optional override; leave unset to derive from `.env` |
| `SANDBOX_MERCHANT_DASHBOARD_URL` | optional override; leave unset to derive from `.env` |

## Step 10: Run The First Workflow Deploy

Trigger either:

1. a push to `main`
2. `workflow_dispatch` for `Sandbox Deploy`

Success means:

- `backend-tests` passes
- `frontend-build` passes
- `deploy-sandbox` passes
- the host checkout advances to the intended commit

Verify with the same commands from Step 7.

## Day-0 Acceptance Checklist

You are done when all of these are true:

- Docker is installed and running
- `github-runner` exists and can use Docker
- the app checkout exists and is owned by `github-runner`
- `.env` exists only on the host
- compose config renders successfully
- manual deploy succeeds
- the self-hosted runner is online
- workflow deploy succeeds
- backend health passes
- both dashboard roots respond

## Handoff After Day-0

After the first successful workflow deploy:

- use `sandbox-deployment.md` for day-2 operations
- use `sandbox-access-inventory.md` for current host facts, ports, and secret
  names
- keep historical rollout notes in `archive/` and `docs/history/completions/`
