# Spike — Red-Team Harness for LiveKit Agents

> Drop-in message for the `#avatar-sync` Slack thread. The intent is to make this
> postable as-is, with only the author's name in the closing line.

---

Following up on the Avatar Sync action item — here is the spike write-up for
the red-team harness. I'd appreciate feedback on the four open questions at the
end before we kick off the MVP.

## TL;DR

- **One Python package**, new repo `varsitytutors/vt-agent-redteam`, distributed
  via `pip install git+ssh://...@vX.Y.Z` for v0.1 (private PyPI is a v0.2 question).
- **Plug-and-play** for any LiveKit-hosted agent: the harness creates a real
  LiveKit room with adversarial metadata, joins as a synthetic candidate
  (TTS → audio track), captures the agent's reply, and scores it.
- **125 scenarios across 22 categories**, covering **every bullet** of the
  Nerdy Tutor `CONTENT_MODERATION_PROMPT` in production
  (`student-onboarding-orchestration/lib/ai/moderation.ts`) plus academic
  extensions from OWASP LLM Top 10 (2025), NIST AI RMF, and MITRE ATLAS.
  Full mapping in `docs/07-corpus-policy-coverage.md`.
- **Four scorers in v0.1**: `openai_moderation` (reused from the Nerdy Tutor
  L2 input filter — applied to *responses* now), `refusal_detector`
  (multilingual EN+PT regex + LLM-as-judge), `prompt_leak_detector` (n-gram
  overlap vs known system prompt), `forbidden_topics_detector`
  (keyword/regex against the named K-12 forbidden topics: modern politicians,
  Gaza/Palestine, climate change, COVID, abortion, etc.). All pluggable
  via a `Scorer` protocol.
- **Runs four ways**: PR-time smoke (Docker LiveKit, ~3 min), pre-deploy gate
  (full corpus on local Docker), pre-prod-promotion (full corpus on Cloud
  staging), weekly cron canary (full corpus on production). Each consumer repo
  owns its own GitHub Actions workflow.
- **Results in a Supabase table** (`redteam.redteam_runs` in the existing
  `vt4s-supabase` project). 90 days hot retention, S3 archive after.

## Architectural shape

```
   ┌──────────────────────────────────────────────────────────────────┐
   │  Consumer repo (e.g. livekit-agents)                             │
   │                                                                  │
   │  1. docker compose up livekit  (or staging Cloud URL)            │
   │  2. start the agent (npm start &)                                │
   │  3. pip install vt-agent-redteam && vt-redteam run --tags smoke  │
   │       └─► YAML corpus → LiveKitRoomRunner → scorers → Supabase   │
   │       └─► exit 1 if pass rate below threshold                    │
   └──────────────────────────────────────────────────────────────────┘
```

Three integration seams in the existing `livekit-agents` Mouth+Brain
architecture make this clean:

1. **Room metadata as config channel** — drive the agent into any persona /
   subject / system prompt via metadata injection. Zero agent code changes.
2. **Final-transcript-in-metadata** — at end-of-session, the agent writes the
   transcript + scores back into room metadata. Harness reads this for scoring.
3. **Phase-scoped tools** — the agent's `assess_answer` tool can later be a
   per-turn alerting seam if needed (v0.2+).

## Connection to the Nerdy Tutor moderation work (PRs #1667, #1669)

These two things are **complementary, not duplicates**:

| Dimension | Nerdy Tutor moderation | Red-team POC |
| --- | --- | --- |
| When it filters | Before LLM sees input | After LLM responds |
| What it measures | Is the *user input* safe? | Is the *agent response* safe? |
| Where it runs | Inline in the request | Test harness + canary |
| Channel | Text (chat) | Voice/avatar (LiveKit) |

What carries over: the categorized corpus from `learner_text_moderation_terms`
seeds the adversarial scenarios, the OpenAI Moderation API integration is
reused as an output scorer, and the Supabase schema patterns inform the
results table. What doesn't: the L1/L2/L3 inline pipeline stays where it is
(input moderation, production); the red-team package is a separate Python
artifact for output testing.

## Options considered, with verdicts

| Option | Verdict |
| --- | --- |
| **A. Synthetic participant via TTS + audio track** | ✅ Chosen for v0.1. Tests the real STT→LLM→TTS path, agnostic to agent language, ~$1.50 per canary run. |
| **B. Add data-channel text input to the agent** | ❌ Not v0.1. Would require an agent-side ticket against `livekit-agents` and only covers our own agents. Loses STT realism. |
| **C. In-process test harness** | ❌ Closed. Only works if harness is same language as agent. Our agents are TS, package is Python. |
| **D. Mock the agent, score stub responses** | ❌ Wrong shape. Misses the whole stack we are trying to verify. |

## Promptfoo

The boss called this out. v0.1 ships a hand-curated corpus (~40 scenarios at
spike close, 30 minimum required at MVP, expanding from there) because
reproducibility beats novelty when we are establishing a regression baseline.
v0.2 lets Promptfoo generate candidate scenarios that humans review and commit
into the corpus YAML. That keeps the test set version-controlled while still
broadening over time.

## What is built today (spike artifacts)

A working `prototype/` skeleton in the `poc_moderation_red_team/` folder:

- Installable Python 3.13 package (`pip install -e .`)
- ~40 scenarios across 9 categories (violence, sexual, self_harm, hate,
  harassment, illicit, jailbreak, prompt_leakage, education_specific), with
  English and Portuguese variants
- Three scorers working end-to-end (refusal_detector multilingual,
  prompt_leak_detector, openai_moderation with graceful offline degradation)
- LiveKitRoomRunner that creates real rooms against a local LiveKit Server
  (verified in `poc-livekit-server` Docker logs)
- Supabase writer with dry-run mode + `schema.sql` ready to apply
- Typer CLI: `vt-redteam run`, `list-scenarios`, `--version`

End-to-end demo:

```
$ vt-redteam run --tags smoke --dry-run
→ Loaded 13 scenario(s)
→ Created 13 real LiveKit rooms (sids visible in server logs)
→ Ran 3 scorers per scenario, 100% pass on stubbed agent responses
→ DRY-RUN: would write 13 rows to redteam.redteam_runs
```

The full design lives in `docs/` (six tech docs + six non-technical companions).

## What is intentionally stubbed at spike close

These are MVP-phase work, scoped out from the spike:

- The synthetic candidate's actual audio path (TTS + livekit-rtc publish +
  capture + Whisper transcription). Today the harness creates the room and
  uses a canned stub response so the scorer/storage chain is exercisable.
- LLM-as-judge layer on top of the refusal heuristic.
- 3x replay for non-determinism mitigation.
- Live Supabase writes (dry-run only today).
- GitHub Actions integration in any consumer repo.

Per the phased plan, MVP v0.1 is ~3 weeks of work, with the audio path being
the biggest single piece (~2-3 days).

## Open questions for the channel

Before MVP kickoff, I'd like the team to weigh in on:

1. **Ownership** — who owns `vt-agent-redteam`? Trust+Safety, VT4S, or AI
   Infra? Affects on-call and review cadence.
2. **Distribution** — is `pip install git+ssh://` acceptable for v0.1, or do
   we want a private PyPI mirror first?
3. **Thresholds** — proposed: 100% pass on PR smoke, 90% on deploy gate, 85%
   on weekly canary. Reasonable, or should we start tighter / looser?
4. **Scope for v0.1** — should the harness red-team only the Mouth's spoken
   output, or also the Brain (the Assessor LLM's `assess_answer` tool)? The
   Brain has its own potential injection surface that input filtering does
   not cover.
5. **Alert channel** — `#avatar-sync`, `#trust-safety`, or a dedicated
   `#red-team-alerts`?

Happy to walk anyone through the prototype or the docs in person. Will plan
to assign MVP once we have alignment on the four points above.

— [author]
