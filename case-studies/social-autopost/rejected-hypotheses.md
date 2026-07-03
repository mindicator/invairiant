# Rejected hypotheses — social-autopost

Kept, not deleted. Each was proposed during the lens passes and **refuted** at
the evidence-verification stage. Recording them stops the next audit from
re-litigating the same ground, and it is why the finding landed where it did.

### H1 — "The rate limiter / circuit breaker already gates what gets published." → **Refuted**

The first instinct on seeing this path is that all the defensive plumbing must
be gating it. Verification reads the plumbing: the rate limiter, the circuit
breaker, and the concurrency lock (`services/action_pipeline.py:74-180`) bound
how **often** and how **reliably** the loop posts — VOLUME and MECHANICS. **None
of them inspects the content.** A perfectly rate-limited, circuit-broken,
lock-serialized loop still publishes whatever text the model emitted. These
guards are real; they just guard the wrong axis, and that is precisely the
safety theater that makes `SAP-001` easy to miss.

### H2 — "A human reviews the content before it posts." → **Refuted**

If a human approved each post, the missing gate would be a documentation nit,
not an S1. Verification reads the trigger: the publish is driven by an
**autonomous background loop** (`services/monitor.py:88-95`), not a manual or
API call. Nothing on the executing path blocks on human approval. There is no
human-in-the-loop between the model output and the live post — so "a human
reviews it" is not a control that exists in the system.

### H3 — "The model won't emit anything harmful, so a gate is unnecessary." → **Refuted**

Tempting, and the reason so many LLM-to-action paths ship ungated. But treating
probabilistic output as safe *by construction* has no basis, and here it is
worse than a generic hope: the upstream post text is **interpolated into the
prompt** (`services/auto_publish.py:242-252`), so untrusted input can steer the
completion. "The model behaves" is not a control; it is a wish — and in this
system the input is attacker-influenceable, which is exactly what pushes
`SAP-001` toward S0.
