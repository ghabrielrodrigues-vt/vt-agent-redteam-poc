# Red-Team Hardening — Executive Summary

**Owner**: VT4S | **Status**: Spike complete, MVP greenlit with conditions | **Date**: May 2026

---

## TL;DR

We built a reusable Python package that adversarially tests **any LiveKit-hosted AI agent at Varsity Tutors / Nerdy**, scores the responses, and blocks deploys when safety thresholds fail. 16 production / POC agents have been mapped; 3 are in MVP scope. Validated end-to-end on real LLM responses, writing real rows to Postgres. **One concrete blocker remains** before v0.1 ship: committing the GitHub Actions workflow inside the first consumer repo.

---

## The problem

Nerdy ships AI agents to K-12 students, tutor candidates, paying customers, and B2B course learners — all over LiveKit + LemonSlice. Today there is **no automated check** that an agent change does not regress on safety behavior. Each team handcrafts moderation logic independently, and policy expectations (FERPA, COPPA, K-12 content rules, brand safety) are inconsistently enforced.

---

## The solution

A Python package — **`vt-agent-redteam`** — that any LiveKit agent repo installs via `pip` and calls from CI. The package contains the adversarial corpus, scorers, runners, and Postgres writer. Each agent ships a small `.redteam/manifest.yaml` describing its dispatch name, metadata schema, and policy profile. **Zero changes to the package** when onboarding a new agent.

Architecture in four bullets:

- **One package, many agents** — installable from a single internal repo
- **Per-agent manifest** — declares dispatch name, scenario buckets, thresholds, override authority
- **Six policy profiles** — `k12_learner`, `support_navigation`, `commerce_checkout`, `interview_assessment`, `b2b_course`, `demo_poc` — so K-12 scenarios run only against K-12 agents
- **One results schema** — `redteam.redteam_runs` in Supabase, with dashboards by category, agent, week, and cost

---

## Status today

- **195 adversarial scenarios** across 22 categories (English + Portuguese), covering content safety, K-12 policy compliance, FERPA/COPPA, prompt security, and stakeholder protection
- **4 scoring layers** running in parallel per scenario (refusal detection, prompt-leak detection, forbidden-topics detection, OpenAI Moderation API)
- **4 runner modes** — local Docker, real LiveKit audio, HTTP moderation endpoint, direct-LLM bypass
- **Validated end-to-end against real LLM responses** — `run_id 7a48a9b6` produced 40 real (non-stub) rows in Postgres, with cost tracking, response hashing, and threshold enforcement
- **16 LiveKit agents mapped** across the `varsitytutors` org — 6 in production, 5 in POC, 5 stale / superseded
- **3 agents selected for MVP coverage**: Conversation Club (P0), Tutor Interviewer (P1), Nerdy Avatar Gemini (P2) — together exercising 2 runtimes × 3 LLM backends × ±LemonSlice avatar
- **Promptfoo + PyRIT integrated** for corpus expansion and multi-turn attack generation
- **Tooling research complete** — 12 industry tools compared across 5 architecture layers, with adopt / watch / avoid verdicts

---

## Cost projection

| Workload | Cost per run | Cadence | Annual estimate |
| --- | --- | --- | --- |
| PR smoke check (per PR) | ~$0.005 | ~50 PRs/week/agent | ~$500 |
| Deploy gate (per deploy) | ~$0.50 | ~3 deploys/week/agent | ~$200 |
| Weekly canary (full corpus) | ~$8 | 52 weeks | ~$416 |
| Promptfoo / PyRIT quarterly generation | ~$1 | 4× per year | ~$4 |
| **Total annual cost (3 agents in MVP)** | | | **~$2,000** |

This is roughly 10× cheaper than the lowest-tier commercial alternative (Lakera Guard, Robust Intelligence) while owning the K-12-specific corpus.

---

## Risks

- **Audio capture race condition** still open — bypassed with direct-LLM runner for the spike, fix in Phase 1
- **Scorer false negatives** on "soft refusals" — known limitation, LLM-as-judge upgrade planned for v0.2
- **Adoption dependency** — needs commitment from one consumer agent team (Conversation Club) to commit the first workflow

---

## What is required to ship v0.1 (the three remaining items)

1. **Workflow committed in a consumer repo** — `.github/workflows/redteam.yml` in `varsitytutors/conversation-club`, with one green Actions run writing a non-stub row
2. **Real audio path closed** — one `transcript_source=livekit_audio_capture` row from staging
3. **Slack alert wired** — webhook flag + on-call channel + one demonstrated alert firing

Estimated effort: **5–10 engineer-days** across these three items.

---

## Decision asked of leadership

Approve VT4S to proceed with **MVP prep work** (Phase 1) on the items above. Phase 2 (canary cadence + second agent onboarding) and Phase 3 (dashboards, multi-language, LLM-as-judge) follow contingent on successful v0.1 close. **No additional headcount requested**; existing sprint capacity covers Phase 1.

---

## Where to go for more detail

- Spike doc (architecture, manifest schema, deploy trigger model): `docs/12-livekit-redteam-hardening-solution.md`
- Tooling research (12 tools compared): `docs/08-tooling-dossier.md`
- Agent inventory (16 agents mapped + MVP rationale): `docs/11-agent-coverage-matrix.md`
- Code: [github.com/ghabrielrodrigues-vt/vt-agent-redteam-poc](https://github.com/ghabrielrodrigues-vt/vt-agent-redteam-poc) (private)
