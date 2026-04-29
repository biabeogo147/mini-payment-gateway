# Merchant Auth And Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement merchant HMAC authentication and merchant readiness checks used by all merchant-facing APIs.

**Architecture:** Auth is a reusable dependency that loads merchant and active credential, validates headers, checks timestamp freshness, verifies HMAC, and returns an authenticated merchant context. Merchant operational readiness stays in a service helper so payment/refund flows can share it.

**Tech Stack:** FastAPI dependencies, SQLAlchemy repositories, HMAC-SHA256 from Python standard library.

---

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
- Modify: `backend/app/api/deps.py`
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

- [ ] Add tests in `backend/tests/test_auth_service.py`:
  - valid signature passes.
  - invalid signature fails.
  - timestamp older than 5 minutes fails.
  - missing header fails with specific error code.
- [ ] Run:

```powershell
cd backend
python -m unittest tests.test_auth_service -v
```

- [ ] Expected: FAIL because security helpers do not exist yet.

### Task 2: Implement HMAC Helpers

- [ ] Create `backend/app/core/security.py`.
- [ ] Implement:
  - `sha256_hex(payload: bytes) -> str`
  - `build_signing_string(timestamp: str, method: str, path: str, body: bytes) -> str`
  - `sign_hmac_sha256(secret: str, message: str) -> str`
  - `constant_time_equal(left: str, right: str) -> bool`
- [ ] Run auth unit tests.
- [ ] Expected: HMAC helper tests pass; service tests may still fail.

### Task 3: Add Merchant And Credential Repositories

- [ ] Create `backend/app/repositories/merchant_repository.py`.
- [ ] Add method:
  - `get_by_public_merchant_id(db, merchant_id: str) -> Merchant | None`
- [ ] Create `backend/app/repositories/credential_repository.py`.
- [ ] Add method:
  - `get_active_by_merchant_and_access_key(db, merchant_db_id, access_key: str) -> MerchantCredential | None`
- [ ] Add repository unit tests using an in-memory or transaction-scoped database fixture if available; otherwise mock the session for now.

### Task 4: Implement Auth Service

- [ ] Create `backend/app/schemas/auth.py`.
- [ ] Define `AuthenticatedMerchant` with:
  - `merchant`
  - `credential`
  - `merchant_id`
- [ ] Create `backend/app/services/auth_service.py`.
- [ ] Implement `authenticate_merchant_request(...)`.
- [ ] Error codes:
  - `AUTH_MISSING_HEADER`
  - `AUTH_INVALID_MERCHANT`
  - `AUTH_INVALID_CREDENTIAL`
  - `AUTH_TIMESTAMP_EXPIRED`
  - `AUTH_INVALID_SIGNATURE`
- [ ] Run:

```powershell
cd backend
python -m unittest tests.test_auth_service -v
```

- [ ] Expected: PASS.

### Task 5: Add FastAPI Dependency

- [ ] Modify `backend/app/api/deps.py`.
- [ ] Add dependency that extracts headers and request body, then calls auth service.
- [ ] Name it `get_authenticated_merchant`.
- [ ] Do not attach it to routes yet unless a minimal test route is needed.

### Task 6: Implement Merchant Readiness

- [ ] Create `backend/app/services/merchant_readiness.py`.
- [ ] Implement:
  - `assert_can_create_payment(merchant)`
  - `assert_can_create_refund(merchant)`
  - `assert_can_receive_ops_update(merchant)` if useful.
- [ ] Rules:
  - `ACTIVE` can create payment/refund.
  - `SUSPENDED`, `DISABLED`, `REJECTED`, `PENDING_REVIEW` cannot create payment/refund.
  - suspended merchants remain inspectable by ops.
- [ ] Add tests in `backend/tests/test_merchant_readiness.py`.
- [ ] Run:

```powershell
cd backend
python -m unittest tests.test_merchant_readiness -v
```

- [ ] Expected: PASS.

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
