# Finding: <ID> — <short title>

<!--
One finding, full form. Machine-readable form: schemas/finding.schema.json.
Hard rules:
  - At least one concrete evidence item, or this is not a finding —
    record it as an observation/hypothesis/open question instead.
  - S0/S1 require high or medium confidence.
  - Severity is assigned to VERIFIED findings only.
-->

- **ID:** <!-- e.g. INV-014 (prefix from config severity_policy.id_prefix) -->
- **Severity:** <!-- S0 | S1 | S2 | S3 | NOTE — per docs/severity-model.md -->
- **Lens:** <!-- lens id, e.g. parnas -->
- **Category:** <!-- optional named category, e.g. BOUNDARY_BYPASS -->
- **Confidence:** <!-- high | medium | low (low => demote to observation) -->
- **Status:** <!-- candidate | verified | rejected -->
- **Source:** <!-- human | ai | hybrid -->
- **Affected components:**

## Claim

<!-- One falsifiable sentence. Not a feeling, not a question.
     Bad:  "The routing layer seems too coupled to the transport."
     Good: "The routing layer reads transport internals directly,
            bypassing the declared data-plane contract." -->

## Evidence

<!-- One bullet per item. Valid types (schemas/finding.schema.json):
     file_lines, diff_hunk, test_failure, missing_test,
     doc_code_contradiction, ci_output, runtime_log, incident,
     command_output, schema_config_mismatch. -->

- `file_lines` — `internal/router/router.go:120-148` @ <commit>: <what it shows>
- `doc_code_contradiction` — `docs/ARCHITECTURE.md:88` vs `internal/router/router.go:120`: <the contradiction>

## Risk

<!-- What concretely goes wrong if unaddressed, and for whom (user,
     operator, availability, data). Tie to the project's risk_assets. -->

## Recommendation

<!-- The fix or mitigation. Prefer recommendations that make the defect
     class impossible (conformance test, CI gate, interface change) over
     "be more careful". -->

## Verification

- **Verified by:**
- **Method:** <!-- file read / command re-run / test executed / docs cross-read -->
- **Notes:**

## Links

<!-- Related findings, issues, ADRs, incident reports. -->
