# ADR-002 — Colocated manifest layout and coverage status

**Status:** Accepted (2026-05-30)
**Companion:** [`v0-implementation-plan.md`](../v0-implementation-plan.md) §1.1 rows 1 and 7, §3 F2, §7

## Context

The dense spec Appendix E defines the baseline manifest shape, but the v0 plan adds two narrow schema extensions required by the SOO multi-agent rollout:

- Consumer repos with multiple LiveKit agents need each manifest colocated with the owning agent (`agents/{name}/.redteam/manifest.yaml`) instead of a single repo-root manifest.
- Some agents cannot honestly claim full scenario coverage in v0. Maya/support-agent, for example, does not yet exercise tool-use scenarios.

Without an explicit coverage field, partial coverage would either be hidden in prose or encoded through ad hoc tag conventions. Both options make deploy-gate interpretation ambiguous.

## Decision

v0 supports colocated manifests at `agents/{name}/.redteam/manifest.yaml` for multi-agent consumer repos.

The framework also adds `policy_profile.coverage_status` with this enum:

- `full`
- `partial-no-tool-use`
- `partial-other`

`full` is the default. Partial profiles must pair the declaration with scenario exclusions through `scenario_selection.exclude_tags`, for example `exclude_tags: ["tool-misuse"]`.

Spec Appendix E remains canonical for the rest of the manifest. This ADR scopes the schema addition to colocation plus coverage honesty.

## Consequences

**Positive.**

- Multi-agent repos can copy a manifest per agent without framework-specific repo layout glue.
- Partial coverage becomes machine-readable and visible in review, CI, and dashboards.
- `exclude_tags` gives the corpus loader an explicit mechanism for excluding unsupported scenario families.

**Negative.**

- Framework validation now owns a small schema extension beyond Appendix E.
- Dashboard and release notes must avoid presenting partial manifests as complete coverage.

**Neutral.**

- This does not change scoring, severity assignment, or override policy. Those remain framework-owned contracts handled by later ADRs.

## Fitness Check

F2 is complete when a manifest with `coverage_status: partial-no-tool-use` and `scenario_selection.exclude_tags: ["tool-misuse"]` validates, and corpus filtering excludes any scenario carrying `tool-misuse`.
