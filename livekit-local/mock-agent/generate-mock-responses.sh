#!/usr/bin/env bash
#
# Generate canned response WAVs the mock agent publishes when a synthetic
# candidate hits its red-team scenarios. The responses are deliberately bland
# refusals — the point of the mock agent is to validate the harness wiring,
# not to model an interesting agent.
#
# Run once after cloning. Writes to mock-agent/responses/.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
RESPONSES="$ROOT/responses"
mkdir -p "$RESPONSES"

if ! command -v say >/dev/null 2>&1 || ! command -v afconvert >/dev/null 2>&1; then
  echo "macOS \`say\` and \`afconvert\` are required." >&2
  exit 1
fi

synth() {
  local out="$1"
  local text="$2"
  local voice="${3:-}"

  local tmp_aiff
  tmp_aiff="$(mktemp -t mock-agent-XXXXXX).aiff"
  if [ -n "$voice" ]; then
    say -o "$tmp_aiff" -v "$voice" "$text"
  else
    say -o "$tmp_aiff" "$text"
  fi
  afconvert -f WAVE -d LEI16@48000 -c 1 "$tmp_aiff" "$out"
  rm -f "$tmp_aiff"
  echo "wrote $out"
}

synth "$RESPONSES/default.wav" \
  "I'm sorry, but I can't help with that. Let's focus on your learning instead. What subject are you studying right now?" \
  "Samantha"

synth "$RESPONSES/default-pt.wav" \
  "Desculpa, mas não posso te ajudar com isso. Vamos focar nos seus estudos. Em vez disso, me conta o que você está estudando agora?" \
  "Luciana"

synth "$RESPONSES/default-es.wav" \
  "Lo siento, no puedo ayudarte con eso. Hablemos de tus estudios. ¿Qué materia estás estudiando?" \
  "Monica"

echo ""
echo "Done. Generated WAVs in $RESPONSES"
ls -la "$RESPONSES"
