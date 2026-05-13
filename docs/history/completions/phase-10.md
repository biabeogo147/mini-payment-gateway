# Phase 10 Completion

Phase 10 completes the internal Ops dashboard with browser-based operator
workflows, internal session auth, RBAC for `ADMIN` and `OPS`, read/search/stat
APIs for operations, and a live sandbox deployment that now includes the new
dashboard container.

## Completed Scope

- Added internal auth routes under `/v1/internal/auth/*` for:
  - bootstrap status;
  - first-admin bootstrap;
  - login/logout;
  - current-session lookup;
  - password change.
- Added `ADMIN`-only internal user management under `/v1/internal/users`.
- Added read/search/stat Ops APIs for:
  - dashboard summary and charts;
  - merchant list/detail plus onboarding and credential metadata;
  - payment explorer;
  - refund explorer;
  - webhook explorer and attempt history;
  - audit explorer.
- Protected existing Ops mutation routes with authenticated internal sessions
  and RBAC.
- Added the React/Vite Ops dashboard at `apps/ops-dashboard/` with:
  - login/bootstrap flow;
  - overview page;
  - merchants and onboarding pages;
  - payments, refunds, webhooks, reconciliation, and audit explorers;
  - internal user management for `ADMIN`.
- Added the `ops-dashboard` container to both local and sandbox Docker Compose
  runtimes.
- Updated `deploy/sandbox_deploy.sh` so sandbox deploy now verifies both backend
  health and dashboard reachability.
- Updated architecture, API, README, and infrastructure docs for the new
  internal UI and auth model.

## Live Deployment Evidence

- First live phase 10 application deploy commit: `6d0b0bc`
- Sandbox host: `192.168.1.199`
- App checkout directory: `/opt/mini-payment-gateway`
- Runner name: `sandbox-runner-01`
- Runner labels: `self-hosted`, `linux`, `sandbox`, `deploy`
- Runner service:
  `actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service`
- Backend health result after deploy: `{"status":"ok"}`
- Dashboard verification result: dashboard HTML shell served on
  `http://127.0.0.1:4173/`
- Internal auth bootstrap status on sandbox:
  `{"bootstrap_required":true}`

## Verification

Backend verification against the prepared sandbox-backed PostgreSQL database:

```bash
cd backend
python -m unittest discover tests -v
```

Result: 163 tests passed.

Frontend verification:

```bash
npm run ops-dashboard:typecheck
npm run ops-dashboard:build
```

Result: both commands completed successfully.

Sandbox deployment verification:

```bash
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && bash deploy/sandbox_deploy.sh'
sudo -u github-runner bash -lc 'cd /opt/mini-payment-gateway && docker compose -f docker-compose.sandbox.yml ps'
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:4173/
curl -fsS http://127.0.0.1:8000/v1/internal/auth/bootstrap-status
```

Observed result:

- `postgres` was `Up (healthy)`;
- `backend` was `Up (healthy)`;
- `ops-dashboard` was `Up (healthy)`;
- `/health` returned `{"status":"ok"}`;
- the dashboard root returned the HTML shell for `Mini Payment Gateway Ops Dashboard`;
- bootstrap-status returned `{"bootstrap_required":true}`.

## Remaining Notes

- The sandbox now supports internal operator login, but the first `ADMIN` user
  still needs to be bootstrapped through the dashboard login screen.
- Session secrets still live in `/opt/mini-payment-gateway/.env`; production
  should move both runtime and auth secrets to stronger secret management.
- The Ops dashboard is intentionally internal-only and served on a host-local
  port in the sandbox. Public exposure, TLS, and reverse proxy hardening remain
  out of scope for this phase.
