# Agent Architecture — `livekit-agents` (Tutor Interview)

This document describes the internal architecture of `varsitytutors/livekit-agents`, the
repo that contains VT's production LiveKit agents. It currently has one agent
(`tutor-interview`); the structure was designed to host more.

## Overview: Mouth + Brain

Two LLM roles working together. **The Mouth never decides what to do next — the Brain
decides.**

- **Mouth**: OpenAI Realtime (`gpt-realtime-mini`). Speaks, listens, follows
  instructions. Has one job-relevant tool: `assess_answer`. Never evaluates. Never
  decides flow.
- **Brain**: Assessor LLM (LLM-as-judge, non-realtime) + state machine (deterministic
  code). Scores each answer, decides what happens next, generates the next instructions
  for the Mouth.

That separation is enforced architecturally: the Mouth has no access to scores or
state. The Assessor has no access to conversation history (judges each answer in
isolation, to avoid anchoring bias).

## Folder map

```
src/
  agents/tutor-interview/
    agent.ts            — Entry point. Wires Mouth + Brain, tool calling, egress, metadata write
    state-machine.ts    — Phases, question tracking, time management, scores
    assessor.ts         — Scores candidate answers (LLM-as-judge)
    prompt-builder.ts   — Builds intro and wrap-up prompts from config
    greeting-controller.ts — Conditional greeting by type (HIRING vs SUBJECT)
    models.ts           — Multi-model factory (OpenAI / Google Gemini)
    types.ts            — Zod schemas for room metadata, internal state types
    constants.ts        — Timing thresholds
  lib/
    logger.ts           — Structured logging with Winston
    metadata.ts         — Room metadata parser (snake_case → camelCase)
    egress.ts           — Room Composite Egress recording to Supabase Storage
    monitoring.ts       — Session tracking, error alerts, global handlers
    langfuse.ts         — LLM call observability
    otel.ts             — OpenTelemetry export
  index.ts              — Agent registration, room-name filter, CLI entry
```

Stack: TypeScript, Node.js 22, LiveKit Agents SDK 1.2.2, Zod, Winston.

## Configuration model: zero database, everything via room metadata

This is the most important architectural fact for the red-team POC.

The agent has **zero database access**, **zero knowledge of the tutors-service API**,
and **zero hardcoded credentials**. Everything it needs arrives in LiveKit room
metadata, set by the Go tutors-service when the room is created:

```json
{
  "interview_id": "uuid",
  "subject_name": "Portugues",
  "interview_type": "HIRING",
  "system_prompt": "Full interview instructions from admin dashboard...",
  "storage": {
    "endpoint": "...", "access_key": "...", "secret_key": "...",
    "bucket": "...", "region": "..."
  }
}
```

The `system_prompt` contains the full interview structure — persona, skill areas,
question guidance, guardrails — assembled by tutors-service from the admin dashboard.
Adding a new subject or changing interview behavior means updating admin UI data; no
agent code change, no redeploy.

**Why this matters for red-teaming**: a red-team test can spin up a room with arbitrary
metadata (different `system_prompt`, different `interview_type`, etc.) and exercise
the agent in any configuration without production admin database access. The
"configuration surface" is room metadata, and it is under our control.

## Per-turn flow

```
┌─────────────────────────────────────────────────────────┐
│                        MOUTH                             │
│                  (Realtime LLM)                          │
│                                                          │
│  1. Speaks the question (following Brain instructions)   │
│  2. Listens to the candidate's answer                    │
│  3. Calls assess_answer(question, candidateResponse)     │
│                         │                                │
│                         ▼                                │
│  6. Receives instructions ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ │
│  7. Speaks naturally following instructions              │ │
└─────────────────────────────────────────────────────────┘ │
                          │                                 │
                          ▼                                 │
┌─────────────────────────────────────────────────────────┐ │
│                        BRAIN                             │ │
│                                                          │ │
│  4a. Assessor LLM scores the answer                      │ │
│      → { score: 7, quality: "adequate", reasoning, ... } │ │
│                                                          │ │
│  4b. State machine processes the score                   │ │
│      → decides: follow-up / next topic / wrap-up         │ │
│                                                          │ │
│  5. Prompt builder generates instructions                │ │
│      → "Ask a follow-up about their teaching method"  ──┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Phase-scoped tools

The Mouth's tool set changes by interview phase. The Brain swaps tools on the Mouth's
list as state advances:

| Phase | Tools available to the Mouth |
| --- | --- |
| `introduction` | `start_interview` |
| `interviewing` | `assess_answer`, `request_end_interview` |
| `wrap_up` | `end_interview` |

State transitions are deterministic:

| From | To | Trigger |
| --- | --- | --- |
| `introduction` | `interviewing` | Mouth calls `start_interview` after candidate signals readiness |
| `interviewing` | `wrap_up` | Remaining time below threshold, OR Mouth calls `request_end_interview` |
| `wrap_up` | `ended` | Mouth calls `end_interview`, OR candidate disconnects, OR wrap-up watchdog fires |

## Type-conditional surface

The agent runs two interview types (`HIRING` and `SUBJECT`). Type-specific
customization is deliberately small — **only three files branch on
`interview_type`**:

1. `greeting-controller.ts` — spoken greeting framing phrase
2. `prompt-builder.ts` `buildIntroductionPrompt` — `typeLabel` and format explanation
   bullet
3. `assessor.ts` — assessor system prompt includes type so the judge LLM adjusts
   standards

Everything else (state machine, tools, phases, finalization) is type-agnostic. Adding a
future type touches only those three files.

## Finalization (when the candidate disconnects)

1. Agent extracts transcript from Realtime LLM conversation history
2. State machine data (phases, scores, timing) is serialized
3. Both are merged into room metadata via `RoomServiceClient.updateRoomMetadata` (room
   is still alive at this moment)
4. Local webhook fires if `WEBHOOK_LOCAL_URL` is set (dev testing)
5. Egress stops → recording finishes uploading to Supabase Storage
6. Room closes → LiveKit sends `room_finished` webhook to tutors-service with updated
   metadata

The backend receives transcript, scores, and recording path in one payload.

## What this says about red-team integration points

There are three natural seams in this architecture where a red-team harness can plug
in:

| Seam | What it gives | Cost |
| --- | --- | --- |
| **Room metadata** (config channel) | Drive the agent to any persona, subject, prompt config via metadata injection. No code change. | Free. How the POC configures scenarios. |
| **`assess_answer` tool response** | Per-turn assessor score/reasoning is structured JSON. A red-team scorer could observe it. | Requires access to agent internal log stream or Langfuse traces. |
| **Final transcript in room metadata** | Full conversation, scores, and recording path written back to metadata at session end. Read-only. | Free. Primary data source for post-hoc scoring. |

The POC should consume the **final transcript** (seam 3) for scoring and use **room
metadata injection** (seam 1) for scenario configuration. Seam 2 is for deeper future
integration if we want per-turn alerting.
