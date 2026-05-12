# Sandbox Host Bootstrap

This document records the manual sandbox host preparation completed on
May 12, 2026 before phase 09 CI/CD implementation.

Phase 09 CI/CD was later completed on May 13, 2026. Use
[sandbox-deployment.md](sandbox-deployment.md) for the live runner/deploy
workflow and [phase-09 completion](../history/completions/phase-09.md) for the
verified handoff record.

Scope of this document:

- what was prepared on the internal sandbox host;
- what was verified from the workstation to the host;
- how the app was brought up manually with the current repo state;
- what is still intentionally not done until phase 09 starts.

This is a host bootstrap record, not the final sandbox deployment runbook.

## Host Snapshot

- Host: `192.168.1.199`
- SSH user used during setup: `thanhlnp`
- Hostname: `ubuntu24`
- OS: `Ubuntu 24.04.4 LTS`
- Repo directory: `/opt/mini-payment-gateway`
- Repo remote: `https://github.com/biabeogo147/mini-payment-gateway.git`
- Checked out branch during setup: `main`
- Checked out commit during setup: `fe9f89a`

## What Was Verified First

- SSH connectivity from the workstation to `192.168.1.199:22`
- outbound HTTPS access from the Ubuntu host to GitHub
- local sudo access for the setup user
- available disk and memory for Docker-based bring-up

These checks confirmed that the default phase 09 topology remains valid:
the self-hosted runner can live directly on the sandbox host, and GitHub does
not need inbound SSH access into the machine.

## Host Preparation Completed

### User And Privileges

- Created non-root runner user: `github-runner`
- Added `github-runner` to the `docker` group
- Verified `github-runner` can execute Docker commands

### Packages And Runtime

Installed or verified:

- `git`
- `curl`
- `tar`
- `ca-certificates`
- Docker Engine
- Docker Compose plugin

Observed during setup:

- `git version 2.43.0`
- `curl 8.5.0`
- `Docker version 29.4.3`
- `Docker Compose version v5.1.3`

Docker service state after setup:

- `systemctl is-enabled docker` -> `enabled`
- `systemctl is-active docker` -> `active`

### App Directory

Prepared:

- created `/opt/mini-payment-gateway`
- assigned ownership to `github-runner:github-runner`
- cloned the repository to `/opt/mini-payment-gateway`

### Server-Only Environment File

Created:

- `/opt/mini-payment-gateway/.env`

The file contains sandbox-local values only and is intentionally not committed.
Secret values are stored only on the host. The file includes:

- `APP_ENV=sandbox`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `BACKEND_BIND_ADDR`
- `BACKEND_PORT`

## Manual Bring-Up Completed

Before phase 09 automation exists, the app was started manually with the
current repository's `docker-compose.yml`.

Commands used on the host:

```bash
cd /opt/mini-payment-gateway
docker compose up -d postgres
docker compose run --rm backend python -m alembic upgrade head
docker compose up -d backend
curl -fsS http://127.0.0.1:8000/health
```

## Result

Manual bring-up succeeded on May 12, 2026.

Observed container state:

```text
NAME                              IMAGE                          STATUS
mini-payment-gateway-backend-1    mini-payment-gateway-backend   Up
mini-payment-gateway-postgres-1   postgres:16-alpine             Up (healthy)
```

Observed health response:

```json
{"status":"ok"}
```

Ports currently exposed by the active compose stack:

- `8000` -> backend
- `5432` -> PostgreSQL

This exposure comes from the current development-oriented `docker-compose.yml`.
It is acceptable for this internal test machine, but it should not be treated
as the final sandbox runtime design.

## Useful Recheck Commands

```bash
cd /opt/mini-payment-gateway
docker compose ps
docker compose logs --tail 50 backend
docker compose logs --tail 50 postgres
curl -fsS http://127.0.0.1:8000/health
```

To stop the current manual stack:

```bash
cd /opt/mini-payment-gateway
docker compose down
```

## What Was Still Not Done At Bootstrap Time

The following items were intentionally left for phase 09 implementation at the
time this bootstrap record was written:

- registering the GitHub self-hosted runner with repository labels
- creating `.github/workflows/sandbox-deploy.yml`
- creating `deploy/sandbox_deploy.sh`
- creating `docker-compose.sandbox.yml`
- creating `.env.sandbox.example`
- creating the final sandbox deployment runbook

This historical bootstrap status should be read as:

- the host is prepared;
- the app can run manually on the host;
- CI/CD automation for sandbox deploy had not been implemented yet.
