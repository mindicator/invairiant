# Security / Threat Lens — Threat-Model Compliance

**Pack:** security-safety · **ID:** `security-threat`

## Purpose

This lens protects against implementation drift away from the project's
threat model: attacks that are "closed" in the document but have no working
response in code, new attack surfaces that appear without being recorded,
assets declared protected that no code actually protects, and emergency
paths that quietly step outside the security model. The threat model is a
contract the code must keep, and every claimed mitigation must be
demonstrable.

The question underneath every check: **does the code still implement the
threat model, or only remember it?**

## Scope

This lens is mandatory by default in invAIriant audits: any system that
handles user data or operates in production receives it, and skipping it
requires an explicit, recorded decision.

**Use when:**

- always by default (see above) — in particular whenever code has changed
  since the threat model was last reviewed;
- a change touches authentication, authorization, secrets, network
  exposure, or a recovery/emergency path;
- a new endpoint, port, protocol, integration, or identifier scheme is
  introduced.

**Skip when:**

- the target is a throwaway prototype with no user data, no secrets, and no
  network exposure — and the exception is recorded in the audit record. A
  missing threat model is never a skip condition: its absence is the first
  finding.

## Core Questions

- Is every row of the threat model's attack → response matrix backed by
  working code and a test that exercises the attack path — or only by
  stated intent?
- Has the attack surface changed — a new port, endpoint, banner, verbose
  error, or predictable identifier — and is the change reflected in the
  threat model?
- Are the assets the threat model declares protected actually protected in
  code: user identities and data, credentials, internal topology,
  administrative capability?
- Are secrets and keys absent from code, logs, crash output, and exported
  telemetry — and does something enforce that (scanner, redaction layer,
  test) rather than convention?
- Does every new or changed endpoint enforce authentication and
  authorization — including internal, debug, and health endpoints?
- Do privilege boundaries hold: does compromise of one component or role
  expose only what its declared scope allows?
- Does a fresh deployment with default configuration land in the secure
  state, or does security depend on operators tightening it afterward?
- Has the change introduced a silent emergency path — a bypass flag,
  break-glass mode, or "temporary" backdoor — that steps outside the
  security model without explicit policy and loud logging?
- Where forward secrecy is declared, does key compromise actually leave
  past traffic and data unreadable?

## Good-State Examples

- The threat model's attack → response matrix links each row to the
  enforcing code and to a test that exercises the attack path; CI fails
  when a linked test is deleted or skipped.
- Adding a public endpoint requires a threat-model diff in the same change;
  the PR template asks for it and reviewers enforce it.
- Secrets come only from the secret manager; CI runs a secret scanner, and
  a redaction test feeds a canary token through the logging pipeline and
  asserts it never reaches any sink.
- Break-glass access exists but is explicit: separately authenticated,
  time-boxed, loudly logged, and it pages the security owner on every use.
- A quarterly drill revokes one service's credentials and verifies that the
  observable blast radius matches the documented privilege boundary.

## Red Flags

- An attack listed in the threat model is closed on paper: a mitigation is
  described, but no code implements it and no test exercises it.
- A new component learns a sensitive mapping it does not need — which user
  is behind which session, request, device, or resource.
- A secret or key appears in code, logs, or exported telemetry.
- The attack surface changed — new port, endpoint, banner, verbose error,
  predictable identifier — with no threat model update.
- A silent emergency path bypasses authentication, encryption, or
  validation without explicit policy and logging.
- An endpoint added since the last audit carries no authentication or
  authorization check — internal and debug endpoints included.
- A default deployment is insecure: open admin interface, default
  credentials, permissive CORS, debug mode enabled.
- Forward secrecy is declared in the docs, but keys are long-lived and
  reused across sessions.

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

Typical for this lens: the threat-model row with no corresponding code path
(doc/code contradiction); the endpoint handler missing an authorization
check (file + lines); a runtime log line containing a credential; a missing
test for a declared mitigation; a configuration/schema mismatch between the
deployed surface and the documented one. Uncertainty alone is not a
finding: name the concrete risk and the concrete evidence gap, or record an
open question instead.

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

### S0 Example

Claim: The webhook verifier logs the shared signing secret at debug level,
and debug logging is enabled in production.

Evidence: `billing/webhooks/verify.py:71-84` — `logger.debug("verify",
secret=SIGNING_SECRET, payload_id=...)`; production log
`logs/prod/billing-2026-06-14.log:2101` contains the secret in plaintext
(runtime log).

Risk: Everyone with log access — a broad internal group plus the log
aggregation vendor — can forge billing webhooks; the secret must be treated
as compromised, and the threat model's "secrets never appear in logs"
invariant is violated in production, not hypothetically.

Recommended fix: Remove the secret from the log call and rotate the secret;
add a redaction layer at the logging boundary plus a CI test that a canary
secret never reaches any sink; audit log-access records for the exposure
window.

### S1 Example

Claim: A data-export endpoint was added to the API without object-level
authorization and without any threat-model update.

Evidence: `services/export/handler.go:64-97` — `GET /v1/exports/{id}`
validates the session and tenant but never checks that the export belongs
to the caller; ids are sequential (`export_id BIGSERIAL`,
`db/migrations/0042_exports.sql:7`); `docs/THREAT-MODEL.md` predates the
endpoint by three months and has no matrix row for it (doc/code
contradiction).

Risk: Any authenticated user can walk sequential ids and download other
users' exports within the tenant, and the new surface is invisible to the
threat model — the next audit inherits an unrecorded attack path.

Recommended fix: Enforce ownership authorization; replace sequential ids
with unguessable ones; add the matrix row and a test exercising the
cross-user access attempt; gate future surface changes with a PR-template
check.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Security / Threat Lens (id: security-threat) from the
invAIriant audit protocol: threat-model compliance.

Examine the provided code/diff/docs for:
- threat-model rows whose mitigation exists only in prose — no enforcing
  code, no test exercising the attack path;
- attack-surface changes (ports, endpoints, banners, error detail,
  predictable identifiers) not reflected in the threat model;
- secrets or keys reachable through code, logs, crash output, or exported
  telemetry, and whether redaction is enforced rather than assumed;
- authentication, authorization, and privilege boundaries on every new or
  changed endpoint, including internal and debug surfaces;
- insecure defaults, and silent emergency paths that bypass the security
  model without explicit policy and logging;
- forward secrecy where declared: whether key compromise exposes past data.

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
   Security / Threat Lens: N / 10
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
