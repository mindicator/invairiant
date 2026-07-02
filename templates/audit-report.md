# invAIriant Audit Report

<!--
Machine-readable form: schemas/audit-report.schema.json.
Rules that bind this report:
  - No evidence, no finding (docs/evidence-rules.md).
  - A high average lens score never cancels an S0/S1 finding.
  - Rejected hypotheses are kept in "Unsupported Hypotheses", never deleted.
  - Every score must reference evidence.
Delete the comments as you fill the sections.
-->

- **Date:**
- **Audit type:** <!-- pr | tactical | full-scale | event-triggered | closure-verification -->
- **Project / commit range:**
- **Phase / milestone (if used):**
- **Participants:** <!-- humans and AI agents, with roles -->
- **Config:** <!-- path to invairiant.config.yml used -->

## Scope

<!-- What was audited — and, just as important, what was explicitly NOT.
     Layers/components, diffs, scenarios, docs, tool outputs. -->

## Inputs Reviewed

<!-- Concrete list: files/dirs at commit X, diffs, canonical docs, CI runs,
     logs, incident reports, evidence-adapter outputs (SAST, review skills…). -->

## Executive Summary

<!-- 3-8 sentences: overall assessment; key S0/S1 risks; the verdict and why.
     Verdict: pass | pass_with_conditions | fail — derived from open
     findings per docs/severity-model.md §7, not from score arithmetic. -->

**Verdict:**

## Lens Scores

<!-- One row per mandatory lens (always) + each optional lens applied.
     Verdict column: one-line justification referencing evidence
     (finding ids, file:lines, tests) — not taste. -->

| Pack | Lens | Score | Verdict |
|---|---|---:|---|
| | | /10 | |

## Critical Findings

<!-- S0. Use the block below per finding (templates/finding.md for the full
     field reference). S0 blocks merge/release/phase transition. -->

### INV-000 — <title> (S0, <lens>, confidence: <high|medium>)

- **Claim:**
- **Evidence:**
  - `path/file.ext:120-148` — <what these lines show>
- **Risk:**
- **Recommendation:**
- **Category:** <!-- optional named category, e.g. SECRET_LEAK -->
- **Owner / deadline:**

## High Findings

<!-- S1 — must be fixed before the next major step. Same block format. -->

## Medium Findings

<!-- S2 — scheduled in the next work cycle. Same block format.
     S3 items may be listed compactly here or under Notes. -->

## Notes / Observations

<!-- Evidence-light items worth recording. No severity. Honest phrasing:
     "Observed X in Y; not verified against Z." -->

## Unsupported Hypotheses

<!-- MANDATORY section — keep it even when empty ("none").
     Candidates that failed evidence verification, with rejection reasons,
     and hypotheses no one checked. These are kept so the next audit starts
     from the record, not from zero. -->

| Hypothesis | Proposed by | Rejection / status |
|---|---|---|

## Strongest Lens

<!-- Which lens scored best and what evidence makes that credible. -->

## Weakest Lens

<!-- Which lens scored worst, the main reason, and the finding/action item
     that explains it (interpretation rule: a low score must be explained
     by a concrete risk). -->

## Required Actions Before Next Phase / Major PR

<!-- Numbered, each with owner, deadline, and blocking|non-blocking.
     Every open S0/S1 must appear here. -->

1.

## Evidence Appendix

<!-- Longer excerpts, command transcripts, tool outputs, reproduction notes —
     referenced from findings by id. -->

## Reviewer Notes

<!-- Process notes: what was hard to verify, what the next audit should
     check first, cadence/scope suggestions. -->
