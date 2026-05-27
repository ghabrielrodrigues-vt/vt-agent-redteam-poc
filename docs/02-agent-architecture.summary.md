# Agent Architecture — Non-Technical Summary

## What is the AI Interviewer really like inside?

The AI Interviewer is not a single AI. It is **two AIs working together**, with very
different jobs.

- The **Mouth** is the voice the candidate hears. Its only job is to speak naturally,
  listen, and follow instructions. It is not allowed to decide which question to ask
  next or whether the candidate's answer was good.
- The **Brain** is invisible to the candidate. It reads each answer the candidate
  gives, **scores** it like a teacher grading homework, then **writes the next
  instruction** for the Mouth — "ask a follow-up", "move to the next topic", "wrap
  up, time is running out", and so on.

We separated the two that way for three reasons:

1. The Mouth can never accidentally reveal the score to the candidate, because it
   does not know it.
2. The Brain grades each answer **independently**, without seeing the rest of the
   conversation. That prevents a bad answer from dragging down later scores or a
   good answer from giving undue benefit of the doubt.
3. Interview flow is **rule-based code**, not LLM. That keeps the experience
   consistent across thousands of interviews.

## Why is this relevant for red-team testing?

Because of three architectural choices, our agent is **unusually easy to red-team**:

1. **All configuration lives in "room metadata".** When a new interview starts, the
   server attaches a small JSON document to the LiveKit room with the system prompt,
   subject, interview type, and storage credentials. The agent reads that and runs the
   interview accordingly. The agent **has no database and no API knowledge** of its
   own.

   For us, that means a red-team test can spin up a room with whatever configuration
   we want and exercise the agent in any state — different subjects, different prompts,
   different personas — without touching production data.

2. **At the end of every interview, the agent writes everything back to room
   metadata** — the full transcript, every score, the recording path. That is the
   perfect place for a red-team tool to read the conversation and judge it.

3. **The system format is the same across all our LiveKit agents.** They all follow
   the same Mouth-Brain pattern, the same metadata configuration channel, the same
   finalization step. A red-team tool that learns that pattern once works against
   every agent we ship.

## What this means for the POC

The POC will not change agent code. It will sit beside the agent as an external tool
that:

1. **Pretends to be a candidate**: opens a LiveKit room with a chosen scenario in
   metadata, joins, and "talks" to the agent.
2. **Reads the final transcript and scores from room metadata** after the
   conversation ends.
3. **Judges the agent's responses** against the safety criteria the company cares
   about.
4. **Writes the result to a small Supabase table** so we have a record of every run.

Because all our LiveKit agents share the same structure, the same tool works against
the AI Interviewer today, Lemon Slice tutors next, and any future avatar the company
builds.
