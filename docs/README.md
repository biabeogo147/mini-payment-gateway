# Documentation Map

This directory is organized by reader intent. Start here instead of scanning
historical phase files.

## For Developers

1. `getting-started/local-setup.md` - local environment and first run.
2. `architecture/system.md` - system context, trust boundaries, and dashboard
   architecture.
3. `architecture/backend.md` - backend layers and request flow.
4. `api/README.md` - API contract index.
5. `testing/README.md` - scenario and test coverage map.

## For Operators And Demo Runs

- `infrastructure/README.md` - infrastructure entrypoint and source-of-truth
  map for setup, operations, and infra-aware development.
- `infrastructure/devops-architecture.md` - internal DevOps topology and
  pipeline design for the backend and both internal dashboards.
- `infrastructure/sandbox-setup-from-zero.md` - detailed setup guide from a
  fresh server to a live sandbox CI/CD host.
- `infrastructure/sandbox-deployment.md` - sandbox CI/CD runner and deployment
  runbook for deploy, verify, rollback, and troubleshooting.
- `infrastructure/sandbox-access-inventory.md` - sandbox account, runner,
  secret-location, and published-port inventory.
- `getting-started/runbook.md` - smoke scripts and full demo flow.
- `getting-started/vietqr-pilot-demo.md` - instructor-facing VietQR pilot demo
  guide with dashboard, Postman/Newman, smoke, and sandbox commands.
- `getting-started/e2e-payment-demo.md` - preferred visible end-to-end demo from
  first Admin bootstrap through merchant checkout webhook result.
- `service-operations/merchant-onboarding-sop.md` - merchant lifecycle
  workflow.
- `service-operations/webhook-retry-sop.md` - failed webhook handling.
- `service-operations/reconciliation-sop.md` - reconciliation review and
  resolution.

## For Product Context

- `product/scope.md`
- `product/business-flow.md`
- `product/requirements.md`
- `product/modules-and-entities.md`
- `product/state-machine.md`
- `product/use-cases.md`
- `product/user-stories.md`
- `product/ui-design.md`

## For Presentation Prep

- `presentation/intro-to-se-slide-outline.md` - slide outline matched to the
  Intro to Software Engineering presentation requirements.

## For Historical Context

- `history/README.md` - roadmap and phase archive.
- `history/phases/` - implementation phase plans.
- `history/completions/` - phase completion records.

## Source Of Truth

- Current API behavior: `api/`
- Current architecture: `architecture/`
- Current verification map: `testing/`
- Current infrastructure operations: `infrastructure/`
- Current service operations: `service-operations/`
- Demo runbook: `getting-started/runbook.md`
- Why a phase happened: `history/`
