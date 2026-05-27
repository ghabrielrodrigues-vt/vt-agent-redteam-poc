"""Publish a WAV file as a LiveKit audio track.

Uses `livekit.rtc.AudioSource` + `LocalAudioTrack.create_audio_track` to push
PCM frames into a room from a synthetic participant.

The WAV must be 16-bit signed PCM, mono, 48 kHz — the format produced by
`audio.tts_local.synthesize_to_wav`. We do not handle resampling here to keep
this module's responsibility narrow.
"""

from __future__ import annotations

import asyncio
import wave
from pathlib import Path

from livekit import rtc


FRAME_DURATION_MS = 20  # standard Opus frame size
EXPECTED_SAMPLE_RATE = 48_000
EXPECTED_CHANNELS = 1


async def publish_wav(
    room: rtc.Room,
    wav_path: Path,
    *,
    track_name: str = "synthetic-candidate-audio",
) -> None:
    """Publish the WAV file as an audio track on `room`, then unpublish.

    Blocks until the WAV's last frame has been pushed. The caller decides when
    to leave the room afterwards (e.g. after waiting for the agent's reply).
    """
    with wave.open(str(wav_path), "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        if sample_rate != EXPECTED_SAMPLE_RATE or channels != EXPECTED_CHANNELS or sampwidth != 2:
            raise ValueError(
                f"WAV must be 16-bit/mono/{EXPECTED_SAMPLE_RATE}Hz; got "
                f"{sampwidth * 8}-bit/{channels}ch/{sample_rate}Hz"
            )
        pcm = wf.readframes(wf.getnframes())

    source = rtc.AudioSource(EXPECTED_SAMPLE_RATE, EXPECTED_CHANNELS)
    track = rtc.LocalAudioTrack.create_audio_track(track_name, source)

    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    publication = await room.local_participant.publish_track(track, options)

    samples_per_frame = (EXPECTED_SAMPLE_RATE * FRAME_DURATION_MS) // 1000
    bytes_per_frame = samples_per_frame * 2  # 16-bit mono

    try:
        for offset in range(0, len(pcm), bytes_per_frame):
            chunk = pcm[offset : offset + bytes_per_frame]
            if len(chunk) < bytes_per_frame:
                chunk = chunk + b"\x00" * (bytes_per_frame - len(chunk))
            frame = rtc.AudioFrame(
                data=chunk,
                sample_rate=EXPECTED_SAMPLE_RATE,
                num_channels=EXPECTED_CHANNELS,
                samples_per_channel=samples_per_frame,
            )
            await source.capture_frame(frame)
            # Pace the push so the agent has real-time-ish audio to consume.
            await asyncio.sleep(FRAME_DURATION_MS / 1000)
    finally:
        await room.local_participant.unpublish_track(publication.sid)
