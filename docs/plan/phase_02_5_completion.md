# Phase 2.5 Completion Summary

Completed on branch `codex-phase-0-2`.

## Completed Scope

- Added `backend/app/controllers/` for FastAPI controllers, request
  dependencies, and HTTP error handling.
- Moved health endpoint registration to `health_controller.py`.
- Updated `backend/app/main.py` to import controllers instead of the old API
  route package.
- Renamed merchant readiness module to
  `backend/app/services/merchant_readiness_service.py`.
- Removed old source files under `backend/app/api/`.
- Updated tests to assert the new controller/service import boundaries.
- Updated future phase plans so new HTTP work lands under
  `backend/app/controllers/`.

## Verification Evidence

### TDD Red Checks

The controller boundary test failed before `app.controllers` existed:

```text
ModuleNotFoundError: No module named 'app.controllers'
```

The readiness service rename test failed before the new service module existed:

```text
ModuleNotFoundError: No module named 'app.services.merchant_readiness_service'
```

### Unit Tests

Run from `backend/`:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

Result:

```text
Ran 25 tests
OK
```

### API Smoke

Uvicorn was started locally and stopped after the smoke check.

Result:

```json
{
  "Health": "{\"status\":\"ok\"}",
  "Title": "Mini Payment Gateway",
  "Version": "0.1.0"
}
```

## Notes

- No commit was created because no commit was requested.
- A local `backend/app/api/` directory may remain on disk if Python cache files
  exist there, but the source modules were removed and runtime imports no longer
  depend on `app.api`.

## Superseded Next Phase

Phase 03 has now been completed. See `docs/plan/phase_03_completion.md`.

That slice added:

- `backend/app/controllers/payment_controller.py`;
- payment request/response schemas;
- order reference and payment repositories;
- payment service and QR service;
- route tests for payment endpoints.
