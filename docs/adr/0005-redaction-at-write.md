# ADR 0005: Redaction at Write Time

## Status

Accepted

## Context

The red-team framework persists adversarial prompts and captured agent
responses. Those values may include synthetic learner identifiers, intentionally
seeded PII, or learner-adjacent transcript fragments from production-canary
runs. The storage layer must protect shared Postgres consumers while preserving
enough evidence for forensic follow-up.

## Decision

The storage writers redact `adversarial_prompt` and `agent_response` immediately
before insert. The redaction pipeline removes email addresses, US SSNs, US phone
numbers, common credit-card numbers, and synthetic learner identifiers. It also
redacts multi-token named entities through spaCy when a local model is available,
with a deterministic fallback for environments without spaCy.

`response_hash` is computed before redaction. If a runner already provides a
hash, the writer preserves it. If the hash is absent, the writer computes a
SHA-256 digest over the unredacted response text before storing the redacted
response.

## Consequences

Database rows are safer for operational dashboards and team review, while
`artifact_uri` and the pre-redaction hash still anchor investigations to the
original captured evidence.

The redaction helper is intentionally dependency-tolerant: spaCy improves entity
coverage when installed, but the framework remains runnable in the existing
prototype environment without downloading new packages.
