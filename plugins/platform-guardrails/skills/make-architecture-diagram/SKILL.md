---
name: make-architecture-diagram
description: >
  Build or regenerate an architecture topology poster or C4 container view as code
  (mingrammer `diagrams` + Graphviz). Use WHEN creating/updating the platform topology
  diagram or a product's C4 context/container diagram, adding vendor icons, or wiring the
  diagram-refresh CI. Triggers on: diagrams-as-code, mingrammer, Graphviz, C4, topology
  poster, platform_overview, container diagram, architecture diagram, vendor icon.
---

# Make an architecture diagram (diagram-as-code)

Authoritative constraint: `.claude/rules/diagrams-as-code.md` (WHEN to use it vs Mermaid/tbls; the
"a diagram must communicate" quality bar; commit both png+svg). This skill is the how-to. References:
`minicloud-platform-docs/diagrams/src/platform_overview.py` (whole platform) · `retrieva/docs/diagrams/`
(C4, Docusaurus product) · `ktayl-core/docs/diagrams/` (C4, plain-docs product).

## Where source + output live
- **Whole-platform:** `minicloud-platform-docs/diagrams/` (`requirements.txt`, `Makefile`, `src/_theme.py`,
  `src/platform_overview.py`, `fetch-icons.sh`, `src/icons/`) → `static/img/architecture/*.{png,svg}`.
- **Per-product C4:** in the **product's OWN repo**, self-contained (`<repo>/docs/diagrams/<name>_container.py`
  + `requirements.txt` + `icons/` + an inlined theme, no cross-repo import). Output → Docusaurus product
  `docs/static/img/architecture/`; plain-docs product `docs/architecture/img/`.
- **Commit both `.png` AND `.svg`** (GitHub Pages/README serve them with no build-time Graphviz; `dot` is a system dep, never pip).

## Build steps
1. `requirements.txt` = `diagrams>=0.24,<0.25`; system dep `brew install graphviz` / `apt-get install -y graphviz`.
2. Model with the **closest real node**: `diagrams.k8s.*`, `diagrams.onprem.*` (groupware/database/gitops/registry/security/monitoring/queue), `diagrams.programming.{framework,language}`, `diagrams.saas.*`, `diagrams.generic.*`. `Cluster` = a layer/trust boundary; `Edge`/`>>` = labelled flows.
3. **Icon-fallback helper (the key pattern):** ~25 components have no built-in icon (Kargo, KEDA, Longhorn, Authentik, Langfuse, LiteLLM, Qdrant, Tailscale, Stripe…). `node(FallbackClass, label, icon="name.png")` renders a vendored PNG from `icons/` if present, else the closest **semantic** built-in — the **label is authoritative**. Upgrade fidelity later by dropping a PNG in `icons/`; no code change.
4. **Vendor logos** via `fetch-icons.sh`: GitHub org avatars (`github.com/<org>.png?size=256`) + CNCF artwork raw PNGs. Best-effort + idempotent; a failed download keeps the fallback.
5. `Diagram(..., outformat=["png","svg"], show=False, graph_attr=…)` → the docs static tree. Embed **SVG** in docs pages, **PNG** in READMEs.

## Make it COMMUNICATE (the quality bar — enforced)
- **Every edge carries a VERB** from the fixed vocabulary (`provisions·configures·reconciles·builds·pushes·promotes·supplies-secrets·issues-certs·routes-traffic·authenticates·scrapes·ships-logs/traces·backs-up·scales·routes-to-LLM`). **Solid = principal flow · dashed = backing dependency.** Put a legend on the page.
- **No invented edges** — base every relationship on the **actual manifests/config** (verify in `minicloud-gitops`). Known-wrong edges to avoid: `ESO→ArgoCD` is inverted (Vault→ESO writes Secret→workloads); `Longhorn→MinIO` is false (**Velero** backs up to MinIO, off-cluster `10.0.0.1:9000`, + R2); MetalLB removed (**Cilium** = CNI + LB `10.0.0.200`); Cilium/Gatekeeper/Falco are substrates not per-node edges; alert sink = SES email + Slack.
- **Light/high-contrast theme** (white bg, dark text, bold edges, ≥13pt) — dark bg hides dashed edges + prints badly.
- **Altitude — complementary views, don't cram:** Capability view (Mermaid, ~8–12 groups) + Technology Topology (mingrammer) + Physical/Deployment (nodes/roles/placement/failure-domains). Mark the logical topology *logical* (capability map, not a liveness claim).

## CI
`update-architecture-diagrams.yml` = regenerate-and-open-a-bot-PR-on-change (NOT a hard gate — Graphviz output isn't byte-identical across `dot` versions → a strict gate flakes). **Merge the first bot refresh once** to make CI's render canonical → converges. `make check` = local same-environment drift check.

## Gotchas (proven)
- **`gh pr create --body "…"` runs backtick command-substitution** → any `` `path` `` in the body is replaced by command output. Use **`--body-file`**.
- **SVGs are NOT self-contained** — Graphviz emits `<image xlink:href="/abs/local/path.png">` → broken on GitHub Pages + leaks your local path. Post-process every local `xlink:href` → base64 data URI (`embed-svg-images.py`, idempotent, last step of `make generate`); verify `grep -c '/Users/' <svg>` == 0. PNG has no such issue.
- `diagrams` has **no `__version__`** → `importlib.metadata.version('diagrams')`. `diagrams.custom.Custom` needs a **PNG** (not SVG). `github.com/cloudflare.png` isn't a PNG → keep the built-in Cloudflare node.
- **retrieva/retrieva-backend enforce husky + commitlint** (`body-max-line-length=100`, lowercase subject, no trailing period) + a required `CI Success` check (even `--admin` can't bypass an *expected* check → wait for CI, squash-merge).
- Per-product placement ⇒ **one PR per repo** (central + each product); no single cross-repo PR.
