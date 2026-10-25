---
name: wire-llmops
description: >
  Wire the per-product LLMOps template (dedicated Langfuse project, nested trace tree, managed
  prompts) for a product that calls an LLM. Use WHEN building/instrumenting a RAG, agent,
  assistant, or extraction feature, adding Langfuse tracing, or managing prompts. Triggers on:
  LLMOps, Langfuse, tracing, prompt management, RAG, agent, LLM observability, LiteLLM, generation.
---

# Wire per-product LLMOps (the golden path)

Authoritative constraint: `.claude/rules/llmops.md` (**any product that calls an LLM MUST wire this** —
it's not optional). Reference implementation: **retrieva** (all sections live). This skill is the how-to.
Two layers, one dedicated Langfuse project per product.

## 1. Dedicated Langfuse project + governed wiring
- Create the project in the Langfuse UI (provisioning API is EE-gated on OSS).
- Keys → Vault `secret/platform/langfuse/<product>` → ESO → backend env (`LANGFUSE_BASE_URL` = in-cluster svc, `LANGFUSE_PUBLIC_KEY`/`SECRET_KEY`).
- **Two-sided NetworkPolicy** (egress product→langfuse:3000 + langfuse `allow-app-tracing` ingress). Media also needs egress to the blob store (controller MinIO `10.0.0.1:9000`).

## 2. Nested trace hierarchy
`Trace` (per request) → `Span`s (business steps) → `Generation`s (LLM calls) → retrieval/DB as **child** spans (not a flat list). Core SDK manual spans (`langfuse-langchain` is incompatible with LangChain v1). Each `Generation` carries `model` + token usage (exact if returned, else `usageEstimated`). Null-safe self-nesting handle so disabled-mode is a no-op (retrieva `config/tracing.js`).

## 3. Session & user + env
Tag every trace with `sessionId` + `userId`. **dev+prod share ONE project**, distinguished by the native `environment` attribute from a per-overlay `LANGFUSE_TRACING_ENVIRONMENT` (image is env-agnostic; never a 2nd project per env; NODE_ENV can't be used).

## 4. Multi-modal (when non-text)
Log images/audio/function-call payloads as the **input of a generation**; the SDK uploads media to the blob store → needs the **host-scoped egress rule** (else `fetch failed`, only a broken ref logs). Best-effort; never fail the main flow.

## 5. Prompt management (MANDATORY — decoupled, label-routed)
- System prompts/few-shot/schemas live **in Langfuse**, not hardcoded; the Git copy is the **seed + runtime fallback** (Langfuse-first, fall back to the committed template — never a runtime SPOF).
- **Dynamic label routing** via per-overlay `LANGFUSE_PROMPT_LABEL` (**prod=`production`, dev=`latest`**) → zero-downtime rollout/rollback by relabelling, no redeploy.
- Mustache `{{var}}` via `prompt.compile()` with the declared variable set; render managed system text as a **literal** message. Pass the resolved prompt object as `prompt` on the generation → links the exact version (A/B + regression attribution). Enables the non-dev Playground.

## Gotchas (learned)
- **ESO SSA no-op:** adding keys to an existing ExternalSecret silently no-ops under ArgoCD SSA → **delete the ES** to force a fresh render.
- **LiteLLM team access = grant by model NAME** in `manifests/ai/40-key-seeder.yaml` (built-in groups don't auto-expand); re-run the seeder Job.
- **ClickHouse system logs (no TTL) fill the Langfuse PVC** → all traces dropped (code 243). Disable the query profiler; never put `<ttl>` on a system-log config element. [[feedback_langfuse_clickhouse_syslog_pvc_full]]
- Prod prompt/model promotion goes through the normal gate, never a manual hot-edit of prod.
