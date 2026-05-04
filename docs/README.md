# Documentation Map

This directory is organized by reader intent. Start here instead of scanning
historical phase files.

## For Developers

1. `getting-started/local-setup.md` - local environment and first run.
2. `architecture/backend.md` - backend layers and request flow.
3. `api/README.md` - API contract index.
4. `testing/README.md` - scenario and test coverage map.

## For Operators And Demo Runs

- `getting-started/runbook.md` - smoke scripts and full demo flow.
- `operations/merchant-onboarding-sop.md` - merchant lifecycle workflow.
- `operations/webhook-retry-sop.md` - failed webhook handling.
- `operations/reconciliation-sop.md` - reconciliation review and resolution.

## For Product Context

- `product/scope.md`
- `product/business-flow.md`
- `product/requirements.md`
- `product/modules-and-entities.md`
- `product/state-machine.md`
- `product/use-cases.md`

## For Historical Context

- `history/README.md` - roadmap and phase archive.
- `history/phases/` - implementation phase plans.
- `history/completions/` - phase completion records.

## Source Of Truth

- Current API behavior: `api/`
- Current architecture: `architecture/`
- Current verification map: `testing/`
- Current operations: `operations/` and `getting-started/runbook.md`
- Why a phase happened: `history/`
