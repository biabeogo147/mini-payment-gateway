# Merchant Auth And Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement merchant HMAC authentication and merchant readiness checks used by all merchant-facing APIs.

**Architecture:** Auth is a reusable dependency that loads merchant and active credential, validates headers, checks timestamp freshness, verifies HMAC, and returns an authenticated merchant context. Merchant operational readiness stays in a service helper so payment/refund flows can share it.

**Tech Stack:** FastAPI dependencies, SQLAlchemy repositories, HMAC-SHA256 from Python standard library.

---

## Implementation Status

Completed. The implementation added HMAC security helpers, merchant and
credential repositories, authenticated merchant context, auth service, FastAPI
auth dependency, and merchant readiness guards.

Verification commands used:

```powershell
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_auth_service -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest tests.test_merchant_readiness -v
& 'D:\Anaconda\envs\mini-payment-gateway\python.exe' -m unittest discover tests -v
```

## Scope

Implement the security foundation for merchant APIs:

- Required auth headers.
- Timestamp validity window: 5 minutes.
- HMAC-SHA256 signature verification.
- Active merchant and credential checks.
- Merchant readiness for create payment/refund.

## Files

- Create: `backend/app/core/security.py`
- Create: `backend/app/repositories/merchant_repository.py`
- Create: `backend/app/repositories/credential_repository.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/services/merchant_readiness.py`
- Create: `backend/app/schemas/auth.py`
- Modify: `backend/app/controllers/deps.py`
- Test: `backend/tests/test_auth_service.py`
- Test: `backend/tests/test_merchant_readiness.py`

## Signature Contract

Canonical signing string:

```text
{timestamp}.{method}.{path}.{body_sha256_hex}
```

Signature:

```text
hex(hmac_sha256(secret_key, signing_string))
```

For the MVP, `secret_key_encrypted` may be treated as plaintext until encryption
is introduced. Keep the decrypt operation isolated behind a helper so later
encryption does not change the auth service interface.

## Tasks

### Task 1: Write Security Unit Tests

- [x] Add tests in `backend/tests/test_auth_service.py`:
  - valid signature passes.
  - invalid signature fails.
  - timestamp older than 5 minutes fails.
  - missing header fails with specific error code.
- [x] Run:

```powershell
cd backend
python -m unittest tests.test_auth_service -v
```

- [x] Expected: FAIL because security helpers do not exist yet.

### Task 2: Implement HMAC Helpers

- [x] Create `backend/app/core/security.py`.
- [x] Implement:
  - `sha256_hex(payload: bytes) -> str`
  - `build_signing_string(timestamp: str, method: str, path: str, body: bytes) -> str`
  - `sign_hmac_sha256(secret: str, message: str) -> str`
  - `constant_time_equal(left: str, right: str) -> bool`
- [x] Run auth unit tests.
- [x] Expected: HMAC helper tests pass; service tests may still fail.

### Task 3: Add Merchant And Credential Repositories

- [x] Create `backend/app/repositories/merchant_repository.py`.
- [x] Add method:
  - `get_by_public_merchant_id(db, merchant_id: str) -> Merchant | None`
- [x] Create `backend/app/repositories/credential_repository.py`.
- [x] Add method:
  - `get_active_by_merchant_and_access_key(db, merchant_db_id, access_key: str) -> MerchantCredential | None`
- [x] Cover repository lookup seams with auth service tests that mock repository dependencies.

### Task 4: Implement Auth Service

- [x] Create `backend/app/schemas/auth.py`.
- [x] Define `AuthenticatedMerchant` with:
  - `merchant`
  - `credential`
  - `merchant_id`
- [x] Create `backend/app/services/auth_service.py`.
- [x] Implement `authenticate_merchant_request(...)`.
- [x] Error codes:
  - `AUTH_MISSING_HEADER`
  - `AUTH_INVALID_MERCHANT`
  - `AUTH_INVALID_CREDENTIAL`
  - `AUTH_TIMESTAMP_EXPIRED`
  - `AUTH_INVALID_SIGNATURE`
- [x] Run:

```powershell
cd backend
python -m unittest tests.test_auth_service -v
```

- [x] Expected: PASS.

### Task 5: Add FastAPI Dependency

- [x] Modify `backend/app/controllers/deps.py`.
- [x] Add dependency that extracts headers and request body, then calls auth service.
- [x] Name it `get_authenticated_merchant`.
- [x] Do not attach it to controllers yet unless a minimal test endpoint is needed.

### Task 6: Implement Merchant Readiness

- [x] Create `backend/app/services/merchant_readiness.py`.
- [x] Implement:
  - `assert_can_create_payment(merchant)`
  - `assert_can_create_refund(merchant)`
  - `assert_can_receive_ops_update(merchant)` if useful.
- [x] Rules:
  - `ACTIVE` can create payment/refund.
  - `SUSPENDED`, `DISABLED`, `REJECTED`, `PENDING_REVIEW` cannot create payment/refund.
  - suspended merchants remain inspectable by ops.
- [x] Add tests in `backend/tests/test_merchant_readiness.py`.
- [x] Run:

```powershell
cd backend
python -m unittest tests.test_merchant_readiness -v
```

- [x] Expected: PASS.

### Task 7: Commit

- [ ] Stage auth/readiness files.
- [ ] Commit message suggestion:

```text
feat: add merchant auth and readiness checks
```

## Acceptance Criteria

- Merchant HMAC auth is reusable by payment/refund/status APIs.
- Timestamp window is enforced.
- Invalid merchant, credential, signature, and missing header errors are distinct.
- Merchant readiness blocks payment/refund for non-active merchants.
