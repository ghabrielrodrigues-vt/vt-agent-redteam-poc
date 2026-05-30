# Handoff — vt-agent-redteam v0 implementation

**From:** Claude grilling session 2026-05-30
**To:** Executing agent (Claude or human) picking up v0 implementation
**Primary artifact:** `./v0-implementation-plan.md` (the canonical plan — read it first; everything below is *why*, not *what*)
**Companion:** `./v0-implementation-plan.summary.md` (non-tech version of the plan)

Do NOT re-read this handoff before reading the plan. Open the plan first; come back here only when a locked decision feels arbitrary and you want the trail behind it.

---

## 1. Skills to load before doing anything

Three are mandatory; two are very-nice-to-have.

| Skill | Why |
|-------|-----|
| `/redteam` (this repo's red-team skill at `~/.claude/skills/redteam/`) | Mandatory. It bundles the 1610-line dense spec (`dense-spec.md`) and the condensed brief. The plan references spec section numbers heavily; you cannot evaluate trade-offs without the spec loaded. |
| `/vt4s` (`~/.claude/skills/vt4s/`) | Mandatory. Loads the team-scope research — who owns what in `varsitytutors/*`, which engineers to ask about specific repos, why `student-onboarding-orchestration` is the "AI cluster", and where `conversation-club` came from. |
| `claude-mem:make-plan` + `claude-mem:do` | If you want to break the plan's phases into subagent-executable slices. The plan's Phase 1A/1B/1C structure is already friendly to this. |
| `diagnose` | When you eventually come back to deferred item D1 (WAV-collector race condition fix), diagnose's reproduce → minimise → instrument loop is the right framing. |
| `octocat` | Any `gh` CLI work — creating manifests' PRs, running the deploy-gate drill, reviewing the Supabase migration PR. |

Skills you can skip unless their trigger fires: `tdd` (only if you write the framework's new tests TDD-style), `to-issues` (only if Ghabriel wants the plan broken into GitHub issues — he chose handoff format, not issues, so default is no), `code-review` (only when reviewing the PRs that come out of execution).

---

## 2. The user's working preferences (auto-memory, persistent)

These come from `~/.claude/projects/-Users-gupy-apps-nerdy/memory/`. Honor them silently — don't ask permission, don't make them visible to the user.

- **Conversational language: Portuguese.** All chat with Ghabriel happens in Portuguese.
- **Artifact language: English.** Plan, summary, ADRs, code comments, commit messages — all English.
- **No `Co-Authored-By: Claude` trailer in commits.** He considers Claude a tool, not a human collaborator.
- **Bilingual docs rule:** every analysis or doc artifact ships as a tech version + a non-tech `.summary.md` companion. Both in English. The v0 plan and its summary already follow this; if you author ADRs or risk register updates, follow it too.
- **LLM_WIKI vault at `~/LLM_WIKI/`** is the source of best-practice principles, loaded into context via the global `CLAUDE.md`. Read `~/LLM_WIKI/index.md` if you need to look up a pattern. The plan cites several wiki entries (see §4 of this handoff).

---

## 3. Decision trail — why each locked item in the plan is what it is

The plan's §1.1 lists 12 locked decisions. Here's the trail behind each.

### 3.1 Target repo: SOO (not `conversation-club`)

Ghabriel originally said "the project that contains the agent we'll work with is `student-experience-v3`". That name doesn't exist as a GitHub repo. Discovery via `gh search code "student-experience-v3"` found:

- `vt4s-ai-skills/vt4s-copilot/assets/repository-map.md` maps `student-onboarding-orchestration` to *"Student Experience v3 (CX v3) — current consumer student experience. Feature flag: student-experience-v3-rollout"*.
- Multiple repos redirect users to `/learner/dashboard` based on the LaunchDarkly flag `student-experience-v3-rollout`. The `/learner/*` paths are served by SOO (basePath in its `next.config.ts`).
- `student-experience-v3` is the **product code-name**, not a repo. The product is hosted by SOO.

So SOO became the repo. Decision aligns with Khononov ch3 (bounded context — the v3 product is one bounded context, and SOO is its solution-space implementation).

### 3.2 Multi-agent scope (3 agents) instead of single-agent pilot

`student-onboarding-orchestration/agents/` contains three LiveKit agents: `language-tutor`, `language-checkpoint`, `support-agent`. Ghabriel directed (verbatim): *"quero que criemos algo que de suporte para todos agentes dentro do repo student-orchestration"*. We honor the directive.

Side effect: this deviates from spec section 4.2 (which says P0 = single agent in `conversation-club`). The deviation is recorded as ADR-SOO-001 in the plan.

### 3.3 The two-home situation for `language-tutor` and `language-checkpoint`

`conversation-club` (the GitHub repo) is **new** — created on 2026-05-20 via extraction from SOO. Its description literally says *"Conversation Club — VT's language-tutor product. Extracted from student-onboarding-orchestration on 2026-05-20."* As of 2026-05-30 it has 100+ PRs in 10 days, all about `language-tutor` and `languages/*`.

Today, `language-tutor` and `language-checkpoint` exist in BOTH repos. The SOO copies are transitional. When the extraction completes, our v0 work will need to be ported to `conversation-club`. The plan's colocated-manifest layout (decision §3.5 below) was chosen specifically so this port is straightforward.

`support-agent` (Maya) is the **only** agent that lives exclusively in SOO — the spec section 4.2 row 4 ("Maya Support Agent | student-onboarding-orchestration | OpenAI Realtime | None | support_navigation") is still correct.

### 3.4 Audio path: Langfuse-native transcript, not WAV-collector

Three of the three SOO agents have `langfuse_tracing.py` with OTel-based span emission. Read the header of `agents/language-tutor/langfuse_tracing.py` — it confirms deployment Mike VoC 2026-05-18 via `livekit.agents.telemetry.set_tracer_provider`. LiveKit emits OTel spans for every LLM, STT, TTS, and tool-call invocation; Langfuse ingests these as GENERATION / SPAN observations.

The dense spec (section 15.1) treated this as the Phase 2 fallback if the WAV-collector race condition couldn't be fixed. We promoted it to v0 primary because:

1. The race condition fix is unbounded in timeline (drafted in a feature branch, not validated E2E).
2. JALMBench (spec ref [9]) shows voice-modality attacks exceed text-modality. Direct-LLM bypass alone is insufficient — we need the full audio chain tested. Langfuse-native gives us TTS adversarial → agent STT → agent LLM → agent TTS, all real, with the transcript pulled from the agent's own traces.
3. The infrastructure is already deployed across all three target agents. No new dependency.
4. Spec section 12.1 already lists `agent_native_transcript` as a valid `transcript_source` value.

Ghabriel explicitly said: *"aceito. mas marque essa pendencia para voltarmos nela"*. The WAV-collector fix is task D1 in the plan's §1.2 deferred items.

### 3.5 Manifest layout: colocated per-agent

The user's directive (multi-agent v0 in one repo) made this the obvious choice. Each agent already has its own `pyproject.toml`, `livekit.{staging,production,local}.toml`, `Dockerfile`, `prompts/`, `tests/` — the red-team manifest is just another per-agent artifact in that pattern. Khononov ch3 (bounded-context-per-agent) and Richards & Ford ch3 (module cohesion) both point to colocation.

Tangible benefit: when `language-tutor` finishes its extraction to `conversation-club`, the manifest travels with the agent directory in the move. Zero port work for the manifest.

### 3.6 Workflow structure A + Triggers II

Three structure options and three trigger options were on the table; the user asked me to decide based on "what most closely matches what we promised in the redteam documentation". I picked single-workflow-three-jobs-path-filtered (A) + PR + deploy gate (II) by literal citation:

- Spec section 17.2 Phase 1 acceptance #5 says *"Commit `.github/workflows/redteam.yml`"* — singular file. Option B (three files) violates this.
- Spec section 17.7 acceptance #3 says *"At least one deploy workflow runs the harness automatically and blocks deploy when thresholds fail"*. Triggers I (PR-only) doesn't satisfy this. Triggers III (PR + deploy + canary) over-delivers — canary is spec section 17.3 Phase 2, not v0.
- House style: SOO's existing `cinematic-judge.yml` is exactly this pattern (single file, multi-job, path-filtered, two-phase deterministic-vs-LLM-cost). Richards & Ford ch6 fitness function = consistency with existing patterns.

### 3.7 Supabase project: piggyback `conversation-club`

SOO has 6 Supabase projects. `supabase/AGENTS.md` Rule 0 (effective 2026-05-15) is explicit: all new tables go in `conversation-club` (project ref `uxxuxhtdixrzcitufhfa`). Spec section 12.4 requires a dedicated `redteam` schema + dedicated roles; it does NOT require a dedicated project. We satisfy spec 12.4 inside the `conversation-club` project via schema + role separation. Migration intent to a dedicated `vt-redteam` project is documented as ADR-SOO-002 and tracked as deferred item D7.

### 3.8 Override read path: direct psycopg query

Boss-review condition #6 noted the spec asserts inserting a row in `redteam.overrides` is the only bypass mechanism but doesn't specify how the workflow reads the table. We pick direct DB query (psycopg) over an HTTP API surface because: simpler, self-contained, no new infrastructure, exit-code decision happens in-process. ADR-FRAMEWORK-003.

### 3.9 Maya tool-use coverage gap: honest declaration

Spec section 15.3 admits the tool-use scorer doesn't exist in v0.1; `support_navigation` profile is architecturally claimed but operationally absent. We don't pretend Maya is fully covered. Manifest declares `policy_profile.coverage_status: "partial-no-tool-use"`. Scenarios tagged `tool-misuse` are excluded from Maya's selection via `exclude_tags`. Dashboards surface the gap. ADR-SOO-003.

### 3.10 Slack target

`#student-experience-v3-launch` is already in use by SOO (referenced in its README for Netlify previews). `eng-met-ui` owns SOO per `vt4s-ai-skills/repository-map.md`. Uniform `responsible_team` across the three agents in v0 because per-agent split only makes sense after extraction completes (deferred item D8).

### 3.11 Spec v2.2 fixes in parallel

The 8 boss-review conditions (condensed-brief.md section 8.2) are textual/diagram defects (e.g., Figure 2 typo "advisory-non-only" → "non-advisory"), not architectural changes. Implementation proceeds in parallel; spec v2.2 merge is gating only on forwarding to the head of engineering.

### 3.12 Deliverable format

Ghabriel picked "Plan + handoff compacted file for another agent to execute". The plan and its summary are at `./v0-implementation-plan.md` and `./v0-implementation-plan.summary.md`. This file is the handoff.

---

## 4. LLM_WIKI principles cited in the plan

For each, read the wiki page if a decision feels under-justified.

| Wiki entry | Where the plan uses it |
|------------|------------------------|
| `~/LLM_WIKI/wiki/books/fundamentals-of-software-architecture/ch03-modularity.md` | Cohesion, coupling, connascence. Justifies colocated manifest layout (decision §3.5) and single-workflow file with multi-job path-filtering (decision §3.6). |
| `~/LLM_WIKI/wiki/books/fundamentals-of-software-architecture/ch06-measuring-governing.md` | Fitness functions. Justifies "consistency with existing pattern" (cinematic-judge.yml as the precedent we copy). |
| `~/LLM_WIKI/wiki/books/fundamentals-of-software-architecture/ch07-scope.md` | Architecture quantum. Justifies treating each agent as its own quantum (independent deploy, independent manifest, independent gate job) within one repo. |
| `~/LLM_WIKI/wiki/books/fundamentals-of-software-architecture/techniques/architecture-decisions.md` | ADR format (Michael Nygard). The plan's §7 lists 6 ADRs to author across the framework repo and SOO. |
| `~/LLM_WIKI/wiki/books/learning-domain-driven-design/ch03-managing-domain-complexity.md` | Bounded contexts. Justifies each agent as a bounded context with its own manifest as the context boundary artifact. |
| `~/LLM_WIKI/wiki/books/learning-domain-driven-design/ch10-design-heuristics.md` | The unified decision tree (subdomain → business logic → architecture → testing). The plan's §2.1 "two boundaries" structure follows this. |
| `~/LLM_WIKI/wiki/processes/documentation.md` (Diátaxis) | How-to-guide format for the plan; the summary follows the "explanation" pattern. |

---

## 5. Things the executing agent will discover and should not panic about

1. **Prototype already exists at `prototype/src/vt_agent_redteam/`.** Version 0.0.2 in `pyproject.toml`. Five scorers (one more than the spec's four — `expected_verdict_scorer` is bonus), three runners (`direct_llm_runner`, `http_moderation_runner`, plus LiveKit-related modules `livekit_room.py` + `synthetic_candidate.py`), storage with `postgres_writer.py` + `supabase_writer.py` + `schema.sql`, audio modules including the race-affected `wav_collector.py`. v0 work is **hardening + integrations + new runner**, not greenfield.

2. **`agents/{name}/livekit.{env}.toml` files already specify the LiveKit dispatch name** (e.g., `agents/language-tutor/livekit.staging.toml` declares subdomain `vt-smsjr10d` and agent id `CA_9CtoDv9LUBuw`). The manifest's `livekit.agent_name.{staging,production}` fields should match what the agent registers when it boots — find this in `agents/{name}/agent.py` at the `@server.rtc_session(agent_name=...)` decorator.

3. **`deploy-language-agent-shared.yml`** is the canonical reusable workflow for deploying any of the three agents from SOO. C1 (deploy gate) hooks into this workflow, not into the per-agent ones. Path: `.github/workflows/deploy-language-agent-shared.yml` — read it before modifying.

4. **`supabase/AGENTS.md` has three "deploy-killer rules"** (no-modify-applied, right-folder, timestamped-filename). Read them before touching `supabase/conversation-club/supabase/migrations/`. The repo has had production migration accidents; the rules exist because of those.

5. **SOO's CLAUDE.md has explicit "Ask First" boundaries** for "Infrastructure, deployment, auth, or database-impacting changes." Tasks S5 (secrets), S6 (Supabase migration), S7 (CI service-account JWT) all hit this. Propose PRs and pause for confirmation rather than acting unilaterally.

6. **The user's last directive was implicit:** he locked all decisions and asked for the plan + handoff. He did NOT say "now go execute." Default to surfacing what you intend to do before doing it, especially for cross-team changes.

---

## 6. What to do when you start executing

1. Open `./v0-implementation-plan.md` and read sections §1, §2, §6 (acceptance criteria), §9 (executor's checklist).
2. Decide whether to execute the plan as a single agent or to delegate phases to subagents via `claude-mem:make-plan` + `claude-mem:do`. The plan's Phase 1A (framework), Phase 1B (SOO integration), Phase 1C (deploy gate + alert) are natural slice boundaries.
3. Author the 6 ADRs from §7 first — before any code change. They take 30 min total and lock in the decision trail for reviewers. Three go in the framework repo (`docs/adr/`), three go in SOO (`docs/adr/`).
4. Start Phase 1A (framework changes F1–F7). These are entirely inside `poc_moderation_red_team_promptfoo/prototype/`. F1 (LangfuseTraceRunner) and F4 (PII redaction) are the substantive work; F2/F3/F5/F6/F7 are plumbing.
5. When Phase 1A is complete and tagged v0.1.0, move to Phase 1B (SOO integration). This requires Ghabriel's involvement for S5 (secrets) and S7 (Supabase JWT).
6. Phase 1C (deploy gate + Slack drill) ships the v0 demo.

If anything in the plan turns out to be wrong or under-specified, surface it as a question to Ghabriel; do not silently deviate. The plan was grilled hard for over an hour — if it's wrong, it's wrong in a way that needs another grilling session, not a quiet fix.
