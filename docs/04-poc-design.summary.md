# POC Design — Non-Technical Summary

## What is this tool, in one sentence?

A small Python package that pretends to be a malicious student or candidate, sends
dangerous prompts to our AI agents through LiveKit, checks whether the AI handles
them safely, and writes the result to a small database table.

## Where will it live?

In its own repository. **Not inside** any existing agent repo. Reasons:

- Our agents are written in TypeScript; the spike requested Python specifically.
- We want other teams (Lemon Slice, video agent, future avatars) to install this tool
  with one command — they cannot if it is buried inside the interview agent repo.
- The tool will evolve faster than any individual agent. Keeping it separate prevents
  "I broke red-team while fixing the interview agent" merges.

## How does it actually work?

Think of it as a tester robot:

1. The tool reads a list of "bad prompts" we maintain (organized by category:
   violence, sexual content, self-harm, jailbreak attempts, system prompt leakage,
   etc.).
2. For each bad prompt, the tool **opens a LiveKit conversation** and pretends to be
   the student or candidate.
3. The tool sends the bad prompt and **records what the AI answers**.
4. The tool **judges the AI's response** using several scoring methods:
   - Does the OpenAI Moderation API flag the response as unsafe?
   - Did the AI refuse politely, or play along?
   - Did the AI accidentally reveal its system instructions?
5. The tool **saves the result** to a Supabase table so we can review it later.

## When does it run?

Four moments, deliberately:

1. **On every pull request** to a LiveKit agent repo — runs a fast set (~10 scenarios)
   against local LiveKit so the PR author knows if they broke something.
2. **Before every deploy** — runs the full set against local LiveKit and blocks deploy
   if too many fail.
3. **Before promoting to production** — runs the full set against the real staging
   environment to catch deploy configuration problems.
4. **Once per week** — runs the full set against the live production environment as a
   canary, even if no deploy happened. Catches slow drift, partner API changes, OpenAI
   model updates.

If any of them fail too many scenarios, the team gets an alert (notification channel
to be decided later).

## What about tools like Promptfoo?

The action item mentioned shopping our prompt generation to Promptfoo. It is a great
fit — but for the next iteration, not the first. The first version uses a hand-curated
list of bad prompts so we know tests are reproducible. Once that is stable, Promptfoo
can generate new categories and we materialize them in the same format.

## How does the POC connect to my Nerdy Tutor moderation work?

See `05-moderation-connection.summary.md` for the full answer. Very short version:
the categories and phrase list I already curated for the Nerdy Tutor input filter
become the **seed corpus** for the red-team tool's adversarial prompts. The OpenAI
Moderation API integration I built as the L2 input filter is **reused to score AI
responses** in the red-team tool. The Supabase schema design follows the same
patterns. The moderation work was not wasted — it produced reusable assets for this
new layer.

## What does "done" look like for the POC?

The POC is a writeup, a functional skeleton, and one end-to-end scenario. It is not a
finished tool. After the spike is accepted, hardening into a v0.1 release is separate
work.
