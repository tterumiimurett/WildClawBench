# Work Sessions

A work session is the documentation boundary for one purpose across a conversation or a related series of conversations. Use this directory for grilling, design, specifications, tickets, experiment plans, evidence, and result interpretation.

## Bind a conversation

1. Look for an explicit session binding in the conversation or an existing `SESSION.md` whose purpose is the same work.
2. If none is established, ask once for the session name or purpose. When the user supplies only a purpose, derive a short lowercase kebab-case name.
3. Create `docs/sessions/YYYY-MM-DD-<name>/SESSION.md`. Record the canonical name, purpose, scope, current phase, and status.
4. Use that directory for every later document tied to the work. Continue the existing binding across follow-up turns and compacted context.

The binding is complete when `SESSION.md` names the session and states a purpose that distinguishes it from every sibling session.

## Contents

Create files only when the work needs them:

```text
docs/sessions/YYYY-MM-DD-<name>/
├── SESSION.md
├── grill.md
├── spec.md
├── evidence/
├── results/
└── tickets/
```

- `grill.md` records answered decisions and remaining questions.
- `spec.md` holds the accepted implementation or experiment specification.
- `evidence/` holds durable research and validation evidence.
- `results/` holds compact result reports; large generated outputs stay in ignored runtime directories and are linked from reports.
- `tickets/` holds tasks derived from this session's accepted specification.

Keep session-local terms in the session documents. Promote vocabulary shared across sessions to `docs/sessions/CONTEXT.md`. Record a formal ADR only for a durable, costly-to-reverse choice whose trade-off would otherwise be surprising.

The historical material under `docs/grilling/` predates this convention. Treat each existing child directory there as a self-contained legacy session. New work uses `docs/sessions/`.
