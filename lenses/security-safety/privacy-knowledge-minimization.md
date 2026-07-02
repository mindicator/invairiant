# Privacy Lens — Knowledge Minimization

**Pack:** security-safety · **ID:** `privacy-knowledge-minimization`

## Purpose

This lens protects against systems that quietly learn more about their
users than any function requires: components that hold both who a user is
and what they do, stable identifiers that stitch separate datasets into a
behavioral profile, logs that collect PII by default, telemetry precise
enough to isolate one person, and retention that never ends. Each component
should know the minimum about users that its contract requires.

The principle underneath every check: **what is not collected cannot be
leaked, seized, or compelled.**

## Scope

**Use when:**

- the system stores, transmits, or logs anything about users — accounts,
  requests, support tickets, telemetry, crash reports;
- a change touches logging, analytics, identifiers, session handling,
  retention, or data export;
- components are being merged or centralized, so a gateway, cache, or sink
  may start joining "who" with "what";
- a feature improves UX by remembering more about the user.

**Skip when:**

- the system provably processes no user or user-derived data (build
  tooling, infrastructure with machine-only identifiers) — record that
  justification instead of scoring.

## Core Questions

- For each component: what exactly does it know about users, and does its
  contract require that knowledge? Can any single component or store answer
  both "who is this" and "what did they do / where did they go"?
- Which fields are PII or user-linked — ids, IP addresses, device ids,
  emails, free text? Is each collected for a named purpose, or merely
  because it was present in the request?
- What correlation channels exist — timing, volume, or stable identifiers —
  that let an observer of two datasets link a user to behavior?
- Are per-user identifiers scoped and rotated, or does one stable id recur
  across services, logs, and telemetry, ready-made for joins?
- For each user-linked store and log stream: is there a defined, enforced
  retention period, or does data live until the disk fills?
- Is telemetry aggregated — counts, histograms, cohorts — rather than
  per-user events, and could a low-cardinality slice still isolate one
  person?
- Do logs capture PII by default (full URLs, request bodies, emails in
  stack traces), or is logging deny-by-default with a justified allowlist?
- When a feature trades identity exposure for UX, is that trade recorded as
  an explicit decision, or absorbed silently?

## Good-State Examples

- The auth service knows identity but not behavior; the content service
  handles behavior keyed by a short-lived opaque token; no shared store
  joins the two, and the separation is stated as a contract in the docs.
- The log pipeline hashes user ids and truncates URLs at the emitter; a
  test pushes synthetic PII through and asserts nothing reaches a sink.
- Analytics events carry a per-session random id that is not linkable
  across days; a recorded decision names the product questions given up.
- Every user-linked table and log stream has retention in configuration,
  enforced by a monitored job — and deletion verifiably deletes.
- Support tooling reveals a user's data only after purpose-bound elevation;
  the access is itself audited without copying data to a second store.

## Red Flags

- One component — or one log index — sees both user identity and the user's
  sensitive behavior or destination.
- A central service stores a "user → activity" map that no current function
  needs.
- Telemetry carries enough — identifiers, fine-grained timestamps, rare
  attribute combinations — to isolate a specific person.
- A stable per-user identifier is reused across services and logs,
  convenient for correlation.
- Logs accumulate PII by default: full request URLs, bodies, and emails in
  stack traces.
- Retention is undefined: no store or stream has a deletion date, and
  backups make deletion notional.
- A UX feature silently expands identity exposure — server-synced history,
  cross-device profiles — with no recorded decision.
- Audit trails or debug tooling replicate user data into secondary stores
  with weaker access control.

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

Typical for this lens: the write path where a component persists
user-linked data beyond its contract (file + lines); a log emitter with PII
fields plus a runtime log sample; a schema whose columns contradict the
documented data map (configuration/schema mismatch); a missing retention
job or missing redaction test; a doc/code contradiction with a privacy
policy that declares data "not stored." Discomfort with data collection is
not a finding — cite the component, the excess knowledge, and the gap.

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

Claim: The edge gateway persists a per-user browsing trail — user id, full
request path, timestamp — to an analytics table, although routing needs the
path only for the lifetime of the request.

Evidence: `edge/plugins/request_log.ts:33-58` writes `{user_id, method,
full_path, ts}` to `analytics.request_log`; `db/schema/analytics.sql:14-22`
defines no TTL or partition-drop policy (configuration/schema mismatch);
`docs/privacy.md:19` states "request paths are processed in memory and not
retained" (doc/code contradiction).

Risk: One compromise, subpoena, or insider query yields months of
who-did-what for the entire user base — exactly the map that knowledge
minimization exists to prevent — and the published privacy statement is
false.

Recommended fix: Drop `user_id` from the event or replace it with a
rotating pseudonym; define and enforce retention with partition drops;
align `docs/privacy.md` with reality; add a pipeline test asserting that no
stable user identifier reaches analytics sinks.

### S2 Example

Claim: The mobile client attaches one permanent installation id to every
telemetry event and every crash report, making all of a device's activity
joinable across systems for its lifetime.

Evidence: `mobile/src/telemetry/client.ts:21-40` generates `install_id`
once and never rotates it; the same id is attached to crash uploads in
`crash/uploader.py:66-79`; no test or document constrains identifier
lifetime (missing test).

Risk: Any party holding two of the streams can join them into a
longitudinal behavior profile keyed to a device; one leaked dataset
re-identifies the others, and the exposure grows monotonically with time.

Recommended fix: Scope identifiers per stream and rotate them on a
schedule; document identifier lifetimes; add a conformance test asserting
that telemetry and crash streams share no stable identifier.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Privacy Lens (id: privacy-knowledge-minimization) from
the invAIriant audit protocol: knowledge minimization.

Examine the provided code/diff/docs for:
- what each component knows about users, and any single place that joins
  "who" with "what" or "where";
- PII and user-linked fields collected without a named purpose, and logs
  that capture identity by default;
- correlation channels: stable identifiers, timing/volume patterns, and
  low-cardinality telemetry that can isolate a person;
- retention: user-linked stores and log streams without defined, enforced
  deletion;
- telemetry aggregation versus per-user events, and UX features that expand
  identity exposure without a recorded decision.

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
   Privacy Lens: N / 10
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
