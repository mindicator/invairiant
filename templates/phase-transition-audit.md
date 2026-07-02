# invAIriant Phase-Transition Audit — <phase X → Y>

<!--
A specialization of the full-scale audit, run before a roadmap phase
transition, major release, or surface expansion (opening membership, new
public API class, new automation authority). It exists because the cost of
error changes at these boundaries.

Hard gates (docs/severity-model.md):
  - No open S0 findings: transition is blocked.
  - No critical lens below the critical_domain_threshold (default 5.0)
    with an open S0/S1 cluster: transition and surface expansion blocked
    until the cluster closes.
  - Any mandatory lens below the low_score_threshold (default 6.0):
    transition requires a written justification for proceeding without a
    stabilization pass.
-->

- **Date / participants / commit range:**
- **Transition:** <!-- e.g. "single-tenant → multi-tenant", "beta → GA",
     "closed membership → open membership" -->
- **What changes at this boundary:** <!-- new attack surface, new user class,
     new automation authority, new scale, new operators -->

## Scope

<!-- The whole system vs canon, with emphasis on what the next phase
     stresses. Name what is out of scope. -->

## Phase-Readiness Checklist

- [ ] Contracts between modules/layers are stable across the transition —
      the next phase does not require rewriting them
- [ ] Every attack→response row of the threat model is covered by working
      code and tests (not intent); threat model updated for the new surface
- [ ] Declared risk assets remain protected under next-phase conditions
- [ ] What each component knows about users does not silently expand at
      the new scale
- [ ] Degradation and recovery behavior defined AND exercised for
      next-phase failure modes; recovery SLO measured, not asserted
- [ ] No single point of failure for the expanded system; declared
      redundancy is real (tested), not paper
- [ ] Automation/oracle boundaries hold at next-phase volume (bounds,
      validation, replayability)
- [ ] Migration path staged, rehearsed, and reversible; rollback tested
- [ ] Canonical docs (README/ARCHITECTURE/threat model/ADRs) describe the
      system that is actually transitioning
- [ ] All prior-audit S0/S1 findings closed or formally risk-accepted in
      writing by the project owner

## Lens Scores

<!-- ALL mandatory lenses + every critical lens for the project.
     Verdict column cites evidence. -->

| Pack | Lens | Score | Verdict |
|---|---|---:|---|

## Findings

<!-- By severity: Critical (S0) / High (S1) / Medium (S2) / Low (S3) —
     block format from templates/audit-report.md. -->

## Unsupported Hypotheses

<!-- Kept, with rejection reasons. -->

## Gate Decision

- **Decision:** <!-- proceed | proceed_with_conditions | blocked -->
- **Justification:** <!-- reference gates above; if any mandatory lens < 6.0,
     the written justification for proceeding goes here -->
- **Conditions (owner, deadline, blocking):**
- **Re-audit trigger:** <!-- date or condition -->

## Evidence Appendix
