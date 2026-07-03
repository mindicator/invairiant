# invAIriant Audit Report

- **Date:** 2026-07-03
- **Audit type:** pr
- **Scope:** Focused PR audit of the auto-publish path: an autonomous background loop that takes a raw completion from a hosted LLM and publishes it as a public post on a third-party social platform, and the action pipeline that carries it there. Two lenses scored in depth (oracle-boundary, leveson) with turing as supporting; other mandatory lenses out of scope for this PR. REAL finding, REDACTED: the project and platform are withheld and the file paths are generic stand-ins for the real modules. Finding is OPEN (not fixed).

## Executive Summary

The auto-publish path takes a raw hosted-LLM completion and publishes it as a public post under a managed account with no deterministic gate in between — no schema validation, allowlist, content moderation, length/format contract, or human approval; the only thing between 'model emitted text' and 'text is live' is a post-frequency counter (SAP-001, S1, oracle-boundary). There is no boundary artifact at all, so the effective content policy is 'whatever the model outputs today', and because the upstream post text is interpolated into the prompt (services/auto_publish.py:242-252), that output is reachable from untrusted input into an irreversible public action — which is why SAP-001 trends toward S0. The loop runs autonomously with no human override on the executing path, no content precondition, and no effect feedback (SAP-002, S2, leveson). The tell is the project's own docs: they loudly document a SIBLING pipeline as deliberately deterministic, no-LLM, and human-approved, while this pipeline does the exact opposite and no doc marks the difference. The service LOOKS defensively engineered — circuit breaker, concurrency lock, rate limiting, human-like delays, logging, passing tests — but every guard protects VOLUME and MECHANICS, none protects CONTENT, so the composed system reliably publishes unsafe text and the safety theater disguises the gap. Finding is OPEN. A diff-level reviewer approves the defensive plumbing; the lenses do not.

**Verdict:** pass_with_conditions

## Lens Scores

| Pack | Lens | Score | Verdict |
|---|---|---:|---|
| ai-generated-code | oracle-boundary | 2 | model output reaches an external publish with no validation between; there is no boundary artifact at all — nothing written about what the model may decide and no deterministic disposition of what it emits (SAP-001) |
| security-safety | leveson | 3 | an autonomous, irreversible public action with unbounded authority per run: no content precondition at execution time, no human override on the executing path, and no effect feedback — docs even note posts can be silently shadowbanned with no auto-detection (SAP-002) |
| core | turing | 4 | probabilistic output is treated as truth: the model's text is published as-is and the garbage/empty/injected path is undefined and untested, so there is no defined system state for 'the model emitted something unsafe' |

## High Findings (S1)

### SAP-001 — A raw completion from a hosted LLM is auto-published as a public post on a third (S1, oracle-boundary, confidence: high)

- **Claim:** A raw completion from a hosted LLM is auto-published as a public post on a third-party social platform with no deterministic gate — no schema validation, no allowlist, no content moderation, no length/format contract, and no human approval — between the model output and the publish call.
- **Evidence:**
  - file_lines — services/auto_publish.py:139 — the raw model text is taken and, at :155-166, passed unmodified into the publish action; nothing between the model call and the publish inspects, validates, bounds, or moderates the content
  - file_lines — services/model_client.py:120-128 — the hosted-LLM client returns the model content only stripped and truncated (and None on failure); it applies no schema, no allowlist, and no content contract — this is the only transformation the text receives before publication
  - file_lines — services/action_pipeline.py:74-180 — the publish action validates account existence, platform match, a concurrency lock, and rate limits, but never inspects the content it is about to publish — every guard is about VOLUME and MECHANICS, none about WHAT is posted
  - file_lines — services/auto_publish.py:242-252 — the upstream post text is interpolated directly into the prompt, so untrusted upstream content is a prompt-injection vector into an irreversible public action; the model output the gate would need to catch is itself attacker-influenceable
  - doc_code_contradiction — this pipeline does the exact opposite of its documented sibling — unreviewed LLM text published autonomously — and no doc marks the difference; the project's own written standard for a public-writing pipeline is determinism + human approval, which this path silently violates
  - missing_test — the auto-publish service's tests exercise only no-op paths (no configs present / feature disabled / target account not found); the publish path itself is never exercised, and no test feeds empty, oversized, hostile, or prompt-injected model output through to the publish boundary
- **Risk:** There is no boundary artifact at all — nothing written down about what the model may decide, and no deterministic disposition of what it emits — so the effective content policy for a public identity is 'whatever the model outputs today'. A model regression, a bad completion, or a crafted upstream post publishes unsafe, off-brand, or attacker-chosen text under the managed account, publicly and irreversibly, with no chance to intervene. This trends toward S0 rather than staying a contained S1 because the prompt-injection vector (services/auto_publish.py:242-252) makes the unsafe output reachable from untrusted input AND the action is public and irreversible — the escalation condition for UNVALIDATED_ORACLE_OUTPUT; it is held at S1 here only because the audit has not demonstrated a concrete injection-to-publish exploit end to end.
- **Recommendation:** Insert a deterministic gate between the model and the publish call: schema/allowlist validation plus an explicit length/format contract, and a human-approval (or auto-block) step before anything is published. Treat the model's score and text as a candidate, never as truth. Add tests that feed empty, oversized, hostile, and prompt-injected model output through to the (mocked) publish boundary and assert it is blocked. Write down the boundary — which decisions the model may make and which stay deterministic — and mark, in the docs, how this pipeline differs from its deterministic sibling.
- **Category:** UNVALIDATED_ORACLE_OUTPUT

## Medium Findings (S2)

### SAP-002 — The auto-publish loop wields unbounded automation authority over an irreversible (S2, leveson, confidence: high)

- **Claim:** The auto-publish loop wields unbounded automation authority over an irreversible public action: there is no human override on the executing path, no content precondition enforced at execution time, and no feedback confirming the effect of what it published.
- **Evidence:**
  - file_lines — services/monitor.py:88-95 — the publish is driven by an autonomous background loop (not a manual or API trigger); nothing on this path waits for a human, so 'a human reviews it before it posts' is not a control that exists in the loop
  - file_lines — services/action_pipeline.py:74-180 — the only preconditions checked at execution time are account existence, platform match, a concurrency lock, and rate limits — all of which bound how OFTEN and how MECHANICALLY it posts; none is a content precondition, so the action is issued regardless of whether the text is safe in the current state of the world
  - doc_code_contradiction — the docs acknowledge a public post can be silently suppressed by the platform, yet the executing path has no effect feedback and no auto-detection of it — the controller acts, then never learns whether the action had the intended effect or was penalized
  - missing_test — no test exercises the composed publish behavior or any override/abort during the autonomous loop; only no-op paths (disabled / no configs / target-not-found) are covered, so the unsafe composition is entirely unexercised
- **Risk:** Every guard on this path protects volume and mechanics; none protects content or gives an operator a way to stop or reverse a bad post in flight. An unsafe or attacker-chosen post is issued autonomously, publicly, and irreversibly, and because there is no effect feedback the system cannot even tell that the managed account has been penalized or shadowbanned afterward — the operator's model of 'we are posting fine' can drift arbitrarily far from reality.
- **Recommendation:** Bound the automation's authority with a content precondition enforced at execution time (a deterministic validation/allowlist + length/format contract) and a human-approval or auto-block step before publish; add a real override/kill path on the executing loop, not just in a runbook; add effect feedback (confirm the post's live status, detect suppression) and alarm on divergence; add tests for override-during-loop and for the composed publish behavior under empty/oversized/hostile/injected output.

## Unsupported Hypotheses

- The rate limiter / circuit breaker already gates what gets published. — Refuted — the rate limiter, the circuit breaker, and the concurrency lock (services/action_pipeline.py:74-180) bound how OFTEN and how reliably the loop posts, i.e. VOLUME and MECHANICS. None of them inspects the content, so none is a gate on WHAT is published. A perfectly rate-limited, circuit-broken loop still publishes whatever text the model emitted.
- A human reviews the content before it posts. — Refuted — the publish is driven by an autonomous background loop (services/monitor.py:88-95), not a manual or API trigger. Nothing on the executing path blocks on human approval, so there is no human-in-the-loop review between the model output and the live post.
- The model won't emit anything harmful, so a gate is unnecessary. — Refuted — there is no basis for treating probabilistic output as safe by construction, and a concrete prompt-injection vector exists: the upstream post text is interpolated into the prompt (services/auto_publish.py:242-252), so untrusted input can steer the completion. 'The model behaves' is a hope, not a control, and here the input is attacker-influenceable.

