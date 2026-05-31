# ADR 0003: Severity Gate and Override Read Path

## Status

Accepted

## Context

The v0 red-team gate must block deploys on high-severity failures even when the
aggregate pass rate would otherwise meet the configured threshold. The same gate
also needs a controlled human override path for non-P0 failures, with the audit
record stored in Postgres.

## Decision

The framework owns severity assignment. Each scenario row receives a `severity`
value (`P0`, `P1`, `P2`, or `P3`) from the policy-profile and category lookup in
`docs/v0-implementation-plan.md` section 2.6.

The harness evaluates gate precedence in this order:

1. Stubbed rows force `threshold_passed = null` and exit code `3`.
2. Any P0 failure blocks with exit code `2`; P0 is never overrideable.
3. Aggregate success with no P1 failure passes.
4. A valid active override passes any non-P0 failed gate.
5. Any remaining P1 failure blocks.
6. Any remaining aggregate threshold failure blocks.

The active override read path is a direct Postgres query:

```sql
SELECT 1
FROM redteam.overrides
WHERE run_id = $1
  AND agent_name = $2
  AND expires_at > now()
LIMIT 1;
```

## Consequences

The framework can make deterministic CI exit-code decisions without requiring a
separate service API. Consumer repositories only supply manifests and approved
override rows; they do not define severity rules locally.

Schema consumers must include the `severity` column on `redteam.redteam_runs`
and the `redteam.overrides` table before enabling persistent gate enforcement.
