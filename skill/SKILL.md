---
name: invairiant
description: >
  invAIriant — an evidence-based, multi-lens architecture-audit protocol for
  LLM coding agents. This skill IS the product: it runs the audit. Commands:
  audit-pr, full-audit, verify-findings, classify-severity, synthesize-report,
  closure-verification.
  Use when the user asks for an architecture / invariant / lens audit, an
  evidence-based review, a PR audit, a phase-transition or post-incident audit,
  to verify candidate findings, classify severity, or synthesize an audit
  report — or when they type `/invairiant ...`. Every finding must cite
  concrete evidence: no evidence, no finding.
---

# invAIriant — evidence-based multi-lens architecture audit

This skill is the **primary product**: the audit discipline itself, run by an
LLM coding agent. The schemas, templates, and prompt pack are the layer it
stands on; the `invairiant` CLI is only infrastructure around it (validate,
collect evidence, render, gate) and never performs the audit.

The protocol's non-negotiable rules — enforce them at every step and repeat
them to every sub-agent you spawn:

```text
No evidence, no finding.
Do not average away critical risks.
Separate observation from verified finding.
Do not produce confident claims from vibes.
```

## Commands

Parse the first token of the invocation as the command. Default (no token) →
`full-audit` for a repo, `audit-pr` when a diff/PR is in scope.

| Command | Does | Pipeline stages |
|---|---|---|
| `audit-pr [<pr#\|range>] [--lenses a,b]` | Audit a PR/diff: checklist + ≤2 focused lenses | 1→2→3→4, PR-comment output |
| `full-audit [<range>] [--lenses ...]` | Full-scale audit: all mandatory lenses | 1→2→3→4, full report |
| `verify-findings <candidates>` | Adversarially verify candidate findings only | stage 2 |
| `classify-severity <verified>` | Map verified findings to severity only | stage 3 |
| `synthesize-report <inputs>` | Assemble the final report only | stage 4 |
| `closure-verification` | Re-verify that claimed fixes closed, no re-search | verify-only |

`--lenses a,b` overrides lens selection (comma-separated lens ids from
`docs/lens-taxonomy.md`); omit it to let the skill pick by risk surface.

The four stages and their prompts:

```text
[1] lens pass          prompts/lens-auditor.md        (one lens per pass)
[2] evidence verify    prompts/evidence-verifier.md   (adversarial: refute)
[3] severity classify  prompts/severity-classifier.md (rules, not averages)
[4] synthesize         prompts/report-synthesizer.md  (rejected items kept)
```

Stage boundaries are load-bearing: stage 1 never assigns final severity;
stage 2 never invents findings; stage 3 touches only verified findings;
stage 4 never drops a rejected hypothesis.

## Try it (copy-paste)

```text
/invairiant audit-pr                              # audit the current diff/PR
/invairiant audit-pr --lenses security-threat,turing
/invairiant audit-pr HEAD~1..HEAD                 # a specific range
/invairiant full-audit                            # whole repo, mandatory lenses
/invairiant verify-findings <candidate findings>  # stage 2 only
/invairiant closure-verification                  # after a fix wave
```

**What `audit-pr` gives you:** a ready-to-paste PR comment
(`templates/pr-comment.md`) — verdict (`pass` / `pass_with_conditions` /
`fail`), the audited range, the checklist, verified findings each with cited
evidence, conditions, and observations/hypotheses kept separate. Nothing is
merged or approved — you own the gate.

## Step 0 — locate the framework

Find the framework root (dir containing `lenses/`, `prompts/`, `schemas/`,
`templates/`, `docs/`, `cli/`): `$INVAIRIANT_HOME`, then this skill's parent,
then `./invairiant/` or `./docs/invairiant/`, then `~/.invairiant/`. If not
found, run **degraded mode** (below) rather than inventing lens content.

## Shared setup (all audit commands)

1. **Config.** Read `invairiant.config.yml`. If absent, offer
   `invairiant init --type <inferred>` (or write one after confirming project
   type, canonical docs, risk assets, and 4–6 mandatory lenses via
   `docs/lens-taxonomy.md`). Validate it: `invairiant validate-config`.
2. **Scope.** Pin the commit/range; state what is in and out of scope.
3. **Lens selection.** Mandatory lenses from config, plus at most the packs the
   change/risk surface justifies. Anti-overengineering is canon: a small PR
   gets the checklist + ≤2 lenses; default full audits use 4–6, not 20.
4. **Evidence gathering.** Run `invairiant collect --range <range> --out
   .invairiant/cache/bundle.json` to build the deterministic evidence bundle
   (diff, tree, language stats, grep signals, import hints, generated mass,
   known-rejected). Hand it to the lens passes as input. Everything in it is a
   **candidate pointer, never a finding** — it still passes stage 2. The raw
   bundle stays gitignored.

## Command procedures

### `audit-pr [<pr#|range>] [--lenses a,b]`
Scope = the diff + its blast radius. Runbook:
1. **Shared setup** (config, scope, lens selection). Lenses: `--lenses` if
   given, else ≤2 chosen by the diff's risk surface (new agent loop →
   `turing`/`oracle-boundary`; new endpoint → `security-threat`; migration →
   `kleppmann`/`mcconnell`; big generated diff → `generated-surface-area`).
2. **Collect** the bundle: `invairiant collect --range <range> --out
   .invairiant/cache/bundle.json` → feed it to the lens passes as input.
3. **Pipeline** stages 1 (lens passes) → 2 (verify) → 3 (classify) →
   4 (synthesize), against the PR checklist in `templates/pr-comment.md`.
4. **Deliverable:** a PR comment — synthesize the report, then render it with
   `invairiant render-comment <report.json>` (the `templates/pr-comment.md`
   shape): verdict (`pass` / `pass_with_conditions` / `fail`), verified
   findings with cited evidence, conditions, observations/hypotheses kept
   separate. Paste it into the PR (the CLI does not post).

Do not merge/approve anything — present the gate.

### `full-audit`
Scope = whole system at a pinned commit. Assign roles
(`docs/methodology.md` §5). Run one stage-1 pass **per selected lens** using
each lens file's Prompt Block (sub-agents may run passes in parallel; a human
or a second agent spot-checks). Then stages 2→4. Fill
`templates/audit-report.md`: lens-score table, findings by severity,
observations, **Unsupported Hypotheses (kept)**, strongest/weakest lens,
required actions with owners, evidence appendix. Every audit produces
decisions; an audit without decisions does not count. Validate the result:
`invairiant validate-report`. File it in the config's report dir.

### `verify-findings`
Input: candidate findings (JSON per `schemas/finding.schema.json`, or prose).
Apply `prompts/evidence-verifier.md` with repo access: open cited lines,
re-run commands, search for "missing" tests before agreeing, read both sides
of contradictions. Emit each as `verified` / `rejected` (with reason) /
`demoted` to observation. Invent nothing; drop nothing.

### `classify-severity`
Input: verified findings. Apply `prompts/severity-classifier.md` with the
config's `severity_policy`, `risk_assets`, named categories, and
`docs/severity-model.md`: named-category defaults, score→severity floors,
confidence constraints (S0/S1 require high/medium), one-line justification per
severity. Never lower a severity because the average is good.

### `synthesize-report`
Input: scored findings + observations/hypotheses + metadata. Apply
`prompts/report-synthesizer.md` to fill the report template. Verdict derives
from open findings (any S0 → fail; any S1 → at best pass_with_conditions),
never from score averages. Optionally render with `invairiant render-report`.

### `closure-verification`
After a wave of fixes or incident fix-forwards, verify closure **without a
full re-audit** (`docs/audit-workflow.md` §5). For each finding claimed closed:
confirm the fix landed with conformance evidence; check no new boundary drift
or hidden channels appeared; CI green at the verified HEAD; canonical docs
synced; temporary workarounds removed. Output a short closure report — each
claim → verified / not-verified, plus remaining open findings with owners. It
re-verifies claims; it does **not** search for new findings.

## The CLI is a seatbelt, not an auditor

Use the `invairiant` CLI for deterministic infrastructure only — never for
judgment (`docs/cli.md`):

- `invairiant init` — scaffold a config;
- `invairiant collect` — gather the deterministic evidence bundle (candidate
  pointers only);
- `invairiant validate-config` / `validate-report` — schema-check inputs/outputs;
- `invairiant render-report` — deterministic JSON→Markdown;
- `invairiant render-comment` — deterministic report→PR-comment;
- `invairiant ci-gate` — exit non-zero on open S0/S1.

The CLI never runs a lens, produces a finding, or assigns a score. All
architectural judgment lives here, in the agent, under these prompts.

## Humans own the gates

Never merge, approve, close, or release on the basis of an audit. Present the
verdict and the gate implication, then stop. Applying fixes is separate work
after the audit; keep the report as the record of what was found.

## Degraded mode (framework files unavailable)

State that the full lens library is not installed, then audit with four
generic lenses — `parnas`, `mcconnell`, `security-threat`, `turing` — scoring
each 0–10, applying the same evidence rules, severity floors (S0 blocks; S1
before next major step; S2 next cycle), and report structure, keeping
observations separate from findings.

## Refuse these failure modes

- A finding without concrete evidence — demote it, whoever proposed it.
- "The average is high, so the S1 is fine" — never.
- Deleting a rejected hypothesis — it goes to Unsupported Hypotheses.
- Running 15 lenses on a 40-line PR — the protocol forbids tribunals.
- Letting a scanner or reviewer-skill's output become a finding without
  stage-2 verification — adapters produce candidate evidence only.
- Using the CLI to "audit" — it has no judgment; it only serves the audit.
