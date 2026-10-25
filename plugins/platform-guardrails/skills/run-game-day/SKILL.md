---
name: run-game-day
description: >
  Run a reliability Game Day (induced failure) end-to-end and write the postmortem, or add a
  new failure scenario / SLO. Use WHEN exercising a failure scenario, inducing a DB/broker/node
  outage, running a DR drill, measuring MTTR/RPO/RTO, or writing a postmortem. Triggers on:
  game day, chaos, induced failure, postmortem, SLO, error budget, RTO, RPO, DR drill, MTTR.
---

# Run a Game Day (induce → measure → postmortem)

Authoritative constraint: `.claude/rules/reliability-and-gamedays.md` (every prod-grade service declares
an SLO contract; the scenario catalog; every Game Day ends in a postmortem — an induced failure with no
write-up is wasted evidence). This skill is the how-to + the postmortem template. Built on Chaos Mesh +
Velero/CNPG/raft backups + Prometheus/Grafana/Loki + the controller `sdlc_loop`.

## The loop (every scenario)
`Detect → Diagnose → Mitigate → Recover → Measure → Postmortem`. **Induce on dev first**; a prod Game Day is
deliberate + announced. **Run the simulator DURING the incident** so MTTR / RPO / RTO / error-rate are
**real measured numbers**, not estimates. **Stop condition:** any volume/DB at 0 usable copies → abort, restore.

## Scenario catalog (induce-with → expected behaviour)
| # | Scenario | Induce | Hypothesis |
|---|---|---|---|
| 01 | baseline | simulator | SLOs green; KPIs captured |
| 02 | traffic ×10 | simulator burst | KEDA autoscale / graceful degrade, no 5xx storm |
| 03 | DB down 15m | Chaos Mesh / scale CNPG to 0 | degrade cleanly, alerts fire, recover, **no data loss** |
| 04 | NATS down | Chaos Mesh | JetStream persists, consumer lag → KEDA scales, backlog drains |
| 05 | bad deploy | push a broken image | canary/BlueGreen analysis **auto-aborts**, no bad version serves |
| 06 | security | leaked secret / rogue workload | Gatekeeper denies / rotate via Vault+ESO; audit shows it |
| 07 | AI failure | LLM down / bad answers | gateway fallback; eval catches regression; human-escalation |
| 08 | DR | destroy a node/cluster | restore from Velero/CNPG/raft (+ R2 off-site) within **RTO**; verify **RPO** |

## Postmortem template (blameless — `docs/reliability/postmortems/<date>-<slug>.md`)
```
# Postmortem — <title>  (<date>, induced | real)
Summary        what happened, impact, duration (one paragraph).
SLO impact     which SLI breached, error-budget burned, MTTR.
Timeline       detect → diagnose → mitigate → recover (timestamps).
Root cause     the actual layer + why (not the symptom).
What worked    the controls/automation that helped.
What didn't    gaps (missing alert, slow runbook, wrong assumption).
Action items   concrete fixes, each an owner + issue link.
Evidence       graphs, logs, kubectl output, the restore proof.
```
A postmortem is a **proof-catalog entry** (`evidence-and-proof.md`) — the clearest "operate under failure" signal.

## Discipline
Modest, honest SLOs (a met lab target beats a faked 99.99%). Every Game Day ends in a postmortem + an
updated KPI scorecard. Don't double-count the gates: CI proves code, the QA gate proves the live dev
service, this proves it **under failure** — distinct evidence. For a DR drill, the off-site restore path is
the `offsite-dr-backup` skill; the OCI restore target is the different-site anchor.
