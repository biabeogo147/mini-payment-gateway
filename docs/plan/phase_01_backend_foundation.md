# Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the backend structure needed for controllers, schemas, services, repositories, dependency injection, and consistent errors.

**Architecture:** FastAPI controllers should stay thin and call service classes. Services own business rules, repositories own SQLAlchemy queries, schemas own request/response validation, and core modules own shared errors/security/time helpers.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Pydantic/FastAPI schemas, unittest or pytest.

---

## Implementation Status

Completed. The implementation added the backend controller boundary, health
controller, database dependency, standard domain error shape, UTC time helper,
and foundation tests. The initial route package was migrated to `controllers/`
in phase 2.5.

Verification commands used:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_app_foundation -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

## Scope

Prepare the codebase for feature implementation without implementing payment or
refund business behavior yet.

## Files

- Create: `backend/app/controllers/__init__.py`
- Create: `backend/app/controllers/deps.py`
- Create: `backend/app/controllers/errors.py`
- Create: `backend/app/controllers/health_controller.py`
- Create: `backend/app/core/errors.py`
- Create: `backend/app/core/time.py`
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/services/__init__.py`
- Modify: `backend/app/main.py`
- Modify: `backend/pyproject.toml` only if a test dependency is needed.
- Test: `backend/tests/test_app_foundation.py`

## Tasks

### Task 1: Move Health Endpoint Into Controller

- [x] Write a failing test in `backend/tests/test_app_foundation.py` that imports `app.main.app` and verifies `/health` still returns `{"status": "ok"}`.
- [x] Run:

```powershell
cd backend
python -m unittest tests.test_app_foundation -v
```

- [x] Expected: FAIL because the test file or controller structure is not present yet.
- [x] Create `backend/app/controllers/health_controller.py` with an `APIRouter`.
- [x] Modify `backend/app/main.py` to include the health controller router.
- [x] Run the test again.
- [x] Expected: PASS.

### Task 2: Add Database Session Dependency

- [x] Create `backend/app/controllers/deps.py`.
- [x] Add `get_db()` that yields `SessionLocal()` and closes it in `finally`.
- [x] Add a unit test that calls the generator and verifies it yields a session-like object.
- [x] Keep this helper small; do not add repository logic here.

### Task 3: Add API Error Model

- [x] Create `backend/app/core/errors.py`.
- [x] Define a small exception type:

```python
class AppError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
```

- [x] Create `backend/app/controllers/errors.py`.
- [x] Add an exception handler that returns:

```json
{
  "error_code": "...",
  "message": "...",
  "details": {}
}
```

- [x] Register the handler in `backend/app/main.py`.
- [x] Add a temporary test-only endpoint or unit-level handler test; remove any test-only endpoint after verification.

### Task 4: Add Time Helper

- [x] Create `backend/app/core/time.py`.
- [x] Add:

```python
from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)
```

- [x] Add tests to verify timezone-aware datetime.

### Task 5: Add Empty Package Boundaries

- [x] Create `backend/app/schemas/__init__.py`.
- [x] Create `backend/app/services/__init__.py`.
- [x] Create `backend/app/repositories/__init__.py`.
- [x] Create `backend/app/controllers/__init__.py`.
- [x] Verify imports do not break:

```powershell
cd backend
python -m unittest discover tests -v
```

### Task 6: Commit

- [ ] Stage foundation files.
- [ ] Commit message suggestion:

```text
chore: add backend foundation structure
```

## Acceptance Criteria

- `/health` still works.
- App has a single registered error shape for domain errors.
- Controller, schema, service, repository, and core utility folders exist.
- No payment/refund/webhook business logic is implemented in this phase.
