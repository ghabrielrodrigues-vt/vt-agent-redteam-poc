"""Audio I/O for the synthetic candidate path.

Three pieces:
- tts_local: synthesise adversarial text into a WAV using the macOS `say` command
- wav_publisher: publish a WAV as a LiveKit audio track via livekit.rtc
- wav_collector: subscribe to the agent's audio track and capture until silence

The OpenAI TTS + Whisper path is a v0.1 upgrade and lives in a parallel module
once we want production-quality audio. This module is offline-capable.
"""

from vt_agent_redteam.audio.tts_local import pick_voice_for_language, synthesize_to_wav
from vt_agent_redteam.audio.wav_collector import WavCollector
from vt_agent_redteam.audio.wav_publisher import publish_wav

__all__ = ["synthesize_to_wav", "pick_voice_for_language", "publish_wav", "WavCollector"]
