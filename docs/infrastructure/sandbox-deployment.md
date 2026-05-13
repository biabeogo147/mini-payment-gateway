# Sandbox Deployment

This document is the day-2 deployment runbook for the sandbox environment.

Use it after the host has already been provisioned and the runner already
exists. For first-time machine provisioning, use `sandbox-setup-from-zero.md`.
For design rationale and topology, use `devops-architecture.md`.

## What This Document Is For

Use this runbook when you need to:

- deploy the current `main` branch to the sandbox;
- verify that the latest deploy actually reached the host;
- run the same deploy flow manually during recovery;
- troubleshoot deploy failures by symptom instead of guessing.

This document is intentionally focused on repeated operations, not server
bootstrap.

## Current Live Context

Current verified live state as of May 13, 2026 (Asia/Saigon):

- Host: `192.168.1.199` (`ubuntu24`)
- App checkout: `/opt/mini-payment-gateway`
- Runner name: `sandbox-runner-01`
- Runner labels: `self-hosted`, `linux`, `sandbox`, `deploy`
- Runner service:
  `actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service`
- Latest verified successful workflow run:
  [Sandbox Deploy #25753873664](https://github.com/biabeogo147/mini-payment-gateway/actions/runs/25753873664)
- Successful backend test job id: `75637063276`
- Successful deploy job id: `75637179632`
- Verified deployed commit on host: `0e95aa7`
- Verified health result: `{"status":"ok"}`

## Operational Invariants

These points should stay true during normal operations:

- GitHub `main` is the deploy source of truth.
- `backend-tests` must pass before deploy is allowed to run.
- The deploy runner lives on the target sandbox host.
- The runner executes deploy commands locally on that host.
- The app checkout path is `/opt/mini-payment-gateway`.
- Runtime configuration is loaded from `/opt/mini-payment-gateway/.env`.
- Runtime orchestration uses `docker-compose.sandbox.yml`.
- A deploy is only considered successful if `/health` passes.

If one of these assumptions changes, update this runbook and
`devops-architecture.md` together.

## Standard Deploy Paths

There are two supported deploy paths.

### Path 1: Automatic Deploy From GitHub Actions

Use this for normal operations.

Why this path exists:

- it enforces test-before-deploy;
- it keeps GitHub `main` as the single deploy source of truth;
- it creates an auditable workflow history.

Trigger:

- push a commit to `main`; or
- run the `Sandbox Deploy` workflow manually from the GitHub Actions UI.

Expected result:

- `backend-tests` finishes `success`;
- `deploy-sandbox` finishes `success`;
- the sandbox host advances to the expected commit.

### Path 2: Manual Deploy On The Host

Use this when:

- GitHub Actions is unavailable;
- you need to reproduce a failure directly on the server;
- you want to verify whether a problem is workflow-related or host-related.

Command:

```bash
cd /opt/mini-payment-gateway
bash deploy/sandbox_deploy.sh
```

Expected result:

- the same build, migration, restart, and health sequence runs locally;
- the host reaches the same runtime state the workflow would produce.

## Normal Automatic Deployment Procedure

This is the standard repeated deployment flow.

### Step 1: Identify The Commit You Expect To Deploy

Why:

- you need a concrete target revision before verifying anything else.

Command:

```bash
git rev-parse --short HEAD
```

Success means:

- you know the exact short SHA that should appear on the sandbox host after the
  deploy.

### Step 2: Trigger Or Observe The Workflow Run

Why:

- the normal deploy path starts in GitHub, not on the host.

Action:

- push to `main`; or
- run `Sandbox Deploy` with `workflow_dispatch`.

Success means:

- a workflow run appears in GitHub Actions for the intended commit.

### Step 3: Wait For `backend-tests`

Why:

- this is the first safety gate and must pass before runtime changes are
  allowed.

Success means:

- the `backend-tests` job ends with `success`.

If it fails:

- stop and fix the application or test issue;
- do not proceed to runtime checks because deploy should not happen.

### Step 4: Wait For `deploy-sandbox`

Why:

- this confirms the self-hosted runner accepted the deploy job and executed the
  host-local deploy flow.

Success means:

- the `deploy-sandbox` job ends with `success`.

### Step 5: Verify The Host Revision

Why:

- a green workflow should correspond to the expected checkout on the server.

Command:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git rev-parse --short HEAD'
```

Success means:

- the returned SHA matches the intended deployed commit.

### Step 6: Verify Container State

Why:

- workflow success alone is not enough; the host runtime must actually be
  healthy.

Command:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
```

Success means:

- `postgres` is `Up` and healthy;
- `backend` is `Up` and preferably healthy.

### Step 7: Verify Application Health

Why:

- this is the final application-level acceptance check.

Command:

```bash
curl -fsS http://127.0.0.1:8000/health
```

Success means:

- the endpoint returns `{"status":"ok"}` and exits successfully.

## Manual Recovery Deploy Procedure

Use this procedure when you need to rerun the deploy logic directly on the host.

### Step 1: Confirm You Are On The Sandbox Host

Command:

```bash
hostname
pwd
```

Success means:

- you are on the intended machine and ready to operate in the app directory.

### Step 2: Run The Deploy Script As `github-runner`

Why:

- this keeps manual recovery behavior aligned with the ownership and trust model
  used by the automated runner.

Command:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && bash deploy/sandbox_deploy.sh'
```

Success means:

- the script completes without error and prints a successful health check.

### Step 3: Repeat The Standard Verification Checks

Run:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git rev-parse --short HEAD'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
curl -fsS http://127.0.0.1:8000/health
```

Success means:

- commit, container state, and health all match the expected deploy target.

## Post-Deploy Verification Checklist

After every deploy, verify all three layers:

### Layer 1: Workflow

- `backend-tests` is `success`
- `deploy-sandbox` is `success`

### Layer 2: Host Runtime

- app checkout on host is the expected commit
- `postgres` is healthy
- `backend` is up

### Layer 3: Application

- `GET /health` returns `{"status":"ok"}`

A deploy should not be treated as complete until all three layers are true.

## Troubleshooting By Symptom

### Symptom: Deploy Job Stays Queued

What it usually means:

- GitHub cannot find a matching online runner for the job labels.

Check:

```bash
systemctl status actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service
journalctl -u actions.runner.* -n 100 --no-pager
```

Also verify in GitHub:

- runner is `Online`
- labels include `self-hosted`, `linux`, `sandbox`, `deploy`

Typical fixes:

- start the runner service;
- correct runner labels;
- confirm the job is targeting the right repository and environment.

### Symptom: Runner Is Offline

What it usually means:

- the systemd service is stopped or the runner lost connectivity to GitHub.

Check:

```bash
systemctl status actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service
journalctl -u actions.runner.* -n 200 --no-pager
curl -I https://github.com
```

Typical fixes:

- restart the runner service;
- restore outbound HTTPS connectivity;
- re-register the runner only if the existing registration is broken.

### Symptom: `git pull --ff-only` Fails

What it usually means:

- the host checkout is dirty; or
- untracked files would be overwritten; or
- the branch is no longer a simple fast-forward.

Check:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git status --short'
```

Typical fixes:

- remove stray untracked files that should not live on the host;
- stop editing tracked files directly on the server;
- keep the host checkout clean between deploys.

Known first-run example:

- the original phase 09 rollout failed once because
  `.env.sandbox.example`, `docker-compose.sandbox.yml`, and
  `deploy/sandbox_deploy.sh` had been copied to the host before Git tracked
  them on `main`.

### Symptom: Migration Step Fails

What it usually means:

- the database is unavailable; or
- the migration code is broken for the current state.

Check:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 postgres'
```

Typical fixes:

- recover PostgreSQL first;
- rerun the deploy script after database health is restored;
- if the migration itself is bad, fix the code on `main` and redeploy.

### Symptom: Backend Container Is Restarting Or Unhealthy

What it usually means:

- the app failed during startup; or
- configuration is invalid; or
- the database is reachable but the app cannot boot cleanly.

Check:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 backend'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
```

Typical fixes:

- correct `.env` values;
- fix the application code on `main`;
- redeploy after the underlying issue is resolved.

### Symptom: Health Check Fails

What it usually means:

- the backend did not finish startup; or
- it is running but not healthy enough to answer `/health`.

Check:

```bash
curl -v http://127.0.0.1:8000/health
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 backend'
```

Typical fixes:

- inspect backend startup logs first;
- then inspect postgres health and connectivity;
- rerun the deploy manually only after the root cause is understood.

## Recovery And Rollback

### Preferred Recovery Model

The preferred recovery path is:

1. fix or revert on `main`
2. let the workflow redeploy
3. verify host commit and health again

Why this is preferred:

- GitHub `main` remains the visible source of truth;
- the host does not drift away from repository history;
- the next operator can understand the state without guessing.

### Emergency Manual Rollback

Only use this when service restoration is more urgent than GitHub workflow
cleanliness.

Possible emergency flow:

```bash
sudo -u github-runner bash -lc '
  cd /opt/mini-payment-gateway &&
  git fetch --prune origin main &&
  git checkout <known-good-commit> &&
  bash deploy/sandbox_deploy.sh
'
```

Warning:

- this puts the host temporarily behind `main`;
- the next normal deploy from `main` will move the host forward again.

Treat this as an emergency bridge, not the default operating model.

## Operational Warnings

- Do not edit tracked application files directly on the host during normal
  operations.
- Do not leave the host checkout dirty between deploys.
- Do not store real runtime secrets in GitHub workflow files or logs.
- Do not run the self-hosted runner as `root`.
- Treat `github-runner` plus Docker access as privileged host-level access.

## Reference Commands

Check current host commit:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && git rev-parse --short HEAD'
```

Check container state:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
```

Check backend logs:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 backend'
```

Check postgres logs:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml logs --tail 100 postgres'
```

Run manual deploy:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && bash deploy/sandbox_deploy.sh'
```

Check runner service:

```bash
systemctl status actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service
```

Check runner logs:

```bash
journalctl -u actions.runner.* -n 200 --no-pager
```
