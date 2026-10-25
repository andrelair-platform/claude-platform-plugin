---
name: test-pyramid-setup
description: >
  Set up the org test pyramid (L0–L4) for a repo — directory layout, make targets, the
  mock-free integration/contract layers, and the CI jobs. Use WHEN adding tests to a repo,
  wiring the test CI, setting up testcontainers/service-container integration tests, or deciding
  which layers a repo needs. Triggers on: tests, test pyramid, L0 L1 L2 L3 L4, pytest, testcontainers,
  contract test, coverage, make test, CI test jobs.
---

# Set up the test pyramid (L0–L4)

Authoritative constraint: `.claude/rules/testing.md` (the 5 layers, the tier→required-layers mapping, the
**mock-discipline** rule, and "unit-only is the anti-pattern"). This skill is the setup how-to. The live
**QA gate** (L5) is a separate backstop → the `prod-promotion-qa-gate` skill. Reference: `minicloud-erpnext`.

## Which layers does THIS repo need? (from the tier, non-negotiable)
- **Tier A — business logic** (services, domain apps): **L0→L4 full.** Unit-only is NOT Done and MUST NOT promote.
- **Tier B — infra code** (gitops/opentofu/ansible): L0, L2 (plan/dry-run), L4 (ArgoCD diff).
- **Tier C — UI/docs:** L0, L1, L4 (Playwright). **Tier D — tooling/ops:** L0, L1.

## The mock discipline (the core lesson — bake it in)
A mock encodes an **assumption** about a collaborator; if wrong, the unit test stays green while prod fails
(the RFC3339 datetime + the alembic-disabled-logging bugs). **Every mocked boundary MUST be backed by an
L3 contract test or an L2 real integration** that validates the assumption against the actual collaborator.
A boundary that is only ever mocked is untested.

## Directory layout (every repo)
```
tests/
  unit/         # L1 — pure logic, no external deps
  integration/  # L2 — real DB/queue (testcontainers or a CI service container)
  e2e/          # L4 — smoke against real infra
  fixtures/     # shared factories — never inline large data blobs
```
Conventions: `make test` = L1 (no Docker/network, <5min); `make test-integration` = L2 (Docker). Coverage
**70%** on business-logic files. Test filenames mirror the module. No `# noqa`/`// nolint` without a reason.

## CI gate mapping
```
dev push    →  L0 + L1                     (~5 min)
PR → main   →  L0 + L1 + L2 + L3 + L4       (blocking; the prod gate)
```
Fail-fast: L0 before L1 before L2 (never spin up a DB if lint fails).

## L2 real-Postgres pattern (prefer a CI service container — deterministic)
Prefer a **GitHub Actions service container** via `TEST_DATABASE_URL` (testcontainers' `get_connection_url`
flaked on the runner); fall back to testcontainers locally; **skip** cleanly when neither is present so a
bare L1 env stays green. Migrate with the app's REAL path (`alembic upgrade head`, not `create_all`).
Pin Postgres **17** everywhere (CNPG parity). A destructive L2 that DROPs the schema MUST refuse to run
unless the URL is an obviously-disposable test DB (localhost + a name containing `test`).

## Language matrix (L0 / L1 / L2 / L3 / L4)
Python-FastAPI: ruff+mypy / pytest / pytest+testcontainers / schemathesis / httpx. Go: golangci-lint /
go test / go test+testcontainers / openapi-validator / curl. TS: eslint+tsc / vitest / vitest+MSW / — / Playwright.
Helm: yamllint+kubeconform / helm lint / helm template+kube-score / — / ArgoCD diff.

## L3 contract — validate YOUR calls against the collaborator's REAL contract
Generate from the collaborator's committed `openapi.yaml`; a contract test must fail pre-merge on wire-format
drift (the RFC3339 class). Reference backfill: `ktayl-underwriting` (L2 + L3 against the policy-service OpenAPI + L4 smoke).
