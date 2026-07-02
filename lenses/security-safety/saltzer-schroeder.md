# Saltzer–Schroeder Lens — Security Design Principles

**Pack:** security-safety · **ID:** `saltzer-schroeder`

## Purpose

This lens protects against security architecture that exists as slogans
rather than as observable properties of the code: credentials wider than
their function, checks that fail open, authorization decisions cached past
revocation, security logic smeared across the codebase until nobody can
review it all, and secure paths so painful that people build bypasses.

The question underneath every check: **can you point to the line where the
principle holds — or the line where it breaks?**

## Scope

**Use when:**

- the system authenticates, authorizes, or isolates principals (users,
  services, tenants, jobs);
- a change touches credentials, roles, policy evaluation, session handling,
  or cryptography;
- dangerous operations exist (deletion, payout, deploy, credential minting)
  whose misuse would be expensive;
- multiple principals share infrastructure: caches, queues, temp storage,
  connection pools.

**Skip when:**

- the code path has a single principal and no privilege boundary (an
  offline tool run only by its author) — note that explicitly instead of
  scoring;
- the question is threat-model coverage as a whole — that belongs to the
  Security / Threat lens; this lens audits the design principles inside it.

## Core Questions

- Least privilege: does each service account, token, and role hold only the
  permissions its code actually exercises? What is the widest credential in
  the system, and what uses that width?
- Fail-safe defaults: when a policy fetch, permission lookup, or dependency
  fails, does the system deny? Is the default branch of every access
  decision a refusal?
- Complete mediation: is every access checked at time of use? Can a cached
  authorization decision outlive revocation, letting a disabled principal
  keep operating?
- Economy of mechanism: how large is the security kernel — authentication,
  authorization, sessions, crypto? Could one reviewer read all of it in a
  sitting, and does it live in one place?
- Open design: does any security property depend on the design staying
  secret — an undocumented endpoint, a magic parameter, home-grown crypto?
- Separation of privilege: do dangerous actions require two independent
  conditions (second approver, key plus confirmation), or does one
  credential suffice?
- Least common mechanism: what state is shared between principals (caches,
  temp dirs, pools), and can one principal influence what another observes?
- Psychological acceptability: is the secure path also the easy path, or do
  docs, scripts, and deadlines teach people to route around it?

## Good-State Examples

- Each service runs with a per-purpose credential; the deploy pipeline's
  token cannot read user data, and granted permissions are enumerated in a
  reviewed manifest that CI diffs against actual API usage.
- The authorization middleware denies by default: unknown routes return
  403, and a policy-engine timeout produces a deny plus an alert — with a
  conformance test asserting both behaviors.
- Session revocation propagates within a documented TTL; a test revokes a
  principal and asserts that cached authorization decisions expire on
  schedule.
- Authentication, authorization, and crypto live in one small, owned
  package; every endpoint goes through it, and the crypto is a vetted
  library rather than local invention.
- Deleting a production dataset requires a second approver; the break-glass
  path exists but is separately authenticated, time-boxed, and pages the
  security owner when used.

## Red Flags

- A catch-all admin credential shared by several services "temporarily,"
  with no removal trigger recorded anywhere.
- An access-check error branch that logs a warning and proceeds — failure
  ends in the unsafe state.
- Authorization evaluated only at login; long-lived sessions or cached
  decisions are never re-checked against revocation.
- Security checks copy-pasted per endpoint instead of enforced at one
  mediated chokepoint — and at least one endpoint missing them.
- An internal endpoint whose only protection is that it is not documented.
- A dangerous operation gated by a single flag, header, or key that any one
  credential can supply.
- A shared cache or temp directory keyed without the tenant or principal,
  so one principal can seed what another reads.
- Onboarding docs or helper scripts that disable TLS verification, widen
  permissions, or skip review "to get unblocked."

## Required Evidence

Findings under this lens must cite one or more of:

- file path + line range
- diff hunk
- test failure
- missing test
- doc/code contradiction
- runtime log
- incident report
- CI output
- configuration/schema mismatch

Typical for this lens: the fail-open branch of an access check (file +
lines); a configuration/schema mismatch between granted and exercised
permissions (IAM manifest vs call sites); a missing test for
deny-on-dependency-failure or for revocation propagation; a doc/code
contradiction where a runbook instructs bypassing a control. A principle
"probably violated" with no such citation is an observation, not a finding.

## Scoring Rubric

| Score | Meaning |
|---:|---|
| 0–2 | Dangerous / uncontrolled |
| 3–4 | Prototype with serious architectural risk |
| 5–6 | Meaningful but debt-heavy |
| 7 | Strong prototype |
| 8 | Strong engineering, not yet boring |
| 9 | Near-reference, survives growth |
| 10 | Mature, boring, repeatedly proven |

## Finding Examples

### S1 Example

Claim: The API gateway's authorization middleware fails open: when the
policy service is unreachable, the request proceeds as if permitted.

Evidence: `gateway/middleware/authorize.ts:57-74` — the `catch` block logs
`policy check skipped` and calls `next()`; no test under `tests/gateway/`
exercises a policy-service timeout (missing test).

Risk: Any policy-service outage — accidental or induced — becomes an
authorization bypass on every route behind the gateway; an attacker who can
degrade one dependency gains access everywhere, and nothing would alert.

Recommended fix: Deny on policy-evaluation failure with a typed outcome and
an alert; add a conformance test asserting timeout → 403; treat fail-open
access checks as a merge blocker in the review guidelines.

### S2 Example

Claim: The report worker holds write and delete permissions on all storage
buckets while its code performs only reads from a single prefix.

Evidence: `deploy/iam/report-worker.yaml:12-31` grants `storage:*` on `*`;
the worker's only storage calls are reads in
`workers/reports/fetch.py:40-66` (configuration/schema mismatch between
granted and exercised permissions).

Risk: A compromise of the least-important worker becomes a full data-plane
compromise: the blast radius is defined by the credential, not by the
function, and the excess grant is invisible in ordinary code review.

Recommended fix: Scope the credential to read-only access on the one
prefix; add a CI policy check that diffs granted permissions against
exercised API calls and fails on unused write or delete grants.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Saltzer–Schroeder Lens (id: saltzer-schroeder) from
the invAIriant audit protocol: security design principles.

Examine the provided code/diff/docs for:
- credentials, roles, and tokens wider than what the code exercises
  (least privilege), and shared state between principals (least common
  mechanism);
- error and default branches of access decisions: whether failure ends in
  deny (fail-safe defaults);
- access checks skipped or cached past revocation (complete mediation);
- the size and concentration of the security kernel, and any property that
  depends on design secrecy (economy of mechanism, open design);
- dangerous actions guarded by a single condition (separation of
  privilege), and workflows where the insecure path is the easy path.

Rules:
- No evidence, no finding. Every finding must cite file+lines, a diff hunk,
  a test (failing or missing), a doc/code contradiction, a log, CI output,
  or a config/schema mismatch.
- If you cannot cite evidence, record the item as an Observation,
  Hypothesis, or Open question — never as a finding.
- Do not average away critical risks.
- Do not produce confident claims from vibes.

Output:
1. A score block:
   Saltzer–Schroeder Lens: N / 10
   Strengths:
   - ...
   Concerns:
   - ...
   Candidate findings:
   - ...
2. Candidate findings as JSON conforming to schemas/finding.schema.json
   (severity is provisional; the severity classifier assigns the final one).
3. Observations / hypotheses / open questions, clearly separated.
```
