"""Langfuse-native transcript runner — agent_native_transcript path.

Why this exists
---------------
The spec section 15.1 named "agent-native transcript via Langfuse" as the
Phase 2 recovery path if the WAV-collector audio capture race condition
proves intractable. In v0 we promote it to the primary audio path because:

1. All three target agents in `student-onboarding-orchestration` already
   emit OpenTelemetry spans to Langfuse via `langfuse_tracing.py` (deployed
   2026-05-18). LiveKit Agents emits OTel spans for every LLM, STT, TTS,
   and tool-call invocation; Langfuse ingests them as GENERATION / SPAN /
   EVENT observations.
2. We read the agent's transcript from the agent's own production trace,
   not from a separate audio-capture pipeline. No race condition exists
   because we never capture audio directly.
3. The full production audio stack is exercised end-to-end: TTS adversarial
   prompt → agent's actual STT → agent's actual LLM → agent's actual TTS.
   The framework only synthesizes the input and reads the trace.

What it returns
---------------
A result with:
- `transcript_source = "agent_native_transcript"` (per spec section 12.1)
- `agent_response_transcript` = concatenation of GENERATION span outputs in
  start_time order across the agent's trace
- `artifact_uri` = Langfuse trace URL of the form
  "{LANGFUSE_BASE_URL}/trace/{trace_id}" so the un-redacted evidence
  remains accessible via Langfuse access control (preserves spec section 12.4
  rollback path)
- `response_hash` = SHA-256 of the response text (deterministic, computed
  pre-redaction by the harness)
- `usd_cost_estimate` = NULL in v0 because the agent's production stack
  paid the LLM/STT/TTS cost, not the red-team — we attribute zero to the
  red-team budget for these calls (TTS adversarial prompt synthesis is
  the only red-team-side cost and is attributed separately by the harness)

Correlation strategy (v0)
-------------------------
The harness propagates `redteam_run_id` and `redteam_scenario_id` into the
LiveKit room metadata. The agent's `langfuse_tracing.py` exporter forwards
these as OTel attributes onto the trace. This runner fetches the trace by
searching Langfuse traces matching the (run_id, scenario_id) metadata
filter, then aggregates GENERATION outputs.

Deferred to v0.2: direct trace-id propagation (instead of metadata search)
would remove a polling step and reduce ingestion-latency exposure. v0
search-by-metadata is good enough for PR + deploy gate cadence.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from vt_agent_redteam.runners.livekit_room import RoomDispatchResult
from vt_agent_redteam.types import AgentConfig, Scenario


DEFAULT_LANGFUSE_BASE_URL = "https://us.cloud.langfuse.com"
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_POLL_MAX_INTERVAL_SECONDS = 8.0
DEFAULT_TIMEOUT_SECONDS = 90.0


@dataclass
class _LangfuseTraceResult:
    """RoomDispatchResult-compatible result for the Langfuse-native path."""

    room_name: str
    room_sid: str | None
    metadata_sent: dict[str, Any]
    agent_response_transcript: str
    notes: list[str]
    is_stub_response: bool = False
    transcript_source: str = "agent_native_transcript"
    response_hash: str | None = None
    artifact_uri: str | None = None
    usd_cost_estimate: float | None = None
    timeout_flag: bool = False
    retry_count: int = 0


@dataclass
class TranscriptFetch:
    """Output of fetch_transcript_by_trace_id / search_and_fetch_by_metadata."""

    transcript_text: str
    trace_id: str | None
    artifact_uri: str | None
    input_tokens: int
    output_tokens: int
    generations_count: int
    notes: list[str] = field(default_factory=list)
    found: bool = False
    timed_out: bool = False


class LangfuseClientProtocol(Protocol):
    """Narrow interface the runner needs from a Langfuse HTTP client.

    Exists so tests can substitute an in-memory fake without touching httpx
    or Langfuse Cloud.
    """

    async def search_traces_by_metadata(
        self, *, run_id: str, scenario_id: str, from_timestamp: float | None = None
    ) -> list[dict[str, Any]]: ...

    async def get_trace(self, trace_id: str) -> dict[str, Any] | None: ...

    def trace_url(self, trace_id: str) -> str: ...


class LangfuseHttpClient:
    """httpx-backed Langfuse v3 public API client.

    Auth: HTTP Basic with public_key:secret_key. Endpoints used:
    - GET /api/public/traces (with metadata filter) → list traces
    - GET /api/public/traces/{traceId} → full trace with observations
    """

    def __init__(
        self,
        *,
        base_url: str,
        public_key: str,
        secret_key: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        creds = f"{public_key}:{secret_key}".encode("utf-8")
        self._auth_header = "Basic " + base64.b64encode(creds).decode("ascii")
        self._timeout = timeout_seconds

    async def search_traces_by_metadata(
        self,
        *,
        run_id: str,
        scenario_id: str,
        from_timestamp: float | None = None,
    ) -> list[dict[str, Any]]:
        # Langfuse encodes metadata filter as a JSON object in the query string.
        # We filter by two keys: redteam_run_id + redteam_scenario_id.
        params: dict[str, Any] = {
            "metadata": json.dumps(
                {"redteam_run_id": run_id, "redteam_scenario_id": scenario_id}
            ),
            "limit": 5,
            "orderBy": "timestamp.desc",
        }
        if from_timestamp is not None:
            # Langfuse expects ISO 8601; pragma: relaxed conversion
            from datetime import datetime, timezone
            params["fromTimestamp"] = datetime.fromtimestamp(
                from_timestamp, tz=timezone.utc
            ).isoformat()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self.base_url}/api/public/traces",
                params=params,
                headers={"Authorization": self._auth_header},
            )
        resp.raise_for_status()
        body = resp.json()
        return body.get("data", [])

    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self.base_url}/api/public/traces/{trace_id}",
                headers={"Authorization": self._auth_header},
            )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def trace_url(self, trace_id: str) -> str:
        return f"{self.base_url}/trace/{trace_id}"


class LangfuseTraceRunner:
    """Drives a scenario by polling Langfuse for the agent's response.

    The runner assumes the agent has been dispatched separately (via
    LiveKitRoomRunner or equivalent) AND the room metadata included
    `redteam_run_id` + `redteam_scenario_id` so the agent's OTel exporter
    tags its trace with those attributes.

    Parameters
    ----------
    client : LangfuseClientProtocol
        Injected for testability. In production: LangfuseHttpClient.
    timeout_seconds : float
        Maximum wall-clock time to wait for the trace to appear AND for at
        least one GENERATION output to be present. Default 90 s.
    poll_interval_seconds : float
        Initial polling interval. Doubles each iteration up to
        `poll_max_interval_seconds`.
    poll_max_interval_seconds : float
        Cap on backoff growth.
    """

    def __init__(
        self,
        *,
        client: LangfuseClientProtocol,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        poll_max_interval_seconds: float = DEFAULT_POLL_MAX_INTERVAL_SECONDS,
    ) -> None:
        self._client = client
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.poll_max_interval_seconds = poll_max_interval_seconds

    async def fetch_transcript_by_trace_id(
        self, trace_id: str, *, search_start_time: float | None = None
    ) -> TranscriptFetch:
        """Poll Langfuse for a known trace_id until at least one GENERATION
        with non-empty output appears, or until timeout.

        Returns a TranscriptFetch carrying everything the harness needs to
        build a result row.
        """
        notes: list[str] = []
        start = search_start_time if search_start_time is not None else time.monotonic()
        interval = self.poll_interval_seconds
        last_trace: dict[str, Any] | None = None

        while time.monotonic() - start < self.timeout_seconds:
            trace = await self._client.get_trace(trace_id)
            if trace is not None:
                last_trace = trace
                transcript = self._extract_generation_outputs(trace)
                if transcript.transcript_text:
                    transcript.found = True
                    transcript.trace_id = trace_id
                    transcript.artifact_uri = self._client.trace_url(trace_id)
                    notes.append(
                        f"Trace {trace_id} ready with "
                        f"{transcript.generations_count} GENERATION span(s) "
                        f"after {time.monotonic() - start:.1f}s"
                    )
                    transcript.notes = notes
                    return transcript
                notes.append(
                    f"Trace {trace_id} present but no GENERATION output yet; "
                    f"sleeping {interval:.1f}s"
                )
            else:
                notes.append(
                    f"Trace {trace_id} not yet in Langfuse; "
                    f"sleeping {interval:.1f}s"
                )
            await asyncio.sleep(interval)
            interval = min(interval * 2, self.poll_max_interval_seconds)

        # Timeout. If we ever saw the trace, surface partial state for forensics.
        partial = (
            self._extract_generation_outputs(last_trace)
            if last_trace is not None
            else TranscriptFetch(
                transcript_text="",
                trace_id=trace_id,
                artifact_uri=None,
                input_tokens=0,
                output_tokens=0,
                generations_count=0,
            )
        )
        partial.timed_out = True
        partial.trace_id = trace_id
        partial.artifact_uri = self._client.trace_url(trace_id)
        notes.append(
            f"Timed out after {self.timeout_seconds}s waiting for "
            f"GENERATION output on trace {trace_id}"
        )
        partial.notes = notes
        return partial

    async def search_and_fetch_by_metadata(
        self, *, run_id: str, scenario_id: str, search_start_time: float | None = None
    ) -> TranscriptFetch:
        """Find the trace by metadata filter then fetch its transcript.

        This is the v0 correlation path until direct trace-id propagation is
        wired in v0.2. Polls the search endpoint until a matching trace
        appears, then delegates to fetch_transcript_by_trace_id.
        """
        notes: list[str] = []
        start = search_start_time if search_start_time is not None else time.monotonic()
        interval = self.poll_interval_seconds

        while time.monotonic() - start < self.timeout_seconds:
            try:
                traces = await self._client.search_traces_by_metadata(
                    run_id=run_id,
                    scenario_id=scenario_id,
                    from_timestamp=start,
                )
            except httpx.HTTPError as exc:
                notes.append(
                    f"Langfuse search error: {exc!r}; backing off {interval:.1f}s"
                )
                traces = []

            if traces:
                trace_id = traces[0].get("id")
                if trace_id:
                    notes.append(
                        f"Found trace {trace_id} for run={run_id} "
                        f"scenario={scenario_id} after "
                        f"{time.monotonic() - start:.1f}s"
                    )
                    fetched = await self.fetch_transcript_by_trace_id(
                        trace_id, search_start_time=start
                    )
                    fetched.notes = notes + fetched.notes
                    return fetched

            await asyncio.sleep(interval)
            interval = min(interval * 2, self.poll_max_interval_seconds)

        notes.append(
            f"Timed out after {self.timeout_seconds}s — no trace matched "
            f"run={run_id} scenario={scenario_id}"
        )
        return TranscriptFetch(
            transcript_text="",
            trace_id=None,
            artifact_uri=None,
            input_tokens=0,
            output_tokens=0,
            generations_count=0,
            notes=notes,
            found=False,
            timed_out=True,
        )

    async def run_scenario(
        self,
        scenario: Scenario,
        agent: AgentConfig,
        *,
        run_id: str,
        room_name: str | None = None,
        room_sid: str | None = None,
        metadata_sent: dict[str, Any] | None = None,
    ) -> RoomDispatchResult:
        """Full-flow runner method.

        Expects the harness to have already dispatched the agent via the
        existing LiveKit infrastructure with `redteam_run_id` + `redteam_scenario_id`
        in the room metadata. This method polls Langfuse for the agent's
        response and assembles the result.

        v0 does not include the LiveKit dispatch here because that logic lives
        in `synthetic_candidate.py` and `livekit_room.py`. F3 (harness) wires
        them together. Tests can call this directly with a mocked client.
        """
        notes: list[str] = []
        effective_room_name = room_name or (
            f"{agent.room_name_prefix}-langfuse-{uuid.uuid4().hex[:8]}"
        )
        effective_metadata = metadata_sent or {
            "redteam_run_id": run_id,
            "redteam_scenario_id": scenario.id,
            "redteam_category": scenario.category,
        }

        fetch = await self.search_and_fetch_by_metadata(
            run_id=run_id, scenario_id=scenario.id
        )
        notes.extend(fetch.notes)

        if not fetch.found:
            # No trace produced. Treat as a stub-marked row so the stub-row
            # guarantee (§9.8) forces threshold_passed = NULL.
            return _LangfuseTraceResult(
                room_name=effective_room_name,
                room_sid=room_sid,
                metadata_sent=effective_metadata,
                agent_response_transcript=(
                    "<langfuse runner: trace never appeared; agent may have "
                    "failed to dispatch or to emit OTel spans>"
                ),
                notes=notes + [
                    "FALLBACK to stub: Langfuse trace not found",
                ],
                is_stub_response=True,
                transcript_source="stub_canned",
                timeout_flag=fetch.timed_out,
                retry_count=0,
            )  # type: ignore[return-value]

        response_hash = (
            hashlib.sha256(fetch.transcript_text.encode("utf-8")).hexdigest()
            if fetch.transcript_text
            else None
        )

        return _LangfuseTraceResult(
            room_name=effective_room_name,
            room_sid=room_sid,
            metadata_sent=effective_metadata,
            agent_response_transcript=fetch.transcript_text,
            notes=notes,
            is_stub_response=False,
            transcript_source="agent_native_transcript",
            response_hash=response_hash,
            artifact_uri=fetch.artifact_uri,
            # usd_cost_estimate left None — agent's production stack paid the
            # LLM/STT/TTS bill; the red-team's TTS-prompt-synthesis cost is
            # attributed by the harness, not by this runner.
            usd_cost_estimate=None,
            timeout_flag=fetch.timed_out,
            retry_count=0,
        )  # type: ignore[return-value]

    @staticmethod
    def _extract_generation_outputs(trace: dict[str, Any]) -> TranscriptFetch:
        """Pull all GENERATION span outputs from a Langfuse trace.

        Concatenates in start_time order with `\\n---\\n` separators so the
        scorers see a coherent agent_response. Token counts aggregate across
        all GENERATION spans.
        """
        observations = trace.get("observations") or []
        generations = [
            obs for obs in observations if obs.get("type") == "GENERATION"
        ]
        generations.sort(key=lambda o: o.get("startTime") or "")

        outputs: list[str] = []
        in_tokens = 0
        out_tokens = 0
        for gen in generations:
            output = gen.get("output")
            text = _coerce_output_to_text(output)
            if text:
                outputs.append(text)
            usage = gen.get("usage") or {}
            in_tokens += int(usage.get("input") or usage.get("promptTokens") or 0)
            out_tokens += int(
                usage.get("output") or usage.get("completionTokens") or 0
            )

        transcript_text = "\n---\n".join(outputs)
        return TranscriptFetch(
            transcript_text=transcript_text,
            trace_id=trace.get("id"),
            artifact_uri=None,  # caller fills via client.trace_url()
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            generations_count=len(generations),
        )


def _coerce_output_to_text(output: Any) -> str:
    """Langfuse `output` field is shape-polymorphic: it can be a plain string,
    a chat-completion-style dict {"role":..., "content":...}, or a list of
    such dicts. Reduce to a flat string for the scorers."""
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        content = output.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            # Chat-style content array: [{"type":"text","text":"..."}, ...]
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            return "\n".join(parts)
        return json.dumps(output, ensure_ascii=False)
    if isinstance(output, list):
        # Sometimes Langfuse stores message arrays directly
        parts = []
        for item in output:
            parts.append(_coerce_output_to_text(item))
        return "\n".join(p for p in parts if p)
    return str(output)


def build_default_client(
    *,
    base_url: str | None = None,
    public_key: str | None = None,
    secret_key: str | None = None,
) -> LangfuseHttpClient | None:
    """Construct a LangfuseHttpClient from explicit args or env vars.

    Returns None if Langfuse credentials are missing — caller treats this as
    "Langfuse path unavailable; fall back to direct-llm" per spec §15.1.
    """
    base_url = base_url or os.environ.get("LANGFUSE_BASE_URL") or os.environ.get(
        "LANGFUSE_HOST"
    ) or DEFAULT_LANGFUSE_BASE_URL
    public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        return None
    return LangfuseHttpClient(
        base_url=base_url,
        public_key=public_key,
        secret_key=secret_key,
    )
