# Audit Workflow

Operational, step-by-step procedures for running invAIriant audits. The
conceptual model is in [methodology.md](methodology.md); this document is the
runbook.

## 0. One-time project setup

1. Write `invairiant.config.yml` at the repo root (validate against
   [`schemas/invairiant.config.schema.json`](../schemas/invairiant.config.schema.json);
   start from an example in [`examples/`](../examples/)).
2. Name the **canonical docs** (README, ARCHITECTURE, THREAT_MODEL, ADRs…) —
   these become the reference side of doc/code-contradiction evidence.
3. Pick **4–6 mandatory lenses** matching the project's risk surface
   (selection guide: [lens-taxonomy.md](lens-taxonomy.md)).
4. Name the **risk assets** (credentials, user data, availability, operator
   safety…) — severity classification references them.
5. Declare **evidence adapters** (test suite, CI, SAST, AI review skills)
   whose outputs feed audits as candidate evidence.
6. Create the report directory (default `docs/audits/`) and commit the
   config.

## 1. PR audit (minutes, every significant PR)

**Inputs:** the diff, PR description, canonical docs, CI results.

1. **Significance check.** Does the PR touch a contract, surface, state
   ownership, automation authority, user-knowledge, or degradation behavior?
   If no — normal code review, no audit artifacts.
2. **Checklist pass** — the generic PR checklist (in
   [`templates/pr-comment.md`](../templates/pr-comment.md)): boundaries
   intact, no new hidden channels, docs updated, no silent degradation, no
   secret in diff, compatibility preserved, rollback exists for
   high-blast-radius changes.
3. **Focused lens pass** — at most two lenses chosen by the diff's risk
   surface (e.g. a new agent loop → `turing`; a new endpoint →
   `security-threat`). Run [`prompts/lens-auditor.md`](../prompts/lens-auditor.md)
   per lens if using an AI auditor.
4. **Verify → classify** any candidate findings (stages 2–3 of the pipeline;
   for a small PR one human can do both in one sitting, but the demotion
   rules still apply).
5. **Post the verdict** as a PR comment from the template:
   `pass` / `pass_with_conditions` / `fail`, findings with evidence,
   unsupported hypotheses kept separate.

**Gate:** no unresolved S0/S1 from this PR; conditions named and owned.

## 2. Tactical audit (an hour, weekly/biweekly)

**Inputs:** merged changes since the last tactical audit, open action items,
canonical docs.

1. Diff the period: `git log --stat` over the window; list changes that were
   significant in aggregate even if each PR was small.
2. Hunt **drift**: code vs canonical docs; temporary workarounds that
   survived their trigger-to-remove; boundaries that widened.
3. Check **action items** from prior audits: closed, stale, or quietly
   dropped?
4. Check **score trends**: any lens falling two audits in a row opens an
   action item (interpretation rule 5).
5. Output: a brief memo (a short audit-report instance) — findings only where
   evidence exists; everything else is observations.

## 3. Full-scale audit (a day or more, per 4–8 weeks or milestone)

**Inputs:** whole repo at a pinned commit, all canonical docs, config,
recent incidents, CI history, evidence-adapter outputs.

1. **Scope & pin.** Record commit range, phase/milestone, participants, and
   what is explicitly out of scope.
2. **Assign roles** (methodology §5) and select lenses: all mandatory lenses
   + packs justified by the project type and the period's changes.
3. **Stage 1 — lens passes.** One pass per lens
   ([`prompts/lens-auditor.md`](../prompts/lens-auditor.md)); each yields a
   score block, candidate findings, observations/hypotheses/open questions.
   AI agents may run passes in parallel; humans spot-check each pass.
4. **Stage 2 — evidence verification.** Adversarial pass over every candidate
   ([`prompts/evidence-verifier.md`](../prompts/evidence-verifier.md)):
   verify / reject / demote, with the verification method recorded.
5. **Stage 3 — severity classification.**
   ([`prompts/severity-classifier.md`](../prompts/severity-classifier.md))
   Apply score→severity rules, named categories, confidence constraints, and
   gate implications from [severity-model.md](severity-model.md).
6. **Stage 4 — synthesis.**
   ([`prompts/report-synthesizer.md`](../prompts/report-synthesizer.md))
   Fill [`templates/audit-report.md`](../templates/audit-report.md): lens
   score table, findings by severity, notes/observations, **unsupported
   hypotheses (kept)**, strongest/weakest lens, required actions, evidence
   appendix.
7. **Decisions.** Every audit produces decisions — accepted, rejected,
   deferred, needs-ADR — plus owned action items with deadlines. An audit
   without decisions does not count.
8. **File the report** in the report directory; link findings to issues.

**Gate:** phase transitions and surface expansions are blocked while a
critical lens is below the critical threshold with an open S0/S1 cluster.

## 4. Event-triggered audit

**Triggers:** production incident; suspected compromise or exposure; a new
external surface (endpoint, transport, membership class); a change to
discovery/trust/automation authority; a major refactor; technical debt
crossing a declared threshold; a real adversarial event.

Use [`templates/event-triggered-audit.md`](../templates/event-triggered-audit.md):
scope is defined by the event; lenses are chosen by what the event stressed;
post-incident audits additionally answer *what did the system actually do,
what recovered, how fast, and which assumptions broke*.

## 5. Incident mode and closure verification

Two special modes inherited from the origin canon, generalized:

- **Red-master freeze.** While CI on the integration branch is red: only
  fix-forward commits aimed at green; no new scope, no opportunistic
  refactors; minimal doc edits required by the fix itself.
- **Production incident mode.** While an incident degrades users: only
  changes that restore service **without sacrificing declared safety/privacy
  properties**; any temporary workaround that trades such a property away
  must be an explicit, documented degradation decision, recorded as a
  finding, with a trigger-to-remove.
- **Closure verification** (after either mode, or a wave of cleanup fixes):
  a short report proving each claimed fix actually closed — conformance
  evidence per claim, no new boundary drift, CI green at verified HEAD,
  canonical docs synced, remaining findings listed with owners, temporary
  workarounds removed. It re-verifies claims; it does not re-search for new
  findings.

## 6. Running the pipeline with AI agents

- **One lens, one agent, one pass.** Give each lens auditor only its lens
  file's Prompt Block + the inputs. Do not ask one agent to "apply all
  lenses" — cross-lens averaging is exactly what the protocol exists to
  prevent.
- **Verification is a different agent (or a human), never the proposer.**
  The verifier gets the candidate findings and repo access, and is prompted
  to refute.
- **Skills and tools are evidence adapters.** Security scanners, code-review
  skills, dependency auditors, and test runs feed stage 1–2 as candidate
  evidence; their raw output lands in the evidence appendix
  ([evidence-rules.md §7](evidence-rules.md)).
- **Agent-skill mode.** If the repo has the invAIriant skill installed
  (see [`skill/SKILL.md`](../skill/SKILL.md)), `/invairiant` orchestrates
  this whole workflow: config discovery → lens selection → staged pipeline →
  report, with humans approving gates.
- Humans own: lens selection, gate decisions, severity overrides (written
  justification), and anything the config marks as blocking.

## 7. Cadence (risk-based)

Generalize cadence from risk, not calendar attachment. Suggested mapping:

| Project risk state | PR audit | Tactical | Full-scale | Event-triggered |
|---|---|---|---|---|
| Early prototype, one operator, low blast radius | significant PRs | weekly | every 4–6 weeks | every incident, every new external surface |
| Growing surface (real users, coordinator/central components) | mandatory | every 1–2 weeks | every 6–8 weeks, critical lenses mandatory | any change to what central components know or control |
| Open/adversarial surface (open membership, untrusted input at scale, autonomous actions) | mandatory for surface-touching PRs | biweekly | every 6–8 weeks, all critical + domain lenses | any change to discovery/trust/automation authority |
| Mature, boring | significant PRs | monthly | quarterly | on trigger, always after real incidents |

The cost of an error grows with each state; audit depth follows the cost of
error, not the size of the diff.

## 8. Follow-up discipline

- Every S0/S1 finding gets an owner and a deadline at synthesis time.
- Re-audit triggers are recorded in the report (date or condition).
- Score history is kept (a simple table per lens over time); two consecutive
  drops open an action item regardless of absolute value.
- Rejected hypotheses are carried forward in the report archive — an auditor
  proposing the same hypothesis later starts from the recorded rejection,
  not from zero.
