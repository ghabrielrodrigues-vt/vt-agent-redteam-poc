# Red Team MVP Review Reports

## Scope

This file records review outcomes for the current Red Team MVP implementation
cycle after the dashboard was created. It captures:

- Review Agent findings against LLM_WIKI, project plan, and spec.
- Strategic View verdicts.
- Blockers found.
- Fixes applied.
- Validation evidence.

Current status after these reviews: Phase 1A is at 6/7, with F7 as the next
current task.

## F3 Review: Severity Gate and Overrides

### Strategic View

Verdict: accepted.

Rationale:

- Severity assignment P0-P3 implemented in the harness.
- Gate precedence implemented with stub exit 3, P0 blocking, P1 blocking,
  aggregate threshold, and valid non-P0 override bypass.
- Active override lookup implemented through `redteam.overrides`.
- Focused gate tests added.

### Review Agent Findings

Initial blockers:

- Override path was not usable in the planned CLI flow because override lookup
  was coupled to the writer and writer was only created under `--write-results`
  or `--dry-run`.
- Override key was unstable because each run generated a fresh UUID, making
  approved re-runs unable to match the original override row.
- Transient failures were classified after category severity, so a K-12
  `violence` network failure could become P1 instead of P3.

Fixes applied:

- Added separate `override_reader` injection to `RedTeamHarness`.
- Added stable `--run-id` / `REDTEAM_RUN_ID` support.
- Allowed `harness.run(..., run_id=...)`.
- Moved transient-failure severity classification before category severity.
- Added tests for injected `run_id`, override lookup, P0 non-bypass,
  active/expired override, and transient-over-critical behavior.

Final Review Agent verdict: cleared.

### Validation

- `tests/test_override_gate.py`: 17 focused tests passed after hardening.
- Full suite after F3: 87 tests passed.
- Later full suite after F5 hardening: 98 tests passed.

## F4 Review: Redaction at Write Time

### Strategic View

Verdict: accepted after blocker fix.

Rationale:

- Storage-time redaction added before Postgres/Supabase writes.
- `response_hash` preserved as pre-redaction hash.
- Redaction tests cover email, SSN, phone, credit card, synthetic learner ID,
  named entities, allowlist behavior, and writer payload behavior.

### Review Agent Findings

Initial blocker:

- Redaction allowlist existed only in helper tests, not in the storage write
  path. Spec/plan require preserving named spans when scenario expected
  behavior explicitly allows them.

Non-blocking concerns:

- `scorer_results` is not redacted. Current scorers mostly avoid raw response
  storage, but richer future scorers could persist sensitive fragments there.
- Supabase writer needed direct redaction-path test.

Fixes applied:

- Added `ScenarioResult.redaction_allowlist`.
- Populated it from `scenario.expected_behavior.must_include` in the harness.
- Passed `redaction_allowlist` into Postgres and Supabase writer calls to
  `redact_text(...)`.
- Added direct Supabase writer payload redaction/hash test.
- Added Postgres writer allowlist preservation test.

Final Review Agent verdict: cleared.

### Validation

- `tests/test_redaction.py`: 7 focused tests passed after hardening.
- Full suite after F4 hardening: 94 tests passed.
- Later full suite after F5 hardening: 98 tests passed.

## F5 Review: Manifest-Driven CLI Modes

### Strategic View

Verdict: accepted after blocker fixes.

Rationale:

- CLI supports manifest-driven `pr`, `deploy`, `canary`, and `manual` trigger
  modes.
- Legacy transport runner modes remain available through `--runner-mode`.
- Manifest thresholds and filters drive execution.
- Dry-run emits `run_summary.json` using a local stub runner without LiveKit
  network calls.

### Review Agent Findings

Initial blockers:

- CLI could not run the v0 primary `agent_native_transcript` / Langfuse path.
  Supported runner modes were only `livekit-stub`, `livekit-audio`,
  `http-moderation`, and `direct-llm`.
- Manifest `known_system_prompt_source` was ignored, causing prompt-leak
  detector to skip manifest-driven runs.

Fixes applied:

- Added `agent-native-transcript` / `langfuse` runner mode.
- Built `LangfuseTraceRunner` through `build_default_client`.
- Added harness support for passing `run_id` into runners that require it.
- Added `AgentManifest.known_system_prompt_source`.
- Loaded prompt source files/directories into `AgentConfig.known_system_prompt`.
- Added tests for prompt-source loading and run-id-aware runner calls.

Remaining blocker from re-review:

- Trigger modes still defaulted to `livekit-stub`, meaning planned workflow calls
  with `--mode pr/deploy/canary` would use stubs unless F6 explicitly supplied
  `--runner-mode agent-native-transcript`.

Final fix:

- Changed trigger-mode default runner to `agent-native-transcript`.
- Kept `--dry-run` on local stub runner.
- Added test proving non-dry-run `--mode pr` fails fast without Langfuse
  credentials instead of silently using stub.

Final Review Agent verdict: cleared.

### Validation

- `tests/test_cli_manifest_run.py`: 3 focused tests passed after hardening.
- `tests/test_cli_manifest_run.py tests/test_override_gate.py`: 21 tests passed
  after final F5 blocker fix.
- Full suite: 98 tests passed, 20 warnings.
- Targeted Ruff on touched files: passed.

## Review Sign-Off Summary

| Task | Strategic View | Review Agent | Status |
|---|---|---|---|
| F3 Severity gate and overrides | Accepted | Blockers cleared | Done |
| F4 Redaction at write | Accepted | Blocker cleared | Done |
| F5 Manifest-driven CLI modes | Accepted | Blockers cleared | Done |
| F6 Reusable workflow | Accepted | Green Actions run recorded | Done |

## F6 Closure Notes and Downstream Watch Items

F6-specific acceptance is closed by the green fixture run recorded below. The
items here remain downstream guardrails for consumer-repo rollout and later
Phase 1B/S6 work.

- Reusable workflow must provide Langfuse secrets.
- Reusable workflow must provide stable `REDTEAM_RUN_ID`.
- Reusable workflow must enable `--enforce-threshold`.
- Reusable workflow should use `--write-results` for persistent gate evidence.
- Workflow should avoid reintroducing raw unredacted prompt/response text in
  Slack payloads, summaries, or logs.
- Supabase schema in `prototype/src/vt_agent_redteam/storage/schema.sql` remains
  prototype-oriented; S6 must use the plan's migration constraints before
  consumer-repo database work.

## F6 Review: Reusable Workflow

### Strategic View

Verdict: accepted after green Actions evidence.

Rationale:

- Reusable workflow file exists.
- `workflow_call` exposes manifest/mode/environment inputs and required live
  secrets.
- `workflow_dispatch` supports framework-repo fixture runs.
- Workflow generates stable `REDTEAM_RUN_ID`.
- Workflow validates manifest before execution.
- Workflow invokes `vt-redteam run`.
- Workflow conditionally applies `--enforce-threshold`, `--write-results`, and
  dry-run behavior.
- Workflow uploads `run_summary.json` as an artifact.

Acceptance evidence:

- Green Actions run recorded for the framework fixture manifest:
  https://github.com/ghabrielrodrigues-vt/vt-agent-redteam-poc/actions/runs/26701859150
- Run id: `26701859150`.
- Head SHA: `c5420a3d98f24b8c714cd3f70db0d9ad3efd102b`.
- Job `red-team gate` completed successfully after validating the fixture
  manifest, preparing a stable run id, running the red-team gate, and uploading
  `run_summary.json`.

### Review Agent Findings

Blocking acceptance item:

- Cleared: the plan's explicit acceptance criterion is now satisfied by the
  green Actions run recorded above.

Non-blocking concerns:

- Workflow contract tests are text-contract tests, not full YAML execution.
- `workflow_call` requires live secrets even if a future consumer sets
  `dry_run: true`; this follows the strict plan contract but raises consumer
  setup friction.
- `REDTEAM_RUN_ID` is stable for reruns of the same GitHub Actions run, not for
  entirely new workflow runs.

Validated locally:

- Fixture manifest validates.
- Fixture dry-run writes `run_summary.json`.
- `tests/test_workflow_contract.py` passes.
- Full local suite passes: 101 tests.
- Dashboard should now mark F6 at 4/4 and promote F7 as current after data
  regeneration.

### Post-Acceptance Review

Strategic View verdict: accepted. Promote F7 as current.

Review Agent verdict: no blockers.

Non-blocking improvements applied after review:

- Tightened the dashboard evidence detector so F6 requires either legacy
  transfer-bundle evidence or both a GitHub Actions run URL and a head SHA in
  this review report.
- Renamed the F6 watch section to separate closed F6 acceptance from downstream
  rollout guardrails.
- Added structured run metadata to the strategic-view source data.

Validation after post-acceptance review:

- `node --check dashboard/scripts/redteam-dashboard.mjs`: passed.
- `git diff --check`: passed.
- `dashboard/data/redteam-status.json` regenerates with F6 at 4/4 and F7 as
  current.

## F7 Review: v0.1.0 Release Tag

### Strategic View

Verdict: accepted.

Rationale:

- Phase 1A framework work is complete.
- `prototype/pyproject.toml` is bumped to `0.1.0`.
- `vt_agent_redteam.__version__` is bumped to `0.1.0`.
- `prototype/README.md` now labels the prototype as `v0.1.0`.
- Main branch contains release commit
  `bd3b1bef7fffd20dde1b1a36348199810ea6cae9`.
- Annotated tag `v0.1.0` is pushed.

Release evidence:

- Remote tag visible on GitHub: `refs/tags/v0.1.0`.
- Tag object SHA: `ac348b6ab497b40a97c5570d34595a9e16725e20`.
- Tag target commit: `bd3b1bef7fffd20dde1b1a36348199810ea6cae9`.
- Install target:
  `git+ssh://git@github.com/ghabrielrodrigues-vt/vt-agent-redteam-poc.git@v0.1.0#subdirectory=prototype`.
- Install from v0.1.0 tag resolved.
- Pip built wheel `vt_agent_redteam-0.1.0-py3-none-any.whl`.
- Pip output: `Successfully installed vt-agent-redteam-0.1.0`.
- Installed metadata reports version `0.1.0`.

### Review Agent Findings

Blocking acceptance item:

- None pending.

Non-blocking concern:

- The install verification used `--no-deps` to isolate Git/tag/package
  resolution. The console script was not executed in that clean venv because
  runtime dependencies were intentionally skipped. Local project venv validation
  covered `vt-redteam --version`.

Validated locally:

- `cd prototype && .venv/bin/python -m pytest`: 101 passed, 20 warnings.
- `cd prototype && .venv/bin/vt-redteam --version`: `vt-agent-redteam 0.1.0`.
- `node --check dashboard/scripts/redteam-dashboard.mjs`: passed.
- `git diff --check`: passed.

### Post-Release Review

Strategic View verdict: accepted. Close Phase 1A and promote S1 as current.

Review Agent verdict: no blockers.

Verified after review:

- `HEAD`, `origin/main`, and `v0.1.0^{}` point to
  `bd3b1bef7fffd20dde1b1a36348199810ea6cae9`.
- Local tag is annotated: object
  `ac348b6ab497b40a97c5570d34595a9e16725e20`, target `bd3b1be`.
- Remote tag exists: `refs/tags/v0.1.0` at
  `ac348b6ab497b40a97c5570d34595a9e16725e20`.
- `dashboard/data/redteam-status.json` shows F7 at 4/4 done and S1 as the
  current task.

Residual non-blocking notes:

- Dashboard release criteria are evidence-document driven rather than live
  network checks.
- Tag is unsigned; no current release policy requires signed tags.

## Plan Update Review: Phase 1D Final Release Governance

### Strategic View

Verdict: accepted.

Rationale:

- Phase 1D should be a release-readiness gate, not a blocker for starting
  Phase 1B.
- S1 remains current and limited to the `language-tutor` manifest.
- Phase 1D correctly runs after Phase 1C and before final team-facing release
  communication.
- Final team communication remains blocked until R1-R8 close and Strategic
  View clears unresolved reviewer blockers.

Required strategic conditions now captured:

- PostHog feature-flag release gate with rollback evidence.
- Non-stub E2E evidence for the red-team tool.
- Cost guardrail proof for `max_cost_usd_per_run` / `budget_exhausted`.
- Strict LLM_WIKI NITPICK review.
- LLM attack-defense review.
- Strategic triage into fix-now work and post-v0 backlog.
- `vt-agent-redteam` repository/package cutover.
- Dense DOCX security traceability audit.
- Security pentest and exploitation review.
- Final technical and non-technical daily report only after governance closure.

### Review Agent Findings

Initial blocker:

- `docs/v0-implementation-plan.codex-transfer.md` still had a stale header that
  claimed the transfer reflected `git HEAD = ad551b8` from 2026-05-30.

Fix applied:

- Updated the transfer-bundle purpose statement to reflect Phase 1A/F7 closure
  and the new Phase 1D final release-governance gate.

Final Review Agent verdict: cleared.

### Validation

- `node --check dashboard/scripts/redteam-dashboard.mjs`: passed.
- `git diff --check`: passed.
- Dashboard snapshot shows S1 as current.
- Dashboard snapshot shows Phase 1D after Phase 1C, with R1-R9 pending and
  0/9 tasks done.

## Plan Update Review: Phase-End Operational Metrics

### Strategic View

Verdict: accepted as a governance addition, not yet release-sufficient evidence.

Rationale:

- The dashboard now tracks cost, latency, scalability, reliability, API-outage
  behavior, and bottlenecks per phase.
- S1 remains current; operational readiness does not block starting S1.
- Final release remains blocked until Phase 1D and operational metrics close.

Strategic conditions:

- Cost gate must prove `max_cost_usd_per_run -> budget_exhausted -> exit 2`.
- Latency must report p50/p95 scenario and full-run duration.
- Reliability must simulate failures for Langfuse, OpenAI Moderation, LiveKit,
  Postgres/Supabase writes, and Slack.
- OpenAI Moderation outage behavior needs triage because the current scorer
  treats provider failure as inconclusive/pass.
- Scalability must test workflow fan-out / simultaneous checks or explicitly
  accept quota and CI risk.
- Bottlenecks must name measured limits for Langfuse trace search, LiveKit
  dispatch, OpenAI calls, DB writes, and GitHub Actions concurrency.

### Review Agent Findings

Blockers: none.

Non-blocking concerns:

- Operational status is maintained as manual JSON. This is acceptable for the
  dashboard MVP, but future drift risk remains.
- Phase 1A is now functionally closed but operationally partial. This is honest
  and creates retroactive follow-up evidence work.

Fix applied after review:

- Added explicit failure-mode cards for LiveKit API outage, Postgres/Supabase
  write outage, and Slack webhook outage.

### Validation

- `node --check dashboard/dashboard.js`: passed.
- `node --check dashboard/scripts/redteam-dashboard.mjs`: passed.
- `git diff --check`: passed.
- Dashboard snapshot shows S1 as current and operational readiness loaded from
  `docs/operational-metrics/status.json`.

## S1 Review: SOO language-tutor Manifest

### Strategic View

Verdict: accepted with active conditions.

Questions captured for follow-up:

- S4 cannot consume the framework until the consumer workflow pins a new
  framework hotfix tag or explicit SHA. Preferred next tag: `v0.1.1`.
- `scenario_selection.languages: [en, pt]` is accepted as adversarial prompt
  language selection; `metadata_template.language: spanish` is the target tutor
  language.
- `coverage_status: full` is acceptable for S1 profile selection, but runtime
  coverage is not proven until a non-stub S4/S5 run validates the real
  language-tutor path.
- `fixtures.*`, `synthetic.*`, and `env.API_BASE_URL` placeholders are deferred
  to workflow execution.
- S1 operational metrics remain manifest/dry-run only. No runtime cost,
  latency, reliability, scalability, or non-stub guarantee is claimed from S1.

### Review Agent Findings

Initial blockers:

- The S1 manifest originally declared nested `redteam.run_id` /
  `redteam.scenario_id`, while the Langfuse runner searches top-level
  `redteam_run_id` / `redteam_scenario_id`.
- PR mode originally selected 36 smoke scenarios while the manifest budget
  declared `max_scenarios_per_pr: 12`.
- After the first fix, the default `agent-native-transcript` path still only
  polled Langfuse. It did not create a LiveKit room or dispatch the agent with
  correlation metadata.

Fixes applied:

- Updated the SOO manifest to declare top-level `redteam_run_id` and
  `redteam_scenario_id` in `metadata_template`.
- Added framework PR selection capping from
  `budgets.max_scenarios_per_pr`.
- Added `build_room_metadata()` so LiveKit room metadata includes
  `redteam_run_id`, `redteam_scenario_id`, and nested red-team context.
- Added `LiveKitLangfuseRunner` as the default manifest trigger path:
  create LiveKit room, create agent dispatch with metadata, then poll
  Langfuse through `LangfuseTraceRunner`.
- Added tests proving the PR cap and dispatch-before-polling metadata path.

Final Review Agent verdict: P1 blockers cleared.

Remaining non-blocking concern:

- PR cap currently keeps the first 12 scenarios after filtering, which is
  deterministic but corpus-order dependent. The selected S1 PR set can omit P0
  categories such as `personal_information` and `prompt_leakage`. Before using
  PR smoke as representative safety coverage, curate smoke tags or add
  priority ordering.

### Validation

- SOO branch: `redteam/v0-language-tutor-manifest`.
- SOO file added: `agents/language-tutor/.redteam/manifest.yaml`.
- `vt-redteam validate-manifest agents/language-tutor/.redteam/manifest.yaml`:
  passed.
- S1 dry-run: capped PR scenario selection to 12 of 36 scenarios.
- Targeted framework tests: 23 passed, 2 warnings.
- Full framework suite: 104 passed, 21 warnings.

## S2 Review: SOO language-checkpoint Manifest

### Strategic View

Verdict: accepted with active conditions.

Questions captured for follow-up:

- `coverage_status: full` remains provisional until non-stub S4/S5 runtime
  proof exists.
- `scenario_selection.languages: [en, pt]` is accepted as adversarial prompt
  language selection; `metadata_template.language: spanish` is the checkpoint
  target language.
- Checkpoint metadata must remain sufficient for dispatch: `goal_type:
  checkpoint`, `preferredMode: structured`, `targets_block`, and
  `sample_targets`.
- Blank `voice_id`, `agent_id`, `checkpoint_image_url`, and `user_local_time`
  are intentional for audio-only red-team coverage.
- `audio_only: true` is scoped to red-team transcript coverage and does not
  prove avatar behavior.
- S4 cannot consume the framework until the consumer workflow pins a new
  framework hotfix tag or explicit SHA.
- S2 operational metrics remain manifest/dry-run only. No runtime cost,
  latency, reliability, scalability, or non-stub guarantee is claimed from S2.

### Review Agent Findings

Blockers: none.

Non-blocking findings:

- PR smoke selection still depends on deterministic first-N after filtering.
  This is the same P2 residual framework behavior found in S1, not a new S2
  manifest defect.
- Dry-run evidence proves schema, filtering, cap behavior, and local stub
  execution. It does not prove non-stub LiveKit dispatch, Langfuse transcript
  capture, or OpenAI moderation for `language-checkpoint`.
- Review noted that `language_v2_enabled` was top-level while the checkpoint
  parser reads it from `ai_settings`. The manifest now includes it in
  `ai_settings` as well.

### Validation

- SOO branch: `redteam/v0-language-tutor-manifest`.
- SOO file added: `agents/language-checkpoint/.redteam/manifest.yaml`.
- SOO commit: `feat(redteam): add language checkpoint manifest`.
- `vt-redteam validate-manifest
  agents/language-checkpoint/.redteam/manifest.yaml`: passed.
- S2 dry-run: capped PR scenario selection to 12 of 36 scenarios.
- S2 dry-run result: 12/12 passed through the local stub path; OpenAI
  moderation was skipped in offline mode.

## S3 Review: SOO support-agent Manifest

### Strategic View

Verdict: accepted with active conditions.

Questions captured for follow-up:

- `partial-no-tool-use` and `exclude_tags: [tool-misuse]` must remain visible;
  support-agent must not be presented as full `support_navigation` coverage.
- `avatar: lemonslice` is accepted as current SOO runtime truth. The older
  `avatar: none` snippet is superseded for Maya in this repo.
- S3 dry-run evidence proves manifest/filter shape only. Runtime coverage
  remains unproven until a non-stub Langfuse run.
- S4 must pin the framework hotfix tag or explicit SHA before live workflow
  use.
- S5 must prove staging-only LiveKit, Langfuse, and DB secrets for
  `support-agent-maya`.
- The first non-stub run must verify dispatch correlation metadata and no
  fixture-shape runtime failure.
- Operational metrics remain dry-run only until live workflow/runtime evidence
  exists.

### Review Agent Findings

Initial blockers:

- The first S3 fixture used `subjectsRegistry` entries shaped as `{label,
  slug}`. The support-agent normalizer accepts compact `{n, s, ...}` rows, so
  the registry would have been dropped before reaching the prompt.
- The first `tutoringContext` fixture missed the current v1 token-route
  fields: `version`, `hasAssignedPrivateTutor`,
  `hasActiveTutorMatchOrRequest`, `shouldOfferTutorHelp`, and
  `prioritySubjectNames`.

Fixes applied:

- Updated `tutoringContext` to match `SupportAgentTutoringContextV1`.
- Updated `subjectsRegistry` to compact `{n, s, f, q, l, p, d, sp}` rows.
- Limited `featureFlags` to the current `languages` allow-list.
- Updated `subjectExpertise` to include `display_name`.
- Added representative `salesCallHistory` shape.

Final Review Agent verdict: blockers cleared.

Remaining non-blocking concern:

- The tool-use gap is honest only while `tool-misuse` stays excluded and
  dashboard/status continue to show `partial-no-tool-use`.

### Validation

- SOO branch: `redteam/v0-language-tutor-manifest`.
- SOO file added: `agents/support-agent/.redteam/manifest.yaml`.
- SOO commit: `feat(redteam): add support agent manifest`.
- `vt-redteam validate-manifest
  agents/support-agent/.redteam/manifest.yaml`: passed.
- S3 dry-run: capped PR scenario selection to 12 of 20 scenarios after
  excluding unsupported tool-use coverage.
- S3 dry-run result: 12/12 passed through the local stub path; OpenAI
  moderation was skipped in offline mode.

## S4 Review: SOO redteam Workflow

### Strategic View

Verdict: approved with tracked deviation.

Questions captured for follow-up:

- Reusable workflow preference is superseded by the stronger requirement that
  SOO jobs consume environment-scoped `redteam` secrets.
- Dashboard copy should say direct thin SOO jobs use an explicit framework SHA
  pin, not reusable workflow call.
- S5 must prove the `redteam` environment contains staging-only secrets before
  any live run is trusted.
- `write-results` and `enforce-threshold` make S6/S7 DB readiness required
  before non-dry live acceptance.
- No prod/canary trigger is present; keep that absent until a later phase or
  ADR explicitly opts in.
- Path scoping must be proven in Actions: one agent path change should run only
  the matching redteam job.
- Fork PR behavior must be accepted: secret-backed jobs skip external fork PRs.
- Operational metrics remain pending until a non-stub workflow run exists.

### Review Agent Findings

Initial blocker:

- The first workflow candidate invoked the framework reusable workflow with
  `secrets: inherit`. GitHub reusable workflow calls cannot consume SOO
  environment-scoped secrets from the caller's `redteam` environment, so the
  planned S5 secret model would not work.

Fix applied:

- Replaced reusable workflow calls with direct thin SOO jobs bound to
  `environment: redteam`.
- Each job installs the pinned `vt-agent-redteam` package, validates its
  manifest, prepares a stable `REDTEAM_RUN_ID`, runs `vt-redteam` in
  `agent-native-transcript` mode, writes results, enforces threshold, and
  uploads a per-agent summary artifact.
- Kept PR trigger scoped to `agents/**` plus the workflow file.
- Kept per-agent `dorny/paths-filter@v3` fan-out.
- Kept fork PR guard so secret-backed jobs do not run on external forks.
- Kept staging target environment only; no production or canary trigger was
  added.

Final Review Agent verdict: blockers cleared.

Remaining non-blocking concern:

- Direct SOO jobs duplicate framework reusable workflow logic. This is accepted
  for S4 to preserve environment-secret segregation, but future framework step
  drift must be watched.

### Validation

- SOO branch: `redteam/v0-language-tutor-manifest`.
- SOO file added: `.github/workflows/redteam.yml`.
- SOO commit: `ci(redteam): add SOO redteam workflow`.
- YAML parse: passed.
- `git diff --check`: passed.
- `vt-redteam validate-manifest` passed for `language-tutor`,
  `language-checkpoint`, and `support-agent`.
