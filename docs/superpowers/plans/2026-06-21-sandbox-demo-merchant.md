# Sandbox Demo Merchant Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically deploy the existing Demo Merchant App on the sandbox and expose its healthy checkout at port `8100`.

**Architecture:** Add the demo app as a Compose service built from the backend package, connected to the gateway through the internal Compose network. Reuse the gateway's provider-secret mapping, extend the deployment script with preflight validation and a demo health probe, and document the distinct LAN and internal webhook URLs.

**Tech Stack:** Docker Compose, Bash, GitHub Actions, FastAPI/Uvicorn, Python `unittest`.

---

### Task 1: Resolve the demo provider secret from the gateway mapping

**Files:**
- Create: `backend/tests/test_demo_merchant_config.py`
- Modify: `backend/demo_merchant/config.py`

- [ ] **Step 1: Write the failing configuration tests**

```python
import os
import unittest
from unittest.mock import patch


class DemoMerchantConfigTest(unittest.TestCase):
    def test_uses_selected_provider_secret_from_gateway_mapping(self) -> None:
        from demo_merchant.config import DemoMerchantSettings

        with patch.dict(
            os.environ,
            {
                "DEMO_PROVIDER_ID": "SIMULATOR",
                "PROVIDER_CALLBACK_SECRETS": "other=other-secret,simulator=sandbox-secret",
            },
            clear=True,
        ):
            settings = DemoMerchantSettings.from_env()

        self.assertEqual(settings.provider_id, "simulator")
        self.assertEqual(settings.provider_callback_secret, "sandbox-secret")

    def test_explicit_demo_secret_overrides_gateway_mapping(self) -> None:
        from demo_merchant.config import DemoMerchantSettings

        with patch.dict(
            os.environ,
            {
                "DEMO_PROVIDER_ID": "simulator",
                "DEMO_PROVIDER_CALLBACK_SECRET": "explicit-secret",
                "PROVIDER_CALLBACK_SECRETS": "simulator=mapped-secret",
            },
            clear=True,
        ):
            settings = DemoMerchantSettings.from_env()

        self.assertEqual(settings.provider_callback_secret, "explicit-secret")

    def test_rejects_mapping_without_selected_provider(self) -> None:
        from demo_merchant.config import DemoMerchantSettings

        with patch.dict(
            os.environ,
            {
                "DEMO_PROVIDER_ID": "simulator",
                "PROVIDER_CALLBACK_SECRETS": "other=other-secret",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "No callback secret configured for provider 'simulator'",
            ):
                DemoMerchantSettings.from_env()
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
cd backend
..\..\..\.venv\Scripts\python.exe -m unittest tests.test_demo_merchant_config -v
```

Expected: the mapping-selection and missing-provider tests fail because `from_env()` only reads `DEMO_PROVIDER_CALLBACK_SECRET`.

- [ ] **Step 3: Implement minimal secret selection**

Update `DemoMerchantSettings.from_env()` to normalize the provider ID and call a helper:

```python
provider_id = os.getenv("DEMO_PROVIDER_ID", "simulator").strip().lower()
provider_callback_secret = _provider_callback_secret(provider_id)
```

Add:

```python
def _provider_callback_secret(provider_id: str) -> str:
    explicit_secret = os.getenv("DEMO_PROVIDER_CALLBACK_SECRET")
    if explicit_secret:
        return explicit_secret

    mapping = os.getenv("PROVIDER_CALLBACK_SECRETS")
    if mapping is None:
        return "dev-insecure-provider-callback-secret-change-me"

    for item in mapping.split(","):
        mapped_provider, separator, secret = item.strip().partition("=")
        if separator and mapped_provider.strip().lower() == provider_id and secret:
            return secret

    raise ValueError(f"No callback secret configured for provider '{provider_id}'.")
```

- [ ] **Step 4: Run focused and existing demo tests and verify GREEN**

Run:

```powershell
cd backend
..\..\..\.venv\Scripts\python.exe -m unittest tests.test_demo_merchant_config tests.test_demo_merchant_app tests.test_demo_merchant_security -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit the configuration behavior**

```powershell
git add backend/demo_merchant/config.py backend/tests/test_demo_merchant_config.py
git commit -m "feat: share sandbox provider secret with demo merchant"
```

### Task 2: Add Demo Merchant App to sandbox Compose and deployment

**Files:**
- Modify: `docker-compose.sandbox.yml`
- Modify: `deploy/sandbox_deploy.sh`
- Modify: `.github/workflows/sandbox-deploy.yml`
- Modify: `.env.sandbox.example`

- [ ] **Step 1: Capture the failing runtime contract**

Run:

```powershell
docker compose -f docker-compose.sandbox.yml config --services
```

Expected before implementation: output does not contain `demo-merchant`.

- [ ] **Step 2: Add the Compose service**

Add a `demo-merchant` service built from `./backend` with:

```yaml
  demo-merchant:
    build:
      context: ./backend
    restart: unless-stopped
    environment:
      GATEWAY_BASE_URL: http://backend:8000
      DEMO_PROVIDER_ID: ${DEMO_PROVIDER_ID:-simulator}
      PROVIDER_CALLBACK_SECRETS: ${PROVIDER_CALLBACK_SECRETS:?PROVIDER_CALLBACK_SECRETS is required for sandbox}
      DEMO_MODE: ${DEMO_MODE:-true}
    depends_on:
      backend:
        condition: service_healthy
    command: bash -lc "uvicorn demo_merchant.main:app --host 0.0.0.0 --port 8100"
    ports:
      - "${DEMO_MERCHANT_BIND_ADDR:-127.0.0.1}:${DEMO_MERCHANT_PORT:-8100}:8100"
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health').read()",
        ]
      interval: 10s
      timeout: 5s
      retries: 6
```

Add these defaults to `.env.sandbox.example`:

```dotenv
DEMO_PROVIDER_ID=simulator
DEMO_MODE=true
DEMO_MERCHANT_BIND_ADDR=127.0.0.1
DEMO_MERCHANT_PORT=8100
```

- [ ] **Step 3: Extend the deploy script**

In `deploy/sandbox_deploy.sh`:

- include `demo-merchant` in failure logs, build, and `up -d` commands;
- run `docker compose -f "$COMPOSE_FILE" config --quiet` before the build;
- read `DEMO_MERCHANT_BIND_ADDR` and `DEMO_MERCHANT_PORT` with the existing `.env` helper;
- derive `DEMO_MERCHANT_URL` with `probe_host_for_bind_addr`;
- poll `/health` after the existing Merchant Dashboard check;
- print the deployed revision and exit only after the demo health probe passes.

The resulting probe block is:

```bash
log "Polling demo merchant health endpoint: $DEMO_MERCHANT_URL"
for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
  if curl -fsS "$DEMO_MERCHANT_URL" >/dev/null; then
    log "Demo merchant health check passed on attempt $attempt"
    git rev-parse --short HEAD
    exit 0
  fi
  sleep "$HEALTH_SLEEP_SECONDS"
done

log "Demo merchant health check did not pass after $HEALTH_ATTEMPTS attempts"
exit 1
```

- [ ] **Step 4: Propagate the optional Actions URL override**

In `.github/workflows/sandbox-deploy.yml`, add:

```yaml
SANDBOX_DEMO_MERCHANT_URL: ${{ vars.SANDBOX_DEMO_MERCHANT_URL }}
```

Resolve and pass it to the script as `DEMO_MERCHANT_URL`, matching the existing dashboard URL variables.

- [ ] **Step 5: Validate the Compose and shell contracts**

Run:

```powershell
$env:POSTGRES_PASSWORD = "test"
$env:DATABASE_URL = "postgresql+psycopg2://postgres:test@postgres:5432/mini_payment_gateway"
$env:INTERNAL_AUTH_SECRET = "test-internal"
$env:MERCHANT_AUTH_SECRET = "test-merchant"
$env:PROVIDER_CALLBACK_SECRETS = "simulator=test-provider"
docker compose -f docker-compose.sandbox.yml config --quiet
docker compose -f docker-compose.sandbox.yml config --services
bash -n deploy/sandbox_deploy.sh
```

Expected: Compose validation succeeds, service output includes `demo-merchant`, and Bash syntax validation exits zero.

- [ ] **Step 6: Commit sandbox deployment support**

```powershell
git add docker-compose.sandbox.yml deploy/sandbox_deploy.sh .github/workflows/sandbox-deploy.yml .env.sandbox.example
git commit -m "feat: deploy demo merchant on sandbox"
```

### Task 3: Document and verify the sandbox demo route

**Files:**
- Modify: `docs/getting-started/e2e-payment-demo.md`
- Modify: `docs/infrastructure/sandbox-deployment.md`
- Modify: `docs/infrastructure/sandbox-setup-from-zero.md`

- [ ] **Step 1: Document local and sandbox URLs**

Add a sandbox section to the E2E guide stating:

```text
Browser checkout: http://<sandbox-host>:8100
Merchant credential webhook URL: http://demo-merchant:8100/webhooks/payment-gateway
```

Keep the five-terminal `.venv` instructions as the local-development path.

- [ ] **Step 2: Complete the sandbox environment inventory**

Add `PROVIDER_CALLBACK_SECRETS`, `DEMO_PROVIDER_ID`, `DEMO_MODE`,
`DEMO_MERCHANT_BIND_ADDR`, and `DEMO_MERCHANT_PORT` to the setup guide example.
This directly prevents the missing-secret failure seen during the first deploy.

- [ ] **Step 3: Extend deploy verification and troubleshooting**

Update the deployment runbook so successful runtime state includes a healthy
`demo-merchant`, endpoint checks include port `8100`, and troubleshooting shows:

```bash
docker compose -f docker-compose.sandbox.yml logs --tail 100 demo-merchant
docker compose -f docker-compose.sandbox.yml ps demo-merchant
```

- [ ] **Step 4: Run regression verification**

Run:

```powershell
cd backend
..\..\..\.venv\Scripts\python.exe -m unittest tests.test_demo_merchant_config tests.test_demo_merchant_app tests.test_demo_merchant_security -v
cd ..
git diff --check
```

Also run the Compose and Bash checks from Task 2. Expected: all commands exit zero.

- [ ] **Step 5: Commit documentation**

```powershell
git add docs/getting-started/e2e-payment-demo.md docs/infrastructure/sandbox-deployment.md docs/infrastructure/sandbox-setup-from-zero.md
git commit -m "docs: explain sandbox demo merchant deployment"
```

### Task 4: Publish, deploy, and verify the hotfix

**Files:**
- No additional source files.

- [ ] **Step 1: Push the hotfix branch and open a pull request into `main`**

```powershell
git push -u origin fix/sandbox-demo-merchant
```

- [ ] **Step 2: Prepare the server-only bind address before merge**

Add without printing secrets:

```dotenv
DEMO_MERCHANT_BIND_ADDR=192.168.1.199
DEMO_MERCHANT_PORT=8100
```

Verify `docker compose -f docker-compose.sandbox.yml config --quiet` on the server.

- [ ] **Step 3: Merge and let Sandbox Deploy run automatically**

Expected: tests, image builds, migration check, all service starts, and the new demo health probe pass.

- [ ] **Step 4: Verify server and LAN access**

Run on the server:

```bash
docker compose -f docker-compose.sandbox.yml ps demo-merchant
curl -fsS http://127.0.0.1:8100/health
```

Run from the development machine:

```powershell
curl.exe -fsS http://192.168.1.199:8100/health
```

Expected: the container is healthy and both probes return a JSON object with `"status":"ok"`.
