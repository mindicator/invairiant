# Severity Model

> **Status:** protocol core. Severity is assigned only to findings that passed
> evidence verification ([evidence-rules.md](evidence-rules.md)). Severity
> derives from risk to the project's declared assets — not from score
> arithmetic, and not from how eloquent the finding is.

## 1. Severity levels

| Level | Name | Gate effect |
|---|---|---|
| **S0** | Critical | Blocks merge / release / phase transition until fixed or formally risk-accepted by the project owner in writing. |
| **S1** | High | Must be fixed before the next major step (release, phase transition, surface expansion). |
| **S2** | Medium | Significant architecture or safety debt; scheduled in the next work cycle. |
| **S3** | Low | Undesirable but non-critical; planned as an improvement. |
| **NOTE** | Note | Observation without mandatory immediate action. |

Generic examples:

- **S0** — a secret or key in code, logs, or exported telemetry; a silent
  fallback that sacrifices a declared safety/privacy property; a single
  component whose failure halts the whole system without a fallback; an
  irreversible compatibility break; model output mutating production state
  with no validation layer.
- **S1** — declared redundancy that has collapsed to a single real path; a
  threat-model row closed on paper but not in code; an agent loop without
  enforced bounds (not yet reachable from production input); logging more
  than justified without direct PII exposure; a high-blast-radius change with
  no rollback.
- **S2** — a mandatory lens scoring below threshold with debt but no
  concrete incident path; doc/code drift on non-contract documentation;
  copy-pasted abstractions accumulating divergence.
- **S3 / NOTE** — naming that misleads; a missing convenience diagnostic;
  observations worth tracking.

## 2. Score scale

Lens scores use a 0–10 scale, identical in every lens file:

| Score | Meaning |
|---:|---|
| 0–2 | Dangerous / uncontrolled |
| 3–4 | Prototype with serious architectural risk |
| 5–6 | Meaningful but debt-heavy |
| 7 | Strong prototype |
| 8 | Strong engineering, not yet boring |
| 9 | Near-reference, survives growth |
| 10 | Mature, boring, repeatedly proven |

A score is a *claim about the system* and follows the evidence rules: every
score must reference the repo/doc/test state that justifies it.

## 3. Score → severity mapping

1. Score **below 6.0 on any mandatory lens** → a finding of at least **S2**
   explaining the gap.
2. Score **below 5.0 on any mandatory lens**, linked to a concrete
   architectural risk → at least **S1**.
3. Score **below 5.0 on a critical lens** (security, safety, privacy, or a
   domain lens guarding the project's core risk), linked to a concrete user
   or operational risk → **S0**, unless a written justification explains why
   not.
4. Thresholds are configurable per project
   (`severity_policy.low_score_threshold`, `critical_domain_threshold` in
   `invairiant.config.yml`); the defaults are 6.0 / 5.0.
5. Every threshold-triggered finding still needs evidence — the score alone
   is the trigger, not the proof.

## 4. Interpretation rules

These rules exist so that scores inform and never launder:

1. **A high average score never cancels an S0/S1 finding.** There is no
   arithmetic in which "9/10 on eight lenses" outweighs one unbounded
   production risk.
2. A low score must be explained by a concrete architectural or user risk —
   not by taste.
3. A score must not be a compliment or an aesthetic opinion.
4. Every score references the actual state of repo, docs, tests, or CI.
5. If a lens score falls for two consecutive audits, an action item is
   opened even if both scores are above threshold.
6. If a mandatory lens scores below 6.0, the next major step must include a
   written explanation of why work proceeds without a stabilization pass.
7. If a critical lens scores below 5.0 with an open S0/S1 cluster, phase
   transitions and surface expansion (new public endpoint, new membership
   class, new automation authority) are prohibited until the cluster closes.
8. **Domain lenses outrank general-engineering lenses** when they conflict:
   a project's value is its core property (safety, availability, privacy,
   reachability), not clean code. Generalization of the same rule: the lens
   closest to the project's declared risk assets wins ties.

## 5. Confidence × severity

| Confidence | May carry |
|---|---|
| high | S0–S3, NOTE |
| medium | S0–S3, NOTE |
| low | **observation only** — not a finding |

- S0/S1 findings **require** high or medium confidence
  (schema-enforced).
- The one exception path for uncertainty is security-critical uncertainty
  per [evidence-rules.md §8](evidence-rules.md): concrete risk + concrete
  evidence gap, phrased as what is unknown, not as what is assumed.

## 6. Named finding categories (starter registry)

Recurring defect patterns get fixed names and default severities so audits
across time and auditors stay comparable. Generic starter registry:

| ID | Default | Description |
|---|---|---|
| `SECRET_LEAK` | **S0** | A secret, key, or credential appears in code, logs, artifacts, or exported telemetry. |
| `SINGLE_POINT_OF_FAILURE` | **S0** | One component/domain/provider whose loss halts the whole system; declared fallbacks absent or untested. |
| `SILENT_DEGRADATION` | **S0** | A fallback silently sacrifices a declared safety, privacy, or correctness property to keep going, with no explicit, documented degradation policy. |
| `BOUNDARY_BYPASS` | **S0** | A hidden channel or direct cross-module link bypasses a declared contract between layers/services. |
| `CONFLICTING_SOURCE_OF_TRUTH` | **S0** | Two or more components hold conflicting authority over the same fact, with no single owner. |
| `UNVALIDATED_ORACLE_OUTPUT` | **S1** | Model/heuristic output reaches state mutations, shell, SQL, or user-visible actions without a deterministic validation layer. Escalates to **S0** when reachable from untrusted input or affecting production state. |
| `UNBOUNDED_AUTONOMY` | **S1** | An automation/agent loop lacks enforced bounds (iterations, deadline, budget, authority). Escalates to **S0** when it can mutate production unattended. |
| `THREAT_MODEL_DRIFT` | **S1** | Attack surface or protected assets changed without a threat-model update, or a documented attack response exists only on paper. |
| `REDUNDANCY_COLLAPSE` | **S1** | Declared redundancy has effectively collapsed to a single real option (provider, path, instance, region). |
| `PRIVACY_SCOPE_CREEP` | **S1** | A component learns or retains more about users than its contract requires. Escalates to **S0** when it links identity to sensitive behavior or location. |
| `MISSING_ROLLBACK` | **S1** | A high-blast-radius change (migration, schema, contract) ships without a rehearsed rollback or staged migration. |
| `REVIEW_DEBT_OVERFLOW` | **S2** | Generated/changed code volume exceeds demonstrated review capacity with no compensating deterministic gates. Escalates to **S1** for security-relevant surfaces. |
| `DOC_CODE_DRIFT` | **S2** | Canonical docs describe a system that no longer exists. Escalates to **S1** when the doc is a contract, runbook, or threat model. |

Projects extend this registry in `invairiant.config.yml`
(`named_categories`), and domain packs ship their own — the
network-persistence pack, for example, carries categories for
distinguishable transports, enumeration exposure, and kill-switch
centralization inherited from its origin project.

## 7. Verdicts and aggregation

Report verdicts (`pass` / `pass_with_conditions` / `fail`) derive from open
findings, not from scores:

- any open **S0** → `fail` for the gate under audit;
- any open **S1** → at best `pass_with_conditions`, with each condition named,
  owned, and blocking the step it must precede;
- S2/S3/NOTE → `pass` with scheduled actions.

A weighted summary score (domain lenses weighted above general-engineering
lenses) **may** be published as a readability aid. It is never a merge gate.
The gate is this severity model.

## 8. Changing a severity

- Escalation or de-escalation requires a written justification referencing
  evidence, recorded in the finding.
- De-escalating an S0/S1 requires naming the compensating control or the
  evidence that voids the risk — "we need to ship" is not a compensating
  control.
- Named-category defaults may be overridden per instance, with the same
  written-justification requirement.
