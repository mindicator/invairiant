# invAIriant PR Audit — <PR # / title>

<!--
Compact format for posting as a PR comment. Full rules still apply:
no evidence, no finding; unsupported concerns go to Observations.
Scope: the diff + its blast radius. At most TWO focused lenses —
a small PR does not trigger a full philosophical tribunal.
-->

**Verdict:** <!-- pass | pass_with_conditions | fail -->
**Audited:** <commit range> · **Lenses applied:** <checklist + e.g. turing, security-threat>

## Checklist

<!-- Generic PR-audit checklist; extend via your invairiant.config.yml.
     Check = verified, not assumed. -->

- [ ] Module/layer boundaries intact; no new hidden channel or direct
      cross-boundary link bypassing a declared contract
- [ ] No component learns more about users than its contract allows
- [ ] Attack surface unchanged, or the threat model was updated
- [ ] No secret/key/credential in code, diff, logs, or telemetry
- [ ] No silent degradation: no fallback that sacrifices a declared
      safety/privacy/correctness property without an explicit policy
- [ ] Automation/model authority unchanged, or bounds + validation updated
      (loops bounded, oracle output validated before state mutation)
- [ ] Compatibility with deployed instances preserved (or migration staged)
- [ ] Rollback exists for high-blast-radius changes
- [ ] Tests accompany the change; canonical docs updated where touched
- [ ] Change is explainable and localized; blast radius matches version bump

## Findings

<!-- Verified findings only. One block each: -->

**<ID> (<S0|S1|S2|S3>, <lens>, confidence <high|medium>)** — <claim>
- Evidence: `path:lines` — <what it shows>
- Risk: <one line>
- Fix: <one line>

## Conditions (if pass_with_conditions)

<!-- Each condition: what, owner, must land before <step>. -->

1.

## Observations / Hypotheses (non-blocking)

<!-- Evidence-light items, honestly labeled. Not findings. -->

-
