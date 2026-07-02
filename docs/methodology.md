# invAIriant Methodology

> **invAIriant** is a structured audit protocol that turns senior-engineer
> judgment into reusable lenses, evidence rules, severity mapping, schemas,
> templates, and AI-compatible prompts. It exists for codebases that must not
> drift — especially codebases evolving at AI speed.

## 1. The problem it solves

Modern codebases change faster than architectural judgment can be applied to
them. AI assistance multiplies code volume; review capacity does not
multiply with it. The usual failure modes:

- reviews become vibes ("looks good", "seems overcomplicated") in both
  directions — false confidence and false alarm;
- architectural invariants erode through many locally-reasonable changes,
  and nobody can say when the erosion happened;
- AI reviewers generate plausible concerns at zero cost, and teams learn to
  ignore them;
- the one senior engineer who *would* have caught it did not see the PR.

invAIriant's answer is not "more review". It is a protocol that makes review
**checkable**: named lenses instead of general vigilance, evidence instead of
confidence, severity rules instead of averaged impressions, and a pipeline in
which AI may propose anything but only verified claims count.

## 2. Design principles

1. **No evidence, no finding.** The full rules are in
   [evidence-rules.md](evidence-rules.md). Everything else is built on this.
2. **Lenses are structured judgment.** A lens is a named school of
   questioning — purpose, core questions, red flags, required evidence,
   scoring rubric — not a famous name attached to a checklist. See
   [lens-taxonomy.md](lens-taxonomy.md).
3. **Severity outranks averages.** One S0 is not offset by nine beautiful
   scores. See [severity-model.md](severity-model.md).
4. **AI proposes; evidence disposes.** AI agents are first-class auditors at
   the hypothesis stage and are never trusted at the conclusion stage.
   Humans own gates.
5. **Domain risk outranks code beauty.** The lenses closest to the project's
   declared risk assets dominate general-engineering lenses.
6. **The protocol must not become ritual.** Anti-overengineering rules (§8)
   are part of the canon, not an afterthought.

## 3. The audit pipeline

Every invAIriant audit — from a PR audit to a full-scale one — runs the same
four-stage pipeline. The stages map one-to-one onto the prompt pack in
[`prompts/`](../prompts/), and any stage can be executed by a human, an AI
agent, or both.

```text
        inputs: diff/repo, canonical docs, config, tool outputs
                             |
   [1] LENS PASS             |   one pass per selected lens
       lens auditor          v   (prompts/lens-auditor.md)
       -> lens score + candidate findings + observations/hypotheses
                             |
   [2] EVIDENCE VERIFICATION |   adversarial: try to refute each candidate
       evidence verifier     v   (prompts/evidence-verifier.md)
       -> verified findings | rejected hypotheses | demoted observations
                             |
   [3] SEVERITY CLASSIFICATION   rules from severity-model.md + config
       severity classifier   v   (prompts/severity-classifier.md)
       -> severities, named categories, gate implications
                             |
   [4] SYNTHESIS                 one report; rejected items stay visible
       report synthesizer    v   (prompts/report-synthesizer.md)
       -> audit report (templates/audit-report.md) + verdict
```

Stage boundaries are load-bearing:

- Stage 1 may not assign final severity (provisional at most).
- Stage 2 may not invent findings — only verify, reject, or demote.
- Stage 3 touches only verified findings.
- Stage 4 may not drop rejected hypotheses — they appear in the report under
  Unsupported Hypotheses, because a wrong hypothesis recorded is cheaper than
  the same hypothesis re-proposed every audit.

## 4. Audit types

| Type | Trigger | Scope | Output |
|---|---|---|---|
| **PR audit** | every architecturally significant PR | the diff + its blast radius | checklist + findings + `pass` / `pass_with_conditions` / `fail` ([templates/pr-comment.md](../templates/pr-comment.md)) |
| **Tactical audit** | calendar (weekly/biweekly) | accumulated drift since last audit | brief memo: drift, debt, workarounds that stuck |
| **Full-scale audit** | calendar (per 4–8 weeks) or milestone | whole system vs canon, all mandatory lenses scored | full report ([templates/audit-report.md](../templates/audit-report.md)) |
| **Event-triggered audit** | incident, security event, new external surface, major refactor, phase transition | determined by the event | full or focused report ([templates/event-triggered-audit.md](../templates/event-triggered-audit.md)) |
| **Closure verification** | after a wave of fixes / incident fix-forwards | did the claimed fixes actually close, without new debt of the same class | short verification report — not a re-audit |

A change is *architecturally significant* if it touches: a contract between
modules/layers, the attack surface or threat model, what a component knows
about users, state ownership or the source of truth, automation authority or
oracle boundaries, degradation/recovery behavior, or compatibility with
deployed instances.

## 5. Roles

A full-scale audit distributes these roles; one person or agent may hold
several, but the roles stay conceptually distinct:

| Role | Verifies |
|---|---|
| **System architect** | overall structure; stability of contracts between modules/layers |
| **Data-flow reviewer** | the primary data path: correctness, boundaries, provider/engine edges |
| **Control & state reviewer** | state ownership, config/secrets handling, control loops, automation authority |
| **Security / threat auditor** | implementation vs threat model; surfaces; secrets; privilege boundaries |
| **Privacy auditor** | knowledge minimization; retention; correlation channels |
| **Resilience / operations auditor** | degradation, recovery, rollback, observability, SLOs |
| **Measurement auditor** | that metrics/telemetry are truthful, minimal, and not themselves a liability |
| **Compliance / opsec auditor** (where applicable) | role separation, jurisdiction/knowledge separation, operator protection |
| **Documentation auditor** | drift between code and canonical docs (README/ARCHITECTURE/threat model/ADRs) |

Roles choose lenses; lenses structure the pass; the pipeline is the same for
everyone.

## 6. Lens selection and mandatory lenses

- The project config ([`invairiant.config.yml`](../schemas/invairiant.config.schema.json))
  names 4–6 **mandatory lenses** scored in every full-scale audit. Defaults
  worth copying: `security-threat`, `parnas`, `mcconnell`, `turing`.
- **Packs are opt-in.** Systems, implementation, correctness, security-safety,
  ai-generated-code, and domain packs are pulled in when the change or the
  project type warrants them — see the selection guide in
  [lens-taxonomy.md](lens-taxonomy.md).
- Every full-scale audit report contains the **lens score block**: one row
  per mandatory lens (score, verdict, evidence refs), plus rows for any
  optional lenses applied. See the template.
- Score → severity mapping and interpretation rules live in
  [severity-model.md](severity-model.md) and are not negotiable per-audit.

## 7. Non-goals

invAIriant is **not**:

- a security certification;
- a replacement for human review;
- a proof of correctness;
- a replacement for tests, static analysis, SAST/DAST, threat modeling, or
  formal methods;
- a generator of findings without evidence;
- an invitation to architecture cosplay or name-dropping.

It **integrates** with those practices by turning their outputs into audit
evidence (see [evidence-rules.md §7](evidence-rules.md) and
[related-work.md](related-work.md)).

## 8. Anti-overengineering rules

Because the framework is lens-heavy, these rules are canon:

1. Default audits use **4–6 lenses**, not 20.
2. Additional packs are **opt-in**.
3. A small PR does not trigger a full philosophical tribunal — the PR audit
   checklist plus at most two focused lenses.
4. Lens selection must match the **risk surface** of the change, not the
   auditor's interests.
5. Lens names are **mnemonic devices**, not appeals to authority. "Parnas
   would object" is not a finding; a cited boundary leak is.
6. A boring concrete finding beats a brilliant abstract concern.
7. The framework must **reduce** review ambiguity. Any practice that adds
   ritual without adding checkability gets removed.

## 9. Change-management extensions (optional)

Two practices inherited from the origin project pair well with the audit
protocol on high-risk systems; both are optional:

- **Component participation table** — a change proposal lists every component
  it touches with its role in the change, a status
  (`active`/`passive`/`deferred`/`test-only`), and any external technology
  plus a one-line boundary argument. A component that cannot justify its row
  is removed, merged, or deferred.
- **Blast-radius cap** — an ordinary single proposal changes at most one
  module-boundary responsibility, one behavior/engine, and one public
  surface; anything larger is split, staged with per-phase acceptance
  criteria, or explicitly declared an emergency fix-forward.

## 10. What "good" looks like

An invAIriant audit succeeded if, months later, a stranger can: read the
report, check three findings against the cited evidence in minutes, see which
hypotheses were rejected and why, and tell exactly what gate decision was
made on what grounds. If any of that requires interviewing the original
auditor, the protocol was not followed.
