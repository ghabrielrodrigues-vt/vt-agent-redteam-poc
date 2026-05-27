# LiveKit Primer — Non-Technical Summary

## What is LiveKit?

LiveKit is the technology that lets two people (or a person and an AI) have a live
audio or video conversation in the browser. It is the same kind of plumbing Zoom or
Google Meet use, but designed to be embedded in our own products instead of being a
standalone meeting tool.

## Why does VT use it?

All of our speaking-avatar products — the AI Interviewer, Lemon Slice tutors,
future Nerdy avatars — need three things:

1. A way for the student or candidate to **speak** in the browser.
2. A place where audio is **routed** in real time with low latency.
3. A way for **our AI to listen and respond**.

LiveKit provides (2) directly, and gives us the toolkit to build (1) and (3) on top.

## The three things called "LiveKit"

When someone says "LiveKit", they usually mean one of three things. People confuse
them constantly:

- **LiveKit Server**: the actual computer program that handles audio routing. We can
  run it on a laptop for local development.
- **LiveKit Cloud**: a paid hosted version of the same program, managed by LiveKit
  Inc. That is what runs in production and staging today.
- **LiveKit Agents SDK**: a separate library that helps write "AI bots" that join a
  conversation as if they were a person. That is the part our engineers actually
  write code against.

When stakeholders say "the agents are hosted on LiveKit", they mean our AI bots run
inside LiveKit Cloud, listening to the conversation through LiveKit routing.

## Why this matters for red-team work

We want to test whether the AI handles dangerous prompts safely. For that, the
red-team tool must **pretend to be a person in the conversation**, send the AI a
risky prompt, listen to what the AI answers, and judge whether it was a safe response.

LiveKit is the medium where that conversation happens. So our red-team tool must speak
LiveKit too — open a room, join, send something adversarial, capture the response.

That is why LiveKit was specified: every one of our avatar products shares this same
plumbing, so a single tool that knows LiveKit can test all of them.

## What the red-team tool will NOT do

It will not replace any of the safety filters that already block bad inputs in Nerdy
Tutor. Those stop students from sending harmful things to the AI up front. The
red-team tool does the inverse job: forces the AI to hear something harmful so we
can verify the AI **responds** safely. The two layers are complementary.
