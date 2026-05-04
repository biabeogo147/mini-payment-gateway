# MVC Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the current backend package shape into a small MVC-style structure before adding payment core routes.

**Architecture:** Keep the mini gateway layered, but not DDD. FastAPI controllers own HTTP concerns, schemas describe API/input-output shapes, services own business rules, repositories own SQLAlchemy persistence queries, models remain the database schema, and core/db provide shared infrastructure.

**Tech Stack:** FastAPI, Pydantic/dataclasses, SQLAlchemy ORM, unittest, existing Alembic-managed PostgreSQL schema.

---

## Implementation Status

Completed. The implementation moved HTTP source modules from `app.api` into
`app.controllers`, renamed merchant readiness to
`merchant_readiness_service.py`, removed old source files from `backend/app/api`,
updated future phase plans to use controller paths, and verified unit/API smoke
behavior.

Verification commands used:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_app_foundation -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_merchant_readiness -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

API smoke result:

```json
{
  "Health": "{\"status\":\"ok\"}",
  "Title": "Mini Payment Gateway",
  "Version": "0.1.0"
}
```

## Scope

This is a structural refactor only:

- Move `app.api.routes.*` into `app.controllers.*`.
- Move FastAPI request dependencies near controllers.
- Move FastAPI exception handler near controllers.
- Rename `merchant_readiness.py` to `merchant_readiness_service.py` for service naming consistency.
- Update tests and docs that reference the old package paths.
- Keep endpoint paths, error payloads, auth behavior, database models, migrations, and business rules unchanged.

Do not implement payment, refund, webhook, reconciliation, or ops workflows in this phase.

## Target Backend Shape

```text
backend/app/
  controllers/
    __init__.py
    deps.py
    errors.py
    health_controller.py
  core/
    config.py
    errors.py
    security.py
    time.py
  db/
    base.py
    session.py
  models/
  repositories/
    credential_repository.py
    merchant_repository.py
  schemas/
    auth.py
  services/
    auth_service.py
    merchant_readiness_service.py
  main.py
```

Future phases should add new HTTP entry points under `controllers/`, for example:

- `payment_controller.py`
- `refund_controller.py`
- `provider_callback_controller.py`
- `ops_controller.py`
- `webhook_controller.py`

## Layer Rules

- `controllers` may import `schemas`, `services`, `core`, and `db` dependencies.
- `services` may import `repositories`, `schemas`, `models`, and `core`.
- `repositories` may import `models` and SQLAlchemy session/query helpers.
- `schemas` may define request/response DTOs and small context objects. Public API schemas should not expose SQLAlchemy model instances directly.
- `models` should not import controllers, services, repositories, or schemas.
- `core` and `db` should stay infrastructure-only and must not contain payment business workflows.

## Files

- Create: `backend/app/controllers/__init__.py`
- Create: `backend/app/controllers/deps.py`
- Create: `backend/app/controllers/errors.py`
- Create: `backend/app/controllers/health_controller.py`
- Create: `backend/app/services/merchant_readiness_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_app_foundation.py`
- Modify: `backend/tests/test_merchant_readiness.py`
- Modify: `docs/history/README.md`
- Modify: `docs/history/phases/phase-03-payment-core.md`
- Delete after imports are migrated: `backend/app/api/deps.py`
- Delete after imports are migrated: `backend/app/api/errors.py`
- Delete after imports are migrated: `backend/app/api/routes/health.py`
- Delete if empty: `backend/app/api/__init__.py`
- Delete if empty: `backend/app/api/routes/__init__.py`
- Delete after replacement exists: `backend/app/services/merchant_readiness.py`

## Tasks

### Task 1: Add Import Boundary Tests

- [x] Update `backend/tests/test_app_foundation.py` so the health router comes from `app.controllers.health_controller`.

```python
from app.controllers.health_controller import router as health_router
```

- [x] Update the same file so `get_db` comes from `app.controllers.deps`.

```python
from app.controllers import deps
```

- [x] Update the same file so the FastAPI `AppError` handler comes from `app.controllers.errors`.

```python
from app.controllers.errors import app_error_handler
```

- [x] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_app_foundation -v
```

- [x] Expected: FAIL because `app.controllers` does not exist yet.

### Task 2: Move HTTP Modules Into Controllers

- [x] Create `backend/app/controllers/__init__.py`.
- [x] Create `backend/app/controllers/health_controller.py` with the current `/health` router behavior.
- [x] Create `backend/app/controllers/deps.py` with the current `get_db` and `get_authenticated_merchant` dependencies.
- [x] Create `backend/app/controllers/errors.py` with the current `app_error_handler`.
- [x] Modify `backend/app/main.py` imports:

```python
from app.controllers.errors import app_error_handler
from app.controllers.health_controller import router as health_router
```

- [x] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_app_foundation -v
```

- [x] Expected: PASS.

### Task 3: Rename Merchant Readiness Service

- [x] Update `backend/tests/test_merchant_readiness.py` imports from:

```python
from app.services.merchant_readiness import assert_can_create_payment
```

to:

```python
from app.services.merchant_readiness_service import assert_can_create_payment
```

- [x] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_merchant_readiness -v
```

- [x] Expected: FAIL because `merchant_readiness_service.py` does not exist yet.
- [x] Create `backend/app/services/merchant_readiness_service.py` with the same functions from the current readiness service.
- [x] Run the same test command again.
- [x] Expected: PASS.

### Task 4: Remove Old API Package Imports

- [x] Search for old imports:

```powershell
rg -n "app\.api|api\.routes|services\.merchant_readiness" backend docs
```

- [x] Replace remaining implementation/test references with:
  - `app.controllers.deps`
  - `app.controllers.errors`
  - `app.controllers.health_controller`
  - `app.services.merchant_readiness_service`
- [x] Delete old `backend/app/api/*` files after there are no imports left.
- [x] Run:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

- [x] Expected: all tests pass.

### Task 5: Update Phase 03 Plan For MVC Paths

- [x] Modify `docs/history/phases/phase-03-payment-core.md`.
- [x] Replace route/controller file references:
  - `backend/app/api/routes/payments.py` -> `backend/app/controllers/payment_controller.py`
  - route wording -> controller wording where appropriate.
- [x] Ensure phase 03 still keeps payment business rules in `payment_service.py`.
- [x] Run:

```powershell
rg -n "app/api|api/routes|app\.api" docs/history/phases/phase-03-payment-core.md
```

- [x] Expected: no matches.

### Task 6: Architecture Documentation Check

- [x] Confirm `docs/architecture/backend.md` describes the new layer order.
- [x] Confirm `docs/history/README.md` lists phase 2.5 before phase 03.
- [x] Run:

```powershell
rg -n "API package boundaries|app/api|api/routes|app\.api" docs/history docs/architecture/backend.md
```

- [x] Expected: no stale references except migration instructions and historical completion notes.

### Task 7: API Smoke Verification

- [x] Start FastAPI locally:

```powershell
cd backend
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- [x] Call:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/openapi.json
```

- [x] Expected:
  - `/health` returns `{"status":"ok"}`.
  - OpenAPI title remains `Mini Payment Gateway`.

### Task 8: Commit

- [ ] Stage MVC refactor files and docs.
- [ ] Commit message suggestion:

```text
refactor: organize backend into mvc layers
```

## Acceptance Criteria

- No runtime import depends on `app.api`.
- Existing tests pass after the package move.
- `/health` and `/openapi.json` keep the same behavior.
- Phase 03 plan points new HTTP work to `backend/app/controllers/`.
- Architecture docs clearly show the allowed dependency direction from controller to database.
