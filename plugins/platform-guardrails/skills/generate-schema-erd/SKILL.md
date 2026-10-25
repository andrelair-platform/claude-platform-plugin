---
name: generate-schema-erd
description: >
  Generate a tbls Mermaid ERD for a DB repo and wire the drift-check CI, or regenerate the
  committed baseline. Use WHEN a repo gains a relational schema, setting up docs/data-model/,
  adding the schema-erd-drift CI job, fixing false ERD drift, or generating an ERD for an
  adopted/vendor DB. Triggers on: tbls, ERD, schema drift, docs/data-model, schema-erd-drift,
  .tbls.yml, data model, erDiagram.
---

# Generate a schema ERD (tbls, drift-gated)

Authoritative constraint: `.claude/rules/schema-erd.md` (every DB repo MUST have this — it's a DoD gate).
Full gotcha history: memory [[reference_tbls_erd_driftcheck]]. This skill is the how-to. Reference CI jobs
to copy: `ktayl-core` (Flyway) · `ktayl-policy-service` (golang-migrate) · `ktayl-underwriting` (Alembic) ·
`ktayl-iam` (TypeORM) · `retrieva-backend` (Drizzle).

## The CI shape (self-contained — NO live cluster)
Ephemeral **Postgres service container** → **apply the repo's migrations** (per toolchain) → run
**digest-pinned tbls** `doc --force` → **`git diff --quiet docs/data-model`** (fail if the committed docs drifted).

## Apply the migrations — per toolchain
| Toolchain | Apply step in CI |
|---|---|
| **Flyway** (raw `V*.sql`) | `psql -f $(ls src/main/resources/db/migration/V*.sql \| sort)` (+ `CREATE SCHEMA`/`SET search_path` if schema-per-module) |
| **golang-migrate** (`*.up.sql`) | `psql -f $(ls db/migrations/*.up.sql \| sort)` |
| **Alembic** (Python) | `pip install .` → `alembic upgrade head` (reads `DATABASE_URL`) |
| **Drizzle** (`*.sql`) | `psql -f $(ls db/migrations/*.sql \| sort)` (`--> statement-breakpoint` is a comment → psql-safe) |
| **TypeORM** (TS, boot-run) | a **standalone `npm run db:migrate`** runner (`DataSource` + `.runMigrations()`, NO app boot) — never `node dist/main` |

## ⚠️ PIN EVERYTHING or you get false drift (`tbls` output is byte-exact — cost ~8 CI iterations once)
1. **tbls** — digest-pinned image `ghcr.io/k1low/tbls@sha256:0d90f07aed0c423a6012d542358c10b13fcdf15a1074ceee3d73676c87cc2f79` via `docker run --network host`. **Never** `setup-tbls@v1` (old version → SVG defaults → false drift).
2. **Explicit flags**, not `.tbls.yml` discovery — `tbls doc -t mermaid --sort -j`; generate the baseline with the **identical** flags.
3. **postgres:17.4** — tbls embeds `database_version`; pin the same image in CI **and** when generating the baseline.
4. **x86_64 baseline** — `database_version` also embeds CPU arch; generate the committed baseline on **x86_64** (controller or CI), **NOT an ARM Mac**.
5. **Gate with regenerate + `git diff`** (`tbls doc … --force` then `git diff --quiet -- docs/data-model`), NOT `tbls diff` (formats inconsistently across environments).

Net: same tbls digest + same pg17.4 + same arch (x86) + explicit flags → byte-identical regen → clean diff.

## `.tbls.yml` + layout
- `docPath: docs/data-model` · `er.format: mermaid` · `format.sort+adjust: true`.
- **Exclude the migration-bookkeeping table**: `flyway_schema_history` / `public.schema_migrations` / `public.alembic_version` / `public.migrations`.
- **Location:** `docs/data-model/` at repo root; monorepo → under the DB-owning component (`backend/docs/data-model/` + `backend/.tbls.yml`, run tbls from that dir). Ensure any CI `paths:` filter covers it.

## Baseline-generation recipe (one-off, on x86)
clone → ephemeral `postgres:17.4` → apply migrations (per toolchain) → digest-pinned tbls `doc … --force`
→ commit `docs/data-model/` + `.tbls.yml`. Docker-as-root leaves root-owned files in a mounted repo →
`chown` back (or generate into a user-owned clone) before `scp`.

## Surfacing (automatic — do nothing)
Committing `docs/data-model/README.md` makes the repo **auto-appear** on the central ERD index
(`minicloud-platform-docs/scripts/gen-erd-index.py`, weekly + on-demand). Do NOT hand-maintain the index
or duplicate the ERD into a per-repo `website/` (a build-time copy is the only sanctioned in-theme route).

## Adopted / vendor DB (no in-repo migrations)
Generate from the **live** DB with `minicloud-ops/scripts/db-erd/generate-erd.sh` (port-forward + tbls,
creds from the k8s secret at runtime). The SSO'd **Adminer** cockpit is the Day-2 browse/operate counterpart.

## The dbt / warehouse carve-out — do NOT force tbls
A dbt warehouse (derived medallion models, not a migration-owned schema) uses **committed model contracts
(`models/**/_*.yml` + `tests:`) + CI `dbt parse`** as its drift gate instead. Don't bolt tbls onto a dbt repo.
