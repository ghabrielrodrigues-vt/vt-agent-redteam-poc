"""Subscribe to the agent's audio track and accumulate PCM until silence.

Used by the synthetic candidate after publishing its adversarial audio: wait
for the agent to start speaking, capture every frame, stop when the agent has
been silent long enough to count as end-of-turn.

The captured PCM is written to a WAV file. Transcription happens elsewhere
(Whisper, OpenAI STT, etc.) and is out of scope for this module — keeping
audio capture and transcription decoupled lets us swap transcribers later.
"""

from __future__ import annotations

import asyncio
import wave
from pathlib import Path

import numpy as np
from livekit import rtc


SILENCE_RMS_THRESHOLD = 200.0  # tuned for 16-bit PCM; well above ambient noise floor
SILENCE_DURATION_S = 0.6
MAX_CAPTURE_S = 30.0


class WavCollector:
    """Listens to one remote audio track and writes captured PCM to a WAV file."""

    def __init__(
        self,
        output_path: Path,
        *,
        sample_rate: int = 48_000,
        channels: int = 1,
        silence_rms_threshold: float = SILENCE_RMS_THRESHOLD,
        silence_duration_s: float = SILENCE_DURATION_S,
        max_capture_s: float = MAX_CAPTURE_S,
    ) -> None:
        self.output_path = output_path
        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_rms_threshold = silence_rms_threshold
        self.silence_duration_s = silence_duration_s
        self.max_capture_s = max_capture_s

        self._buffer: list[bytes] = []
        self._done = asyncio.Event()

    async def capture(
        self,
        source: rtc.RemoteAudioTrack | rtc.AudioStream,
    ) -> Path:
        """Collect frames from `source` until silence or timeout. Returns the WAV path.

        `source` may be either a `RemoteAudioTrack` (we'll build an `AudioStream`
        for it here) or a pre-constructed `AudioStream`. Prefer passing a
        pre-constructed stream that was created synchronously inside the
        `track_subscribed` callback — the LiveKit FFI only starts forwarding
        frames once `AudioStream` has bound the track, so building the stream
        later can lose audio (or, in the worst case, never receive any).
        """
        own_stream = False
        if isinstance(source, rtc.AudioStream):
            stream = source
        else:
            stream = rtc.AudioStream(source)
            own_stream = True

        loop = asyncio.get_event_loop()
        deadline = loop.time() + self.max_capture_s

        last_voice_t: float | None = None
        heard_voice = False

        async for event in stream:
            frame = event.frame
            pcm_bytes = bytes(frame.data)
            self._buffer.append(pcm_bytes)

            samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
            rms = float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0

            now = loop.time()
            if rms >= self.silence_rms_threshold:
                heard_voice = True
                last_voice_t = now
            elif heard_voice and last_voice_t is not None:
                if now - last_voice_t >= self.silence_duration_s:
                    break

            if now >= deadline:
                break

        if own_stream:
            await stream.aclose()
        self._write_wav()
        return self.output_path

    def _write_wav(self) -> None:
        with wave.open(str(self.output_path), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(b"".join(self._buffer))
