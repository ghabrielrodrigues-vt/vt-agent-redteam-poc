"""Mock agent — Python LiveKit worker that stands in for the real
TypeScript `livekit-agents` interviewer.

Why this exists: the real agent needs an OpenAI Realtime API key and connects
to OpenAI for STT/LLM/TTS. For laptop-local MVP testing without burning API
budget (or when an API key is not available), this mock agent gives the
harness something real to talk to over WebRTC.

What it does:
1. Listens for rooms with names starting with `interview-` on the local
   LiveKit Server (via the room-list polling pattern).
2. When a candidate joins, reads the room metadata (specifically
   `redteam.scenario_id`), picks the matching pre-recorded response WAV.
3. Publishes the response WAV as an audio track.
4. Leaves the room when the candidate disconnects.

The response WAVs live in `responses/` next to this file. By default the agent
ships with `default.wav` (a generic safe refusal) and any number of
`<scenario-id>.wav` files for scenario-specific responses.

Run:
    python mock_agent.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import wave
from pathlib import Path

from livekit import api, rtc


LOG = logging.getLogger("mock-agent")
RESPONSES_DIR = Path(__file__).parent / "responses"

FRAME_DURATION_MS = 20
SAMPLE_RATE = 48_000
CHANNELS = 1


async def _publish_wav(room: rtc.Room, wav_path: Path) -> None:
    """Publish a WAV file as an audio track on `room`."""
    with wave.open(str(wav_path), "rb") as wf:
        if (
            wf.getframerate() != SAMPLE_RATE
            or wf.getnchannels() != CHANNELS
            or wf.getsampwidth() != 2
        ):
            raise ValueError(
                f"WAV must be 16-bit/mono/{SAMPLE_RATE}Hz; got "
                f"{wf.getsampwidth() * 8}-bit/{wf.getnchannels()}ch/"
                f"{wf.getframerate()}Hz"
            )
        pcm = wf.readframes(wf.getnframes())

    source = rtc.AudioSource(SAMPLE_RATE, CHANNELS)
    track = rtc.LocalAudioTrack.create_audio_track("agent-reply", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    publication = await room.local_participant.publish_track(track, options)

    samples_per_frame = (SAMPLE_RATE * FRAME_DURATION_MS) // 1000
    bytes_per_frame = samples_per_frame * 2

    try:
        for offset in range(0, len(pcm), bytes_per_frame):
            chunk = pcm[offset : offset + bytes_per_frame]
            if len(chunk) < bytes_per_frame:
                chunk = chunk + b"\x00" * (bytes_per_frame - len(chunk))
            frame = rtc.AudioFrame(
                data=chunk,
                sample_rate=SAMPLE_RATE,
                num_channels=CHANNELS,
                samples_per_channel=samples_per_frame,
            )
            await source.capture_frame(frame)
            await asyncio.sleep(FRAME_DURATION_MS / 1000)
    finally:
        await room.local_participant.unpublish_track(publication.sid)


def _pick_response_wav(scenario_id: str | None, language: str | None) -> Path:
    candidates = []
    if scenario_id:
        candidates.append(RESPONSES_DIR / f"{scenario_id}.wav")
    if language:
        candidates.append(RESPONSES_DIR / f"default-{language}.wav")
    candidates.append(RESPONSES_DIR / "default.wav")

    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"No response WAV found. Looked at: {[str(p) for p in candidates]}. "
        f"Run scripts/generate-mock-responses.sh to seed them."
    )


CANDIDATE_WAIT_TIMEOUT_S = 20.0


async def _serve_room(
    url: str, api_key: str, api_secret: str, room_name: str
) -> None:
    """Connect to one room, wait for the candidate to join, then publish a response."""
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity("mock-agent")
        .with_name("Mock Agent")
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

    room = rtc.Room()
    candidate_joined = asyncio.Event()

    @room.on("participant_connected")
    def _on_participant_connected(p: rtc.RemoteParticipant) -> None:  # pyright: ignore[reportUnusedFunction]
        if p.identity.startswith("redteam-candidate"):
            LOG.info("Candidate %s joined; will publish reply.", p.identity)
            candidate_joined.set()

    await room.connect(url, token)
    LOG.info("Mock agent joined room=%s (remote participants=%d)",
             room_name, len(room.remote_participants))

    # The candidate might already be in the room when we connect — check
    # remote_participants synchronously before falling back to the event wait.
    for participant in room.remote_participants.values():
        if participant.identity.startswith("redteam-candidate"):
            candidate_joined.set()
            break

    if not candidate_joined.is_set():
        try:
            await asyncio.wait_for(candidate_joined.wait(), CANDIDATE_WAIT_TIMEOUT_S)
        except asyncio.TimeoutError:
            LOG.warning("No candidate joined within %ss; leaving room without publishing.",
                        CANDIDATE_WAIT_TIMEOUT_S)
            await room.disconnect()
            return

    metadata_raw = room.metadata or "{}"
    try:
        metadata = json.loads(metadata_raw)
    except json.JSONDecodeError:
        metadata = {}

    scenario_id = metadata.get("redteam", {}).get("scenario_id")
    language = metadata.get("redteam", {}).get("language")
    wav_path = _pick_response_wav(scenario_id, language)
    LOG.info("Responding to scenario=%s with wav=%s", scenario_id, wav_path.name)

    try:
        await _publish_wav(room, wav_path)
        # Linger briefly so the candidate's collector can detect end-of-utterance.
        await asyncio.sleep(1.5)
    finally:
        await room.disconnect()


async def _poll_and_serve(url: str, api_key: str, api_secret: str, room_prefix: str) -> None:
    """Poll the room list and serve each matching room exactly once."""
    http_url = url.replace("ws://", "http://").replace("wss://", "https://")
    lk = api.LiveKitAPI(http_url, api_key, api_secret)

    served: set[str] = set()
    try:
        while True:
            rooms = await lk.room.list_rooms(api.ListRoomsRequest())
            for room_info in rooms.rooms:
                if not room_info.name.startswith(room_prefix):
                    continue
                if room_info.name in served:
                    continue
                served.add(room_info.name)
                LOG.info("Detected new room: %s", room_info.name)
                try:
                    await _serve_room(url, api_key, api_secret, room_info.name)
                except Exception as exc:  # noqa: BLE001
                    LOG.error("Failed to serve room %s: %s", room_info.name, exc)
            await asyncio.sleep(0.5)
    finally:
        await lk.aclose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.environ.get("LIVEKIT_URL", "ws://localhost:7880"))
    parser.add_argument("--api-key", default=os.environ.get("LIVEKIT_API_KEY", "devkey"))
    parser.add_argument(
        "--api-secret", default=os.environ.get("LIVEKIT_API_SECRET", "secret")
    )
    parser.add_argument("--room-prefix", default="interview-redteam-")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    LOG.info("Mock agent watching prefix=%s url=%s", args.room_prefix, args.url)

    try:
        asyncio.run(
            _poll_and_serve(args.url, args.api_key, args.api_secret, args.room_prefix)
        )
    except KeyboardInterrupt:
        LOG.info("Mock agent stopped by user")


if __name__ == "__main__":
    main()
