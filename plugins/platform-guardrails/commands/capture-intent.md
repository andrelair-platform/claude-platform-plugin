---
description: Brainstorm an idea into a committed intent/<slug>.md proto-spec (AI-native SDLC Play 1).
argument-hint: "[a sentence describing the idea or problem]"
allowed-tools: Read, Write, Bash(git add:*), Bash(git status:*)
---

Help the author turn a raw idea into an `intent.md` proto-spec, using `@intent/TEMPLATE.md`
as the shape and `@intent/README.md` for the flow. This is the front door of the SDLC — no
formal language required.

Idea: `$ARGUMENTS`

Steps:
1. Ask the clarifying questions an analyst would — **briefly**: scope, who's affected, hard
   constraints (PII / auth / budget / compliance), and what success looks like. Don't
   interrogate; 3–5 sharp questions.
2. Draft `intent/<slug>.md` (slug = kebab-case of the title) in the author's own words,
   filling: Problem · Proposed outcome · Affected users and systems · Constraints · Open
   questions. Capture *what* and *why*, never the implementation.
3. Show the draft and let the author correct anything you misread. **Do NOT invent
   requirements** — mark unknowns as Open questions.
4. On approval, `Write` it to `intent/<slug>.md`. The author commits it (author + timestamp
   become the record); the product owner picks it up from there.

Do not design the solution or write code — this stage only captures intent.
