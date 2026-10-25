---
name: github-board-ops
description: >
  Operate the product GitHub Projects boards with the gh CLI — set Status/Priority/Sprint on an
  issue, create a new product board from the template, or query a board's field/option IDs. Use
  WHEN updating an issue's board status, promoting an issue to a sprint, creating a product board,
  or scripting board fields. Triggers on: gh project, board status, Priority field, Sprint field,
  product board, project item-edit, board field IDs, gh project copy.
---

# GitHub Projects board ops (the gh CLI how-to)

Authoritative constraint/reference: `.claude/rules/github-projects.md` (the two-layer model, the
portfolio-of-products structure, **one Project per product, NO roll-up**, the product-board table, the
standard field schema, and the where-does-an-issue-go decision rule). This skill is the **command**
how-to; the policy stays in the rule.

## Create a new product board — ALWAYS from the template (MANDATORY)
```bash
gh project copy 26 --title "<name>" --owner andrelair-platform   # #26 = 🧩 Product Board Template
```
**Never `gh project create`** — a bare board has none of the standard schema/views and **cannot be
retro-fitted** (GitHub has no API to push views into an existing board; copy seeds them at creation).
Copy inherits fields + the 4 role-tailored views (NOT items, NOT the Burndown insight — recreate that one).
After copying: add the product's repos/namespaces + its row in the rule's *Product boards* table.

## Discover a board's field + option IDs (per board — there is no shared roll-up)
```bash
gh project view <n> --owner andrelair-platform --format json --jq .id          # board node id
gh project field-list <n> --owner andrelair-platform --format json             # fields + option ids
# Status field + its options specifically:
gh project field-list <n> --owner andrelair-platform --format json \
  | python3 -c "import sys,json;[print(f['id'],f['name'],[o['name'] for o in f.get('options',[])]) for f in json.load(sys.stdin)['fields'] if f['name']=='Status']"
```

## Set a field value on an issue/item
```bash
gh project item-edit --id <ITEM_ID> --project-id <BOARD_NODE_ID> \
  --field-id <STATUS_FIELD_ID> --single-select-option-id <OPTION_ID>
```
- **Status flow** (Scrum): `Backlog → This Sprint → In Progress → Blocked → In Review → Done`.
- **Promoting to active work:** set **Priority** (P1–P5) **and** the **`Sprint`** iteration — a story
  missing the `Sprint` value won't appear on the `sprint:@current` views.
- `Kind`/`Priority`/`Initiative` are **auto-set by the BMAD bridge** from story frontmatter (`type:`/`priority:`/`initiative:`) — prefer that over hand-setting on BMAD-synced issues.

## The automation line (know it before promising "zero manual")
- ✅ CLI/API: create TEXT/SELECT/DATE/NUMBER fields, set field **values** (`item-edit`), add/copy/delete boards+items, `mark-template`.
- ✋ **UI-only:** the built-in **Status** options, **iteration (`Sprint`)** fields, **views**, and **Insights** charts. The pattern is **gold template (#26) + `gh project copy`**; cross-board glance = the Grafana *Delivery Portfolio* dashboard.

## Exclusions (don't surface on boards)
`label:change-record` (`[CHANGE]` ITIL/DORA audit log) and CSPM/`IAM Audit` scanner findings are **not roadmap** — exclude from board views. Only real `enhancement`/`bug` issues belong.
