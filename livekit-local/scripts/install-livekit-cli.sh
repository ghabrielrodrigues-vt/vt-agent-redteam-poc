#!/usr/bin/env bash
#
# Install the LiveKit CLI (`lk`) used by dispatch-test-room.sh.
# Idempotent: re-running is safe.

set -euo pipefail

if command -v lk >/dev/null 2>&1; then
  echo "lk already installed: $(lk --version 2>/dev/null || lk -v 2>/dev/null || echo present)"
  exit 0
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found. Install from https://brew.sh first."
  exit 1
fi

echo "Installing livekit-cli via Homebrew..."
brew install livekit-cli

echo ""
echo "Installed:"
lk --version 2>/dev/null || lk -v 2>/dev/null || echo "livekit-cli is on PATH"
