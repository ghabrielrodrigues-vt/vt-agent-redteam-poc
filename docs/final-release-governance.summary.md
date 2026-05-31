# v0 Final Release Governance Gate — Summary

## What This Adds

Before v0 is presented as release-ready, the project now has a final governance
stage after implementation:

```text
Phase 1D - Final release governance
```

## What Must Happen

- Release must be protected by a PostHog feature flag.
- Integration and E2E tests must prove the red-team tool works through a real
  non-stub workflow path, including the cost guardrail.
- A strict LLM_WIKI NITPICK code review must inspect implementation quality.
- An LLM attack-defense reviewer must check whether the hardening actually
  protects agents from relevant attacks.
- Strategic View must triage reviewer findings into fix-now work or post-v0
  backlog.
- Final repository/package naming must become `vt-agent-redteam`.
- Dense DOCX documentation must be reread against implementation evidence.
- Security pentest and exploitation review must identify unresolved gaps.
- Final technical and non-technical daily messages are drafted only after the
  governance checks close and Strategic View clears unresolved reviewer
  blockers.

## Evidence Rule

Every final-gate item needs written evidence under:

```text
docs/release-governance/
```

No item should be marked done from chat memory alone.

## Outcome

When this phase closes, the team can receive a final state report with:

- what shipped,
- what was reviewed,
- what still needs attention,
- what is safe to defer,
- and what blocks release if unresolved.
