# Demo

One full pass through the pipeline, then a few imaginary scenarios. Everything
in the first walkthrough is **real CLI output** except the `/invairiant
audit-pr` step, which the agent runs.

## The full flow — `collect → audit-pr → report → render-comment → record`

Setting: a PR changes a shell TLS renderer. This is the
[`persistent-mesh-transport`](../case-studies/persistent-mesh-transport/)
case; a diff-level reviewer approved it.

### 1 · `collect` — gather the evidence bundle *(CLI)*

```console
$ invairiant collect --range main..pr-branch --out .invairiant/cache/bundle.json
wrote evidence bundle to .invairiant/cache/bundle.json (120 candidate signal(s); raw — keep it gitignored)
```

Diff scope, tree, language stats, grep signals, import hints, generated mass,
and `known_rejected` from past audits. **Candidate pointers only — never
findings.** The raw bundle stays gitignored.

### 2 · `audit-pr` — the skill runs the pipeline *(agent)*

```text
> /invairiant audit-pr
```

The skill selects lenses by risk surface (here: `cormen`, `security-threat`,
`parnas`, `network-persistence`), runs one lens pass each over the bundle,
**adversarially verifies** every candidate (refuting two hypotheses — see
[`rejected-hypotheses.md`](../case-studies/persistent-mesh-transport/rejected-hypotheses.md)),
classifies severity, and synthesizes
[`report.json`](../case-studies/persistent-mesh-transport/report.json). The
CLI never does this part — all judgment lives in the skill.

### 3 · `report` — validate it *(CLI)*

```console
$ invairiant validate-report report.json
OK: report valid. (schema + semantic)
```

Schema **plus** the semantic pass: verdict↔severity consistency, S0/S1
confidence, reference integrity, kept hypotheses.

### 4 · `render-comment` — paste-ready PR comment *(CLI)*

```console
$ invairiant render-comment report.json
# invAIriant PR audit — persistent-mesh-transport (genuine-TLS SNI derivation)

**Verdict:** pass_with_conditions
**Audited:** … · **Lenses:** cormen, security-threat, parnas, network-persistence

## Findings

**PMT-001 (S1, security-threat, confidence high)** — The genuine-TLS SNI
fallback makes an own-cert family present the node's own certificate under the
cover domain's SNI on nodes without a wildcard cert — a cert/SNI active-probe
tell and a cross-family correlation channel.
- Evidence: diff hunk
- Risk: … detectable by active probing, and a correlation channel …
- Fix: Drop the cover fallback; reject tls_sni == cover_sni. (This is exactly
  the fix in diff.patch.)
…
```

### 5 · `ci-gate` — block the merge *(CLI)*

```console
$ invairiant ci-gate report.json; echo exit=$?
ci-gate: blocking severities ['S0', 'S1']; report verdict: pass_with_conditions
FAILED: 1 open blocking finding(s):
  ✗ PMT-001 [S1] The genuine-TLS SNI fallback makes an own-cert family …
exit=1
```

The S1 blocks the merge. A generic reviewer passed this PR; invAIriant gates it.

### 6 · `record` — remember it *(CLI)*

```console
$ invairiant record report.json
recorded into .invairiant/history/ — 3 finding(s), 2 rejected hypothes(e)s, 4 lens score(s). Sanitized; commit history/, keep cache/ local.

$ invairiant history
lens score history (oldest → newest):
  cormen                     6
  network-persistence        6
  parnas                     6
  security-threat            5
```

Sanitized memory — distilled fields only, **never raw evidence or secrets**.
The loop closes: next audit, `collect` surfaces those refuted hypotheses as
`known_rejected` so they are not re-proposed, and `validate-report` warns if a
finding revives one.

---

## Imaginary flows — same six steps, different catch

The pipeline is identical; only the risk surface, the lenses, and the catch
change. Each links a worked case study.

### A SaaS webapp PR adds a `/refunds` endpoint

`audit-pr` picks `security-threat` + `saltzer-schroeder`. A generic reviewer
praises the validation and error handling. The lens asks *what must never
happen* — and finds the new endpoint trusts a client-supplied `tenant_id`
with no complete-mediation check → **S0 `BOUNDARY_BYPASS`**. `ci-gate` →
`fail`. (Shape: [`ai-agent-refund-bot`](../case-studies/ai-agent-refund-bot/).)

### An AI-agent PR wires a model into an action

`audit-pr` picks `turing` + `oracle-boundary` + `leveson`. The reviewer likes
the clean prompt. The lens finds model output flowing into a money-movement
call with no cap, allowlist, or human step → **S0 `UNVALIDATED_ORACLE_OUTPUT`**
plus an unbounded agent loop. (See
[`ai-agent-refund-bot`](../case-studies/ai-agent-refund-bot/).)

### A big AI-generated TypeScript API lands in one PR

`audit-pr` picks `generated-surface-area` + `review-bottleneck`. The reviewer
sees "consistent, nice types." The lens diffs the near-duplicate handlers and
finds the one that silently dropped an authz check → **S1**, plus a
rubber-stamp-merge note. (See
[`generated-typescript-api`](../case-studies/generated-typescript-api/).)

### A data migration changes a schema

`audit-pr` picks `kleppmann` + `mcconnell`. The lens asks about backward
compatibility and rollback: the migration is not reversible and old readers
break mid-deploy → **S1 `MISSING_ROLLBACK`**.

---

**No tooling at all?** The same protocol runs by hand — copy a config from
[`../examples/`](../examples/) and follow
[`audit-workflow.md`](audit-workflow.md) with each lens file's Prompt Block and
the [`../templates/`](../templates/). The CLI just makes it faster and
gate-able.
