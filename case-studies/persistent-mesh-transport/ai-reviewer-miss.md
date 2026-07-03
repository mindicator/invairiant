# What a normal AI reviewer missed — persistent-mesh-transport

The diff is a few lines of shell that derive a TLS SNI, with a documented
fallback and a guard that says it fails closed. Here is the gap between a
diff-level reviewer and an invAIriant lens pass.

## A generic AI PR reviewer says

> ✅ Looks good. Clean use of cert-SAN parsing to pull the SNI. The
> `|| tls_domain="$cover"` fallback is a sensible default so the field is never
> empty, and it's clearly commented. The downstream guard `die`s on an empty
> value, so a misconfigured node fails closed. Nice defensive coding. Approving.

Every sentence is *locally* true. The code works, the fallback is documented,
the guard exists. Nothing here is wrong at the diff level — which is exactly
why it merges.

## invAIriant's lens pass says

**cormen (invariants).** What invariant must this code preserve? *An own-cert
family's SNI must never equal the cover SNI.* Is it enforced? No — it holds
only if a wildcard SAN happens to exist. The guard the comment points to checks
a *different* property (non-empty), so the stated "fails closed" is false.
→ `PMT-002`.

**security-threat (the tell).** Follow the fallback to its worst input: a
self-signed cert with no wildcard SAN. Then `tls_sni = $cover`, and the node
serves its **own** certificate under the **cover domain's SNI** — a cert/SNI
mismatch an active prober can see, plus a correlation channel between two
families that must look unrelated. → `PMT-001`.

**parnas (ownership).** A security-critical decision lives in two shell files
that must agree by hand, with no typed contract owning it. → `PMT-003`.

## The difference in one line

> The reviewer asked **"is this code correct?"** and the answer was yes.
> The lens asked **"what must never happen, and is that guaranteed?"** — and the
> answer was no.

## Why the process matters, not just the catch

- **Evidence-bound:** every claim cites the fallback line, the guard, and the
  docstring/code contradiction — a second reviewer verifies it in minutes.
- **Severity is honest:** the "all nodes exposed" hypothesis was *refuted*
  (live nodes use real wildcard certs), so this is S1, not S0 theatre.
- **Gated deterministically:** `invairiant ci-gate report.json` exits non-zero
  on the S1, so the merge is blocked until the fix.
