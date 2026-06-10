# Sandbox Setup From Zero

This guide explains how to take a fresh Ubuntu server from an empty starting
point to the full sandbox DevOps state described in
`devops-architecture.md`.

Use this document when:

- you are provisioning a brand-new sandbox host;
- you are rebuilding the sandbox host after loss or replacement;
- you want one repeatable checklist from "bare server" to "live CI/CD".

This is the repeatable setup guide.
Historical rollout evidence and one-time notes still live in:

- `archive/sandbox-bootstrap.md`
- `sandbox-deployment.md`
- `docs/history/completions/phase-09.md`
- `docs/history/completions/phase-10.md`

## What You Will End Up With

When this guide is complete, the server will have:

- Docker Engine and Docker Compose installed;
- a non-root deployment user named `github-runner`;
- the repository checked out at `/opt/mini-payment-gateway`;
- a server-only `.env` file with sandbox runtime values;
- a working manual deploy path through `deploy/sandbox_deploy.sh`;
- a registered GitHub self-hosted runner running as a systemd service;
- a working CI/CD pipeline where GitHub tests first and then deploys to the
  sandbox host;
- a healthy backend, postgres stack, Ops dashboard, and Merchant Dashboard
  reachable locally on the host;
- internal auth configuration ready so the first `ADMIN` user can be
  bootstrapped from the browser.

## Setup Flow

```mermaid
flowchart TB
    A["Fresh Ubuntu server"] --> B["Verify access and assumptions"]
    B --> C["Install base packages"]
    C --> D["Install Docker"]
    D --> E["Create github-runner user"]
    E --> F["Prepare /opt/mini-payment-gateway"]
    F --> G["Clone repo and create .env"]
    G --> H["Validate compose config"]
    H --> I["Run first manual deploy"]
    I --> J["Install and register self-hosted runner"]
    J --> K["Configure GitHub sandbox environment (optional but recommended)"]
    K --> L["Run first live workflow deploy"]
    L --> M["Verify server matches DevOps architecture"]
```

## Assumptions

This guide assumes:

- the target machine is Ubuntu x64;
- you can SSH into the machine;
- your SSH user has `sudo` access;
- the server can reach GitHub over outbound HTTPS;
- the repository already contains the phase 09, phase 10, and dashboard
  deploy/runtime
  files:
  - `.github/workflows/sandbox-deploy.yml`
  - `deploy/sandbox_deploy.sh`
  - `docker-compose.sandbox.yml`
  - `.env.sandbox.example`
  - `apps/ops-dashboard/`
  - `apps/merchant-dashboard/`
- you have GitHub access to register a self-hosted runner for the repository.

## Information You Need Before Starting

Prepare these inputs first:

| Item | Why you need it |
| --- | --- |
| Server IP or hostname | Needed for SSH and verification |
| SSH username and password or key | Needed to access and bootstrap the host |
| Sudo password | Needed to install packages and system services |
| Repository URL | Needed for the server checkout |
| GitHub repo admin access | Needed to register the self-hosted runner |
| Sandbox runtime values | Needed to populate `.env` |

Minimum sandbox runtime values:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `APP_ENV`
- `BACKEND_BIND_ADDR`
- `BACKEND_PORT`
- `INTERNAL_AUTH_SECRET`
- `INTERNAL_AUTH_COOKIE_NAME`
- `INTERNAL_AUTH_TTL_SECONDS`
- `INTERNAL_AUTH_COOKIE_SECURE`
- `MERCHANT_AUTH_SECRET`
- `MERCHANT_AUTH_COOKIE_NAME`
- `MERCHANT_AUTH_TTL_SECONDS`
- `MERCHANT_AUTH_COOKIE_SECURE`
- `OPS_DASHBOARD_BIND_ADDR`
- `OPS_DASHBOARD_PORT`
- `MERCHANT_DASHBOARD_BIND_ADDR`
- `MERCHANT_DASHBOARD_PORT`
- optionally `POSTGRES_BIND_ADDR` and `POSTGRES_PORT`

## Step 0: Verify The Starting Conditions

### Why This Step Exists

Before installing anything, confirm the machine is actually suitable for the
chosen deployment model. This prevents partial setup on a host that cannot
reach GitHub or does not allow privileged changes.

### Commands

Run these as your initial SSH user:

```bash
whoami
hostname
uname -a
lsb_release -a
sudo -v
curl -I https://github.com
df -h
free -h
```

### What To Look For

- `sudo -v` succeeds.
- `curl -I https://github.com` succeeds.
- Disk and RAM are sufficient for Docker, PostgreSQL, and image builds.

If outbound HTTPS to GitHub fails, stop here and fix network access first.
The phase 09 design depends on the runner being able to initiate outbound
connections to GitHub.

## Step 1: Install Base Packages

### Why This Step Exists

The server needs a minimal toolchain for cloning the repo, downloading the
GitHub runner, and executing the deploy script. These packages are the base of
every later step.

### Commands

```bash
sudo apt update
sudo apt install -y git curl tar ca-certificates
```

### Verify

```bash
git --version
curl --version
tar --version
```

## Step 2: Install Docker Engine And Compose

### Why This Step Exists

The sandbox runtime is containerized. Both manual deploy and CI/CD deploy use
Docker Compose on the host, so Docker must be installed before app checkout,
migrations, or health checks can work.

### Commands

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable docker
sudo systemctl start docker
```

### Verify

```bash
sudo systemctl is-enabled docker
sudo systemctl is-active docker
docker version
docker compose version
```

Expected:

- Docker service is `enabled`
- Docker service is `active`
- `docker compose version` returns successfully

## Step 3: Create The Deploy User

### Why This Step Exists

The self-hosted runner must not run as `root`. A dedicated user keeps ownership
clear, keeps the app checkout predictable, and matches the phase 09 trust
model.

### Commands

```bash
sudo adduser github-runner
sudo usermod -aG docker github-runner
```

If the user already exists, keep it and just confirm the group membership.

### Verify

```bash
id github-runner
```

Look for the `docker` group in the output.

## Step 4: Prepare The Application Directory

### Why This Step Exists

The sandbox design keeps a normal Git checkout on the host. This makes both
manual and automated deploys easy to inspect and keeps the runtime close to
normal developer commands.

### Commands

```bash
sudo mkdir -p /opt/mini-payment-gateway
sudo chown -R github-runner:github-runner /opt/mini-payment-gateway
```

### Verify

```bash
ls -ld /opt/mini-payment-gateway
```

The owner should be `github-runner`.

## Step 5: Clone The Repository

### Why This Step Exists

The deploy pipeline is built around fast-forwarding a persistent checkout on the
host. The first clone establishes that checkout.

### Commands

Run as `github-runner`:

```bash
sudo -u github-runner git clone --branch main https://github.com/biabeogo147/mini-payment-gateway.git /opt/mini-payment-gateway
```

If the repository is private in the future, replace the clone method with a
deploy key or PAT-based HTTPS clone. For the current setup, a normal HTTPS
clone is sufficient.

### Verify

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git status && git rev-parse --abbrev-ref HEAD'
```

Expected:

- branch is `main`
- working tree is clean

## Step 6: Create The Server-Only `.env`

### Why This Step Exists

The application needs runtime configuration and secrets that must stay on the
server. The DevOps model intentionally keeps these values out of Git history and
out of workflow logs.

### Commands

Run as `github-runner`:

```bash
sudo -u github-runner cp /opt/mini-payment-gateway/.env.sandbox.example /opt/mini-payment-gateway/.env
sudo -u github-runner chmod 600 /opt/mini-payment-gateway/.env
sudo -u github-runner editor /opt/mini-payment-gateway/.env
```

### Minimum Example

```dotenv
APP_ENV=sandbox

POSTGRES_DB=mini_payment_gateway
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql+psycopg2://postgres:change-me@postgres:5432/mini_payment_gateway

POSTGRES_BIND_ADDR=127.0.0.1
POSTGRES_PORT=5432
BACKEND_BIND_ADDR=127.0.0.1
BACKEND_PORT=8000
INTERNAL_AUTH_SECRET=replace-with-a-long-random-secret
INTERNAL_AUTH_COOKIE_NAME=mini_payment_gateway_internal_session
INTERNAL_AUTH_TTL_SECONDS=43200
INTERNAL_AUTH_COOKIE_SECURE=false
MERCHANT_AUTH_SECRET=replace-with-a-different-long-random-secret
MERCHANT_AUTH_COOKIE_NAME=mini_payment_gateway_merchant_session
MERCHANT_AUTH_TTL_SECONDS=43200
MERCHANT_AUTH_COOKIE_SECURE=false
OPS_DASHBOARD_BIND_ADDR=127.0.0.1
OPS_DASHBOARD_PORT=4173
MERCHANT_DASHBOARD_BIND_ADDR=127.0.0.1
MERCHANT_DASHBOARD_PORT=4174
```

### Important Notes

- Keep `DATABASE_URL` pointed at the Docker service host `postgres`, not
  `localhost`.
- `INTERNAL_AUTH_SECRET` should be a long random value and must stay
  server-only.
- `MERCHANT_AUTH_SECRET` should use a different long random value from
  `INTERNAL_AUTH_SECRET`; merchant and internal dashboard sessions are separate
  auth surfaces.
- `INTERNAL_AUTH_COOKIE_SECURE=false` is acceptable for the current internal
  sandbox because the dashboard is served on plain local HTTP. Revisit this if
  TLS is introduced later.
- Keep `MERCHANT_AUTH_COOKIE_SECURE` aligned with the merchant dashboard URL:
  `false` for the current plain HTTP sandbox, `true` after TLS is introduced.
- Keep the real `.env` only on the server.
- Do not commit `.env` to Git.

### Verify

```bash
sudo -u github-runner ls -l /opt/mini-payment-gateway/.env
```

The permissions should be restricted, ideally `600`.

## Step 7: Validate The Sandbox Compose File

### Why This Step Exists

Before trying to deploy, confirm that environment interpolation and Compose
syntax are valid. This catches missing variables and syntax mistakes early.

### Commands

Run as `github-runner`:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml config'
```

### Verify

The command should print a valid merged Compose configuration and exit with
status `0`.

If this fails, fix `.env` or the compose file before continuing.

## Step 8: Run The First Manual Deploy

### Why This Step Exists

Do one clean manual deploy before automation. This proves the host runtime,
Docker, repository checkout, database connectivity, and migrations all work
independently of GitHub Actions. If this step fails, you know the issue is host
setup, not CI/CD wiring.

### Commands

Run as `github-runner`:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && bash deploy/sandbox_deploy.sh'
```

### What This Script Does

The script:

1. checks for `git`, `docker`, and `curl`
2. fast-forwards the local checkout to `origin/main`
3. builds the backend, Ops dashboard, and Merchant Dashboard images
4. starts PostgreSQL
5. runs Alembic migrations
6. starts the backend, Ops dashboard, and Merchant Dashboard
7. polls `/health`
8. verifies both dashboard roots return HTML

### Verify

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:4173/
curl -fsS http://127.0.0.1:4174/
curl -fsS http://127.0.0.1:8000/v1/internal/auth/bootstrap-status
```

Expected:

- `postgres` is healthy
- `backend` is up
- `ops-dashboard` is up
- `merchant-dashboard` is up
- health returns `{"status":"ok"}`
- both dashboard roots return HTML
- bootstrap status returns JSON such as `{"bootstrap_required":true}`

## Step 9: Install The GitHub Actions Runner

### Why This Step Exists

This is what turns a manually deployable sandbox into an automatically
deployable sandbox. The runner is the internal execution point that GitHub uses
to run the deploy job on the host itself.

### Commands

Log in to GitHub and open:

```text
Repository -> Settings -> Actions -> Runners -> New self-hosted runner
```

Choose:

```text
OS: Linux
Architecture: x64
```

Then run the GitHub-provided commands as `github-runner`.
A typical flow looks like this:

```bash
sudo -u github-runner bash
cd /home/github-runner
mkdir -p actions-runner
cd actions-runner

# Use the download command shown by GitHub, not a hard-coded old version.
curl -o actions-runner-linux-x64.tar.gz -L <github-provided-runner-url>
tar xzf actions-runner-linux-x64.tar.gz

./config.sh \
  --url https://github.com/biabeogo147/mini-payment-gateway \
  --token <runner-registration-token> \
  --name sandbox-runner-01 \
  --labels sandbox,deploy
exit
```

Then install and start the service:

```bash
cd /home/github-runner/actions-runner
sudo ./svc.sh install github-runner
sudo ./svc.sh start
sudo ./svc.sh status
```

### Why The Labels Matter

The workflow targets:

```yaml
runs-on: [self-hosted, linux, sandbox, deploy]
```

`self-hosted` and `linux` come from the runner platform.
`sandbox` and `deploy` are the environment-specific selectors that make sure
only the correct host accepts the deploy job.

### Verify

In GitHub:

- the runner appears in the repository runner list
- the runner status is `Online`

On the server:

```bash
systemctl list-unit-files "actions.runner*" --no-pager
systemctl status actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service
```

## Step 10: Configure The GitHub Environment

### Why This Step Exists

The current workflow has sensible defaults, so this step is optional.
It is still recommended because it makes environment-specific values visible and
editable from GitHub without changing the workflow file.

### Recommended GitHub Environment

Create:

```text
Environment name: sandbox
```

Recommended environment variables:

| Variable | Value |
| --- | --- |
| `SANDBOX_APP_DIR` | `/opt/mini-payment-gateway` |
| `SANDBOX_COMPOSE_FILE` | `docker-compose.sandbox.yml` |
| `SANDBOX_HEALTH_URL` | `http://127.0.0.1:8000/health` |
| `SANDBOX_OPS_DASHBOARD_URL` | `http://127.0.0.1:4173/` |
| `SANDBOX_MERCHANT_DASHBOARD_URL` | `http://127.0.0.1:4174/` |

### Important Note

The current topology does not require SSH secrets because the self-hosted
runner is installed directly on the target host.

## Step 11: Run The First Live Workflow Deploy

### Why This Step Exists

This is the final proof that the full DevOps system works:

- GitHub can run tests
- GitHub can queue the deploy job
- the self-hosted runner can receive the deploy job
- the host can deploy itself successfully

### How To Trigger It

Use one of these methods:

1. push a new commit to `main`
2. open the GitHub Actions UI and run `Sandbox Deploy` manually with
   `workflow_dispatch`

### What Should Happen

1. `backend-tests` starts on a GitHub-hosted runner
2. `deploy-sandbox` waits for test success
3. the self-hosted runner picks up `deploy-sandbox`
4. the host runs `deploy/sandbox_deploy.sh`
5. `/health` passes
6. the Ops dashboard root responds successfully
7. the Merchant Dashboard root responds successfully

### Verify

In GitHub:

- `backend-tests` ends in `success`
- `deploy-sandbox` ends in `success`

On the server:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git rev-parse --short HEAD'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:4173/
curl -fsS http://127.0.0.1:4174/
curl -fsS http://127.0.0.1:8000/v1/internal/auth/bootstrap-status
```

Expected:

- host checkout matches the deployed commit from `main`
- `postgres` is healthy
- `backend` is healthy or up
- `ops-dashboard` is healthy or up
- `merchant-dashboard` is healthy or up
- health returns `{"status":"ok"}`
- both dashboard roots return HTML
- bootstrap status responds successfully

## Step 12: Confirm The Host Matches The Architecture

### Why This Step Exists

The goal is not just "app runs". The goal is "the server now matches the
current sandbox DevOps design with internal auth, the Ops dashboard, and the
Merchant Dashboard".

### Acceptance Checklist

You are done when all of these are true:

- Docker is installed and running
- `github-runner` exists and can use Docker
- `/opt/mini-payment-gateway` exists and is owned by `github-runner`
- `.env` exists only on the host
- `docker-compose.sandbox.yml` renders successfully
- `deploy/sandbox_deploy.sh` works manually
- the GitHub runner is `Online`
- the runner service survives reboot
- a full workflow deploy succeeds
- `/health` returns `{"status":"ok"}`
- the Ops dashboard is reachable on its configured local port
- the Merchant Dashboard is reachable on its configured local port
- `/v1/internal/auth/bootstrap-status` responds successfully

At that point, the host should match the model documented in
`devops-architecture.md`.

## Troubleshooting

### Runner Is Online But Deploy Job Stays Queued

Check:

- labels match `self-hosted`, `linux`, `sandbox`, `deploy`
- runner is attached to the correct repository
- the `sandbox` environment allows the job to run

### `git pull --ff-only` Fails On The Server

This usually means:

- the working tree is dirty; or
- untracked files would be overwritten

Inspect with:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git status --short'
```

### Health Check Fails

Inspect:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 backend'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 postgres'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 ops-dashboard'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 merchant-dashboard'
```

### Runner Service Fails

Inspect:

```bash
journalctl -u actions.runner.* -n 200 --no-pager
```

## Why This Design Was Chosen

This guide produces the architecture in `devops-architecture.md`, which
intentionally favors:

- simple topology over maximum isolation
- outbound runner connectivity over inbound SSH exposure
- host-local builds over registry promotion complexity
- manual recoverability over advanced release orchestration

That makes it a good fit for an internal sandbox where speed of setup,
inspectability, and operational clarity matter more than production-grade
platform sophistication.
