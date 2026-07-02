# Cormen Lens (cross-listed) — Algorithmic Rigor and Invariants

**Pack:** correctness (cross-listed) · **Canonical file:** [`../core/cormen.md`](../core/cormen.md)

This lens is cross-listed into the Correctness Pack to avoid duplicating
content. Use the canonical file for the full definition, scoring rubric, and
prompt block; do not fork it.

**Correctness-pack emphasis** — when applying this lens in a correctness
audit, weight these questions highest:

- Is the invariant for each critical flow stated explicitly, and is there a
  test (unit or property) that would fail the moment it broke?
- Can every state transition be written down as a table — states, events,
  next states — with no "it depends" cells left unresolved?
- Are the operations idempotent or monotonic under retry and restart, so a
  replayed step cannot corrupt what a completed step established?
