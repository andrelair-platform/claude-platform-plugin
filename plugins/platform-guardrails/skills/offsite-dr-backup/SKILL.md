---
name: offsite-dr-backup
description: >
  Add an off-site (3-2-1) copy of an on-cluster/controller backup store to Cloudflare R2 and
  VERIFY a restore from it. Use WHEN a backup lives single-site (same room/failure domain),
  wiring off-site DR, or proving a restore from R2. Triggers on: off-site backup, DR, 3-2-1,
  R2 mirror, Longhorn backup, Velero, restore verification, room-level loss, DORA Art. 11.
---

# Off-site DR backup → R2 (+ verified restore)

Authoritative context: `.claude/rules/cloud-adoption.md` (R2 = always-free, zero-egress, the off-site tier)
+ `.claude/rules/reliability-and-gamedays.md` (DR scenario 08). Controller specifics (aliases, buckets,
the systemd timer) live in the **private** `platform-ops-runbooks` skill. Reference build: Longhorn→R2
(gitops #1936, 2026-10-24).

## The principle
A backup that sits only in the controller's **local MinIO** is in the **same room / failure domain** as the
cluster — a room-level loss (power/fire/theft) takes it too. The fix is a **3-2-1 off-site copy on R2**
(different provider; the same R2 account CNPG/barman already uses). **CNPG prod DBs already PITR to R2
natively** — this pattern covers the MinIO-only stores (Longhorn backups, kine/vault snapshots).

## Design: MIRROR, don't switch
- **Leave the working backup target untouched** (don't switch/multi-target the live Longhorn `BackupTarget`).
  Mirror the MinIO backup bucket → R2 → zero risk to the proven path; `mc mirror` preserves the exact
  backupstore structure so R2 is restore-valid.
- **`mc mirror --overwrite --remove`** so R2 tracks the source's *managed* retention EXACTLY (Longhorn
  manages its own block-chain retention; naive age-pruning R2 would corrupt incremental chains).
- **SAFETY guard:** abort the mirror if the source bucket is suspiciously empty (`< MIN_SRC_OBJECTS`) — a
  wiped/broken primary must not propagate a delete to the only off-site copy.
- **Run it off-cluster** (controller systemd timer, as the user owning the `mc` aliases) — DR tooling must
  work when the cluster is down, and MinIO is controller-local. Schedule *after* the primary backup settles.

## Verify a restore FROM R2 (the acceptance test — don't skip)
1. Structural parity: R2 object/`cfg`/block counts == MinIO (diff = 0 only-in-source, 0 stale-on-R2).
2. Add a **temporary** read-only Longhorn `BackupTarget` → the R2 bucket + a cred secret (creds from the
   controller `mc` config, not echoed) → confirm `status.available: True` and that it **discovers the
   BackupVolumes** from R2.
3. Restore ONE small volume to a **scratch** PVC → confirm `restoreRequired: False`, `actualSize > 0`,
   `Restore` condition `False` (no error).
4. **Tear down** the scratch volume + temp target + temp secret; confirm the `default` target + prod volumes untouched.

## Gotchas
- `aws`/`mc` to R2: region is **`auto`** (`AWS_DEFAULT_REGION=auto`); R2 `ListBuckets` may return empty under a scoped token even though writes to a known bucket work — reuse the proven alias.
- The true **room-loss** test restores onto a **different site** (the OCI free node, `cloud-adoption.md`) — that's the Game Day (reliability-and-gamedays scenario 08), which this off-site copy unblocks.
- Longhorn backup blocks are an **incremental chain** — never age-prune the R2 bucket by hand; let `--remove` mirror the source's managed state.
