# Sandbox Demo Merchant Service Design

## Goal

Deploy the existing `backend/demo_merchant/` application as a first-class
sandbox service so it starts automatically with the gateway and is reachable
from the LAN at port `8100`.

## Architecture

Add a `demo-merchant` service to `docker-compose.sandbox.yml`. It reuses the
backend image and runs:

```text
uvicorn demo_merchant.main:app --host 0.0.0.0 --port 8100
```

The browser reaches the service through the published host address, normally
`http://192.168.1.199:8100`. Inside the Compose network, the demo merchant calls
the gateway through `http://backend:8000`.

The gateway worker must deliver demo webhooks to the Compose service address:

```text
http://demo-merchant:8100/webhooks/payment-gateway
```

The service keeps its existing in-memory state. Restarting or redeploying the
container intentionally clears the demo setup and orders.

## Configuration

The sandbox Compose service accepts:

- `DEMO_MERCHANT_BIND_ADDR`, defaulting to `127.0.0.1`.
- `DEMO_MERCHANT_PORT`, defaulting to `8100`.
- `DEMO_PROVIDER_ID`, defaulting to `simulator`.
- `PROVIDER_CALLBACK_SECRETS`, shared with the gateway backend.
- `DEMO_MODE`, defaulting to `true` for sandbox.

`DemoMerchantSettings` will use `DEMO_PROVIDER_CALLBACK_SECRET` when explicitly
set. Otherwise it will select the `DEMO_PROVIDER_ID` value from
`PROVIDER_CALLBACK_SECRETS`. This avoids maintaining two copies of the same
provider secret in the server-only `.env`.

The real secret remains server-only and is never rendered into frontend code or
printed by deployment checks.

## Deployment Flow

`deploy/sandbox_deploy.sh` will:

1. Validate Compose interpolation before building.
2. Build the backend, worker, demo merchant, and dashboards.
3. Apply migrations and start all services.
4. Poll the demo merchant `/health` endpoint after the existing gateway and
   dashboard checks.
5. Include demo merchant logs in failure output.

The GitHub Actions deploy job may provide `SANDBOX_DEMO_MERCHANT_URL`. When it
is absent, the deploy script derives the probe URL from the server `.env` bind
address and port, following the existing dashboard pattern.

## Failure Handling

- Missing provider callback configuration fails during Compose validation,
  before images are built.
- A demo merchant that cannot start or pass `/health` fails the deployment.
- Existing gateway services remain independently health-checked.
- The demo service depends on a healthy backend but does not block PostgreSQL
  or gateway startup during an isolated restart.

## Verification

- Unit tests cover provider secret selection, explicit override, and missing
  provider configuration.
- `docker compose -f docker-compose.sandbox.yml config --quiet` validates the
  service and environment contract.
- Backend tests verify the demo app and settings behavior.
- A sandbox probe verifies both `http://127.0.0.1:8100/health` on the host and
  `http://192.168.1.199:8100/` from a LAN client.
- The final E2E check configures a credential webhook URL with the internal
  Compose hostname and confirms the checkout changes state only after worker
  webhook delivery.

## Scope

This change only makes the existing demo application part of sandbox
deployment. It does not add production hosting, persistent demo order storage,
real bank integration, or public internet exposure.
