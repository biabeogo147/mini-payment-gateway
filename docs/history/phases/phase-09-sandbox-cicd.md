# Sandbox CI/CD Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the backend to the internal sandbox automatically when `main`
is updated.

**Architecture:** GitHub Actions runs backend verification first, then schedules
deployment on a self-hosted runner inside the internal network. The runner
connects outbound to GitHub over HTTPS, so GitHub does not need inbound SSH
access to the sandbox. The deploy job pulls `main` on the Ubuntu server,
rebuilds the backend Docker image, runs Alembic migrations, starts
PostgreSQL/backend with Docker Compose, and verifies `/health`.

**Tech Stack:** GitHub Actions, GitHub self-hosted runner on Ubuntu, systemd,
Docker Engine, Docker Compose v2, FastAPI, PostgreSQL 16, Alembic, Bash, Python
`unittest`.

---

## Implementation Status

Planning only. Do not create CI/CD workflow files, Docker Compose sandbox files,
deploy scripts, or sandbox runbooks until the user explicitly asks to implement
phase 09.

The chosen deployment model is **internal pull via self-hosted runner**, not
external SSH into the sandbox. Do not mark phase 09 complete until the workflow
has successfully deployed to the real sandbox host at least once.

## Scope

Implement:

- GitHub Actions backend verification on every push to `main`.
- A self-hosted GitHub Actions runner on Ubuntu inside the internal network.
- CD on successful verification using `runs-on: [self-hosted, sandbox, deploy]`.
- Server-side `git pull --ff-only` from `main`.
- Dockerized backend deployment with `docker compose`.
- Alembic migrations before backend restart.
- Post-deploy `/health` check.
- Operator documentation for runner setup, server prerequisites, and deploy
  recovery.

Default topology:

- Install the self-hosted runner directly on the sandbox Ubuntu server.
- The deploy job runs local commands on that server.
- No inbound SSH from GitHub or the public Internet is required.

Optional topology for later:

- Install the self-hosted runner on a separate internal CI host.
- That runner SSHs over the private LAN to the sandbox server.
- This is cleaner for multi-server environments, but it adds one more host and
  key-management path. Keep it out of the first implementation unless needed.

Do not implement:

- Public SSH access to the sandbox server.
- Tunnels such as ngrok/cloudflared for SSH deploy.
- Cron-based polling deploys.
- Kubernetes, ECS, Nomad, or managed container platforms.
- Blue/green or canary deployments.
- Production secrets management beyond server `.env` and GitHub environment
  variables where necessary.
- Domain, TLS, reverse proxy, external monitoring, or database backup
  automation.

## Deployment Model

```mermaid
flowchart LR
    Push["Push to main"]
    CI["GitHub-hosted backend tests"]
    Queue["GitHub Actions queues deploy job"]
    Runner["Self-hosted runner inside internal network"]
    Pull["Local git pull --ff-only"]
    Compose["Docker Compose build/up"]
    Migrate["Alembic upgrade head"]
    Health["GET /health"]

    Push --> CI --> Queue --> Runner --> Pull --> Compose --> Migrate --> Health
```

Important network rule:

- GitHub does not SSH into the sandbox.
- The Ubuntu runner initiates outbound connections to GitHub.
- Deployment commands execute inside the internal network.

The server keeps a normal repository checkout, usually at
`/opt/mini-payment-gateway`. This makes the running sandbox easy to inspect and
keeps deploy behavior close to local developer commands.

## Files

- Create: `.github/workflows/sandbox-deploy.yml`
  - Runs backend tests and triggers sandbox deploy on `main`.
  - Deploy job uses `runs-on: [self-hosted, sandbox, deploy]`.
- Create: `deploy/sandbox_deploy.sh`
  - Idempotent local deploy script executed by the self-hosted runner.
- Create: `docker-compose.sandbox.yml`
  - Sandbox runtime stack without the local development bind mount.
- Create: `.env.sandbox.example`
  - Template for sandbox-only environment variables.
- Create: `docs/operations/sandbox-deployment.md`
  - Operator runbook for runner setup, server setup, manual deploy, and
    troubleshooting.
- Modify: `README.md`
  - Link to sandbox deployment docs.
- Modify: `docs/README.md`
  - Link deployment docs from the operator entry points.
- Modify: `docs/operations/README.md`
  - Add sandbox deployment to the SOP index.
- Modify: `docs/history/README.md`
  - Add phase 09 to phase plans.

## Runner Labels, Variables, And Secrets

Runner labels:

- `self-hosted`
- `linux`
- `sandbox`
- `deploy`

Recommended GitHub Environment:

- `sandbox`

Default direct-runner deployment does not require SSH secrets because the deploy
job runs on the sandbox server itself.

Optional GitHub environment variables:

- `SANDBOX_APP_DIR`
  - Defaults to `/opt/mini-payment-gateway`.
- `SANDBOX_COMPOSE_FILE`
  - Defaults to `docker-compose.sandbox.yml`.
- `SANDBOX_HEALTH_URL`
  - Defaults to `http://127.0.0.1:8000/health`.

Only use SSH secrets if choosing the optional separate internal CI host model:

- `SANDBOX_HOST`
- `SANDBOX_USER`
- `SANDBOX_PORT`
- `SANDBOX_SSH_KEY`
- `SANDBOX_KNOWN_HOSTS`

## Security Notes

- Prefer a private repository for self-hosted runner deployment.
- Do not run the runner as `root`.
- The runner user can access Docker; treat that as highly privileged.
- Keep real sandbox secrets in `/opt/mini-payment-gateway/.env` on the server.
- Do not print `.env` contents in workflow logs.
- Do not allow untrusted pull-request workflows to run on the deploy runner.
- Use GitHub Environment protection if manual approval is desired before
  deploying from `main`.

## Tasks

### Task 0: Choose Runner Topology

- [ ] Confirm default topology: runner runs directly on the Ubuntu sandbox
  server.
- [ ] Confirm Ubuntu can initiate outbound HTTPS connections to GitHub.
- [ ] Confirm the sandbox server does not need inbound SSH from GitHub.
- [ ] If choosing separate internal CI host instead, document the LAN SSH path
  before implementation.

### Task 1: Ubuntu Server Prerequisites

- [ ] Create a non-root runner user:

```bash
sudo adduser github-runner
sudo usermod -aG docker github-runner
```

- [ ] Install required packages:

```bash
sudo apt update
sudo apt install -y git curl tar ca-certificates
```

- [ ] Install Docker Engine if it is not already installed:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker github-runner
```

- [ ] Log out and log back in as `github-runner` so Docker group membership is
  active.
- [ ] Verify:

```bash
git --version
docker version
docker compose version
curl --version
```

### Task 2: Register Self-Hosted Runner

- [ ] In GitHub, open:

```text
Repository -> Settings -> Actions -> Runners -> New self-hosted runner
```

- [ ] Select:

```text
OS: Linux
Architecture: x64
```

- [ ] Copy the GitHub-generated download and configuration commands.
- [ ] On the Ubuntu server, run those commands as `github-runner`.
- [ ] Configure the runner with labels:

```bash
./config.sh \
  --url https://github.com/<owner>/<repo> \
  --token <token-from-github> \
  --name sandbox-runner-01 \
  --labels sandbox,deploy,docker
```

- [ ] Install and start the runner as a service:

```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

- [ ] Expected: GitHub shows the runner as `Online`.
- [ ] Optional on Ubuntu systems with `needrestart`: configure it not to restart
  the runner service during a job.

### Task 3: App Checkout And Server Environment

- [ ] Create the app directory:

```bash
sudo mkdir -p /opt/mini-payment-gateway
sudo chown -R github-runner:github-runner /opt/mini-payment-gateway
```

- [ ] Clone the repository:

```bash
git clone --branch main <repo-url> /opt/mini-payment-gateway
cd /opt/mini-payment-gateway
```

- [ ] Create server-only `.env`:

```bash
cp .env.sandbox.example .env
```

- [ ] Edit `.env` with sandbox values:

```bash
APP_ENV=sandbox
POSTGRES_PASSWORD=<strong-password>
SANDBOX_DATABASE_URL=postgresql+psycopg2://postgres:<strong-password>@postgres:5432/mini_payment_gateway
BACKEND_BIND_ADDR=127.0.0.1
BACKEND_PORT=8000
```

- [ ] Keep `SANDBOX_DATABASE_URL` pointed at Docker service host `postgres`.

### Task 4: Docker Runtime

- [ ] Add `docker-compose.sandbox.yml`.
- [ ] Ensure PostgreSQL uses a named volume instead of `./pgdata`.
- [ ] Ensure backend runs as a Docker container built from `backend/Dockerfile`.
- [ ] Do not mount `./backend:/app` in sandbox runtime.
- [ ] Add backend health check.
- [ ] On the server, run:

```bash
docker compose -f docker-compose.sandbox.yml config
```

- [ ] Expected: Compose prints a valid merged configuration.

### Task 5: Local Deploy Script

- [ ] Add `deploy/sandbox_deploy.sh`.
- [ ] The script must run locally on the sandbox server.
- [ ] Check required commands: `git`, `docker`, `curl`.
- [ ] Use `APP_DIR=${APP_DIR:-/opt/mini-payment-gateway}`.
- [ ] Pull `main` with:

```bash
git fetch --prune origin main
git checkout main
git pull --ff-only origin main
```

- [ ] Build backend image:

```bash
docker compose -f docker-compose.sandbox.yml build backend
```

- [ ] Start PostgreSQL:

```bash
docker compose -f docker-compose.sandbox.yml up -d postgres
```

- [ ] Run migrations inside the backend container:

```bash
docker compose -f docker-compose.sandbox.yml run --rm backend python -m alembic upgrade head
```

- [ ] Start backend:

```bash
docker compose -f docker-compose.sandbox.yml up -d backend
```

- [ ] Poll health:

```bash
curl -fsS http://127.0.0.1:8000/health
```

- [ ] On failure, print recent backend logs and exit non-zero.

### Task 6: GitHub Actions Workflow

- [ ] Add `.github/workflows/sandbox-deploy.yml`.
- [ ] Trigger on push to `main` and `workflow_dispatch`.
- [ ] Add `backend-tests` job using GitHub-hosted Ubuntu and PostgreSQL service
  container.
- [ ] Add `deploy-sandbox` job:

```yaml
runs-on: [self-hosted, sandbox, deploy]
needs: backend-tests
environment: sandbox
```

- [ ] Deploy job should run local commands, not SSH from GitHub:

```bash
cd "${SANDBOX_APP_DIR:-/opt/mini-payment-gateway}"
git fetch --prune origin main
git checkout main
git pull --ff-only origin main
bash deploy/sandbox_deploy.sh
```

- [ ] Ensure the workflow never prints `.env`.

### Task 7: First Live Deployment

- [ ] Confirm runner status is `Online` in GitHub.
- [ ] Push to `main` or run `workflow_dispatch`.
- [ ] Confirm `backend-tests` passes.
- [ ] Confirm `deploy-sandbox` is picked up by the self-hosted runner.
- [ ] Confirm deploy log reaches health success.
- [ ] On server, run:

```bash
cd /opt/mini-payment-gateway
docker compose -f docker-compose.sandbox.yml ps
curl -fsS http://127.0.0.1:8000/health
```

- [ ] Expected: backend and postgres are running; health returns
  `{"status":"ok"}`.

### Task 8: Completion Record

- [ ] Create `docs/history/completions/phase-09.md` only after first live
  deployment succeeds.
- [ ] Record:
  - commit SHA deployed;
  - GitHub Actions run URL;
  - runner name and labels;
  - server app directory;
  - health-check result;
  - remaining production-hardening notes.
- [ ] Update this phase plan status to completed.

## Acceptance Criteria

- A push to `main` runs backend tests before deploy.
- The deploy job runs on the internal self-hosted runner with labels
  `sandbox` and `deploy`.
- GitHub does not require inbound SSH access to the sandbox server.
- The sandbox server pulls the latest `main` branch itself.
- Backend runs from a Docker container built by Docker Compose.
- Migrations run before backend restart.
- Deployment fails loudly when `/health` does not pass.
- Runner setup, server setup, and recovery commands are documented for
  repeatable handoff.
