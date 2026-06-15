# Sandbox Deployment

This is the day-2 operations runbook for the sandbox environment.

Use it when you need to:

- deploy the latest `main` revision;
- verify that the host is running the intended revision;
- recover manually when GitHub Actions is unavailable;
- troubleshoot deploy failures by symptom.

This file owns normal operations, verification, rollback, and troubleshooting.
For current host facts, published ports, and secret names, use
`sandbox-access-inventory.md`. For day-0 provisioning, use
`sandbox-setup-from-zero.md`.

## Before You Deploy

Read the current host facts from `sandbox-access-inventory.md`.

Before a deploy, confirm:

- the expected commit on `main`
- the self-hosted runner is online
- the host checkout is not dirty
- `.env` has already been updated if the change includes compose, auth, port,
  or runtime-key changes

Useful pre-checks:

```bash
git rev-parse --short HEAD
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git status --short'
systemctl status actions.runner.* --no-pager
```

If a change includes new runtime keys or port changes, compare the host `.env`
against `.env.sandbox.example` and the inventory doc before deploying.

## Standard Deploy Paths

### Automatic Deploy From GitHub Actions

Use this for normal operations.

Expected gate order:

1. `backend-tests`
2. `frontend-build`
3. `deploy-sandbox`

The deploy is successful only when backend health and both dashboard roots
pass.

### Manual Recovery Deploy

Use this when:

- GitHub Actions is unavailable
- deeper host-side debugging is needed
- you want to reproduce the deploy flow directly on the server

Command:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && bash deploy/sandbox_deploy.sh'
```

## Normal Deployment Procedure

Use the current host and port values from `sandbox-access-inventory.md` when
replacing placeholders below.

### Step 1: Identify The Target Revision

```bash
git rev-parse --short HEAD
```

Success means you know the exact commit that should appear on the sandbox host.

### Step 2: Trigger Or Observe The Workflow

- push to `main`; or
- run `Sandbox Deploy` with `workflow_dispatch`

Success means a GitHub Actions run exists for the intended revision.

### Step 3: Wait For Verification Gates

Success means:

- `backend-tests` finished `success`
- `frontend-build` finished `success`

If either job fails, stop and fix the code or build issue before inspecting the
host.

### Step 4: Wait For `deploy-sandbox`

Success means the self-hosted runner accepted the job and the deploy job ended
with `success`.

### Step 5: Verify The Host Revision

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git rev-parse --short HEAD'
```

Success means the host SHA matches the intended deploy target.

### Step 6: Verify Container State

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
```

Success means:

- `postgres` is healthy
- `backend` is healthy
- `ops-dashboard` is healthy
- `merchant-dashboard` is healthy

### Step 7: Verify Application Endpoints

```bash
curl -fsS http://<sandbox-host>:<backend-port>/health
curl -fsS http://<sandbox-host>:<ops-dashboard-port>/
curl -fsS http://<sandbox-host>:<merchant-dashboard-port>/
curl -fsS http://<sandbox-host>:<backend-port>/v1/internal/auth/bootstrap-status
```

Success means:

- `/health` returns `{"status":"ok"}`
- both dashboard roots return HTML
- internal auth bootstrap-status responds successfully

## Post-Deploy Verification Checklist

Treat the deploy as complete only when all three layers are true:

### Layer 1: Workflow

- `backend-tests` is `success`
- `frontend-build` is `success`
- `deploy-sandbox` is `success`

### Layer 2: Host Runtime

- host checkout is the expected commit
- `postgres`, `backend`, `ops-dashboard`, and `merchant-dashboard` are healthy

### Layer 3: Application

- backend health endpoint responds successfully
- Ops Dashboard root responds successfully
- Merchant Dashboard root responds successfully
- published PostgreSQL port is reachable when direct DB access is expected

## Manual Recovery Procedure

### Step 1: Confirm The Host And App Directory

```bash
hostname
pwd
```

### Step 2: Run The Deploy Script As `github-runner`

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && bash deploy/sandbox_deploy.sh'
```

### Step 3: Repeat The Standard Verification Checks

Run the commands from:

- Step 5: Verify The Host Revision
- Step 6: Verify Container State
- Step 7: Verify Application Endpoints

## Rollback Model

Preferred recovery path:

1. fix or revert on `main`
2. let the workflow redeploy
3. verify revision and health again

Why:

- GitHub `main` stays the visible source of truth
- the host does not drift away from repository history

Emergency manual rollback is still possible:

```bash
sudo -u github-runner bash -lc '
  cd /opt/mini-payment-gateway &&
  git fetch --prune origin main &&
  git checkout <known-good-commit> &&
  bash deploy/sandbox_deploy.sh
'
```

Use this only as a short-lived recovery bridge.

## Troubleshooting By Symptom

### Deploy Job Stays Queued

Usually means GitHub cannot find a matching online runner.

Check:

```bash
systemctl status actions.runner.* --no-pager
journalctl -u actions.runner.* -n 100 --no-pager
```

Confirm in GitHub:

- runner is `Online`
- labels match `self-hosted`, `linux`, `sandbox`, `deploy`

### Runner Is Offline

Usually means the service is stopped or outbound HTTPS to GitHub is broken.

Check:

```bash
systemctl status actions.runner.* --no-pager
journalctl -u actions.runner.* -n 200 --no-pager
curl -I https://github.com
```

### `git pull --ff-only` Fails

Usually means the host checkout is dirty or has conflicting untracked files.

Check:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git status --short'
```

### Migration Step Fails

Usually means PostgreSQL is unavailable or the migration does not match the
current schema state.

Check:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 postgres'
```

### Backend Container Is Restarting Or Unhealthy

Usually means startup failed or runtime configuration is invalid.

Check:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 backend'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
```

### Dashboard Root Fails

Usually means the dashboard container did not start correctly or the published
port is wrong for the current `.env`.

Check:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 ops-dashboard merchant-dashboard'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
```

### Backend Health Fails

Usually means the app did not finish startup or is unhealthy after boot.

Check:

```bash
curl -v http://<sandbox-host>:<backend-port>/health
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 backend'
```

## Reference Commands

Current host revision:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git rev-parse --short HEAD'
```

Container state:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
```

Backend logs:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 backend'
```

Dashboard logs:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 ops-dashboard merchant-dashboard'
```

PostgreSQL logs:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 postgres'
```

Manual deploy:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && bash deploy/sandbox_deploy.sh'
```

Runner status:

```bash
systemctl status actions.runner.* --no-pager
```
