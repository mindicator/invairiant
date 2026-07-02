# Evidence Rules

> **Status:** protocol core. Every other part of invAIriant depends on this
> document. If a practice here conflicts with a lens, a template, or a prompt,
> this document wins.

The core rule:

```text
No evidence                  -> no finding.
Low confidence               -> observation, not finding.
Security-critical
uncertainty                  -> finding only if tied to a concrete risk
                                AND a concrete evidence gap.
```

## 1. Why evidence-first

AI assistants can propose plausible architectural concerns at effectively zero
cost. That is useful — and dangerous. A review process that accepts confident,
unsupported claims will drown in noise, and worse, it will train the team to
ignore audits entirely.

invAIriant therefore splits the work:

- **Anyone (human or AI) may propose hypotheses.** Cheap, encouraged,
  unlimited.
- **Only evidence-backed claims become findings.** Every finding must be
  independently checkable by a second reviewer in minutes.
- **Severity attaches only to verified findings.** Rejected candidates are
  kept — visibly — as unsupported hypotheses, never silently deleted and never
  silently promoted.

## 2. Valid evidence types

These are the ten evidence types accepted by
[`schemas/finding.schema.json`](../schemas/finding.schema.json):

| Type (schema id) | What it is | Valid when |
|---|---|---|
| `file_lines` | file path + line range | the cited lines actually exhibit the claimed property at the audited commit |
| `diff_hunk` | a diff hunk | the hunk is from the change under review |
| `test_failure` | a failing test | the failure is reproducible and named |
| `missing_test` | an absent test | the untested behavior is named, and where the test would live is stated |
| `doc_code_contradiction` | doc says X, code does Y | both sides are cited (doc path + code path) and genuinely conflict |
| `ci_output` | CI behavior | the run is referenced (URL/id) with the relevant excerpt |
| `runtime_log` | runtime log excerpt | source and excerpt are given; the log shows the claimed behavior |
| `incident` | production incident | the incident report is referenced |
| `command_output` | reproducible command output | the command is stated and re-runnable |
| `schema_config_mismatch` | schema/config disagreement | both artifacts are cited and the mismatch described |

## 3. What is not evidence

None of the following supports a finding, at any severity:

- "looks risky";
- "probably overcomplicated";
- "AI may have generated this";
- "this feels wrong";
- "the architecture seems unclear" — without a file/doc citation showing the
  unclarity;
- a lens name ("this violates Parnas") without the concrete leak;
- another tool's warning, by itself (see §7);
- seniority, confidence, or eloquence.

## 4. The claim ladder

Every claim an auditor produces lands on exactly one rung:

| Rung | Definition | Requires |
|---|---|---|
| **Finding** | falsifiable defect claim with severity | ≥1 valid evidence item, verified |
| **Observation** | something noticed and worth recording | honest phrasing; no severity |
| **Hypothesis** | proposed explanation not yet checked | a statement of what evidence would confirm or refute it |
| **Open question** | something the audit could not determine | a statement of who/what could answer it |

Promotion rules:

- An observation/hypothesis becomes a finding **only** by acquiring evidence —
  never by repetition, never by consensus of auditors, never because it sounds
  serious.
- A finding whose evidence fails verification is **demoted**, not deleted: it
  moves to the report's Unsupported Hypotheses section with the rejection
  reason.
- Open questions must name their resolution path ("run the partition test",
  "ask the owner of `billing/`", "check the retention config in prod").

## 5. Evidence quality bar

Each evidence item must be:

1. **Specific** — points at an exact location or artifact, not at a module
   "in general".
2. **Checkable** — a second reviewer can verify it in minutes without the
   original author.
3. **Current** — taken at the audited commit/range; record the commit for
   `file_lines` where drift is likely.
4. **Sufficient** — actually supports the claim. A citation that is merely
   *near* the problem is decoration, not evidence.

Two anti-patterns fail this bar even though they look rigorous:

- **Vibe laundering** — a confident claim with a citation that does not
  support it. Verifiers must check that the evidence carries the claim, not
  just that the file exists.
- **Evidence stuffing** — five weak items standing in for one strong one.
  Verifiers evaluate the strongest item; padding does not add up to proof.

## 6. Verification

Every candidate finding passes an adversarial verification step before it may
carry severity (see [`prompts/evidence-verifier.md`](../prompts/evidence-verifier.md)):

- the verifier's job is to **refute**: open the cited lines, re-run the
  command, read both sides of the contradiction, run or locate the test;
- per-type minimum checks: `file_lines`/`diff_hunk` → read them;
  `command_output` → re-run it; `test_failure` → reproduce or locate in CI;
  `doc_code_contradiction` → read both artifacts; `missing_test` → search for
  the test before agreeing it is missing;
- outcome per candidate: `verified`, `rejected` (evidence absent, stale, or
  insufficient), or `demoted` to observation (real signal, not yet a defect
  claim);
- verification is recorded in the finding's `verification` field: who, method,
  notes.

A finding that skips verification is a candidate, whatever its author thinks.

## 7. Tool and skill outputs are evidence inputs, not findings

Static analyzers, SAST/DAST, AI code reviewers, test suites, dependency
auditors, and other agent skills plug into invAIriant as **evidence
adapters** (declared in `evidence_adapters` in the config):

- a Semgrep/CodeQL hit, a failing pipeline, a security-review report item, or
  an AI reviewer comment enters the audit as a **candidate finding with
  attached evidence** (`command_output`, `ci_output`, or `file_lines`);
- it becomes a finding only after the same verification as any other
  candidate — tools produce false positives, and a tool's severity label is
  not the audit's severity;
- the adapter's raw output goes to the Evidence Appendix, so the chain from
  claim to source stays auditable.

This is how invAIriant integrates with — rather than replaces — existing
tooling.

## 8. Security-critical uncertainty

Uncertainty about a security/safety/privacy property is the one place where
an *absence* can justify a finding, because "we could not determine X" is
itself an operational risk. The bar:

- the claim must name the **concrete risk** ("token lifetime is not bounded
  anywhere we could find; a leaked token may be valid forever");
- and the **concrete evidence gap** as a checkable item (`missing_test`,
  absent config, unanswered doc reference — cited);
- generalized anxiety ("the auth code is complex, something might be wrong")
  stays an observation.

## 9. Evidence in reports

- Findings embed their evidence items inline (see
  [`templates/finding.md`](../templates/finding.md)).
- Longer excerpts, command transcripts, and reproduction notes go to the
  report's **Evidence Appendix**, referenced by finding id.
- Lens scores are claims too: every score cites the evidence that justifies
  it (finding ids, file references, test names). An unscored-but-praised lens
  section is a formality, and formalities do not count.
