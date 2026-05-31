"""LiveKit room runner.

Creates a real LiveKit room with red-team metadata and (in v0.1) joins as a synthetic
participant publishing TTS audio. For the prototype (v0.0.1), the room is created and
metadata dispatch is invoked, but the candidate audio path is stubbed — we return a
canned response so the rest of the pipeline (scorers, storage) can be exercised
end-to-end.

This separation is intentional: it lets the spike demonstrate the full data flow
without blocking on the TTS + livekit-rtc-python integration, which is real work that
belongs to the MVP phase.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from livekit import api

from vt_agent_redteam.types import AgentConfig, Scenario


@dataclass
class RoomDispatchResult:
    room_name: str
    room_sid: str | None
    metadata_sent: dict[str, Any]
    agent_response_transcript: str
    notes: list[str]


class LiveKitRoomRunner:
    """Creates and tears down LiveKit rooms for red-team scenarios.

    Parameters
    ----------
    url: LiveKit Server URL (e.g. ws://localhost:7880 or wss://staging.livekit.cloud)
    api_key, api_secret: LiveKit Server SDK credentials (dev defaults: devkey/secret)
    stub_agent_response: if set, skip real participant join and return this string as
        the agent's response. Used in the prototype until the synthetic-candidate
        TTS path lands in MVP.
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        api_secret: str,
        *,
        stub_agent_response: str | dict[str, str] | None = None,
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.stub_agent_response = stub_agent_response

    def _resolve_stub(self, language: str) -> str | None:
        """Pick the stub response that matches the scenario language."""
        if self.stub_agent_response is None:
            return None
        if isinstance(self.stub_agent_response, str):
            return self.stub_agent_response
        return self.stub_agent_response.get(
            language, self.stub_agent_response.get("en")
        )

    def _http_url(self) -> str:
        """Translate ws://... → http://... for the REST API."""
        if self.url.startswith("ws://"):
            return "http://" + self.url[len("ws://") :]
        if self.url.startswith("wss://"):
            return "https://" + self.url[len("wss://") :]
        return self.url

    async def run_scenario(
        self,
        scenario: Scenario,
        agent: AgentConfig,
        run_id: str | None = None,
    ) -> RoomDispatchResult:
        """Execute one scenario. v0.0.1: creates room, returns stub response."""
        notes: list[str] = []
        room_name = f"{agent.room_name_prefix}-redteam-{uuid.uuid4().hex[:8]}"

        metadata = build_room_metadata(
            agent,
            scenario,
            run_id=run_id,
            harness_version="0.0.1",
        )

        lk_api = api.LiveKitAPI(
            self._http_url(),
            self.api_key,
            self.api_secret,
        )

        room_sid: str | None = None
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

            stub = self._resolve_stub(scenario.language)
            if stub is not None:
                notes.append(
                    f"Using stub agent response (v0.0.1 prototype mode, "
                    f"language={scenario.language})."
                )
                response = stub
            else:
                # MVP path: dispatch the agent, join as synthetic participant,
                # publish TTS audio, capture agent's audio reply, transcribe.
                # Not implemented in v0.0.1.
                notes.append("Real participant path not yet implemented; falling back to stub.")
                response = (
                    "I'm sorry, but I can't help with that. Let's focus on your "
                    "learning instead. What subject are you studying?"
                )

            # Tear down the room so we do not accumulate leftover state.
            try:
                await lk_api.room.delete_room(api.DeleteRoomRequest(room=room_name))
                notes.append(f"Deleted room {room_name}")
            except Exception as exc:  # noqa: BLE001
                notes.append(f"Room cleanup failed (non-fatal): {exc}")

        finally:
            await lk_api.aclose()

        return RoomDispatchResult(
            room_name=room_name,
            room_sid=room_sid,
            metadata_sent=metadata,
            agent_response_transcript=response,
            notes=notes,
        )


def build_room_metadata(
    agent: AgentConfig,
    scenario: Scenario,
    *,
    run_id: str | None,
    harness_version: str,
) -> dict[str, Any]:
    """Build LiveKit room metadata with Langfuse correlation fields.

    The Langfuse native transcript runner searches top-level trace metadata
    keys, so the room metadata must include these exact keys before the agent
    exports its OpenTelemetry spans.
    """
    metadata = dict(agent.metadata_template)
    existing_redteam = metadata.get("redteam")
    redteam = dict(existing_redteam) if isinstance(existing_redteam, dict) else {}
    redteam.update(
        {
            "scenario_id": scenario.id,
            "category": scenario.category,
            "language": scenario.language,
            "harness_version": harness_version,
        }
    )
    metadata["redteam"] = redteam
    if run_id:
        metadata["redteam_run_id"] = run_id
    metadata["redteam_scenario_id"] = scenario.id
    return metadata
