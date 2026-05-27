# Implementation Plan — Non-Technical Summary

This document is the output of a self-conducted review of the POC design. I played both
the tough reviewer asking hard questions and the engineer giving committed answers. The
full transcript is in `06-implementation-plan.md`. This summary captures only the
conclusions.

## The package

- **A new repository**, separate from any existing agent. Name: `vt-agent-redteam`.
- **Distributed via `pip install` from a Git URL** in v0.1 — works in CI without
  internal PyPI infra.
- **Built on the LiveKit Server SDK for Python**, directly. No abstraction layer for
  v0.1; we can add one later if we ever support non-LiveKit agents.

## How the tool talks to the AI

The current AI Interviewer only listens to audio — it has no text input mode. So the
red-team tool will:

1. **Type** the bad prompt.
2. **Convert to speech** using OpenAI TTS.
3. **Publish that audio** into a LiveKit room as if a person were speaking.
4. **Listen back** to the AI's response, transcribe it, and judge it.

That matches the real candidate experience, including speech-to-text variance. Cost per
scenario: ~$0.015. Cost per weekly canary: about $1.50. Negligible.

## What is tested

A scenario lasts at most **90 seconds**, up to **4 turns**. Scenarios run **one at a
time** in v0.1 to keep failure attribution clean; concurrency comes later.

To handle AI non-determinism, **each scenario runs 3 times** and the result is by
majority vote. It costs more, but prevents single-run flakes from failing the build.

## How the corpus works

The catalog of bad prompts is **YAML files inside the package repo**, committed under
version control. That means:

- Running the same package version twice produces the same tests.
- Reviewing the corpus is a normal PR.
- When a scenario fails, the team knows which corpus version produced it.

The first corpus version comes from three places: my Nerdy Tutor moderation list
(already curated), OpenAI Moderation API categories (calibration baseline), and
LiveKit-specific failure modes (prompt injection, system prompt leakage, etc.).

Promptfoo will generate **new** prompts later (v0.2), but those will be human-reviewed
and committed to the corpus — not regenerated on every run. That matches the action
item's call for "weekly/nightly expansion beyond our fixed test set".

## How AI responses are scored

**Three scorers ship in v0.1**:

1. **OpenAI Moderation API** — the same one Nerdy Tutor uses as an input filter, but
   applied to the **AI response** instead of user input.
2. **Refusal detector** — checks whether the AI refused appropriately. Uses simple
   pattern matching plus a small LLM-as-judge call for edge cases patterns miss.
3. **Prompt-leak detector** — checks whether the AI accidentally revealed parts of its
   system instructions.

The team can plug in custom scorers later without changing the package.

## Where results go

A single Supabase table called `redteam_runs`, in the existing VT4S Supabase project,
under a new `redteam` schema. One row per scenario per run. The action item stated
"for now can just be a supabase table"; we follow that.

Retention: 90 days hot, then archived to S3.

CI access: GitHub Actions → AWS OIDC → AWS Secrets Manager → Supabase service-role key.
No long-lived secrets in GitHub.

## When the tool runs

Four moments, each with a different bar:

| Trigger | What runs | Bar to pass |
| --- | --- | --- |
| Every PR | ~10 scenarios (smoke set) | 100% pass |
| Pre-deploy | Full set ~100 scenarios | 90% pass |
| Weekly cron | Full set ~100 scenarios against staging | 85% pass, alert otherwise |
| Manual | Any | Configurable |

Each consumer repo (`livekit-agents`, `lemonslice-demo-agent`, etc.) writes its own
GitHub Actions workflow that imports the package. The package itself owns no workflow
— that keeps the package's job small.

## Risks we already know, with answers

- **AI non-determinism** → each scenario runs 3 times.
- **TTS recognition variance** → store what the AI heard alongside what was intended;
  detect drift in review.
- **Runaway cost** → hard 90-second cap per scenario + per-run budget cap.
- **Agent crashes mid-scenario** → recorded as failure, harness continues.
- **Alert fatigue** → start conservative, adjust thresholds after a month.
- **Corpus staleness** → Promptfoo-generated additions (v0.2) plus quarterly refresh
  from trust+safety incident reports.

## Explicitly out of scope for v0.1

To avoid scope creep:

- Non-LiveKit agent support (the action item stated "evaluate that after").
- Real-time per-turn alerting.
- Replacing any production moderation pipeline.
- Custom STT.
- Custom dashboard UI (Supabase Studio is enough).
- Languages beyond English (Portuguese and Spanish come in Phase 3).

## Phases and timeline

- **Spike (this week)**: this folder + functional prototype.
- **MVP v0.1 (~3 weeks)**: package standing, 30 scenarios, integrated against
  `livekit-agents` as reference consumer, PR check live.
- **Phase 2 (~2 weeks)**: weekly canary, alert notifications, Promptfoo, second agent
  consumer.
- **Phase 3 (ongoing)**: hardening, multi-language, dashboards, more consumers.

## Open questions for the team (not for me to answer alone)

- Who owns the repo? (Trust+safety, VT4S, AI infra?)
- Does ops want a private PyPI mirror first, or is `pip install git+ssh://` OK?
- Final threshold numbers — start at 90% / 85% or different?
- Which alert channel should receive failures?
- SLA to fix a PR blocked by red-team?
- Do we red-team only Mouth output, or also the Brain (Assessor LLM)? The Brain has
  its own potential injection surface.
