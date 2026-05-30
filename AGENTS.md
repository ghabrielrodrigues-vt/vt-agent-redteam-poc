# AGENTS.md — vt-agent-redteam POC

> **Start here:** read [`docs/v0-implementation-plan.codex-transfer.md`](./docs/v0-implementation-plan.codex-transfer.md) before doing anything else. It is the single entry point for any agent (Codex, Cursor, Claude, human) picking up the v0 implementation.

## Scope

This repo holds the `vt-agent-redteam` prototype (Python package + corpus + scorers + storage) plus the v0 implementation plan that ships it as a working safety gate inside `varsitytutors/student-onboarding-orchestration`.

Code lives in `prototype/`. Documentation, plan, ADRs, and the source-of-truth specifications live in `docs/`.

## Non-negotiable conventions

- **Conversational language with the user: Portuguese.** Artifacts (code, comments, commit messages, docs, ADRs): **English**. Always.
- **No AI co-authorship in commits.** Never add `Co-Authored-By: Claude` or any agent attribution.
- **Every analysis or doc artifact ships with a `.summary.md` companion**, both in English. See `docs/v0-implementation-plan.md` ↔ `docs/v0-implementation-plan.summary.md` for the pattern.
- **"Ask First" boundaries:** dependency add/remove, file deletion, large refactors, infrastructure/deployment/auth/database changes. Surface the proposed action before executing.
- **Lock decisions are in [`docs/v0-implementation-plan.md`](./docs/v0-implementation-plan.md) §1.1.** Deviating requires a new ADR in `docs/adr/` explaining the why. Do not silently change.

## Where things are

| Need | Location |
|------|----------|
| Canonical implementation plan (v1.1) | `docs/v0-implementation-plan.md` |
| Codex/agent transfer entry point | `docs/v0-implementation-plan.codex-transfer.md` |
| Non-tech summary of the plan | `docs/v0-implementation-plan.summary.md` |
| Decision trail behind every locked item | `docs/v0-implementation-plan.handoff.md` |
| Boss-role second-pass review verdict | `docs/v0-implementation-plan.review.md` |
| Source specification (v2.1, 1610 lines) | `docs/exports/livekit-agent-red-team-hardening.md` |
| Condensed VT-focused brief | `docs/exports/livekit-redteam-condensed.md` |
| ADRs | `docs/adr/` |
| Framework prototype code | `prototype/src/vt_agent_redteam/` |
| Tests | `prototype/tests/` |
| Adversarial scenario corpus | `prototype/src/vt_agent_redteam/corpus/` |

## Verification

From `prototype/`:

```bash
source .venv/bin/activate
python -m pytest
```

Do not commit if the suite is not green.

## Commit conventions

See `git log --oneline` for examples. Pattern: lowercase prefix (`docs:`, `feat:`, `feat(framework):`, `fix:`), imperative subject ≤ 70 chars, body explains the why, no AI attribution, no `--no-verify`, no `--amend` of pushed commits.

## Where to start when you walk in cold

1. Read [`docs/v0-implementation-plan.codex-transfer.md`](./docs/v0-implementation-plan.codex-transfer.md).
2. Then [`docs/v0-implementation-plan.md`](./docs/v0-implementation-plan.md).
3. Then check `git log --oneline -10` to see what shipped most recently.
4. Then run the test suite to confirm baseline green.
5. Then look at the next pending task in the plan §3 / §4 / §5.
