# Running LiveKit Locally — Non-Technical Summary

## Why does "local" matter?

Every time we test the AI, two things cost us:

1. **Money**: LiveKit Cloud charges per participant-minute, OpenAI charges per token,
   and our staging Supabase is shared.
2. **Pollution**: Test runs against staging show up in metrics and dashboards, mixed
   with real interviewer test data.

The red-team tool will run **a lot** — on every pull request, weekly as a canary, plus
whenever someone is developing. We need most of those runs to cost zero and pollute
nothing.

The trick is to run LiveKit infrastructure **on the developer's laptop** for cheap
frequent runs, and only hit the cloud for runs that need to be realistic.

## The three options, plainly

There are three ways to "run LiveKit locally", and they are not interchangeable:

1. **Agent on laptop, LiveKit in the cloud.** Easiest if you have AWS access. The AI
   runs on your machine but routing servers are in the cloud. Costs a little money per
   run.
2. **Everything on the laptop.** Slightly more setup (Docker), but completely free and
   can work offline. That is what most red-team runs will use, especially per pull
   request.
3. **Skip LiveKit entirely.** There is a "fake room" mode for unit tests. It is very
   fast, but only works if the test code is in the same programming language as the
   AI. Because our AI is TypeScript and the spike requires the tool in Python, that
   option is closed for us.

## What we will actually do

- For daily red-team tool development and every pull-request check: **everything on
  the laptop** (option 2).
- For the weekly canary that catches problems we otherwise miss (deploy configs, real
  WebRTC behavior, real OpenAI latency): **local-or-cloud agent against LiveKit
  cloud** (option 1).

## What the developer experience should be

A new engineer on the team should be able to clone the POC folder and run two
commands:

```
docker compose up        # starts LiveKit on the laptop
./scripts/dispatch-test-room.sh
```

…and see a red-team scenario running against the AI, with the result printed in the
terminal. The scripts and templates that make that possible live in the POC's
`livekit-local/` folder.
