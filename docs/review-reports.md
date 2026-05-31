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
