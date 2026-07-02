# Harel Lens (cross-listed) — Statecharts and Reactive Behavior

**Pack:** correctness (cross-listed) · **Canonical file:** [`../systems/harel.md`](../systems/harel.md)

This lens is cross-listed into the Correctness Pack to avoid duplicating
content. Use the canonical file for the full definition, scoring rubric, and
prompt block; do not fork it.

**Correctness-pack emphasis** — when applying this lens in a correctness
audit, weight these questions highest:

- Is every reachable state and transition explicit in code or a chart, with
  none existing only implicitly in scattered conditionals?
- Are impossible transitions actively rejected — and does a test attempt
  each forbidden transition and assert the rejection?
- Does every state that waits on an external event define timeout and
  recovery transitions, so no state can silently become terminal?
