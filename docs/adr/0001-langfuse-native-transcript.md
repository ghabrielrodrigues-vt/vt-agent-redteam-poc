# ADR-001 — Langfuse-native transcript as v0 primary audio path

**Status:** Accepted (2026-05-30)
**Companion:** [`v0-implementation-plan.md`](../v0-implementation-plan.md) §1.1 row 4, §2.2 stages [3g]–[3l], §3 F1

## Context

The framework spec ([`livekit-agent-red-team-hardening.md`](../exports/livekit-agent-red-team-hardening.md)) §17.2 names the synthetic-candidate audio capture pipeline (the `WavCollector` race in §15.1) as Phase 1 acceptance criterion #1: the gate must capture the agent's real spoken response and transcribe it via Whisper before scoring.

The race condition is documented but unfixed: frames begin arriving before `WavCollector` has constructed its audio stream, and end-of-utterance detection waits on a silence threshold that never resolves because the start of the utterance is never registered. The proposed fix (move `AudioStream` construction inside the `track_subscribed` callback synchronously) is drafted in a feature branch but has not been validated end-to-end.

Spec §15.1 itself names an alternative: "Phase 2's revised scope is to integrate Whisper-equivalent transcription via agent-native transcript hooks (Langfuse traces, agent-emitted transcript events) as the recovery path."

Discovery in `student-onboarding-orchestration/agents/{language-tutor,language-checkpoint,support-agent}/langfuse_tracing.py` confirms that all three v0 target agents already export OpenTelemetry spans to Langfuse via `livekit.agents.telemetry.set_tracer_provider`. LiveKit Agents emits OTel spans for every LLM, STT, TTS, and tool-call invocation; Langfuse ingests them as GENERATION / SPAN / EVENT observations. Deployed 2026-05-18 (twelve days before this ADR).

## Decision

v0 promotes the agent-native Langfuse path from "Phase 2 fallback" to **primary audio path**. The framework reads the agent's response from the agent's own Langfuse trace, not from a synthetic audio capture. `transcript_source = "agent_native_transcript"`.

The synthetic candidate still publishes a TTS-rendered adversarial prompt into the LiveKit room — that exercises the agent's full production stack (STT → LLM → TTS) — but the framework does not attempt to capture the agent's spoken response itself. It searches Langfuse for the trace matching `(redteam_run_id, redteam_scenario_id)` propagated through LiveKit room metadata, then aggregates the GENERATION span outputs as the captured response.

`artifact_uri` is set to the Langfuse trace URL (`{LANGFUSE_BASE_URL}/trace/{trace_id}`) so the un-redacted evidence remains accessible to authorized readers via Langfuse access control — preserving spec §12.4's rollback path that condition #7 of the prior boss-review identified as missing.

**Forward reference to spec §17.2 acceptance #1:** this ADR explicitly deviates from the literal text of that criterion (which demands WAV-collector capture). The deviation is honest, recorded here, and consistent with the spec's own §15.1 fallback language.

## Status of the WAV-collector path

Deferred to v0.2 hardening (D1 in the plan). The proposed synchronous-track-subscribed fix remains the right approach when revisited. The Langfuse path covers the same risk surface (regression in safety behavior across the production audio chain) without taking on the timeline risk of solving an async-race-condition bug as a v0 blocker.

## Consequences

**Positive.**

- v0 timeline is bounded: no unbounded async race to fix.
- The full production audio stack is exercised end-to-end (TTS adversarial → agent STT → agent LLM → agent TTS), which the WAV-collector path would not test even when fixed (it captures only the agent's audio output, not its STT input — and STT degradation is a documented voice-modality attack vector per JALMBench / spec ref [9]).
- One framework runner serves all three v0 target agents uniformly because all three emit Langfuse traces.
- `transcript_source = "agent_native_transcript"` is already listed in spec §12.1 as a valid source — no schema bump required for this value.

**Negative.**

- v0 inherits a new operational dependency on Langfuse Cloud availability. Mitigated by `direct-llm` runner fallback (existing) when Langfuse is unreachable. Tracked as v0 risk in plan §8.
- Langfuse ingestion latency adds polling time per scenario. Bounded by `scenario_timeout_seconds` per manifest. Polling backoff is exponential up to a configured cap so latency does not multiply scenario count linearly.
- Trace correlation is by metadata search in v0 (`{redteam_run_id, redteam_scenario_id}`). Direct trace-id propagation via OTel context would be more robust; deferred to v0.2.
- A v0 agent that does NOT yet have Langfuse instrumentation cannot use this path. The only v0 targets (the three SOO agents) all have it; future onboarding requires either Langfuse instrumentation or falling back to WAV-collector (when fixed).

**Neutral.**

- Cost: red-team budget no longer pays for Whisper because the agent's production STT was already paid by the agent's own workload. Adjusted in plan §1.1 row 10 cost-guardrail math.

## Implementation

Framework code:

- `prototype/src/vt_agent_redteam/runners/langfuse_trace_runner.py` — new runner implementing `LangfuseTraceRunner`, a polling client (`LangfuseHttpClient`), and helpers.
- `prototype/tests/test_langfuse_runner.py` — 17 unit tests covering trace polling, search-by-metadata, run_scenario orchestration, stub-row fallback (spec §9.8), and the polymorphic Langfuse output coercion.
- `prototype/src/vt_agent_redteam/runners/__init__.py` — exports.

Plan §3 F1.
