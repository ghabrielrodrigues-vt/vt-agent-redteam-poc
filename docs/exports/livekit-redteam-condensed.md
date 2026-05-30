# LiveKit Agent Red-Team Hardening — Condensed Solution Brief

**Audience:** VT4S team and per-agent owning teams
**Purpose:** What we are building, how we will roll it out, and which repositories adopt it in which order
**Companion:** the full technical specification (`livekit-agent-red-team-hardening.docx`)

---

## 1. The solution in one paragraph

A single Python package, `vt-agent-redteam`, runs adversarial scenarios against every LiveKit-hosted AI agent at Varsity Tutors and decides whether the agent's behavior passes safety thresholds. Each agent declares its configuration in a `.redteam/manifest.yaml` file in its own repository — there is no central registry. A GitHub Actions workflow invokes the framework on pull requests, deploys, and a weekly canary. Failures block the gate, alert the responsible team, and land in Postgres for dashboarding. The architecture is uniform; the per-agent variation lives in the manifest.

![Figure 1 — System overview](diagrams/01-system-overview.png)

---

## 2. The execution pipeline

For each scenario, the framework loads the manifest, renders the agent's expected metadata, creates a LiveKit room, dispatches the agent worker, joins as a synthetic participant, publishes an adversarial prompt (via TTS audio, HTTP, or a direct-LLM bypass), captures the agent's response, scores it with four parallel detectors, and persists the result with full provenance. The pipeline is identical across runner modes.

![Figure 2 — Per-scenario execution pipeline](diagrams/02-pipeline.png)

---

## 3. Triggers and gating

| Trigger | When | What runs | Blocks? |
|---------|------|-----------|---------|
| Pull request | On every PR | 12 smoke scenarios (~3 min) | Yes |
| Deploy gate | On merge to main | Smoke + high-risk (~5 min) | Yes |
| Production release | On release tag | High-risk against canary | Yes |
| Weekly canary | Cron | Full corpus (195 scenarios) | Alert only |
| Manual | Operator invocation | Targeted category | No |

![Figure 3 — Trigger model](diagrams/03-triggers.png)

The blocking decision applies severity precedence: a single P0 failure (privacy leak, prompt leak, severe safety failure) blocks regardless of aggregate pass rate; below that, the manifest's threshold applies. A stubbed run (any row marked `is_stub_response = true`) forces the gate to a NULL state with exit code 3 — the framework refuses to let a stub pretend to be a real gate.

![Figure 4 — Gate decision tree](diagrams/04-gate-decision.png)

---

## 4. Results capture and feedback

Every scenario execution produces one durable row in Postgres (`redteam.redteam_runs`) with the adversarial prompt, the captured agent response, per-scorer verdict, severity, cost, and provenance fields (`is_stub_response`, `transcript_source`, `response_hash`, `artifact_uri` pointing to the captured audio or transcript).

Results are surfaced to the responsible team through four channels:

- **GitHub Check** on the PR or deploy workflow with pass/fail + a link to the run.
- **Slack alert** on failure with the agent, severity, failing scenario identifiers, scorer reasons, and a dashboard link.
- **Dashboard** backed by three Postgres views: pass rate by bucket per agent per week, recent failures, and cost per run.
- **`run_summary.json`** artifact attached to every workflow run for CI consumption.

Categorization is uniform across the fleet. The 22 detailed scenario categories collapse into three general buckets (computed by Postgres, not by the application — they cannot drift):

- **`content_safety`** — violence, sexual, self-harm, hate, harassment.
- **`policy_compliance`** — politics, forbidden topics, dating and romance, diversity framing, off-topic academic.
- **`privacy_integrity`** — personal information, prompt leakage, cheating integrity, brand and stakeholder protection, impersonation, emotional manipulation, jailbreak, illicit content.

Every dashboard, every Slack alert, and every weekly trend report uses these three buckets. The agent owning team always sees "your agent's pass rate by content_safety, policy_compliance, privacy_integrity" — not a different categorization per team.

## 5. Implementation at Varsity Tutors

Implementation is deliberately incremental and per-team. Each agent's owning team commits the manifest in their own repository; VT4S maintains the framework. Adoption proceeds in five waves:

1. **Pilot (4 weeks) — Conversation Club Language Tutor.** VT4S owns the manifest end-to-end. Goal: one non-stub deploy gate run that blocks a deliberately failing PR. Produces the canonical reference implementation.
2. **First voluntary onboarding (2 weeks) — Tutor Interviewer.** Pair-engineered with the owning team. Validates the TypeScript path and the 30-minute onboarding target.
3. **Pattern documentation (1 week).** VT4S publishes a one-page adoption guide, a `vt-agent-redteam-cookbook` repo with three pre-filled manifest templates (K-12, support, commerce), and a brown-bag for the broader org.
4. **Wave onboarding (6 weeks).** Maya Support, Course Platform Live, Checkout Quote Avatar, and the Checkout Video variants onboard in parallel with light VT4S support — under four hours of VT4S engagement per agent.
5. **Steady state.** New agents adopt the framework as part of their initial deploy workflow, not as a retrofit. VT4S supports asynchronously via a dedicated Slack channel.

**Adoption metrics surfaced to leadership.** Number of agents with active manifests; number with workflows running; median time from PR open to first gate result; active overrides per agent and per team; canary pass rate by bucket over time.

---

## 6. Per-repository applicability

The sixteen LiveKit-hosted agents discovered in the `varsitytutors` organization, with the wave each enters:

| # | Agent | Repository | Policy profile | Wave |
|---|-------|------------|----------------|------|
| 1 | Tutor Interviewer | `varsitytutors/livekit-agents` | `interview_assessment` | **Pilot+1 (P1)** |
| 2 | Language Tutor (Conversation Club) | `varsitytutors/conversation-club` | `k12_learner` | **Pilot (P0)** |
| 3 | Language Checkpoint | `varsitytutors/conversation-club` | `k12_learner` | Wave 4 |
| 4 | Maya Support Agent | `varsitytutors/student-onboarding-orchestration` | `support_navigation` | Wave 4 |
| 5 | Course Platform Live | `varsitytutors/b2b-course-platform` | `b2b_course` | Wave 4 |
| 6 | Checkout Quote Avatar | `varsitytutors/livekit-lemonslice-avatar-quotes` | `commerce_checkout` | Wave 4 |
| 7 | Nerdy Avatar Tutor (Gemini POC) | `varsitytutors/nerdy-avatar` | `k12_learner` | **Pilot+2 (P2)** |
| 8 | Nerdy Avatar JPW fork | `varsitytutors/nerdy-avatar-jpw` | `k12_learner` | Wave 4 |
| 9 | Nerdy Tutor POC | `varsitytutors/nerdy-tutor-poc` | `demo_poc` | Out of scope (stale) |
| 10 | Nerdy Tutor POC2 | `varsitytutors/nerdy-tutor-poc2` | `demo_poc` | When promoted |
| 11 | Checkout Video Agent (redesign) | `varsitytutors/redesign-avatars-quotes-checkouts` | `commerce_checkout` | Wave 4 |
| 12 | Checkout Video Agent (transfer) | `varsitytutors/temporary-quote-avatar-transfer` | `demo_poc` | When promoted |
| 13 | Cloud Avatar Video Agent | `varsitytutors/video-agent` | n/a | Superseded |
| 14 | AI Video Agent (Groq POC) | `varsitytutors/ai-video-agent` | n/a | Abandoned |
| 15 | LemonSlice Demo Agent | `varsitytutors/lemonslice-demo-agent` | `demo_poc` | When promoted |
| 16 | temp-practice-v2 | `varsitytutors/temp-practice-v2` | n/a | Scratch |

The MVP coverage (rows 1, 2, 7) is selected because it spans every dimension of stack diversity in the inventory: two runtimes (Python + TypeScript), three LLM backends (OpenAI Realtime, OpenAI gpt-5-mini, Gemini Live), agents with and without the LemonSlice avatar, and both typed and ad-hoc metadata schemas. Validating these three validates the framework's reusability claim against the full fleet.

---

## 7. What changes in each repository

For an agent to be covered, three small artifacts must exist in its own repository:

- `.redteam/manifest.yaml` — declares the agent's LiveKit dispatch name, policy profile, metadata template, thresholds, and override authority. Roughly 100 lines of YAML, copied from a template.
- `.github/workflows/redteam.yml` — a ten-line workflow file invoking the framework's reusable workflow with the manifest path and the trigger mode.
- Four CI secrets configured in repository settings: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `OPENAI_API_KEY`.

No source code changes to the agent. No central registry to update. The agent's owning team retains control of the configuration and reviews the manifest pull request normally.

---

## 8. Boss-role review — current standing

The document has been through two rounds of cold review by the role of senior engineering leadership. The most recent verdict is **greenlight-with-conditions** — the document is ready to forward once the small textual defects and operational reframing items below are addressed.

### 8.1 Issues fully resolved through revision

1. Section 4.2 no longer forwards to a non-existent "companion document" — the full sixteen-agent catalog is inline.
2. Section 15 leads with the audio-capture P0 blocker, names the race condition, defines four validation criteria for declaring the fix complete, and is honest about the `messageCount=0` caveat in the prior TypeScript proof.
3. Section 16.4 walks the cost model arithmetically — $0.003 per scenario, $54/year per agent at MVP cadence, $2,000/year aggregate with contingency, reconciled to the $20,000/year twenty-agent extrapolation.
4. Sections 10.6 and 10.7 supply per-scorer false-positive budgets (XSTest, OR-Bench) and the over-refusal counter-gate.
5. Section 14 frames reusability as design intent pending Phase 2–3 validation rather than asserting it as fact.

### 8.2 Conditions for greenlight (must fix before forwarding to head of engineering)

1. **Figure 2 typo.** "all advisory-non-only scorers must pass" must read "all non-advisory scorers must pass". This is the canonical pipeline diagram — the typo is the first thing a reader notices.
2. **Document version banner.** Top of the doc still says v2.1; bump to v2.2.
3. **Section 4.2 lifecycle accounting prose.** The sentence "Transitional or demo: 3 … totaling 4" is internally contradictory. The leading "3" should be "4"; labels need to be consistent across the table and the prose.
4. **Section 17.6 (adoption strategy).** Currently reads as if other organizations (security & compliance, engineering leadership) have already committed to the listed behaviors. Either cite written sign-off or reframe the section as "proposed adoption strategy, pending stakeholder sign-off."
5. **Appendix K.12 contradicts Section 15.1.** The chronological run example shows the audio path working end-to-end, but the audio capture P0 is documented as unresolved. Either label K.12 as a post-Phase-1 target run or rewrite in `direct-llm` mode.
6. **Override read path is asserted but not specified.** The override runbook (Appendix I) says inserting a row in `redteam.overrides` is the only mechanism that allows bypass, but no section describes how the workflow reads that table at gate-evaluation time. Specify the code path.
7. **Section 12.4 PII redaction.** Clarify whether the un-redacted agent response is preserved under `artifact_uri` — otherwise the evidence the scorer flagged is destroyed at write time.
8. **Storage naming inconsistency.** Figure 1 says "Postgres / Supabase", Section 12.1 says "Postgres", Section 17.2 says "Supabase". Pick one and use it consistently.

### 8.3 Polish items (nice to have)

- Section 5.4 token-scoping #4 should name the GitHub mechanism (Environments + OIDC, branch-protected secrets, etc.) by which production-canary secrets are scoped.
- Section 13 prose should add one sentence acknowledging that a stubbed P0 produces exit code 3 (NULL), not exit code 2.
- Section 17.6 metric "deploy is gated by the threshold" should split into "gate exists" and "gate blocks deploy" — different states with different acceptance criteria.
- Appendix J should name at least one concrete test per layer; currently it is a coverage target plus three sentences.
- Section 14.1 line items "Add support-agent deploy workflow if absent" and "Needs course fixture maintainer" need owners or a delegation to the post-MVP wave.
- Add a paragraph on "framework is down or broken" — the operational path when the gate itself is the blocker, not the agent.
- Section 10.6 calibration and Section 8.4 corpus expansion are both quarterly; specify ordering (calibration runs after corpus stabilizes).

### 8.4 Assessment against the original criteria

Sixteen of sixteen review criteria pass or pass-with-edit. None fail. Once items 1–3 in 7.2 are applied — they are textual defects, not architectural changes — the document is ready to forward. Items 4–8 in 7.2 should follow before the broader engineering audience reads it.

---

## 9. What we ask the team for next

- Conversation Club, Tutor Interviewer, and Nerdy Avatar Gemini teams: a 30-minute kickoff with VT4S to confirm policy-profile assignments and walk through the manifest template.
- Security & compliance: written confirmation of the policy-profile assignments and of the FERPA/COPPA scenario scope.
- Engineering leadership: agreement on the adoption metrics surfaced in 17.6 and on the override-audit visibility commitment.
- Infrastructure: provisioning of the Postgres schema (`redteam`) and of the four CI secrets per consuming repository.

Once those are in place, Pilot week 1 begins.
