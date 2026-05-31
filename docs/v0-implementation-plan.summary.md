# vt-agent-redteam v0 Implementation Plan — Summary

**Audience:** non-technical stakeholders, leadership, owning teams who need to know what's shipping and what isn't
**Companion to:** `v0-implementation-plan.md` (the full technical plan)
**Date:** 2026-05-30
**Status:** Implementation-ready

---

## What we are shipping in v0

A working safety gate that automatically tests three production LiveKit agents — Language Tutor, Language Checkpoint, and Maya (Support Agent) — every time their code changes, and again before each deploy to production. Failures block the deploy and notify the responsible engineering team on Slack. All three agents live inside the `student-onboarding-orchestration` repository, which hosts the Student Experience v3 product (the `/learner/*` surface that students see today).

The framework is a Python package (`vt-agent-redteam`) installed from a single internal repository. Each agent declares its red-team configuration in a small YAML file next to its own code. There is no central registry to update when a new agent joins.

---

## What changed since the spec was written

The spec was finalized in May 2026 and targeted a single pilot agent (Conversation Club Language Tutor) in a single repository. Between then and now, two things shifted:

1. **The Language Tutor agent was extracted out of `student-onboarding-orchestration` into a new repository called `conversation-club`** (on 2026-05-20). The agent now exists in two places — the new canonical home and a transitional copy in the old home. v0 targets the old home (`student-onboarding-orchestration`) because that is where the Student Experience v3 product lives and where most active engineering attention currently sits.

2. **The audio-capture race condition described in section 15.1 of the spec was bypassed entirely.** Instead of fixing the synthetic-candidate audio capture pipeline (a fix with an open and uncertain timeline), we use Langfuse — already deployed in production across all three agents since 2026-05-18 — as the source of the agent's response transcript. This was explicitly named in the spec as the Phase 2 recovery path; we promoted it to Phase 1 primary. The WAV-collector fix is deferred to v0.2 hardening.

3. **The single-manifest-per-repo pattern in the spec becomes a colocated-manifest-per-agent pattern in v0**, so a multi-agent repository (like `student-onboarding-orchestration`) can describe each agent independently inside its own folder.

All three of these are recorded as Architecture Decision Records (ADRs) committed to the repositories, so future reviewers see exactly what changed and why.

---

## What v0 is not (deferred to later releases)

These items are real and acknowledged. None of them block v0 ship; each has a documented revisit trigger.

| Item | Why deferred | When we come back |
|------|--------------|--------------------|
| Synthetic-candidate audio capture (WAV-collector race fix) | Langfuse-native transcript covers the same need with no race condition. | v0.2 hardening cycle, after v0 adoption is validated. |
| Tool-use scorer for Maya | Architectural gap acknowledged in spec section 15.3. Maya's manifest declares "partial coverage" honestly; the gap surfaces in dashboards. | v0.2 as the highest-priority follow-up. |
| Weekly canary trigger and drift detection | Phase 2 in the spec; adds drift signal that complements PR + deploy gates. | After v0 ships and we have four weeks of evidence from PR/deploy gates. |
| Over-refusal counter-gate (XSTest + OR-Bench) | Detects an agent that refuses everything indiscriminately. Pairs with canary. | v0.2 with canary. |
| LLM-as-judge upgrade for "soft refusal" detection | Today's regex misses empathetic redirects. | v0.3 (Phase 3 per spec). |
| PagerDuty integration for P0 events | v0 ships Slack-only alerts to `#student-experience-v3-launch`. | v0.2. |
| Migration to a dedicated `vt-redteam` Supabase project | v0 piggybacks on the existing `conversation-club` Supabase project with a dedicated schema and access-control roles. | When observability data scope grows beyond red-team, or cross-tenant blast radius becomes a security concern. |
| Per-agent split of the alert-responsible team | All three v0 agents share `eng-met-ui` as the responsible team. | When `language-tutor` and `language-checkpoint` complete their extraction to `conversation-club`, each agent's owning team will own its own alerts. |

---

## What the agents are and what each one tests

| Agent | Where it appears in the student experience | What v0 red-team will check |
|-------|---------------------------------------------|------------------------------|
| **Language Tutor** | The voice tutor for K-12 language learning. Lives at `/learner/nerd-tutor/session` and `/learner/languages/[language]`. | Content safety (violence, sexual, self-harm, hate, harassment); FERPA-relevant data handling; COPPA age gating; prompt injection; system-prompt leakage; brand safety; off-topic redirection. Full coverage. |
| **Language Checkpoint** | The mini-boss/checkpoint screens for K-12 language assessment, with cinematic cutscenes. | Same as Language Tutor — full K-12 coverage. Already shares the repository with a separate "Cinematic Judge" content evaluator; the red-team gate is independent and runs in parallel. |
| **Maya (Support Agent)** | The global support widget present across the entire `/learner/*` shell, invoked with `?ask=maya`. | Prompt injection, system-prompt leakage, escalation boundaries, hallucinated policy, content safety. **Partial coverage:** tool misuse is not scored in v0 (a known gap in the framework). Maya's manifest declares this honestly so dashboards never pretend Maya is fully covered. |

---

## How the gate fires

| Trigger | What runs | Blocks merge / deploy? |
|---------|-----------|------------------------|
| Pull request that touches code under `agents/<name>/` | The smoke set (~12 scenarios) for that agent only. Other agents' jobs are skipped. | Yes — PR cannot merge until the gate is green or an authorized override is recorded. |
| Deploy to staging or production | Smoke set plus high-risk scenarios for the agent being deployed. | Yes — the LiveKit deploy step is never reached if the red-team gate fails. |
| Weekly canary | (Deferred to v0.2.) | n/a in v0 |

Each scenario costs approximately $0.0008 in third-party API tokens (down from $0.003 quoted in spec section 16.4, because the Langfuse-native runner removes the Whisper transcription bill — the agent's own production speech-to-text pipeline pays for that). A typical PR fires ~12 scenarios at ~$0.01 total. A deploy fires ~30 scenarios at ~$0.025. Budget caps in each agent's manifest abort the run if cost exceeds the cap.

---

## What we expect from each stakeholder

| Stakeholder | What we need from them |
|-------------|------------------------|
| **eng-met-ui (the SOO owning team)** | Review and merge the three manifests (one per agent), the new workflow file, and the Supabase migration. Acknowledge alert ownership in `#student-experience-v3-launch`. |
| **Security & compliance** | Approve the policy-profile assignment for each agent (k12_learner / k12_learner / support_navigation). Confirm the FERPA/COPPA scenario scope is appropriate for Language Tutor and Language Checkpoint. |
| **VT4S (framework owner — Ghabriel)** | Ship `vt-agent-redteam` v0.1.0 with the new Langfuse-native runner, the override read path, and PII redaction at write. Author the framework-side ADRs. Support pilot week 1. |
| **Infrastructure / DevOps** | Provision the eight CI secrets for the SOO repository under a new `redteam` environment. Generate the CI service-account JWT scoped to the `ci_redteam_writer` role in the `conversation-club` Supabase project. |
| **Engineering leadership** | Agree on how the v0 adoption metrics (manifest counts, gate-blocking counts, time-to-first-result, active overrides) feed into existing engineering reviews. Treat persistent override usage as a code-yellow signal. |

---

## Risks worth flagging to leadership

1. **The two-home situation for Language Tutor and Language Checkpoint** (transitional copies in `student-onboarding-orchestration`, canonical homes in `conversation-club`) means our work in v0 will need to be ported when the extraction completes. The colocated manifest layout was chosen specifically to make that port trivial.
2. **Maya's tool-use coverage gap** is honestly declared but real. If a tool-misuse incident occurs in production before v0.2 ships the missing scorer, the gate cannot have caught it. This is the most important known gap.
3. **Langfuse ingestion latency** is the only new operational dependency we are taking on. If Langfuse becomes unavailable during a PR run, the framework falls back to the existing direct-LLM runner — coverage degrades but the gate continues to function and the degradation is recorded.

---

## When v0 is done

We declare v0 shipped when, on a real PR against a real branch:

1. The deploy gate blocks a deliberately failing scenario;
2. A Slack alert lands in `#student-experience-v3-launch` with the full payload;
3. The corresponding row appears in `redteam.redteam_runs` with `is_stub_response = false` and `transcript_source = "agent_native_transcript"`;
4. The block can be cleared either by fixing the underlying issue or by a recorded override in `redteam.overrides` (with the override audit table showing who approved, when, and why);
5. All three manifests exist and validate;
6. The final release governance gate closes.

The final release governance gate adds:

- PostHog feature-flag protection for release;
- integration and E2E evidence for the red-team tool;
- strict LLM_WIKI NITPICK code review;
- LLM attack-defense review;
- Strategic View triage of reviewer reports;
- final `vt-agent-redteam` repository/package cutover;
- dense DOCX security traceability audit;
- security pentest and exploitation review;
- final technical and non-technical daily messages after all checks close.

Estimated end-to-end timeline: three weeks from kickoff plus the final governance
window. Two weeks for framework changes; one week for the SOO integration; a few
days for the deploy gate and Slack drill; 3–5 days for final governance if the
reviews do not uncover blockers.
