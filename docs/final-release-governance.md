# v0 Final Release Governance Gate

## Status

Drafted as a new final implementation stage. This gate runs after Phase 1C and
before declaring v0 ready for team-facing release communication.

## Purpose

The v0 implementation now needs a final governance layer that is stricter than
normal feature completion. This layer verifies release safety, end-to-end
confidence, defensive quality, documentation traceability, and team-ready
communication.

This stage does not replace the implementation phases. It closes them.

## Required Evidence Location

All release-governance evidence must live under:

```text
docs/release-governance/
```

Do not mark a release-governance task complete from memory or chat history
alone. Each task needs a written evidence report, run link, traceability table,
or explicit disposition record.

## R1. PostHog Feature-Flag Release Gate

The release may only proceed behind a PostHog feature flag.

Required evidence file:

```text
docs/release-governance/posthog-feature-flag.md
```

Acceptance:

- The PostHog flag key is recorded.
- The flag owner is recorded.
- Initial rollout audience is recorded.
- Rollback/off procedure is recorded.
- The release path is proven to be guarded by the flag.
- Default-off behavior is verified where applicable.

## R2. Integration and E2E Tests

The release must include integration and end-to-end coverage for the red-team
tool in the consumer path.

Required evidence file:

```text
docs/release-governance/integration-e2e-evidence.md
```

Acceptance:

- Integration test scope is documented.
- E2E test scope is documented.
- At least one non-stub run exercises the tool through the intended workflow
  path.
- Cost guardrail behavior is tested with a contrived run that exceeds
  `max_cost_usd_per_run`, records `budget_exhausted`, and exits with the
  expected blocking status.
- Evidence links include command output, workflow run, trace, artifact, or test
  report.
- Any untested path is explicitly marked as a risk or post-v0 backlog item.

## R3. LLM_WIKI NITPICK Code Review

A strict NITPICK review must be applied before final release. The reviewer
should act like a senior specialist in the language, framework, and tooling in
use. LLM_WIKI standards must be applied strongly, including architecture,
modularity, documentation, testing discipline, and security posture.

Required evidence file:

```text
docs/release-governance/nitpick-llm-wiki-review.md
```

Acceptance:

- LLM_WIKI sources used by the review are listed.
- Review scope lists files, workflows, migrations, and docs inspected.
- Findings are grouped by blocker, fix-before-release, and post-v0 backlog.
- Every finding has a disposition.
- No unresolved blocker remains.

## R4. LLM Attack-Defense Review

An LLM attack reviewer must inspect each red-team hardening artifact and answer
whether the implementation is actually defending the agents against relevant
attack classes.

Required evidence file:

```text
docs/release-governance/llm-attack-defense-review.md
```

Acceptance:

- Each corpus category, scorer, gate rule, override path, runner path, and
  workflow trigger is reviewed for attack coverage.
- Missed attack classes are mapped to immediate fixes or post-v0 backlog.
- The review checks both under-blocking and over-blocking risks.
- The review explicitly checks prompt leakage, jailbreaks, tool misuse,
  learner-safety harms, identity/impersonation, hallucinated policy, privacy
  leakage, and operational bypasses.

## R5. Strategic Triage

Strategic View must consume all reviewer reports and decide what must be fixed
immediately versus what can safely move to a post-v0 backlog.

Required evidence file:

```text
docs/release-governance/strategic-triage.md
```

Acceptance:

- Inputs list all reviewer reports consumed.
- Immediate release blockers are listed and prioritized.
- Fix-before-release items are owned.
- Cost guardrail status is explicitly classified as fix-now or proven complete.
- Post-v0 backlog items are listed with rationale.
- No reviewer blocker is silently deferred.

## R6. vt-agent-redteam Repository and Package Cutover

The final project must live in a repository/package named `vt-agent-redteam`,
as established in the documentation.

Required evidence file:

```text
docs/release-governance/repo-package-cutover.md
```

Acceptance:

- Final repository name is `vt-agent-redteam`.
- Python package name remains `vt-agent-redteam`.
- Python import remains `vt_agent_redteam`.
- Consumer install examples point at the final repository/package.
- Reusable workflow references point at the final repository/package.
- Legacy `vt-agent-redteam-poc` references are either removed, intentionally
  preserved as history, or tracked as cutover work.

## R7. Dense DOCX Security Traceability Audit

A cold, methodical, security-focused documentation analyst must consume the
dense source documentation again and verify the implementation point by point.

Primary source documents:

```text
docs/exports/livekit-agent-red-team-hardening.docx
docs/exports/livekit-agent-red-team-hardening.md
docs/exports/livekit-redteam-condensed.docx
docs/exports/EXECUTIVE_SUMMARY.docx
```

Required evidence file:

```text
docs/release-governance/docx-security-traceability.md
```

Acceptance:

- Requirements from the dense DOCX/source export are enumerated.
- Each requirement maps to implementation evidence, explicit deviation, or
  post-v0 backlog.
- Security-sensitive deviations are marked fix-now unless Strategic View
  accepts the deferral with rationale.
- The audit checks for omissions in token scoping, storage redaction,
  traceability, policy coverage, override controls, alerts, dashboards, and
  operational rollout.

## R8. Security Pentest and Exploitation Review

The same security analyst must apply a pentest process to the generated code
and operational design.

Required evidence file:

```text
docs/release-governance/security-pentest.md
```

Acceptance:

- Threat model is recorded.
- Attack surface is listed across CLI, workflow, storage, secrets, manifests,
  runner inputs, scoring outputs, and dashboard artifacts.
- Exploit attempts are recorded with outcome and metrics.
- Unresolved exploitable gaps are classified as blocker, fix-before-release, or
  post-v0 backlog.
- The report explicitly names metrics and exploitation paths the code does not
  yet resolve.

## R9. Final Team Report

Only after R1-R8 close, prepare a final report and daily-message pair for the
team.

Required evidence file:

```text
docs/release-governance/final-daily-report.md
```

Acceptance:

- Technical daily message is drafted.
- Non-technical daily message is drafted.
- Current development state is accurate.
- Open risks and post-v0 backlog are included.
- The message does not claim final release readiness until R1-R8 are complete.
- Final team communication is embargoed until Strategic View confirms no
  unresolved reviewer blocker remains.

## Dashboard Mapping

The project dashboard tracks this stage as:

```text
Phase 1D - Final release governance
R1-R9
```

The dashboard must not mark these tasks done unless the required evidence files
exist and contain the minimum acceptance language.
