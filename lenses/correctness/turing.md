# Turing Lens (cross-listed) — Computability, Termination, and Oracle Boundaries

**Pack:** correctness (cross-listed) · **Canonical file:** [`../core/turing.md`](../core/turing.md)

This lens is cross-listed into the Correctness Pack to avoid duplicating
content. Use the canonical file for the full definition, scoring rubric, and
prompt block; do not fork it.

**Correctness-pack emphasis** — when applying this lens in a correctness
audit, weight these questions highest:

- Does every loop, retry, and polling path have a termination bound that
  code actually enforces — an iteration cap, a deadline, or a budget?
- Is the system state defined and typed when an oracle fails, times out, or
  reports uncertainty, rather than left as an unhandled branch?
- Can every oracle-mediated decision be replayed from persisted prompt
  version, model id, inputs, and raw output?
