# LiveKit Primer

LiveKit is a real-time media platform — WebRTC underneath. Think of it as
"Zoom-as-a-service, but programmable". It is the foundation every VT voice and avatar
agent is built on.

The confusion most people hit is that **the name "LiveKit" refers to three different
things** that come together. Once you separate them, the architecture becomes simple.

## The three layers

| Layer | What it is | Where it appears in the VT stack |
| --- | --- | --- |
| **LiveKit Server** | Open-source WebRTC server (Go binary). Hosts "rooms", routes audio/video/data between participants. Can run locally via Docker. | Not in any VT repo — we do not self-host. We consume the Cloud version. |
| **LiveKit Cloud** | Hosted version of LiveKit Server, managed by LiveKit Inc. That is what we use in production and staging today. | Our agents authenticate against AWS secret `tutors-service/st/livekit`. |
| **LiveKit Agents SDK** | Node and Python framework for writing "bots" that join rooms as participants with extra powers (capture audio, run STT→LLM→TTS, publish audio back). | Exactly what `varsitytutors/livekit-agents` was built on (`@livekit/agents` v1.2.2). |

The "agent" referenced in the action item is a **process** (a Node worker, in our case)
that connects to a LiveKit room **as if it were a participant**, but with the ability
to hear human audio, run a model, and speak back.

## Why this matters for red-teaming

Red-teaming an agent means: send adversarial input to it, observe the output, score
whether the output is safe. With LiveKit, "input" and "output" are both **audio
streams routed through a room**.

That means a red-team harness must either:

1. **Be a synthetic participant** — join a room as a fake user, send adversarial text
   (or synthesized audio), capture the agent's response, score it. This path is
   language-agnostic (works for TS or Python agents) and mirrors real LiveKit runtime.
2. **Or run the agent in-process** under a test harness — skips the room. Faster, but
   only works if the harness is in the same language as the agent. Because our agents
   are TypeScript and the spike requires a Python package, that path is closed.

Implication: the POC will be a "synthetic participant" against a real LiveKit server
(local or staging).

## Anatomy of a session (concrete step by step)

This is what happens when a tutor candidate starts an interview today:

```
1. Admin dashboard calls the Go tutors-service
2. tutors-service calls the LiveKit Server SDK:
     - Creates room "interview-<uuid>"
     - Sets room metadata (interview_id, subject, system_prompt, storage creds)
     - Dispatches the agent (agentName = "interview-agent")
3. LiveKit Cloud routes the dispatch to a worker in the livekit-agents pool
4. Worker process (Node) wakes up:
     - Parses metadata
     - Connects to OpenAI Realtime websocket (the "Mouth")
     - Starts Room Composite Egress (recording to Supabase Storage)
     - Joins the room as a participant
5. Candidate opens the browser, receives a token, joins the same room
6. WebRTC negotiation: audio flows both directions via LiveKit Cloud
7. Interview loop runs (see docs/02-agent-architecture.md)
8. Candidate disconnects:
     - Agent merges transcript + state machine into room metadata
     - Egress stops, recording finishes uploading
     - LiveKit fires room_finished webhook → tutors-service consumes it
```

The candidate and agent **never talk directly**. Every byte passes through LiveKit
Cloud. That is why rooms are the only sensible isolation unit for red-team: one room
= one test scenario.

## Vocabulary glossary

These terms appear constantly in LiveKit code:

- **Room** — session container. One room = one conversation. Has metadata, participants, tracks.
- **Participant** — anyone in the room: human candidate, agent worker, recorder.
- **Track** — an audio or video stream published by a participant.
- **Data channel** — text messages exchanged between participants (no audio).
- **Egress** — server-side recording or streaming of room tracks. Used for interview MP4s.
- **Dispatch** — LiveKit Cloud telling a worker pool "this room needs an agent named X".
- **Metadata** — arbitrary JSON attached to a room or participant. Used extensively as agent config channel.
- **Token** — JWT a client presents to join a room. Encodes identity, room name, permissions.

## Cost dimension (for context)

LiveKit Cloud charges per participant-minute. A red-team run that opens N rooms × M
turns × ~30s per turn adds up. The package design must be cheap per test, which is
why "local Docker server for PR-time tests, Cloud staging for weekly canary" is the
proposed split — see `docs/03-running-local.md` and `docs/04-poc-design.md`.
