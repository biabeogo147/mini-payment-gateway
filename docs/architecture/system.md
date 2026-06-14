# System Architecture

This document is the presentation-level system architecture for the current
implemented mini payment gateway. It complements `backend.md`, which explains
the internal backend layer structure.

## Implemented System Context

```mermaid
flowchart LR
    admin["Admin / Ops user"]
    merchant_user["Merchant portal user"]
    merchant_backend["Merchant backend"]
    provider["Provider simulator"]
    scheduler["Scheduler / timer"]

    ops_ui["Ops Dashboard\nReact/Vite on :4173"]
    merchant_ui["Merchant Dashboard\nReact/Vite on :4174"]
    api["FastAPI backend\n/v1 APIs on :8000"]
    db["PostgreSQL\nmini_payment_gateway"]
    merchant_webhook["Merchant webhook URL"]

    admin --> ops_ui
    merchant_user --> merchant_ui
    merchant_backend --> api
    provider --> api
    scheduler --> api
    ops_ui --> api
    merchant_ui --> api
    api --> db
    api --> merchant_webhook
```

The system has three user-facing API surfaces:

| Surface | Actor | Auth model | Main purpose |
| --- | --- | --- | --- |
| Merchant API | Merchant backend | HMAC headers | Create/query payments and refunds. |
| Ops API | Admin/Ops user | Internal HttpOnly session cookie | Operate merchants, users, reconciliation, webhooks, and audit workflows. |
| Merchant Portal API | Merchant portal user | Merchant HttpOnly session cookie | Read merchant-scoped dashboard data and change own password. |

Provider callbacks and scheduler-triggered jobs are separate system inputs. They
do not use the merchant dashboard session or merchant HMAC credentials.

## Runtime Containers

```mermaid
flowchart TD
    subgraph browser["Browsers"]
      ops_browser["Ops Dashboard UI"]
      merchant_browser["Merchant Dashboard UI"]
    end

    subgraph backend["FastAPI backend"]
      controllers["Controllers\nFastAPI routers and dependencies"]
      schemas["Schemas\nrequest/response DTOs"]
      services["Services\nbusiness rules and workflows"]
      repos["Repositories\nSQLAlchemy queries"]
      models["Models\nSQLAlchemy entities and enums"]
    end

    migrations["Alembic migrations"]
    db["PostgreSQL"]

    ops_browser --> controllers
    merchant_browser --> controllers
    controllers --> schemas
    controllers --> services
    services --> repos
    services --> models
    repos --> models
    repos --> db
    models --> db
    migrations --> db
```

The frontend apps are separate containers in sandbox deployment:

- `ops-dashboard` serves the internal UI on port `4173`.
- `merchant-dashboard` serves the merchant portal UI on port `4174`.
- Both proxy `/api` to the FastAPI backend in local and container deployment.

## Trust Boundaries

```mermaid
flowchart LR
    subgraph public_merchant["Merchant integration boundary"]
      merchant_backend["Merchant backend"]
    end

    subgraph internal_ops["Internal operations boundary"]
      admin["Admin / Ops"]
      ops_ui["Ops Dashboard"]
    end

    subgraph merchant_portal["Merchant portal boundary"]
      merchant_user["Merchant user"]
      merchant_ui["Merchant Dashboard"]
    end

    subgraph gateway["Mini Payment Gateway"]
      api["FastAPI backend"]
      db["PostgreSQL"]
    end

    merchant_backend -- "HMAC headers" --> api
    ops_ui -- "internal session cookie" --> api
    merchant_ui -- "merchant session cookie" --> api
    api --> db
```

Important boundaries:

- Merchant HMAC credentials are for server-to-server API calls only.
- Merchant Dashboard users are stored in `merchant_users` and login with a
  separate session cookie.
- Ops users are stored in `internal_users`; only `ADMIN` users can provision
  merchant portal users.
- Merchant Portal APIs never accept `merchant_id` from the client for scoping.
  The backend resolves merchant scope from the authenticated portal user.
- Raw credential secrets and plaintext generated passwords are never
  retrievable after the immediate create/reset response.

## Component Responsibilities

| Component | Responsibility |
| --- | --- |
| Ops Dashboard | Internal workflow UI for merchant lifecycle, credentials, reconciliation, audit, internal users, and merchant portal user provisioning. |
| Merchant Dashboard | Read-only merchant portal for overview, analytics, payments, refunds, webhooks, profile, credentials, and password change. |
| Controllers | Define routes, dependencies, auth boundaries, and response models. |
| Services | Enforce payment, refund, webhook, auth, merchant lifecycle, audit, and analytics rules. |
| Repositories | Own focused SQLAlchemy aggregate and lookup queries. |
| Models | Define tables, enums, relationships, constraints, and indexes. |
| Alembic | Applies database schema changes before backend restart in sandbox deploy. |

## Key Request Flows

### Merchant Creates A Payment

```mermaid
sequenceDiagram
    autonumber
    participant Merchant as Merchant backend
    participant API as FastAPI controller
    participant Auth as HMAC auth service
    participant Payment as Payment service
    participant DB as PostgreSQL

    Merchant->>API: POST /v1/payments with HMAC headers
    API->>Auth: verify merchant id, access key, timestamp, signature
    Auth->>DB: load merchant and active credential
    DB-->>Auth: merchant context
    API->>Payment: create payment with authenticated merchant
    Payment->>DB: create or reuse order/payment rows
    DB-->>Payment: payment transaction
    Payment-->>API: response DTO
    API-->>Merchant: payment id, status, QR payload
```

### Admin Provisions A Merchant Portal User

```mermaid
sequenceDiagram
    autonumber
    participant Admin as Admin user
    participant OpsUI as Ops Dashboard
    participant API as Ops API
    participant Service as Merchant portal user admin service
    participant DB as PostgreSQL

    Admin->>OpsUI: create or reset merchant portal user
    OpsUI->>API: /v1/ops/merchants/{merchant_id}/portal-users
    API->>API: require internal ADMIN session
    API->>Service: create/reset/update scoped merchant user
    Service->>DB: write merchant_users and audit_logs
    DB-->>Service: persisted user
    Service-->>API: generated password only for this response
    API-->>OpsUI: user metadata and one-time password
```

### Merchant Reads Analytics

```mermaid
sequenceDiagram
    autonumber
    participant User as Merchant portal user
    participant UI as Merchant Dashboard
    participant API as Merchant Portal API
    participant Service as Merchant portal service
    participant Repo as Analytics aggregate queries
    participant DB as PostgreSQL

    User->>UI: open Analytics and choose 7d, 30d, or 90d
    UI->>API: GET /v1/merchant-portal/analytics?days=30
    API->>API: authenticate merchant session cookie
    API->>Service: analytics for current merchant user
    Service->>Repo: aggregate payments, refunds, webhooks by day
    Repo->>DB: merchant-scoped grouped queries
    DB-->>Repo: aggregate rows
    Repo-->>Service: series and totals
    Service-->>API: zero-filled date buckets
    API-->>UI: chart/table response
```

## Out Of Scope For The Current Implementation

The current branch does not implement settlement, disputes, accounting ledger,
multi-provider routing, multi-currency support, merchant self-service
onboarding, CSV export, or realtime analytics polling.
