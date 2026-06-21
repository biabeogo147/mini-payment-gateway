# Sandbox Demo Reset Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single guarded command that backs up and resets sandbox demo data while preserving migrations and restoring services.

**Architecture:** A host-side Bash script orchestrates existing Compose services and PostgreSQL tools. A Python unittest harness replaces Docker and curl with deterministic fakes so destructive behavior is verified without touching a real database.

**Tech Stack:** Bash, Docker Compose, PostgreSQL `pg_dump`/`psql`, Python `unittest`.

---

### Task 1: Test and implement the reset orchestration

**Files:**
- Create: `backend/tests/test_reset_sandbox_demo_script.py`
- Create: `deploy/reset_sandbox_demo.sh`

- [ ] Write tests that reject missing confirmation and non-sandbox `.env`.
- [ ] Run the focused tests and verify they fail because the script is absent.
- [ ] Add happy-path assertions for backup, stop, truncate, restart, health, and `alembic_version` preservation.
- [ ] Add a failure-path assertion proving services restart when psql fails.
- [ ] Implement the minimal Bash script to satisfy the tests.
- [ ] Run focused tests and `bash -n deploy/reset_sandbox_demo.sh`.

### Task 2: Document and verify server usage

**Files:**
- Modify: `docs/getting-started/e2e-payment-demo.md`
- Modify: `docs/infrastructure/sandbox-deployment.md`

- [ ] Add the exact server reset command and destructive-data warning.
- [ ] Document backup location, expected bootstrap state, and recovery behavior.
- [ ] Run the complete backend suite, shell syntax checks, and `git diff --check`.
- [ ] Commit, push, and open a pull request into `main`.
