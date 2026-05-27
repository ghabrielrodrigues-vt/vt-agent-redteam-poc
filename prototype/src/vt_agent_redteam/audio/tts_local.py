"""TTS via macOS `say` — offline, zero-cost, good enough to condition the
Realtime API's STT in dev.

Flow:
  1. `say -o tmp.aiff <text>` writes an AIFF
  2. `afconvert -f WAVE -d LEI16@48000 -c 1 tmp.aiff out.wav` rewrites it as
     48 kHz / mono / 16-bit PCM (the format livekit.rtc.AudioSource expects)

Both `say` and `afconvert` are built into macOS. For Linux/CI, swap this module
for an OpenAI TTS or Piper-backed implementation.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


SAMPLE_RATE_HZ = 48_000
CHANNELS = 1
BITS_PER_SAMPLE = 16


def synthesize_to_wav(
    text: str,
    output_path: Path | None = None,
    *,
    voice: str | None = None,
    rate_wpm: int = 175,
) -> Path:
    """Synthesise `text` to a WAV file. Returns the path written.

    If `output_path` is None, writes to a temp file the caller is expected to
    clean up. The file is mono, 16-bit PCM, 48 kHz — the canonical format the
    LiveKit Audio SDK expects.
    """
    if not text or not text.strip():
        raise ValueError("synthesize_to_wav requires non-empty text")

    if shutil.which("say") is None or shutil.which("afconvert") is None:
        raise RuntimeError(
            "Local TTS requires macOS `say` and `afconvert` on PATH. "
            "Use the OpenAI TTS adapter instead on Linux/CI."
        )

    if output_path is None:
        output_path = Path(tempfile.mkstemp(suffix=".wav")[1])

    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp_aiff:
        aiff_path = Path(tmp_aiff.name)

    try:
        say_cmd: list[str] = ["say", "-o", str(aiff_path), "-r", str(rate_wpm)]
        if voice:
            say_cmd += ["-v", voice]
        say_cmd.append(text)

        subprocess.run(say_cmd, check=True, capture_output=True)

        subprocess.run(
            [
                "afconvert",
                "-f", "WAVE",
                "-d", f"LEI{BITS_PER_SAMPLE}@{SAMPLE_RATE_HZ}",
                "-c", str(CHANNELS),
                str(aiff_path),
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        aiff_path.unlink(missing_ok=True)

    return output_path


def pick_voice_for_language(language: str) -> str | None:
    """Pick a sensible default `say` voice for the scenario language.

    macOS ships English voices by default; Portuguese / Spanish voices may need
    to be downloaded by the user (System Settings → Accessibility → Spoken
    Content → System Voice → Manage Voices). If the requested voice is not
    installed, `say` falls back to the system voice gracefully.
    """
    return {
        "en": "Samantha",
        "pt": "Luciana",   # pt_BR
        "es": "Monica",
    }.get(language)
