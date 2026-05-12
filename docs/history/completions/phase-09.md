# Phase 09 Completion

Phase 09 completes sandbox CI/CD with a GitHub-hosted verification job, a
self-hosted deploy runner on the internal Ubuntu sandbox host, a host-local
deploy script, and infrastructure handoff documentation.

## Completed Scope

- Added `.github/workflows/sandbox-deploy.yml` with:
  - `backend-tests` on GitHub-hosted Ubuntu plus PostgreSQL service;
  - `deploy-sandbox` on `runs-on: [self-hosted, linux, sandbox, deploy]`;
  - `environment: sandbox`;
  - host-local deploy execution instead of inbound SSH from GitHub.
- Added `docker-compose.sandbox.yml` for the sandbox runtime stack.
- Added `deploy/sandbox_deploy.sh` for idempotent host-local pull, build,
  migrate, restart, and health verification.
- Added `.env.sandbox.example` as the sandbox env template.
- Added infrastructure runbooks under `docs/infrastructure/`.
- Registered and started self-hosted runner `sandbox-runner-01` on
  `192.168.1.199`.
- Completed the first live sandbox workflow deployment successfully.

## Live Deployment Evidence

- First successful workflow run:
  [Sandbox Deploy #25751189003](https://github.com/biabeogo147/mini-payment-gateway/actions/runs/25751189003)
- Successful deploy job id: `75635343180`
- Successful backend test job id: `75635343405`
- First live deployed commit: `e9e04f8`
- Runner name: `sandbox-runner-01`
- Runner labels: `self-hosted`, `linux`, `sandbox`, `deploy`
- Runner service:
  `actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service`
- Server app directory: `/opt/mini-payment-gateway`
- Health result after deploy: `{"status":"ok"}`

## Verification

Workflow evidence:

- GitHub Actions `backend-tests` completed with `success`.
- GitHub Actions `deploy-sandbox` completed with `success`.
- The deploy log showed:
  - `git pull --ff-only origin main`;
  - backend image rebuild;
  - Alembic migration run;
  - backend container recreate;
  - health success on attempt 2;
  - final deployed revision `e9e04f8`.

On-host verification after the successful deploy:

```bash
cd /opt/mini-payment-gateway
docker compose -f docker-compose.sandbox.yml ps
curl -fsS http://127.0.0.1:8000/health
```

Observed result:

- `mini-payment-gateway-postgres-1` was `Up (healthy)`;
- `mini-payment-gateway-backend-1` was `Up (healthy)`;
- `/health` returned `{"status":"ok"}`.

First-run remediation that was required once:

- The original queued deploy job failed because `.env.sandbox.example`,
  `docker-compose.sandbox.yml`, and `deploy/sandbox_deploy.sh` had been copied
  onto the server before they existed in Git history on `main`.
- Removing those untracked copies and rerunning the deploy job allowed the
  checkout to fast-forward cleanly and the deploy to succeed.

## Remaining Hardening Notes

- Sandbox still stores runtime secrets in `/opt/mini-payment-gateway/.env`;
  production should move to stronger secret management.
- The workflow currently deploys on every push to `main`; environment approval
  can be enabled later if manual promotion is desired.
- TLS, reverse proxying, external monitoring, and backup automation remain out
  of scope for this internal sandbox phase.
