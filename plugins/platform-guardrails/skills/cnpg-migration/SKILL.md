---
name: cnpg-migration
description: >
  Migrate a raw/vendor Postgres (plain StatefulSet) onto its own CloudNativePG cluster, at
  parity, with a safe cutover. Use WHEN moving a DB to CNPG, adding HA/PITR to a single-instance
  Postgres, or choosing how a new Postgres should run. Triggers on: CNPG, CloudNativePG,
  cnpg migration, Postgres HA, barman, PITR, pg_dump restore, DATABASE_HOST cutover, datastore.
---

# Migrate a Postgres onto CloudNativePG (at parity, safe cutover)

Authoritative constraint: `.claude/rules/datastore-selection.md` (**CNPG is the default** for every
Postgres; the 10-second "incident-or-shrug" test decides CNPG vs plain-STS; the App-HA-1r tier =
2 instances × Longhorn RF1). Full playbook + gotcha history: memory [[reference_cnpg_migration_playbook]].
This skill is the migration how-to. Reference migrations: Langfuse (first), Synapse (C-collation +
stateful-RWO incident), ktayl-iam / ktayl / retrieva / policy-service (the 2026-10-17 prod sweep).

## The 4-phase migration (additive → parity → cutover → bake-gated cleanup)
1. **Additive** — stand up a NEW `Cluster` (2 instances, R2 PITR for prod) *alongside* the live STS. Bake
   the **same-namespace `:5432` NetworkPolicy in from the start** (the ktayl #1818 lesson — else the app
   can't reach `-rw`). Wait for **healthy 2/2** (watch for a 1/2 stall).
2. **Parity** — quiesce writes → `pg_dump` the STS → restore into CNPG → verify row/table parity
   (count tables, spot-check). `--clean` restore errors on migration-bookkeeping tables
   (`__drizzle_migrations`, etc.) are **non-fatal**. An 18→17 Prisma dump restores clean.
3. **Cutover** — repoint the app's DB host `-rw`:
   - **values flip** (`DATABASE_HOST`) when the DSN is in plain values (iam).
   - **ESO host-rewrite** when the DSN lives in a Vault path needing break-glass root (`secret/platform/*`):
     the app's ExternalSecret `target.template` rewrites `<old-host>`→`<cnpg>-rw` (`mergePolicy: Merge`;
     `index . "database-url"` for a hyphenated key). **Gotcha:** adding a `template` to a *live* ES is an
     **ArgoCD-SSA no-op** → **delete the ES** so it recreates WITH the template (secret re-renders rewritten).
   - Follow-up (non-urgent): update the Vault DSN host + remove the ES template (Vault back to single source).
4. **Cleanup (bake-gated)** — keep the old STS until a soak passes, then retire it to reclaim the volume.

## Gotchas (proven)
- **CNPG socket is peer-auth** → always connect over **TCP `-h <svc>`**, never the unix socket.
- **Managed-role password drift after a failover/recovery** — CNPG skips re-applying (resourceVersion
  already "reconciled") → app "password authentication failed" though the secret is right. Fix: `ALTER ROLE`
  to the secret value via the peer-auth superuser (SQL on stdin; `:'pw'` fails under `-c`). [[feedback_cnpg_managed_role_password_drift]]
- **ArgoCD `$values`/multi-source app** may need a **hard refresh** nudge to pick the new cluster.
- **Postgres EIO "could not open file … Input/output error (58030)"** while robustness=healthy = **stale
  Longhorn mount**, NOT corruption → `kubectl delete pod` to remount (data intact), before any restore. [[feedback_postgres_eio_stale_mount]]
- **WAL/backup retention when repointing barman** — keep old WALs until all replicas healthy, else a
  diverged replica's `pg_rewind` breaks ([[feedback_cnpg_repoint_wal_retention]]). `aws` needs `AWS_DEFAULT_REGION=auto` for R2.
- **R2 PITR is PROD-only** (dev needs no off-site). Prove restore via a throwaway-ns recovery from R2 ([[feedback_cnpg_backup_restore_ops]]).

## RF placement (datastore-selection.md)
CNPG 2-instance → **Longhorn RF1 each** (App-HA-1r: app-layer redundancy, minimal block churn), on 2
distinct storage-healthy nodes (anti-affinity). Don't stack RF3 under 2 CNPG instances (over-replicates + churns).
