# Codex Transfer Bundle — vt-agent-redteam v0 Implementation

**Purpose:** everything Codex (or any non-Claude agent) needs to pick up the v0
implementation after Phase 1A/F7 closure and the addition of the final Phase 1D
release-governance gate (2026-05-31).

This file is the **single entry point**. Read it first; everything else is reachable from here.

---

## 1. Read in this order

| # | Path | Why |
|---|------|-----|
| 1 | This file | Orientation, user preferences, what's done, what's next. |
| 2 | [`v0-implementation-plan.md`](./v0-implementation-plan.md) | Canonical tech plan v1.1. Phases 1A/1B/1C, manifests schema, Postgres schema (with §2.5 + §2.6 + §2.7 carrying severity column + assignment table + precedence table), ADR catalog, risk register, verification checklist. |
| 3 | [`v0-implementation-plan.summary.md`](./v0-implementation-plan.summary.md) | Non-tech companion for stakeholders. |
| 4 | [`v0-implementation-plan.handoff.md`](./v0-implementation-plan.handoff.md) | Decision trail behind every locked item in the plan, LLM_WIKI principles cited (Richards & Ford, Khononov, Diátaxis), and the gotchas the executing agent will discover and should not panic about. |
| 5 | [`v0-implementation-plan.review.md`](./v0-implementation-plan.review.md) | Boss-role second-pass review, verdict greenlight-with-conditions. All six conditions have been resolved in plan v1.1 — the review file is preserved as audit trail. |
| 6 | [`exports/livekit-agent-red-team-hardening.md`](./exports/livekit-agent-red-team-hardening.md) | The 1610-line v2.1 specification. Authoritative. Plan v1.1 cites its sections heavily. |
| 7 | [`exports/livekit-redteam-condensed.md`](./exports/livekit-redteam-condensed.md) | VT-focused condensed solution brief. |
| 8 | [`adr/0001-langfuse-native-transcript.md`](./adr/0001-langfuse-native-transcript.md) | First ADR — documents Phase 2 fallback promoted to v0 primary audio path. |

After reading 1–4, you have enough to start work. Read 5–8 on demand when a specific decision needs background.

---

## 2. User preferences (Claude had these in auto-memory; Codex must honor them explicitly)

These are non-negotiable and apply to every action you take in this repo:

- **Conversational language: Portuguese.** When you talk to the user (Ghabriel Rodrigues, `ghabriel.rodrigues@varsitytutors.com`), use Portuguese.
- **Artifact language: English.** All code, comments, commit messages, documentation, ADRs, plan revisions — English. No exceptions.
- **Bilingual docs rule:** every analysis or doc artifact ships as a tech version plus a non-tech `.summary.md` companion. Both in English. Look at `v0-implementation-plan.md` + `v0-implementation-plan.summary.md` for the pattern.
- **No AI co-authorship in commits.** Never add `Co-Authored-By: Claude` or any equivalent attribution. Ghabriel considers AI tools, not collaborators. Commit messages are first-person plural or imperative ("add", "fix", "refactor") — no agent attribution.
- **"Ask First" boundaries** apply to: dependency changes, deleting files, large refactors/renames, infrastructure/deployment/auth/database changes, anything affecting shared state. When in doubt, surface the proposed action before executing.
- **Skill packs Claude used are NOT available to you.** The bundled knowledge that backed those skills lives in the repos themselves — see §6 below for the file paths.

---

## 3. Current state of the implementation

`git log --oneline -5` (most recent first):

```
bd3b1be release(framework): bump package to v0.1.0
b23e047 fix(dashboard): handle malformed local routes
4ed189b fix(dashboard): avoid snapshot churn while serving
519f1f6 docs(framework): record F6 actions acceptance
c5420a3 feat(framework): redteam mvp dashboard and gates
```

Phase 1A progress:

| Task | Status | Where |
|------|--------|-------|
| F1 LangfuseTraceRunner + 17 unit tests | ✅ Done | `prototype/src/vt_agent_redteam/runners/langfuse_trace_runner.py`, `prototype/tests/test_langfuse_runner.py`, exported via `prototype/src/vt_agent_redteam/runners/__init__.py` |
| F2 manifest_loader extensions (`coverage_status`, `exclude_tags`) | ✅ Done | `prototype/src/vt_agent_redteam/types.py`, `prototype/src/vt_agent_redteam/manifest_loader.py`, ADR-002. |
| F3 Severity precedence gate + override read path | ✅ Done | `prototype/src/vt_agent_redteam/harness.py`, `prototype/src/vt_agent_redteam/storage/postgres_writer.py`, `prototype/tests/test_override_gate.py`, ADR-003. |
| F4 PII redaction at write | ✅ Done | `prototype/src/vt_agent_redteam/storage/redaction.py`, writer redaction path, `prototype/tests/test_redaction.py`, ADR-005. |
| F5 CLI flags `--mode`, `--environment`, `--enforce-threshold` | ✅ Done | `prototype/src/vt_agent_redteam/cli.py`, manifest-driven runner modes, run summary smoke tests. |
| F6 Reusable workflow YAML | ✅ Done | `.github/workflows/redteam.yml`, fixture manifest, green Actions run `26701859150`. |
| F7 Tag v0.1.0 | ✅ Done | `prototype/pyproject.toml` version `0.1.0`, tag `v0.1.0`, pip install from tag resolves. |

Test suite as of `bd3b1be`: **101/101 passing in 9.71s**.

Local branch is pushed to `origin/main`. Tag `v0.1.0` is pushed.

---

## 4. What to do next — recommended sequence

1. **Start Phase 1B in `student-onboarding-orchestration`.** First target: S1
   language-tutor manifest at `agents/language-tutor/.redteam/manifest.yaml`.
2. **Do not start SOO database or secrets work without Ask First.** S5 secrets
   and S7 Supabase JWT require explicit user involvement.
3. **Use framework tag `v0.1.0`.** Consumer workflow references should pin the
   reusable workflow/package to the release tag.
4. **Finish Phase 1D before any final release-ready communication.** Phase 1D is
   the new final release governance gate: PostHog flag, integration/E2E tests,
   LLM_WIKI NITPICK review, LLM attack-defense review, Strategic View triage,
   `vt-agent-redteam` repo/package cutover, DOCX security traceability audit,
   pentest/exploitation review, and final daily report.
5. **Update operational metrics at every phase end.** The dashboard reads
   `docs/operational-metrics/status.json` for cost, latency, scalability,
   reliability, API-outage behavior, and bottlenecks.
6. **Keep dashboard/review reports updated after each delivery iteration.**

Phase 1A has shipped. Phase 1B is the consumer-repo integration (manifests +
workflow YAML + Supabase migration in `student-onboarding-orchestration`).
Phase 1D closes the release after implementation and rollout-control work.

---

## 5. Hard constraints — things that must not change without a new ADR

These were locked through 14+ rounds of grilling and a boss-role review. Deviating requires authoring a new ADR explaining why; do not silently change them.

- **Target consumer repo:** `varsitytutors/student-onboarding-orchestration` (NOT `varsitytutors/conversation-club`, even though the spec section 4.2 says otherwise — see ADR-SOO-001 to be authored). Three agents in scope: `language-tutor`, `language-checkpoint`, `support-agent` (Maya).
- **Manifest layout:** colocated at `agents/{name}/.redteam/manifest.yaml`. Not centralized.
- **Audio path:** Langfuse-native transcript (spec section 12.1 `transcript_source = "agent_native_transcript"`). WAV-collector race condition fix is deferred to v0.2 — do not attempt it in v0.
- **Workflow structure:** single `.github/workflows/redteam.yml` in SOO with three path-filtered jobs (one per agent). Mirrors the existing `cinematic-judge.yml` pattern in the same repo.
- **Supabase project for redteam schema:** `conversation-club` project (ref `uxxuxhtdixrzcitufhfa`). Migration folder `supabase/conversation-club/supabase/migrations/`. SOO `supabase/AGENTS.md` Rule 0 must be honored — three deploy-killer rules in S6.
- **Severity model:** spec §13 four-tier (P0–P3) with persistent `severity` column, lookup table in plan §2.6, precedence table in plan §2.7. F3 implements both verbatim.
- **Slack target in v0:** channel `#student-experience-v3-launch`, `responsible_team: eng-met-ui` for all three agents.

---

## 6. External knowledge you need to fetch

Claude bundled these via local skill packs at `~/.claude/skills/{redteam,vt4s}/`, which Codex cannot use. The actual content lives in the following repos, all of which are clones on the user's machine:

| Need | Path | What's there |
|------|------|--------------|
| The spec, in markdown | `/Users/gupy/apps/nerdy/poc_moderation_red_team_promptfoo/docs/exports/livekit-agent-red-team-hardening.md` | Same file referenced in §1 #6 — also accessible via this repo. |
| VT4S team research (who owns what across `varsitytutors/*`) | `/Users/gupy/apps/nerdy/vt4s-team-scope/00-overview.md` and `/01-repos-ranked.md` | Per-engineer focus, area heatmap, 37 ranked repos. Read when you need to know "who should review this PR" or "what is repo X". |
| Accessibility deep-dive | `/Users/gupy/apps/nerdy/vt4s-team-scope/accessibility-matt.md` | Matt Stitz's WCAG work + broader org A11y landscape. Likely irrelevant for v0; flagged for completeness. |
| Target consumer repo (SOO) | `/Users/gupy/apps/nerdy/student-onboarding-orchestration/` | The repo that will host the three manifests + workflow + Supabase migration in Phase 1B. Read its top-level `CLAUDE.md` (renamed `AGENTS.md` per its own conventions), `supabase/AGENTS.md`, `.github/workflows/cinematic-judge.yml`, `.github/workflows/deploy-language-agent-shared.yml`. |
| LLM_WIKI vault (Richards & Ford, Khononov, Diátaxis, et al.) | `/Users/gupy/LLM_WIKI/index.md` then `wiki/books/...` | Architecture and DDD principles cited throughout the plan. Read on demand when the plan references chapter numbers. |

---

## 7. Verification before any commit

Run from `prototype/`:

```bash
source .venv/bin/activate
python -m pytest                            # expect 62/62 (more once F2+ land)
python -m pytest tests/test_langfuse_runner.py -v   # F1 specifically
```

If the suite is not green, do not commit. Resolve the failure first.

---

## 8. Commit conventions in this repo

Pattern visible in `git log --oneline`:

- Lowercase prefix: `docs:`, `feat:`, `feat(framework):`, `fix:`, `chore:`.
- Subject line ≤ 70 chars, imperative.
- Body explains the why, not the what.
- No AI attribution (see §2).
- No `--no-verify`, no `--amend` of pushed commits, no force-push without explicit user request.

Recent good examples to model: `ad551b8`, `ba08f21`, `535d304`.

---

## 9. If you get stuck

Surface the blocker to the user in Portuguese. Do not silently work around the plan or improvise without an ADR. Past Claude grilling produced the locked decisions in §5; if you discover one is wrong, propose a new ADR rather than overriding.

The most common kinds of blockers expected to surface:

- **Langfuse trace correlation latency** during integration testing (Phase 1B). Mitigations: backoff is already implemented; if needed, the harness can fall back to `direct-llm` runner per ADR-001 consequences section.
- **Multi-Supabase confusion** in SOO. Always read `supabase/AGENTS.md` first; default destination for new tables is `supabase/conversation-club/`.
- **Cross-team review needed.** `eng-met-ui` owns SOO; surface the PR to them when integration lands.

---

## 10. Quick-reference one-liners

```bash
# clone state
cd /Users/gupy/apps/nerdy/poc_moderation_red_team_promptfoo
git log --oneline -10
git status

# run tests
cd prototype && source .venv/bin/activate && python -m pytest

# next task
sed -n '/F2\. Extend/,/F3\./p' docs/v0-implementation-plan.md

# all 6 ADRs to author (catalog)
sed -n '/## 7. ADRs to author/,/## 8. Risk register/p' docs/v0-implementation-plan.md

# every locked decision
sed -n '/## 1. Pre-flight/,/## 2. Target architecture/p' docs/v0-implementation-plan.md
```
