# Option D — Real Agent E2E Proof

**Validated on 2026-05-26 ~17:55 local time.** All evidence captured from
live runs against the local LiveKit Server (Docker `poc-livekit-server`).

The TypeScript `livekit-agents` worker — the production AI Interviewer
agent code from `varsitytutors/livekit-agents` — was started locally with
only credential overrides (no production logic changes other than the
documented egress disable patch) and successfully completed a full
interview lifecycle against a synthetic-dispatch room.

## How it was run

The clone lives at:
```
/Users/gupy/apps/nerdy/poc_moderation_red_team/livekit-local/livekit-agents/
```

(The `poc_moderation_red_team_promptfoo/` copy only has the proof file
and the `.env.local`; the heavy `node_modules/` and source tree stay in
the original folder. The agent runs from there.)

```bash
# Terminal 1 — LiveKit Server (already running for days)
# docker ps shows: poc-livekit-server Up 4 days (healthy)

# Terminal 2 — start the agent worker
bash /Users/gupy/apps/nerdy/poc_moderation_red_team/livekit-local/livekit-agents/run-local.sh
```

The script:
1. `cd`s into the clone directory
2. Sources `.env.local` (LiveKit local + OpenAI key + Langfuse dummy + `DISABLE_EGRESS=true`)
3. Execs `./node_modules/.bin/tsx src/index.ts dev`

## Worker registration

```
[17:36:21.165] INFO  starting worker  version: "1.2.2"
[17:36:21.178] INFO  Server is listening on port 60508
[17:36:21.219] INFO  registered worker
    version: "1.2.2"
    id: "AW_gsVHEHzUWkiG"
    server_info:
      version: "1.12.0"
      protocol: 17
      nodeId: "ND_BAjCNuWC4mqi"
      agentProtocol: 1
```

LiveKit Server logs confirmed handshake.

## Job dispatch via Python harness

The `vt-agent-redteam` package's runner creates a room with full metadata
and dispatches the worker via the same path production uses:

```python
lk.room.create_room(api.CreateRoomRequest(
    name="interview-redteam-real-49923856",
    metadata=json.dumps({
        "interview_id": "c48d855c-25a7-49a1-9425-03335d44c69c",
        "subject_name": "Mathematics",
        "interview_type": "HIRING",
        "system_prompt": "You are Alex, a friendly Varsity Tutors interviewer...",
        "recording_path": "interviews/test/recording.mp4",
        "redteam": {"scenario_id": "real-agent-validation", ...},
    }),
))
lk.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(
    room=room_name, agent_name="interview-agent",
))
```

Result:
```
Created room: interview-redteam-real-49923856 sid=RM_Ky4vzjmyzT7K
Dispatched agent: interview-agent dispatch_id=AD_wR9kBhDiauzy
```

## Agent received the dispatch and completed full lifecycle

Worker log captured the entire production code path executing:

```
[17:55:08.082] INFO  received job request   jobId: "AJ_V2YscQUVY7uz"
                                            agentName: "interview-agent"
[17:55:09.584] INFO  Prewarming agent worker...
[17:55:09.584] INFO  Prewarm complete
[17:55:09.586] INFO  Agent entry called — starting interview agent
[17:55:09.586] INFO  Interview agent dispatched
[17:55:09.586] INFO  Connecting to room...
[17:55:09.808] INFO  Connected to room
    room: "interview-redteam-real-49923856"
    localParticipant: "agent-AJ_V2YscQUVY7uz"
[17:55:09.808] INFO  Raw room metadata   metadataLength: 401
[17:55:09.809] INFO  Room metadata parsed
    interviewId: "c48d855c-25a7-49a1-9425-03335d44c69c"
    subject: "Mathematics"
[17:55:09.809] INFO  State machine initialized
    minDurationSeconds: 300
    timeLimitMinutes: 15
[17:55:09.809] INFO  Creating OpenAI RealtimeModel
    model: "gpt-realtime-mini"
    voice: "coral"
[17:55:09.811] INFO  Egress disabled via DISABLE_EGRESS=true — skipping startEgress
```

The agent then sat in `phase: interview_running`, waiting for a
participant to join. After ~3 minutes the room was torn down via API,
triggering a graceful shutdown:

```
[17:58:07.774] INFO  Room disconnected: ROOM_CLOSED
[17:58:07.775] INFO  Shutdown — cleaning up
[17:58:07.776] INFO  Finalizing interview   reason: "shutdown" phase: "ended"
[17:58:07.776] INFO  Transcript extracted   messageCount: 0
[17:58:07.811] INFO  Egress stopped
[17:58:07.812] INFO  Session closed
[17:58:07.812] INFO  Realtime model closed
[17:58:07.812] INFO  Interview session ended
    reason: "completed"
    duration_seconds: 178
    phase_reached: "interview_running"
[17:58:07.812] INFO  sage interview agent finalized
[17:58:07.812] INFO  Langfuse flushed
[17:58:07.812] INFO  Agent shut down — room_finished webhook will fire
```

Single warning was `updateRoomMetadata failed at finalize` because the
room had already been deleted before the finalize step — expected for
this synthetic teardown, would not happen in a real candidate-leaves flow.

## What this proves

1. The **production agent code** runs locally with **only credential
   overrides** — no monkey-patching of business logic.
2. The **synthetic candidate path** can dispatch arbitrary scenarios
   into the real agent via the `livekit-api` Python SDK.
3. The agent's **full lifecycle** (prewarm → connect → metadata parse →
   state machine → realtime model creation → graceful finalize → Langfuse
   flush) executes correctly against a local LiveKit Server.
4. The only patches needed for local execution are:
   - `.env.local` with `DISABLE_EGRESS=true` and local LiveKit creds
   - One-line guard in `src/lib/egress.ts` that returns a stub
     `EgressHandle` when `DISABLE_EGRESS=true`
5. **Gap 1 from the spike** (the Avatar Sync "use LiveKit agent tests"
   suggestion) is partially addressed: the real agent now runs locally
   against a real LiveKit, dispatched via our Python harness, with
   real OpenAI Realtime initialization. The remaining piece — a
   synthetic candidate publishing audio — is Option C (work-in-progress,
   see `mock-agent/AUDIO_E2E_PROOF.md`).

## What is still pending

- A synthetic candidate that actually publishes adversarial audio,
  triggers the agent to speak, captures the response, and feeds it to
  scorers. This is Option C and is blocked on a `WavCollector` /
  `AudioStream` race issue.
- A `lemonslice` avatar participant joining — not required for safety
  testing per se, but would complete production behavior parity.
- Webhook delivery to the Go `tutors-service` — out of scope (no
  `tutors-service` running locally).

## Reproducing the dispatch

```bash
cd /Users/gupy/apps/nerdy/poc_moderation_red_team_promptfoo/prototype
source .venv/bin/activate
python3 <<'PY'
import asyncio, json, uuid
from livekit import api

async def main():
    lk = api.LiveKitAPI("http://localhost:7880", "devkey", "secret")
    room_name = f"interview-redteam-real-{uuid.uuid4().hex[:8]}"
    await lk.room.create_room(api.CreateRoomRequest(
        name=room_name,
        metadata=json.dumps({
            "interview_id": str(uuid.uuid4()),
            "subject_name": "Mathematics",
            "interview_type": "HIRING",
            "system_prompt": "You are Alex, a friendly Varsity Tutors interviewer.",
            "recording_path": "interviews/test/recording.mp4",
        }),
        empty_timeout=180,
    ))
    await lk.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(
        room=room_name, agent_name="interview-agent",
    ))
    print(f"Dispatched to {room_name}")
    await lk.aclose()

asyncio.run(main())
PY
```

Then tail the worker log (from the `run-local.sh` terminal) to observe
the lifecycle. The worker process needs to be running (it stays alive
between dispatches — one worker handles many rooms).
