# Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the backend structure needed for routes, schemas, services, repositories, dependency injection, and consistent errors.

**Architecture:** FastAPI route handlers should stay thin and call service classes. Services own business rules, repositories own SQLAlchemy queries, schemas own request/response validation, and core modules own shared errors/security/time helpers.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Pydantic/FastAPI schemas, unittest or pytest.

---

## Scope

Prepare the codebase for feature implementation without implementing payment or
refund business behavior yet.

## Files

- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/errors.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/app/core/errors.py`
- Create: `backend/app/core/time.py`
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/services/__init__.py`
- Modify: `backend/app/main.py`
- Modify: `backend/pyproject.toml` only if a test dependency is needed.
- Test: `backend/tests/test_app_foundation.py`

## Tasks

### Task 1: Move Health Route Into Router

- [ ] Write a failing test in `backend/tests/test_app_foundation.py` that imports `app.main.app` and verifies `/health` still returns `{"status": "ok"}`.
- [ ] Run:

```powershell
cd backend
python -m unittest tests.test_app_foundation -v
```

- [ ] Expected: FAIL because the test file or route structure is not present yet.
- [ ] Create `backend/app/api/routes/health.py` with an `APIRouter`.
- [ ] Modify `backend/app/main.py` to include the health router.
- [ ] Run the test again.
- [ ] Expected: PASS.

### Task 2: Add Database Session Dependency

- [ ] Create `backend/app/api/deps.py`.
- [ ] Add `get_db()` that yields `SessionLocal()` and closes it in `finally`.
- [ ] Add a unit test that calls the generator and verifies it yields a session-like object.
- [ ] Keep this helper small; do not add repository logic here.

### Task 3: Add API Error Model

- [ ] Create `backend/app/core/errors.py`.
- [ ] Define a small exception type:

```python
class AppError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
```

- [ ] Create `backend/app/api/errors.py`.
- [ ] Add an exception handler that returns:

```json
{
  "error_code": "...",
  "message": "...",
  "details": {}
}
```

- [ ] Register the handler in `backend/app/main.py`.
- [ ] Add a temporary test-only route or unit-level handler test; remove any test-only route after verification.

### Task 4: Add Time Helper

- [ ] Create `backend/app/core/time.py`.
- [ ] Add:

```python
from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)
```

- [ ] Add tests to verify timezone-aware datetime.

### Task 5: Add Empty Package Boundaries

- [ ] Create `backend/app/schemas/__init__.py`.
- [ ] Create `backend/app/services/__init__.py`.
- [ ] Create `backend/app/repositories/__init__.py`.
- [ ] Create `backend/app/api/routes/__init__.py`.
- [ ] Verify imports do not break:

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
- Route, schema, service, repository, and core utility folders exist.
- No payment/refund/webhook business logic is implemented in this phase.
