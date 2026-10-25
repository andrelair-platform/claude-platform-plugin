---
name: longhorn-incident-recovery
description: >
  Recover Longhorn storage after a node reboot / power loss / mass-drain, or diagnose
  volumes stuck degraded, faulted, oscillating, or not rebuilding. Use WHEN Longhorn
  shows degraded/faulted volumes, rebuilds won't complete, a volume won't attach, after
  a controller/node power incident, or minicloud-recovery-check reports Longhorn FAILED.
  Triggers on: Longhorn degraded, faulted, ReplicaSchedulingFailure, stuck rebuild,
  Multi-Attach, instance-manager, replica-auto-balance, node cordon/uncordon, storage recovery.
---

# Longhorn incident recovery — forensics first, ONE reversible lever, watch (don't poke)

Authoritative source: `minicloud-gitops/docs/storage-hardening/` (**read `phase1-execution-plan.md`
FIRST**) + memories [[feedback_longhorn_recovery_dont_poke]], [[reference_longhorn_stuck_rebuild_113_resolution]],
[[feedback_longhorn_stale_rofs_after_churn]], [[reference_longhorn_rebuild_benchmark]],
[[feedback_rwo_longhorn_pattern]]. This skill is the decision tree + the anti-patterns.

## The discipline (the hard-won rule — violating it CAUSED a secondary incident 2026-10-24)
1. **Read `docs/storage-hardening/` first.** The resolution is often already written down.
2. **Read-only forensics before ANY mutation** — separate evidence from hypothesis.
3. **ONE reversible lever, then WATCH ≥15 min.** Rebuilds finalize on a DELAY → re-check the live
   count before ever calling it "stuck." Never stack actions.
4. **Settings are ArgoCD-managed → change via PR, never `kubectl patch`** (selfHeal reverts a live edit).

## Data-safety gate FIRST (tells you how much time you have)
```
kubectl get volumes.longhorn.io -n longhorn-system -o json | python3 -c \
"import sys,json;from collections import Counter;print(dict(Counter(v['status'].get('robustness') for v in json.load(sys.stdin)['items'])))"
```
- **`faulted: 0`** and no volume at 1 usable replica → **SAFE**. A degraded (2-of-3) volume is redundant,
  **not** an emergency. Do NOT bulk-delete toward a fix. Only a volume at **0 usable replicas** is an
  emergency → STOP, restore from backup (R2/MinIO), abort the plan.

## Diagnostic decision tree (match the symptom, apply the ONE fix)
| Symptom | Root cause | The ONE fix |
|---|---|---|
| degraded + **0 stopped replicas** + `Scheduled=False · ReplicaSchedulingFailure · "disks are unavailable"` | **NODE-ELIGIBILITY EXHAUSTION** — RF3 needs 3 distinct schedulable nodes; one is cordoned/fenced/already-holding | **`kubectl uncordon <node>`** (restore an eligible node). NOT delete replicas. (k8s cordon blocks Longhorn via `disable-scheduling-on-cordoned-node=true` even if the Longhorn-node `allowScheduling=true`.) |
| degraded + **stopped replicas with `rebuildRetryCount=5`** + `failedAt` set | retry exhaustion — Longhorn gave up | delete the **retry-exhausted stopped** replicas (each with a healthy running sibling) → fresh replica, retry resets |
| degraded **oscillating** (count climbs/falls) + an instance-manager restarting | a node/IM problem (disk EIO, or IM missing its liveness probe under load) | **fence that node** (`kubectl cordon` + Longhorn `allowScheduling=false`); diagnose its disk (SMART on the real disk, not the iSCSI virtual devices) |
| rebuild reaches ~99% then fails `replica is not in mode WO: RW` | engine WO:RW bug (Longhorn ≤1.12.1) | upgrade the chart (≥1.13.0) + enable `concurrent-automatic-engine-upgrade-per-node-limit` |
| pod `ContainerCreating` + `Multi-Attach error` (RWO vol) | pod scheduled off the node holding the RWO volume | cordon-all-but-the-volume-holder → delete the stuck pod → it converges onto the holder → uncordon ([[feedback_rwo_longhorn_pattern]]) |

## Anti-patterns (these CAUSE churn / deadlock — do NOT)
- **Bulk-deleting replicas** or **fencing nodes** reactively → removes eligible nodes → `ReplicaSchedulingFailure` deadlock.
- **`concurrent-replica-rebuild-per-node-limit: 1`** → a single stuck rebuild deadlocks the node's slot. Tuned value is **2**.
- **Live-patching `01-settings.yaml` settings** → ArgoCD reverts it (drift). PR only.
- **`replica-auto-balance` must stay `disabled`** — `least-effort`/`best-effort` LOOK inert on a static
  topology but **THRASH the moment a node is re-admitted** (transient faulted blips on prod DBs). De-concentrate
  replicas via **targeted, observed manual relocation**, never auto-balance.

## Gotchas
- **"EXT4 EIO" on `sda`/`sdi`/… is usually NOT disk failure** — those are iSCSI-attached Longhorn *virtual*
  devices; many erroring at the same instant = the node's instance-manager was killed (verify the real disk,
  e.g. `nvme0n1`, with `smartctl`/`nvme smart-log`). The 10s IM liveness probe can be too tight under heavy
  rebuild load → it's extended to 30s (`instance-manager-pod-liveness-probe-timeout`).
- **`ReadonlyFilesystem=True` NPD latch** is often **stale** after churn — check for actual `ro` mounts; empty = stale (no reboot needed), restart NPD.
- **Re-admitting a fenced node is NOT zero-impact** — it triggers Longhorn engine-ownership redistribution →
  affected volumes briefly detach/reattach → consuming stateful pods bounce ONCE (clean). Do it in a quiet window.
- **RF policy** (`datastore-selection.md`): app-HA stores (CNPG 2-instance, Vault Raft, NATS JS) → RF1;
  single-copy durable → RF2 (never below 2); dev/regenerable → RF1. New-volume default = `default-replica-count: 2`.

## Verify recovery (don't declare done early)
- `degraded = 0` AND `faulted = 0` stable for **≥4 consecutive polls / 15 min**, 0 active rebuilds.
- Live-query the prod DBs that were affected (`SELECT 1` on each CNPG primary) — serving, not just "CNPG says healthy".
- `ssh controller "minicloud-recovery-check"` → Longhorn ✓.
