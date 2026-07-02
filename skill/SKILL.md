---
name: invairiant
description: Run an evidence-based, multi-lens architecture audit (invAIriant protocol) on a repo, diff, or PR. Use when the user asks for an architecture audit, invariant audit, lens audit, evidence-based review, PR audit, phase-transition/readiness audit, post-incident audit, or invokes /invairiant. Produces a scored, severity-classified audit report where every finding cites concrete evidence — no evidence, no finding.
---

# invAIriant — evidence-based multi-lens architecture audit

You are orchestrating an invAIriant audit. The protocol's non-negotiable
rules, which you enforce at every step and repeat to every subagent:

```text
No evidence, no finding.
Do not average away critical risks.
Separate observation from verified finding.
Do not produce confident claims from vibes.
```

## Step 0 — Locate the framework

Find the invAIriant framework root (the directory containing `lenses/`,
`prompts/`, `schemas/`, `templates/`, `docs/`). Check in order:

1. `$INVAIRIANT_HOME` if set;
2. this skill's own parent directory (when the skill ships inside the
   framework repo);
3. `./invairiant/` or `./docs/invairiant/` in the target repo;
4. `~/.invairiant/`.

If not found, tell the user where to get it and run **degraded mode**
(§ Degraded mode) rather than inventing lens content.

## Step 1 — Scope, config, audit type

1. Read `invairiant.config.yml` at the target repo root. If absent, offer a
   60-second setup: infer `project.type` from the repo, propose 4–6
   mandatory lenses from the selection table in `docs/lens-taxonomy.md`,
   ask the user to confirm risk assets and canonical docs, write the config
   (validate against `schemas/invairiant.config.schema.json`).
2. Determine audit type from the request: a PR/diff → **pr**; "audit the
   system / full audit" → **full-scale**; an incident or event →
   **event-triggered** (template `templates/event-triggered-audit.md`);
   a release/phase gate → **phase-transition**
   (`templates/phase-transition-audit.md`); "verify the fixes" →
   **closure-verification**.
3. Pin the commit/range being audited and state scope explicitly (what is
   in, what is out).
4. Select lenses: mandatory lenses from config, plus at most the packs the
   change/risk surface justifies. **Anti-overengineering is canon:** a
   small PR gets the checklist plus ≤2 focused lenses; default full-scale
   audits use 4–6 lenses, not 20.

## Step 2 — Gather evidence inputs (evidence adapters)

Before any lens pass, collect cheap deterministic evidence so auditors cite
facts, not impressions:

- run the test suite and linters if available; capture failures;
- check CI status for the range if accessible;
- if security/code-review skills or scanners are available (e.g.
  `/security-review`, `/code-review`, semgrep), run the relevant ones and
  **treat their output as candidate evidence, never as findings** — each
  claim they make must still pass verification;
- collect the canonical docs named in the config for contradiction checks.

Store raw outputs for the report's Evidence Appendix.

## Step 3 — Run the pipeline

Run the four stages with strict boundaries. Use subagents where available
(one lens per subagent, in parallel; a **different** agent for
verification). If subagents are unavailable, run the stages sequentially
yourself — but never skip stage 2, and never let stage 1's author-view
survive unverified into the report.

1. **Lens passes** — for each selected lens, use the lens file's
   `## Prompt Block` (or `prompts/lens-auditor.md` + the lens file). Each
   pass returns: a 0–10 score block with evidence-referencing
   justification, candidate findings (JSON per
   `schemas/finding.schema.json`, `status: candidate`, provisional
   severity), and clearly separated observations/hypotheses/open questions.
2. **Evidence verification** — apply `prompts/evidence-verifier.md` to
   every candidate: open the cited lines, re-run commands, search for
   "missing" tests before agreeing, read both sides of contradictions.
   Verdicts: verified / rejected (with reason) / demoted to observation.
   Nothing is dropped.
3. **Severity classification** — apply `prompts/severity-classifier.md`
   with the config's `severity_policy`, `risk_assets`, named categories,
   and `docs/severity-model.md`: named-category defaults, score→severity
   floors (mandatory lens <6.0 → ≥S2; <5.0 with concrete architectural
   risk → ≥S1; critical lens <5.0 with user/operational risk → S0),
   confidence constraints (S0/S1 require high/medium), one-line written
   justification per severity.
4. **Synthesis** — apply `prompts/report-synthesizer.md` to fill
   `templates/audit-report.md` (or the audit-type template): lens score
   table, findings by severity, notes/observations, **Unsupported
   Hypotheses kept visible with rejection reasons**, strongest/weakest
   lens, required actions with owners, evidence appendix. Verdict derives
   from open findings: any S0 → fail; any S1 → at best
   pass_with_conditions; never from score averages.

## Step 4 — Deliver and gate

- Write the report to the config's report dir (default `docs/audits/`,
  fall back to the working directory), named
  `YYYY-MM-DD-<type>-<slug>.md`.
- Tell the user: the verdict, open S0/S1 findings with their evidence, the
  weakest lens and why, and the required actions. Lead with the outcome.
- Humans own gates: never merge/approve/close anything yourself on the
  basis of the audit; present the gate implication and stop.
- If the user asks to fix findings, that is new work after the audit —
  keep the report as the record of what was found first.

## Degraded mode (framework files unavailable)

State clearly that the full lens library is not installed, then audit with
only these four generic lenses, all other rules unchanged:

- **parnas** — do modules read each other's internals past declared
  interfaces; can implementations be replaced; is any registry/config
  service accumulating knowledge beyond its contract?
- **mcconnell** — are changes localized and documented; do code and
  canonical docs diverge; do tests accompany changes; is there rollback
  for high-blast-radius changes?
- **security-threat** — does code cover the threat model's attack rows;
  new surfaces recorded; secrets out of code/logs/telemetry; authn/authz
  on new endpoints; no silent path bypassing the security model?
- **turing** — does every loop/retry have an enforced bound; is
  model/heuristic output validated before touching state; are
  model-mediated decisions replayable; is there a deterministic fallback
  for uncertainty?

Score each 0–10, apply the same evidence rules, severity floors, and
report structure (embed the severity table: S0 blocks, S1 before next
major step, S2 next cycle, S3 low, NOTE no action).

## Failure modes to refuse

- A finding without concrete evidence — demote it, whoever proposed it.
- "The average is high, so the S1 is fine" — never.
- Deleting a rejected hypothesis — it goes to Unsupported Hypotheses.
- Running 15 lenses on a 40-line PR — the protocol forbids tribunals.
- Letting a scanner's or reviewer-skill's output become findings without
  verification — adapters produce candidate evidence only.
