# Rejected hypotheses — persistent-mesh-transport

Kept, not deleted. Each was proposed during the lens passes and **refuted** at
the evidence-verification stage. Recording them stops the next audit from
re-litigating the same ground, and it is why the severity landed where it did.

### H1 — "All production nodes are exposed by this tell." → **Refuted**

A first read of `PMT-001` suggests every node ships the cert/SNI tell, which
would make it S0. Verification refutes it: live nodes are provisioned with a
**real wildcard certificate**, so the wildcard-SAN branch derives `tls_sni` and
the `|| tls_sni=$cover` fallback is never taken. Only nodes running on a
built-in **self-signed** cert (no wildcard SAN) hit the fallback. The blast
radius is a node *class*, not the fleet — so `PMT-001` is held at **S1**
(escalates to S0 on an affected node), not S0 across the board.

### H2 — "The SNI guard already prevents this; it 'fails closed'." → **Refuted**

The docstring claims the downstream guard fail-closes a misconfigured node.
Verification reads the guard: `[ -n "$_tls_sni" ] || die ...`. It rejects an
**empty** `tls_sni` only. The cover fallback produces a **non-empty** value,
which passes. The guard's real behavior does not match its documented behavior
— that gap is itself `PMT-002`.

### H3 — "Rendering in shell is the root cause; rewrite it in a typed engine." → **Demoted to observation**

Tempting, but out of scope for this PR and not a defect on its own. The
untyped-shell ownership is recorded as `PMT-003` (S3); it is context for the
fix, not a blocker for this diff. Demoted, not dropped.
