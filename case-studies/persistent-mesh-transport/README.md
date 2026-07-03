# Case study — persistent-mesh-transport (illustrative)

> **Illustrative / synthesized.** This models a real, *fixed* class of defect in
> persistent-mesh transports; no project is named and the specifics are
> generic. The architectural lesson is the point.

## Context

A persistent-mesh node renders its own transport configs from shell
(`transport/*.sh`). Two families run side by side:

- an **own-certificate TLS family** — presents the node's own certificate, so
  its SNI (`tls_sni`) must be the node's own domain;
- a **camouflaged family** — hides behind a **cover domain** (a decoy site the
  traffic is disguised as), whose SNI is a **separate** field, `cover_sni`.

The own-cert family's SNI must **never** be the cover domain.

## The change under review

The renderer derives `tls_sni` from the served wildcard cert's SAN, with a
fallback:

```sh
tls_domain="$(cert_san ... | grep 'DNS:*.<zone>' | sed 's/*./m./')"
[ -n "$tls_domain" ] || tls_domain="$cover"       # <-- the fallback
```

and a downstream guard that "fails closed":

```sh
# docstring: "...a misconfigured node fails closed rather than shipping a cert/SNI tell."
[ -n "$_tls_sni" ] || die "... tls_sni is empty ..."   # rejects EMPTY only
```

It builds, it has a documented fallback, and it has a guard that says it fails
closed. A diff-level reviewer approves.

## What invAIriant caught

On a node whose cert has **no wildcard SAN** (e.g. a built-in self-signed cert,
`CN=<cover domain>`, no SAN), the fallback sets `tls_sni = $cover`. The guard
only rejects an *empty* value, so the cover value sails through. Result: the
node serves its **own** certificate under the **cover domain's SNI** — a
cert/SNI-mismatch **active-probe tell**, and a **correlation channel** linking
the own-cert family to the camouflaged family by shared SNI. The "fails closed"
docstring is simply false for this input.

Three lenses converge:

- **cormen** — the invariant *own-cert SNI ≠ cover SNI* is not enforced;
  correctness depends on whether a wildcard SAN incidentally exists, and the
  guard's stated fail-closed property is false (`PMT-002`).
- **security-threat** — the emitted config is distinguishable under active
  probing and creates a correlation channel (`PMT-001`).
- **parnas / network-persistence** — a security-critical SNI decision lives in
  scattered shell with a silent fallback and no typed owner (`PMT-003`).

## Outcome

Verdict **pass_with_conditions** — one S1 (`PMT-001`) blocks release until
fixed. `invairiant ci-gate` on this report **exits non-zero**, so the merge is
gated. `PMT-001`'s recommendation is exactly [`diff.patch`](diff.patch): drop
the cover fallback, leave `tls_sni` empty when no own-cert domain is derivable
(so the guard genuinely fail-closes), and additionally reject
`tls_sni == cover_sni`.

Files: [`report.json`](report.json) · [`report.md`](report.md) ·
[`rejected-hypotheses.md`](rejected-hypotheses.md) ·
[`ai-reviewer-miss.md`](ai-reviewer-miss.md) · [`invairiant.config.yml`](invairiant.config.yml)
