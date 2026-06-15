# Infrastructure Docs

This folder is organized by operational intent. Active docs are split into
system shape, day-0 setup, day-2 operations, and current sandbox facts.

## Active Docs

- `devops-architecture.md` - topology, trust boundaries, runtime shape, and
  CI/CD flow. Read this when you need to understand why the sandbox is wired
  this way.
- `sandbox-setup-from-zero.md` - day-0 provisioning from a fresh Ubuntu host to
  the first successful sandbox deploy.
- `sandbox-deployment.md` - day-2 deploy, verify, rollback, and troubleshoot
  runbook for the running sandbox.
- `sandbox-access-inventory.md` - current live host facts: account, runner,
  paths, published ports, secret names, and inspect commands.
- `archive/README.md` - historical-only notes that are no longer part of the
  active operating model.

## Reader Paths

- New sandbox host setup:
  `sandbox-setup-from-zero.md` -> `sandbox-access-inventory.md`
- Routine operations and recovery:
  `sandbox-deployment.md` -> `sandbox-access-inventory.md`
- Infra-aware development:
  `devops-architecture.md` -> this file

## Update Ownership

Use this map when code or runtime behavior changes:

| If you change | Update |
| --- | --- |
| workflow gates, CI jobs, or deploy flow | `devops-architecture.md`, `sandbox-deployment.md` |
| compose services, bind ports, auth/env keys, or runtime secret categories | `sandbox-setup-from-zero.md`, `sandbox-access-inventory.md` |
| bootstrap procedure, host prerequisites, or runner installation | `sandbox-setup-from-zero.md` |
| deploy commands, verification, rollback, or troubleshooting steps | `sandbox-deployment.md` |
| current host facts, runner labels/service, published ports, or secret locations | `sandbox-access-inventory.md` |
| historical rollout evidence | `docs/history/completions/`, `archive/` |

## Historical Only

Do not use `archive/` or `docs/history/completions/` as current operational
source of truth. They exist to preserve rollout context, not to replace the
active runbooks above.
