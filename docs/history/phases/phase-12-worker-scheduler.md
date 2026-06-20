# Worker / Scheduler Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a background worker so the mini payment gateway automatically
expires overdue payments and delivers or retries due webhooks without manual
operator intervention.

**Architecture:** Phase 12 adds one worker service inside the existing backend
codebase. The worker runs as a long-lived process, reuses the current payment
expiration and webhook delivery domain services, and operates directly against
PostgreSQL through the same application layer as the API. The design favors a
small polling worker over a larger task-queue platform.

**Tech Stack:** Python, FastAPI codebase, SQLAlchemy, PostgreSQL, existing
expiration and webhook delivery services, Docker Compose, structured logging,
and simple worker health/heartbeat instrumentation.

---

## Implementation Status

Implemented in the pilot VietQR API branch after the user explicitly requested
product completion beyond MVP.

This plan assumes:

- phase 10 owns the internal Ops dashboard;
- phase 11 owns the merchant dashboard;
- payment expiration logic already exists at the service level;
- webhook delivery and retry scheduling logic already exists at the service
  level;
- sandbox CI/CD from phase 09 can be extended to start and deploy one worker
  service alongside the backend API.

This branch implements the worker in `backend/app/worker/*`, adds local and
sandbox Compose services, and documents worker operation in the runbook and
infrastructure docs. Commit only when requested.

## Scope

Implement:

- a dedicated worker entrypoint inside the backend codebase;
- an automated loop for expiring overdue payments;
- an automated loop for delivering due webhook events;
- automatic execution of webhook retry attempts based on `next_retry_at`;
- concurrency protection so duplicate workers do not process the same batch
  unsafely;
- environment-driven worker intervals and batch sizes;
- worker logging and minimal health visibility;
- Docker Compose and sandbox deploy integration for the worker;
- docs updates for worker operations and deployment.

Do not implement:

- Celery, Redis, Kafka, or a distributed task queue platform;
- a generic background job framework for arbitrary future jobs;
- a UI for managing scheduler jobs;
- autoscaling multiple workers as a first-class feature in this phase;
- complex alerting or full observability stack rollout;
- unrelated business features such as settlement, provider expansion, or new
  dashboard surfaces.

## Product Intent

This phase closes the operational gap between API behavior and real system
automation.

The desired system outcome is:

- overdue `PENDING` payments move to `EXPIRED` automatically;
- due webhook events are delivered without manual triggering;
- failed webhook events are retried automatically according to the existing retry
  policy;
- operators no longer need to depend on ad hoc scripts or manual replay for
  normal background activity.

The worker should remain intentionally simple:

- one responsibility-focused process;
- direct reuse of application services;
- idempotent loops;
- easy to deploy and reason about in sandbox.

## Design Decisions

- Keep the worker in the same repository and backend package so it can reuse the
  existing service layer directly.
- Use a polling loop rather than cron-per-task or a queue broker.
- Separate logical jobs inside the worker:
  - payment expiration;
  - webhook delivery and retry.
- Use database-backed locking, recommended via PostgreSQL advisory locks, to
  reduce duplicate processing risk if more than one worker starts.
- Prefer short loop intervals and bounded batch sizes over long-running single
  transactions.
- Call domain services directly instead of making HTTP calls back into the same
  API.
- Emit structured logs for every worker cycle so DevOps can verify behavior from
  logs alone if needed.

## Runtime Model

Recommended runtime shape:

- `postgres`
- `backend`
- `worker`

Recommended worker cycle:

1. open an application DB session;
2. acquire job lock;
3. expire overdue payments;
4. deliver due webhooks;
5. commit and close the session;
6. sleep for the configured interval;
7. repeat until shutdown.

The worker should support graceful shutdown so container restarts do not leave
the loop in an undefined state.

## Configuration

Required environment variables:

- `WORKER_ENABLED=true`
- `WORKER_LOOP_INTERVAL_SECONDS=15`
- `PAYMENT_EXPIRATION_BATCH_LIMIT=200`
- `WEBHOOK_DELIVERY_BATCH_LIMIT=100`
- `WORKER_LOG_LEVEL=INFO`

Optional environment variables:

- `WORKER_HEARTBEAT_PATH`
- `WORKER_HEALTH_PORT`
- `WORKER_PAYMENT_EXPIRATION_ENABLED=true`
- `WORKER_WEBHOOK_DELIVERY_ENABLED=true`

Configuration goals:

- intervals and batch sizes can be tuned without code changes;
- feature flags can disable one job type during debugging;
- health/heartbeat can be exposed in a lightweight way for operations.

## Locking And Safety Model

The worker must be safe if a second instance is started accidentally.

Recommended behavior:

- acquire one advisory lock for payment expiration;
- acquire one advisory lock for webhook delivery;
- if a lock cannot be acquired, log a skip and continue the next cycle;
- keep each batch idempotent so partial reruns do not corrupt business state.

Safety expectations:

- no unsafe duplicate expiration transitions;
- no unsafe duplicate webhook attempt creation from parallel workers;
- worker restarts do not require manual repair for normal cases.

## Logging And Health

Each cycle should log:

- cycle start time;
- job name;
- whether the lock was acquired;
- number of records processed;
- number of records skipped;
- number of failures;
- duration;
- next sleep interval.

Minimal health visibility should include one of:

- a heartbeat file timestamp;
- a tiny HTTP health endpoint;
- or a clearly documented log-based liveness check.

The goal is not full observability, but enough signal for DevOps to answer:

- is the worker running?
- is it doing useful work?
- is it stuck or erroring repeatedly?

## Files

### Backend

- Create: `backend/app/worker/main.py`
- Create: `backend/app/worker/runner.py`
- Create: `backend/app/worker/config.py`
- Create: `backend/app/worker/locks.py`
- Create: worker tests as needed under `backend/tests/`
- Modify: `backend/app/main.py` only if shared config/bootstrap needs exposure

### Infrastructure And Deployment

- Modify: `docker-compose.yml`
- Modify: `docker-compose.sandbox.yml`
- Modify: `deploy/sandbox_deploy.sh`
- Modify: `docs/infrastructure/sandbox-deployment.md`
- Modify: `docs/infrastructure/devops-architecture.md`

### Documentation

- Modify: `docs/architecture/backend.md`
- Modify: `README.md`
- Modify: `docs/history/README.md`
- Add completion record only after the worker is implemented and verified

## Tasks

### Task 0: Baseline And Service Readiness

- [ ] Run current backend test baseline:

```bash
cd backend
python -m unittest discover tests -v
```

- [ ] Confirm current expiration service behavior is covered well enough to be
      automated.
- [ ] Confirm current webhook delivery service behavior is covered well enough
      to be automated.
- [ ] Expected: current tests pass before worker code starts.

### Task 1: Worker Skeleton

- [ ] Create the worker package and entrypoint.
- [ ] Add environment/config parsing for intervals, flags, and batch limits.
- [ ] Add a long-lived loop with graceful shutdown handling.
- [ ] Add clear top-level structured cycle logging.

### Task 2: Concurrency Guard

- [ ] Implement advisory lock helpers for worker jobs.
- [ ] Protect payment expiration with a dedicated lock.
- [ ] Protect webhook delivery with a dedicated lock.
- [ ] Log skip behavior when a lock is already held elsewhere.
- [ ] Add tests for lock acquisition and contention handling.

### Task 3: Payment Expiration Automation

- [ ] Integrate the existing payment expiration service into the worker loop.
- [ ] Apply a bounded batch size.
- [ ] Log processed and expired counts.
- [ ] Add tests for automatic transition of overdue payments.

### Task 4: Webhook Delivery And Retry Automation

- [ ] Integrate the existing due-webhook delivery service into the worker loop.
- [ ] Process only due events according to `next_retry_at`.
- [ ] Respect the existing retry cadence and max-attempt policy.
- [ ] Log delivered, deferred, retry-scheduled, and failed outcomes.
- [ ] Add tests for automatic retry execution and terminal failure behavior.

### Task 5: Runtime Integration

- [ ] Add a `worker` service to local Docker Compose.
- [ ] Add a `worker` service to sandbox Docker Compose.
- [ ] Ensure the sandbox deploy script restarts or recreates the worker along
      with the backend.
- [ ] Document expected container names and health checks.

### Task 6: Health And Operations Visibility

- [ ] Add minimal worker liveness visibility via heartbeat or HTTP health.
- [ ] Document how to verify the worker from logs and runtime state.
- [ ] Ensure repeated failures are visible in logs without flooding noise
      excessively.

### Task 7: Verification And Documentation

- [ ] Add backend tests for worker loops, lock handling, and batch processing.
- [ ] Run worker smoke tests locally.
- [ ] Verify sandbox deploy brings up the worker successfully.
- [ ] Update infrastructure and architecture docs with the worker service.
- [ ] Write a completion record only after the worker is running correctly in
      sandbox.

## Acceptance Criteria

- Overdue `PENDING` payments are automatically transitioned to `EXPIRED`.
- Due webhook events are automatically delivered by the worker.
- Webhook retries are automatically attempted when `next_retry_at` is reached.
- Retry scheduling still respects the existing policy and terminal failure
  behavior.
- Starting a second worker instance does not create unsafe duplicate processing
  when locking works as designed.
- Worker restarts do not corrupt state or require manual reconciliation for
  normal cases.
- Local and sandbox compose stacks can run backend and worker together.
- DevOps can verify worker health from documented commands, logs, or health
  signals.

## Recommended Next Phase After Phase 12

Proceed to production hardening and go-live preparation after the operator
surfaces and worker automation are in place. Do not broaden this phase into a
general platform rewrite unless scope changes explicitly.
