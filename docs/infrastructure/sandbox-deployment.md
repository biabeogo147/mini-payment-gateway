# Sandbox Deployment

This runbook describes the phase 09 sandbox CI/CD path.

Use this document for the ongoing deployment flow after host bootstrap.
Use [sandbox-bootstrap.md](sandbox-bootstrap.md) for the initial machine setup
record on `192.168.1.199`.
Use [devops-architecture.md](devops-architecture.md) for the full internal
architecture, trust boundary, and pipeline design rationale.

## Live Status

Phase 09 is live as of May 13, 2026 (Asia/Saigon).

- Host: `192.168.1.199` (`ubuntu24`)
- App checkout: `/opt/mini-payment-gateway`
- Runner name: `sandbox-runner-01`
- Runner labels: `self-hosted`, `linux`, `sandbox`, `deploy`
- Runner version during first live deploy: `2.334.0`
- systemd unit:
  `actions.runner.biabeogo147-mini-payment-gateway.sandbox-runner-01.service`
- First successful workflow run:
  [Sandbox Deploy #25751189003](https://github.com/biabeogo147/mini-payment-gateway/actions/runs/25751189003)
- Successful deploy job id: `75635343180`
- First live deployed commit: `e9e04f8`
- Health result after deploy: `{"status":"ok"}`

## Deployment Model

- GitHub-hosted Actions run backend verification on pushes to `main`.
- On success, GitHub schedules a deploy job on a self-hosted runner inside the
  internal network.
- That runner runs locally on the sandbox Ubuntu host and executes deploy
  commands there.
- The host pulls `main`, rebuilds the backend image, runs Alembic migrations,
  starts the sandbox compose stack, and verifies `/health`.

No inbound SSH from GitHub is required.

## Runtime Files

- Workflow: `.github/workflows/sandbox-deploy.yml`
- Deploy script: `deploy/sandbox_deploy.sh`
- Sandbox compose: `docker-compose.sandbox.yml`
- Sandbox env template: `.env.sandbox.example`
- Server checkout directory: `/opt/mini-payment-gateway`

## Runner Labels

The deploy runner should advertise:

- `self-hosted`
- `linux`
- `sandbox`
- `deploy`

Recommended runner name:

- `sandbox-runner-01`

## GitHub Environment

Recommended GitHub Environment:

- `sandbox`

Optional GitHub environment variables:

- `SANDBOX_APP_DIR`
  Default: `/opt/mini-payment-gateway`
- `SANDBOX_COMPOSE_FILE`
  Default: `docker-compose.sandbox.yml`
- `SANDBOX_HEALTH_URL`
  Default: `http://127.0.0.1:8000/health`

The workflow does not require SSH secrets when the runner is installed directly
on the sandbox host.

## Register The Self-Hosted Runner

In GitHub, open:

```text
Repository -> Settings -> Actions -> Runners -> New self-hosted runner
```

Select:

```text
OS: Linux
Architecture: x64
```

Run the GitHub-provided commands on the sandbox host as `github-runner`. Use
labels matching this phase:

```bash
./config.sh \
  --url https://github.com/biabeogo147/mini-payment-gateway \
  --token <runner-registration-token> \
  --name sandbox-runner-01 \
  --labels sandbox,deploy
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

Expected result:

- the runner shows `Online` in GitHub;
- the service survives reboot;
- the runner user remains non-root.

Implemented state on `192.168.1.199`:

- the runner is registered directly on the sandbox host;
- the runner service is enabled with systemd;
- the runner connects outbound to GitHub and accepts deploy jobs.

## Prepare Server Checkout

If the host is not already prepared:

```bash
sudo mkdir -p /opt/mini-payment-gateway
sudo chown -R github-runner:github-runner /opt/mini-payment-gateway
git clone --branch main https://github.com/biabeogo147/mini-payment-gateway.git /opt/mini-payment-gateway
cd /opt/mini-payment-gateway
cp .env.sandbox.example .env
```

Edit `.env` with sandbox-local values only. Keep `DATABASE_URL` pointed at the
Docker service host `postgres`.

## Manual Deploy Command

The workflow eventually runs the host-local deploy script. You can run the same
flow manually on the sandbox host:

```bash
cd /opt/mini-payment-gateway
bash deploy/sandbox_deploy.sh
```

Optional overrides:

```bash
APP_DIR=/opt/mini-payment-gateway \
COMPOSE_FILE=docker-compose.sandbox.yml \
HEALTH_URL=http://127.0.0.1:8000/health \
bash deploy/sandbox_deploy.sh
```

## What The Deploy Script Does

`deploy/sandbox_deploy.sh` performs:

1. required command checks for `git`, `docker`, and `curl`;
2. `git fetch --prune origin main`;
3. `git checkout main`;
4. `git pull --ff-only origin main`;
5. `docker compose -f docker-compose.sandbox.yml build backend`;
6. `docker compose -f docker-compose.sandbox.yml up -d postgres`;
7. `docker compose -f docker-compose.sandbox.yml run --rm backend python -m alembic upgrade head`;
8. `docker compose -f docker-compose.sandbox.yml up -d backend`;
9. health polling against `/health`.

On failure it prints compose status plus recent backend and postgres logs.

## Validation Commands

On the sandbox host:

```bash
cd /opt/mini-payment-gateway
docker compose -f docker-compose.sandbox.yml config
docker compose -f docker-compose.sandbox.yml ps
curl -fsS http://127.0.0.1:8000/health
```

Expected result:

- `config` renders cleanly;
- `postgres` is healthy;
- `backend` is up;
- `/health` returns `{"status":"ok"}`.

Observed after the first successful live deploy on May 13, 2026:

- `docker compose -f docker-compose.sandbox.yml ps` showed `postgres` healthy
  and `backend` up on `127.0.0.1`;
- `curl -fsS http://127.0.0.1:8000/health` returned `{"status":"ok"}`.

## Troubleshooting

If deploy fails:

- inspect runner service logs with `journalctl -u actions.runner.* -n 200`;
- inspect app containers with `docker compose -f docker-compose.sandbox.yml ps`;
- inspect backend logs with
  `docker compose -f docker-compose.sandbox.yml logs --tail 100 backend`;
- inspect database logs with
  `docker compose -f docker-compose.sandbox.yml logs --tail 100 postgres`;
- rerun the deploy script manually to reproduce on-host.

If the very first workflow deploy fails with:

```text
The following untracked working tree files would be overwritten by merge
```

that usually means phase 09 files were copied onto the server before they were
tracked in Git. Remove the untracked copies once, then rerun the job:

```bash
cd /opt/mini-payment-gateway
rm -f .env.sandbox.example docker-compose.sandbox.yml deploy/sandbox_deploy.sh
git status --short
```

This was the exact remediation used before the successful rerun of workflow run
`25751189003`.

If GitHub queues the job but the host does not pick it up:

- verify runner labels match `self-hosted`, `linux`, `sandbox`, `deploy`;
- verify the runner is `Online`;
- verify the repository and environment permit Actions to use the runner.

## Security Notes

- Keep real sandbox secrets only in `/opt/mini-payment-gateway/.env`.
- Do not print `.env` contents in logs.
- Do not run the self-hosted runner as `root`.
- Treat Docker group membership as privileged access.
