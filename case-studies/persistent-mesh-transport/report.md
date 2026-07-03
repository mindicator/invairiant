# invAIriant Audit Report

- **Date:** 2026-07-03
- **Audit type:** pr
- **Scope:** The shell renderer for an own-certificate genuine-TLS transport family (transport/render_params.sh, render_server.sh) and its tls_sni derivation. Illustrative case, synthesized from a real, fixed defect class; no project is named.

## Executive Summary

The renderer's genuine-TLS SNI fallback (|| tls_sni=$cover) makes the own-cert family present its own certificate under the cover domain's SNI on nodes without a wildcard cert — a cert/SNI active-probe tell and a cross-family correlation channel (PMT-001, S1). The invariant is not enforced and the guard's fail-closed docstring is false (PMT-002). A diff-level reviewer approves a documented, working fallback; the lenses do not. Live nodes with real wildcard certs are unaffected, holding PMT-001 at S1. ci-gate blocks the merge until fixed.

**Verdict:** pass_with_conditions

## Lens Scores

| Pack | Lens | Score | Verdict |
|---|---|---:|---|
| core | cormen | 6 | the 'own-cert SNI ≠ cover SNI' invariant is not enforced; correctness depends on an incidental wildcard SAN and the guard's fail-closed docstring is false (PMT-002) |
| security-safety | security-threat | 5 | on a no-wildcard-SAN node the own-cert family emits a cert/SNI active-probe tell + correlation channel (PMT-001) |
| core | parnas | 6 | the SNI decision is split across two shell files with a silent fallback and no typed owner (PMT-003) |
| domain | network-persistence | 6 | indistinguishability regresses for the affected node class (PMT-001) |

## High Findings (S1)

### PMT-001 — The genuine-TLS SNI fallback makes an own-cert family present the node's own cer (S1, security-threat, confidence: high)

- **Claim:** The genuine-TLS SNI fallback makes an own-cert family present the node's own certificate under the cover domain's SNI on nodes without a wildcard cert — a cert/SNI active-probe tell and a cross-family correlation channel.
- **Evidence:**
  - diff_hunk
  - file_lines — transport/render_params.sh:40-52 — on a self-signed cert (CN=cover domain, no wildcard SAN) the wildcard grep is empty, so tls_domain becomes $cover
  - doc_code_contradiction — the SNI guard rejects only an EMPTY tls_sni; the non-empty cover fallback passes, so the fail-closed claim is false and the tell ships
- **Risk:** The own-cert genuine-TLS family serves the node's own certificate under the cover domain's SNI: a cert/SNI mismatch detectable by active probing, and a channel correlating the own-cert family with the camouflaged family by shared SNI. Directly hits traffic indistinguishability and anonymity.
- **Recommendation:** Drop the cover fallback; leave tls_sni empty when no own-cert domain is derivable so the guard genuinely fail-closes; additionally reject tls_sni == cover_sni. (This is exactly the fix in diff.patch.)
- **Category:** DISTINGUISHABLE_TRANSPORT

## Medium Findings (S2)

### PMT-002 — The invariant that an own-cert family's SNI must never equal the cover SNI is no (S2, cormen, confidence: high)

- **Claim:** The invariant that an own-cert family's SNI must never equal the cover SNI is not enforced; correctness depends on whether a wildcard SAN incidentally exists, and the guard's stated fail-closed property is false.
- **Evidence:**
  - file_lines — transport/render_server.sh:8-11 — the SNI guard is `[ -n "$_tls_sni" ] || die` — it rejects an empty value only, not tls_sni == cover_sni
  - doc_code_contradiction — the documented invariant is not the one the guard checks
- **Risk:** A security property that holds 'because of how it is called' (whether a wildcard cert happens to exist) is not a design property; the false docstring hides the gap from the next reader.
- **Recommendation:** Enforce the invariant explicitly (reject tls_sni == cover_sni for enabled own-cert families) and make the docstring describe what the guard actually checks.

## Unsupported Hypotheses

- All production nodes are exposed by this tell. — Refuted — live nodes use a real wildcard cert, so the wildcard-SAN branch derives tls_sni and the cover fallback is never taken. Only nodes on a built-in self-signed cert (no wildcard SAN) are affected. This is why PMT-001 is held at S1, not S0.
- The SNI guard already prevents the tell (it 'fails closed'). — Refuted — the guard rejects only an EMPTY tls_sni; the cover fallback yields a non-empty value that passes. The docstring's fail-closed claim does not match the code.

