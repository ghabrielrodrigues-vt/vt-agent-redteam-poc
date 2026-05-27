"""HTTP runner for the Nerd Tutor input-side moderation endpoint.

Option B of the demo: instead of pushing audio into a LiveKit room and judging
the agent's *output*, we POST scenario text directly at the Nerdy Tutor
moderation route (`/api/nerd-tutor/moderate-text`) and judge the *input filter
verdict*.

This is conceptually the inverse of the LiveKit red-team flow:

  LiveKit red-team   →  "Does the agent's response cross a safety line?"
  HTTP moderation    →  "Does the moderation pipeline block / mask / pass the
                         input as we expect?"

The endpoint returns `{ layer, terms, text }` where `text` is the censored
version of the input. We derive a coarse `block | mask | pass` verdict from
that response so existing scorers can grep the transcript exactly as they do
for the audio path.

The runner returns a `RoomDispatchResult` (same dataclass the LiveKit runners
use) so the harness needs no per-runner branching — the JSON response from the
moderation API is serialised as a string and stored in
`agent_response_transcript`.

Dry-run mode: when `dry_run=True` the runner skips the network call entirely
and synthesises a `pass` verdict. This lets the demo's "validate the pipeline"
path run without a live Next.js server.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from vt_agent_redteam.runners.livekit_room import RoomDispatchResult
from vt_agent_redteam.types import AgentConfig, Scenario


def derive_verdict(original_text: str, response_payload: dict[str, Any]) -> str:
    """Map the moderation API's `{layer, terms, text}` shape onto a coarse
    `block | mask | pass` verdict.

    The Nerdy Tutor API does not expose an `action` field directly — it
    returns the (potentially-censored) text. We classify:
      - `pass`  : layer == 'none' AND text unchanged
      - `block` : text is fully censored (every non-whitespace char is '*')
      - `mask`  : text changed but not fully censored
    """
    layer = response_payload.get("layer", "none")
    censored = response_payload.get("text", original_text)
    terms = response_payload.get("terms", []) or []

    if censored == original_text and layer == "none" and not terms:
        return "pass"

    # Fully-censored output → block. Treat empty strings as block when the
    # original had content; the production pipeline replaces all non-whitespace
    # with '*' on the fail-closed path.
    non_whitespace = [c for c in censored if not c.isspace()]
    if non_whitespace and all(c == "*" for c in non_whitespace):
        return "block"

    if not censored.strip() and original_text.strip():
        return "block"

    return "mask"


class HttpModerationRunner:
    """Drives scenarios against a Next.js moderation endpoint.

    Parameters
    ----------
    endpoint: Absolute URL to POST scenario text at. Defaults to the
        Nerdy Tutor moderation route on localhost.
    timeout_s: HTTP timeout in seconds (total).
    headers: Optional extra HTTP headers (e.g. an auth cookie). The Nerdy
        Tutor route requires a Supabase session; the human user is expected
        to wire that up out-of-band for the demo.
    dry_run: When True, skip the network call entirely and synthesise a
        `pass` verdict. Used by `vt-redteam run --mode http-moderation
        --dry-run` to validate the pipeline without a live next dev server.
    transport: Optional httpx transport override (used by tests to inject
        a `MockTransport`).
    """

    def __init__(
        self,
        endpoint: str,
        *,
        timeout_s: float = 10.0,
        headers: dict[str, str] | None = None,
        dry_run: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.headers = headers or {}
        self.dry_run = dry_run
        self._transport = transport

    def _dry_run_response(self, scenario_text: str) -> dict[str, Any]:
        # Mirrors the API's "no moderation needed" success shape.
        return {"layer": "none", "terms": [], "text": scenario_text}

    async def run_scenario(
        self,
        scenario: Scenario,
        agent: AgentConfig,  # noqa: ARG002 - kept for runner-interface parity
    ) -> RoomDispatchResult:
        notes: list[str] = []
        scenario_text = scenario.turns[0]
        metadata: dict[str, Any] = {
            "redteam": {
                "scenario_id": scenario.id,
                "category": scenario.category,
                "language": scenario.language,
                "harness_version": "0.0.4-http",
                "mode": "http-moderation",
            },
            "endpoint": self.endpoint,
        }

        if self.dry_run:
            payload = self._dry_run_response(scenario_text)
            notes.append("Dry-run: skipped HTTP call, synthesised pass verdict.")
            verdict = derive_verdict(scenario_text, payload)
            notes.append(f"Derived verdict={verdict}")
            return RoomDispatchResult(
                room_name=f"http-moderation-{scenario.id}",
                room_sid=None,
                metadata_sent=metadata,
                agent_response_transcript=json.dumps(payload),
                notes=notes,
            )

        async with httpx.AsyncClient(
            timeout=self.timeout_s,
            transport=self._transport,
        ) as client:
            try:
                response = await client.post(
                    self.endpoint,
                    json={"text": scenario_text},
                    headers=self.headers,
                )
            except httpx.HTTPError as exc:
                error_payload = {
                    "error": str(exc),
                    "layer": "error",
                    "terms": [],
                    "text": scenario_text,
                }
                notes.append(f"HTTP error: {exc!r}")
                return RoomDispatchResult(
                    room_name=f"http-moderation-{scenario.id}",
                    room_sid=None,
                    metadata_sent=metadata,
                    agent_response_transcript=json.dumps(error_payload),
                    notes=notes,
                )

        notes.append(f"POST {self.endpoint} → {response.status_code}")
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            payload = {
                "error": f"non-JSON response: {exc}",
                "status_code": response.status_code,
                "body": response.text[:500],
                "layer": "error",
                "terms": [],
                "text": scenario_text,
            }
            notes.append("Response was not JSON")
            return RoomDispatchResult(
                room_name=f"http-moderation-{scenario.id}",
                room_sid=None,
                metadata_sent=metadata,
                agent_response_transcript=json.dumps(payload),
                notes=notes,
            )

        if response.status_code >= 400:
            # The route returns `{ error: "..." }` for 400/401/429/500/503.
            # Tag the payload as an error so the scorer marks the run as a
            # failure rather than silently treating it as 'pass'.
            payload = {
                **payload,
                "layer": "error",
                "status_code": response.status_code,
            }
            notes.append(f"HTTP {response.status_code} treated as error verdict")
            return RoomDispatchResult(
                room_name=f"http-moderation-{scenario.id}",
                room_sid=None,
                metadata_sent=metadata,
                agent_response_transcript=json.dumps(payload),
                notes=notes,
            )

        verdict = derive_verdict(scenario_text, payload)
        notes.append(
            f"layer={payload.get('layer')} terms={len(payload.get('terms') or [])} "
            f"verdict={verdict}"
        )

        return RoomDispatchResult(
            room_name=f"http-moderation-{scenario.id}",
            room_sid=None,
            metadata_sent=metadata,
            agent_response_transcript=json.dumps(payload),
            notes=notes,
        )
