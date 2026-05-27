"""Real-audio scenario runner — synthetic candidate over LiveKit.

End-to-end flow per scenario:
1. Create LiveKit room with red-team metadata
2. Generate WAV from `scenario.turns[0]` via local TTS (`say`)
3. Connect to the room as identity "redteam-candidate-<scenario>"
4. Subscribe to the *next* remote audio track that appears — the mock agent
   (or real agent) will publish it
5. Publish the candidate's WAV
6. Block until the collector hits end-of-silence or max-capture timeout
7. Transcribe the captured WAV via OpenAI Whisper
8. Tear down the room and return the transcript as the agent_response

If OPENAI_API_KEY is missing, step 7 returns a placeholder string and the
downstream scorers will see "<audio captured, transcription unavailable>" —
honest about the gap without crashing the run.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from livekit import api, rtc

from vt_agent_redteam.audio import (
    WavCollector,
    pick_voice_for_language,
    publish_wav,
    synthesize_to_wav,
)
from vt_agent_redteam.runners.livekit_room import RoomDispatchResult
from vt_agent_redteam.types import AgentConfig, Scenario


SUBSCRIBE_TIMEOUT_S = 30.0
TRANSCRIPTION_PLACEHOLDER = "<audio captured, transcription unavailable (no OPENAI_API_KEY)>"


@dataclass
class _TrackArrival:
    """A subscribed remote audio track plus the AudioStream already bound to it.

    The AudioStream MUST be constructed synchronously inside the
    `track_subscribed` event handler — the LiveKit FFI only forwards audio
    frames once a stream is bound to the track. Building the stream later in
    `WavCollector.capture()` resulted in `async for event in stream:` hanging
    forever (no frames ever arrived). See `audio/wav_collector.py` for context.
    """

    track: rtc.RemoteAudioTrack
    stream: rtc.AudioStream
    participant_identity: str


def _http_url(url: str) -> str:
    if url.startswith("ws://"):
        return "http://" + url[len("ws://"):]
    if url.startswith("wss://"):
        return "https://" + url[len("wss://"):]
    return url


class SyntheticCandidateRunner:
    """Runner that produces real audio against a LiveKit room.

    Designed to interoperate with the Python `mock_agent.py` worker (or the
    real TypeScript livekit-agents worker, if OPENAI Realtime credentials are
    available).
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        api_secret: str,
        *,
        whisper_model: str = "whisper-1",
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.whisper_model = whisper_model

    async def run_scenario(
        self,
        scenario: Scenario,
        agent: AgentConfig,
    ) -> RoomDispatchResult:
        notes: list[str] = []
        room_name = f"{agent.room_name_prefix}-redteam-{uuid.uuid4().hex[:8]}"

        metadata: dict[str, Any] = dict(agent.metadata_template)
        metadata["redteam"] = {
            "scenario_id": scenario.id,
            "category": scenario.category,
            "language": scenario.language,
            "harness_version": "0.0.2",
        }

        lk_api = api.LiveKitAPI(_http_url(self.url), self.api_key, self.api_secret)
        room_sid: str | None = None
        candidate_room: rtc.Room | None = None
        candidate_wav: Path | None = None
        captured_wav: Path | None = None

        try:
            room_info = await lk_api.room.create_room(
                api.CreateRoomRequest(
                    name=room_name,
                    metadata=json.dumps(metadata),
                    empty_timeout=120,
                    max_participants=4,
                )
            )
            room_sid = room_info.sid
            notes.append(f"Created room sid={room_sid}")

            candidate_wav = synthesize_to_wav(
                scenario.turns[0],
                voice=pick_voice_for_language(scenario.language),
            )
            notes.append(f"Synthesised candidate prompt to {candidate_wav.name}")

            candidate_room = rtc.Room()
            track_future: asyncio.Future[_TrackArrival] = asyncio.get_event_loop().create_future()

            def _maybe_capture_track(
                track: rtc.Track, participant: rtc.RemoteParticipant
            ) -> None:
                if track.kind != rtc.TrackKind.KIND_AUDIO:
                    return
                if track_future.done():
                    return
                # Construct AudioStream synchronously here — see _TrackArrival
                # docstring for why this matters.
                stream = rtc.AudioStream(track)
                track_future.set_result(
                    _TrackArrival(
                        track=track,
                        stream=stream,
                        participant_identity=participant.identity,
                    )
                )

            @candidate_room.on("track_subscribed")
            def _on_track_subscribed(  # pyright: ignore[reportUnusedFunction]
                track: rtc.Track,
                publication: rtc.RemoteTrackPublication,
                participant: rtc.RemoteParticipant,
            ) -> None:
                _maybe_capture_track(track, participant)

            token = (
                api.AccessToken(self.api_key, self.api_secret)
                .with_identity(f"redteam-candidate-{scenario.id}")
                .with_name("Synthetic Candidate")
                .with_grants(
                    api.VideoGrants(
                        room_join=True,
                        room=room_name,
                        can_publish=True,
                        can_subscribe=True,
                    )
                )
                .to_jwt()
            )

            await candidate_room.connect(self.url, token)
            notes.append("Candidate connected to room")

            # Catch tracks that already existed when we connected. The
            # track_subscribed event handler covers tracks published after
            # connect; this loop covers tracks published before.
            for participant in candidate_room.remote_participants.values():
                for publication in participant.track_publications.values():
                    if publication.track is not None:
                        _maybe_capture_track(publication.track, participant)

            publish_task = asyncio.create_task(publish_wav(candidate_room, candidate_wav))

            try:
                arrival = await asyncio.wait_for(track_future, timeout=SUBSCRIBE_TIMEOUT_S)
                notes.append(f"Subscribed to agent track (participant={arrival.participant_identity})")
            except asyncio.TimeoutError:
                notes.append(f"No agent audio track within {SUBSCRIBE_TIMEOUT_S}s")
                await publish_task
                response_text = "<no agent response captured: track subscription timed out>"
                return RoomDispatchResult(
                    room_name=room_name,
                    room_sid=room_sid,
                    metadata_sent=metadata,
                    agent_response_transcript=response_text,
                    notes=notes,
                )

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                captured_wav = Path(tmp.name)
            collector = WavCollector(captured_wav)
            try:
                await collector.capture(arrival.stream)
            finally:
                await arrival.stream.aclose()
            notes.append(f"Captured agent audio → {captured_wav.name}")

            await publish_task
            response_text = await self._transcribe(captured_wav)
            notes.append(f"Transcribed: {response_text[:80]}...")

            return RoomDispatchResult(
                room_name=room_name,
                room_sid=room_sid,
                metadata_sent=metadata,
                agent_response_transcript=response_text,
                notes=notes,
            )

        finally:
            if candidate_room is not None:
                try:
                    await candidate_room.disconnect()
                except Exception:  # noqa: BLE001
                    pass
            try:
                await lk_api.room.delete_room(api.DeleteRoomRequest(room=room_name))
                notes.append(f"Deleted room {room_name}")
            except Exception as exc:  # noqa: BLE001
                notes.append(f"Room cleanup failed (non-fatal): {exc}")
            await lk_api.aclose()
            for path in (candidate_wav, captured_wav):
                if path is not None:
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        pass

    async def _transcribe(self, wav_path: Path) -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key.startswith("sk-replace"):
            return TRANSCRIPTION_PLACEHOLDER

        try:
            from openai import AsyncOpenAI
        except ImportError:
            return TRANSCRIPTION_PLACEHOLDER

        client = AsyncOpenAI(api_key=api_key)
        try:
            with wav_path.open("rb") as fp:
                transcript = await client.audio.transcriptions.create(
                    model=self.whisper_model,
                    file=fp,
                )
            return transcript.text or "<empty transcription>"
        except Exception as exc:  # noqa: BLE001
            return f"<transcription error: {exc}>"
