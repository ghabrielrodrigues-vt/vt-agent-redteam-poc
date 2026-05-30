# Codex Transfer Bundle — vt-agent-redteam v0 Implementation

**Purpose:** everything Codex (or any non-Claude agent) needs to pick up the v0 implementation from where Claude left off as of `git HEAD = ad551b8` (2026-05-30).

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
ad551b8 feat(framework): F1 LangfuseTraceRunner — agent_native_transcript path
ba08f21 docs: v0 plan v1.1 — resolve boss-review conditions
9b2ace1 docs: v2.1 spec hardening — Mermaid diagrams, condensed brief, executive summary
535d304 docs: add v0 implementation plan, summary, handoff, and boss review
5b80a43 feat: direct-llm runner + manifest validate + threshold enforcement + Phase 1 schema
```

Phase 1A progress:

| Task | Status | Where |
|------|--------|-------|
| F1 LangfuseTraceRunner + 17 unit tests | ✅ Done | `prototype/src/vt_agent_redteam/runners/langfuse_trace_runner.py`, `prototype/tests/test_langfuse_runner.py`, exported via `prototype/src/vt_agent_redteam/runners/__init__.py` |
| F2 manifest_loader extensions (`coverage_status`, `exclude_tags`) | Not started | Pending. Plan §3 F2. |
| F3 Severity precedence gate + override read path | Not started | Plan §3 F3. Requires plan §2.6 + §2.7 transcribed into framework code. |
| F4 PII redaction at write | Not started | Plan §3 F4. Closes spec §15.3 documented gap. |
| F5 CLI flags `--mode`, `--environment`, `--enforce-threshold` | Not started | Plan §3 F5. |
| F6 Reusable workflow YAML | Not started | Plan §3 F6. |
| F7 Tag v0.1.0 | Not started | Final Phase 1A step. |

Test suite as of `ad551b8`: **62/62 passing in 9.46s** (zero regressions from the F1 addition).

Local commits ahead of `origin/main`: **4**. No push has been performed.

---

## 4. What to do next — recommended sequence

1. **Read the plan §3 F2** then implement it. F2 is small (Pydantic schema extension for two new fields in `prototype/src/vt_agent_redteam/types.py`) with at most one new test file. Estimate: 30–45 min. Plan-deviation risk: low.
2. **F3 next.** This is the most substantive remaining Phase 1A task. The plan §2.6 + §2.7 transcribed the severity assignment table and the spec §13 precedence table verbatim — your job is to translate those tables into `harness.py` code plus a new `test_severity_gate.py` exercising at least eight cases (every row of the §2.7 table).
3. **F4.** PII redaction at write time. Plan §3 F4 spec — regex strips (SSN, phone, email, credit card, `synthetic.learner_id`) plus spaCy NER. The `response_hash` must be computed pre-redaction. New file `prototype/src/vt_agent_redteam/storage/redaction.py`, new test `test_redaction.py`.
4. **F5 (CLI), F6 (workflow YAML), F7 (tag v0.1.0).** These are sequential plumbing tasks.
5. **Author the remaining ADRs.** Plan §7 lists six total. ADR-001 is done; author ADR-002 alongside F2, ADR-005 alongside F3, etc. Each ≤ 1 page using Michael Nygard's Context-Decision-Status-Consequences format.

After Phase 1A ships (tag `v0.1.0`), Phase 1B is the consumer-repo integration (manifests + workflow YAML + Supabase migration in `student-onboarding-orchestration`).

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
