"""Unit tests for LangfuseTraceRunner.

The runner has three substantive surfaces:
1. fetch_transcript_by_trace_id — polls a known trace_id with backoff
2. search_and_fetch_by_metadata — finds the trace by (run_id, scenario_id) then delegates
3. run_scenario — orchestrates the full flow and emits a RoomDispatchResult

Tests use an in-memory fake LangfuseClient that implements
LangfuseClientProtocol. No HTTP calls are made; backoff is verified via the
fake's call counter, not real time.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest

from vt_agent_redteam.runners.langfuse_trace_runner import (
    LangfuseClientProtocol,
    LangfuseTraceRunner,
    TranscriptFetch,
    _coerce_output_to_text,
)
from vt_agent_redteam.types import AgentConfig, Scenario


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class FakeLangfuseClient:
    """In-memory LangfuseClientProtocol implementation for tests.

    The fake tracks how many times each method is called and lets the test
    program a sequence of responses.
    """

    base_url: str = "https://fake.langfuse"
    # Responses are popped off in order; if empty, returns the last item.
    search_responses: list[list[dict[str, Any]]] = field(default_factory=list)
    trace_responses: dict[str, list[dict[str, Any] | None]] = field(default_factory=dict)
    search_calls: int = 0
    trace_calls: dict[str, int] = field(default_factory=dict)

    async def search_traces_by_metadata(
        self, *, run_id: str, scenario_id: str, from_timestamp: float | None = None
    ) -> list[dict[str, Any]]:
        self.search_calls += 1
        if not self.search_responses:
            return []
        if len(self.search_responses) == 1:
            return self.search_responses[0]
        return self.search_responses.pop(0)

    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        self.trace_calls[trace_id] = self.trace_calls.get(trace_id, 0) + 1
        responses = self.trace_responses.get(trace_id, [])
        if not responses:
            return None
        if len(responses) == 1:
            return responses[0]
        return responses.pop(0)

    def trace_url(self, trace_id: str) -> str:
        return f"{self.base_url}/trace/{trace_id}"


def _make_runner(client: LangfuseClientProtocol) -> LangfuseTraceRunner:
    # Aggressive timing so tests stay fast.
    return LangfuseTraceRunner(
        client=client,
        timeout_seconds=2.0,
        poll_interval_seconds=0.05,
        poll_max_interval_seconds=0.1,
    )


def _scenario() -> Scenario:
    return Scenario(
        id="test-scenario-001",
        category="violence",
        language="en",
        tags=["smoke"],
        turns=["Adversarial prompt example."],
    )


def _agent() -> AgentConfig:
    return AgentConfig(
        name="test-agent",
        livekit_agent_name="test-agent",
        room_name_prefix="test-redteam",
        metadata_template={"system_prompt": "stub prompt"},
        known_system_prompt="System prompt for the test agent.",
    )


def _trace_with_generation(
    trace_id: str = "tr-001",
    outputs: list[str] | None = None,
    input_tokens: int = 100,
    output_tokens: int = 25,
) -> dict[str, Any]:
    outputs = outputs or ["I cannot help with that request."]
    return {
        "id": trace_id,
        "name": "language-tutor session",
        "observations": [
            {
                "id": f"obs-{i}",
                "type": "GENERATION",
                "name": "llm.complete",
                "startTime": f"2026-05-30T12:00:{i:02d}Z",
                "output": text,
                "usage": {"input": input_tokens, "output": output_tokens},
            }
            for i, text in enumerate(outputs)
        ],
    }


def _trace_no_generation(trace_id: str = "tr-001") -> dict[str, Any]:
    """Trace exists but only carries SPAN/EVENT observations — no LLM output yet."""
    return {
        "id": trace_id,
        "name": "language-tutor session",
        "observations": [
            {"id": "span-1", "type": "SPAN", "name": "session.start"},
            {"id": "event-1", "type": "EVENT", "name": "track.subscribed"},
        ],
    }


# ---------------------------------------------------------------------------
# fetch_transcript_by_trace_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_transcript_success_first_poll():
    client = FakeLangfuseClient(
        trace_responses={"tr-001": [_trace_with_generation()]}
    )
    runner = _make_runner(client)
    fetch = await runner.fetch_transcript_by_trace_id("tr-001")

    assert fetch.found is True
    assert fetch.timed_out is False
    assert fetch.transcript_text == "I cannot help with that request."
    assert fetch.trace_id == "tr-001"
    assert fetch.artifact_uri == "https://fake.langfuse/trace/tr-001"
    assert fetch.input_tokens == 100
    assert fetch.output_tokens == 25
    assert fetch.generations_count == 1
    assert client.trace_calls["tr-001"] == 1


@pytest.mark.asyncio
async def test_fetch_transcript_waits_for_generation_then_succeeds():
    # First two polls: trace exists but no GENERATION yet. Third: success.
    client = FakeLangfuseClient(
        trace_responses={
            "tr-002": [
                _trace_no_generation("tr-002"),
                _trace_no_generation("tr-002"),
                _trace_with_generation("tr-002", outputs=["Sure, here is what I can share."]),
            ]
        }
    )
    runner = _make_runner(client)
    fetch = await runner.fetch_transcript_by_trace_id("tr-002")

    assert fetch.found is True
    assert fetch.transcript_text == "Sure, here is what I can share."
    assert client.trace_calls["tr-002"] == 3


@pytest.mark.asyncio
async def test_fetch_transcript_timeout_when_trace_never_appears():
    client = FakeLangfuseClient(trace_responses={})  # always returns None
    runner = _make_runner(client)
    fetch = await runner.fetch_transcript_by_trace_id("tr-missing")

    assert fetch.found is False
    assert fetch.timed_out is True
    assert fetch.transcript_text == ""
    assert fetch.trace_id == "tr-missing"
    # artifact_uri still set so the failing row can link to the (empty) trace URL
    assert fetch.artifact_uri == "https://fake.langfuse/trace/tr-missing"


@pytest.mark.asyncio
async def test_fetch_transcript_timeout_when_trace_lacks_generation():
    # Trace appears but GENERATION never lands.
    client = FakeLangfuseClient(
        trace_responses={"tr-003": [_trace_no_generation("tr-003")]}
    )
    runner = _make_runner(client)
    fetch = await runner.fetch_transcript_by_trace_id("tr-003")

    assert fetch.found is False
    assert fetch.timed_out is True
    assert fetch.transcript_text == ""
    assert fetch.generations_count == 0


@pytest.mark.asyncio
async def test_fetch_transcript_aggregates_multiple_generations_in_order():
    # Two GENERATION spans with start_time-based ordering.
    client = FakeLangfuseClient(
        trace_responses={
            "tr-multi": [
                _trace_with_generation(
                    "tr-multi",
                    outputs=["First reply.", "Follow-up reply."],
                    input_tokens=50,
                    output_tokens=10,
                )
            ]
        }
    )
    runner = _make_runner(client)
    fetch = await runner.fetch_transcript_by_trace_id("tr-multi")

    assert fetch.transcript_text == "First reply.\n---\nFollow-up reply."
    assert fetch.input_tokens == 100  # 2 generations × 50 each
    assert fetch.output_tokens == 20
    assert fetch.generations_count == 2


# ---------------------------------------------------------------------------
# search_and_fetch_by_metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_and_fetch_finds_trace_and_returns_transcript():
    client = FakeLangfuseClient(
        search_responses=[[{"id": "tr-found", "metadata": {}}]],
        trace_responses={"tr-found": [_trace_with_generation("tr-found")]},
    )
    runner = _make_runner(client)
    fetch = await runner.search_and_fetch_by_metadata(
        run_id="run-1", scenario_id="scn-1"
    )

    assert fetch.found is True
    assert fetch.trace_id == "tr-found"
    assert fetch.transcript_text == "I cannot help with that request."


@pytest.mark.asyncio
async def test_search_returns_empty_until_trace_appears():
    # Search returns [] then [] then [trace]. Tests the polling loop.
    client = FakeLangfuseClient(
        search_responses=[[], [], [{"id": "tr-late"}]],
        trace_responses={"tr-late": [_trace_with_generation("tr-late")]},
    )
    runner = _make_runner(client)
    fetch = await runner.search_and_fetch_by_metadata(
        run_id="run-2", scenario_id="scn-2"
    )

    assert fetch.found is True
    assert fetch.trace_id == "tr-late"
    assert client.search_calls == 3


@pytest.mark.asyncio
async def test_search_timeout_when_no_match():
    client = FakeLangfuseClient(search_responses=[[]])  # never matches
    runner = _make_runner(client)
    fetch = await runner.search_and_fetch_by_metadata(
        run_id="run-x", scenario_id="scn-x"
    )

    assert fetch.found is False
    assert fetch.timed_out is True
    assert fetch.trace_id is None


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scenario_success_returns_agent_native_transcript():
    client = FakeLangfuseClient(
        search_responses=[[{"id": "tr-rs-1"}]],
        trace_responses={"tr-rs-1": [_trace_with_generation("tr-rs-1")]},
    )
    runner = _make_runner(client)
    result = await runner.run_scenario(_scenario(), _agent(), run_id="run-rs-1")

    assert result.is_stub_response is False  # type: ignore[attr-defined]
    assert result.transcript_source == "agent_native_transcript"  # type: ignore[attr-defined]
    assert result.agent_response_transcript == "I cannot help with that request."
    assert result.artifact_uri == "https://fake.langfuse/trace/tr-rs-1"  # type: ignore[attr-defined]
    assert result.response_hash is not None  # type: ignore[attr-defined]
    assert result.timeout_flag is False  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_run_scenario_falls_back_to_stub_when_trace_never_found():
    # Spec §9.8 stub-row guarantee: if Langfuse path produces nothing, the
    # row must be marked is_stub_response=True so threshold_passed is forced
    # NULL upstream.
    client = FakeLangfuseClient(search_responses=[[]])  # nothing ever matches
    runner = _make_runner(client)
    result = await runner.run_scenario(_scenario(), _agent(), run_id="run-stub")

    assert result.is_stub_response is True  # type: ignore[attr-defined]
    assert result.transcript_source == "stub_canned"  # type: ignore[attr-defined]
    assert result.timeout_flag is True  # type: ignore[attr-defined]
    assert "trace never appeared" in result.agent_response_transcript.lower()


@pytest.mark.asyncio
async def test_run_scenario_sets_room_metadata_from_inputs():
    client = FakeLangfuseClient(
        search_responses=[[{"id": "tr-meta"}]],
        trace_responses={"tr-meta": [_trace_with_generation("tr-meta")]},
    )
    runner = _make_runner(client)
    result = await runner.run_scenario(
        _scenario(),
        _agent(),
        run_id="run-meta",
        room_name="explicit-room-name",
        room_sid="RM_explicit",
        metadata_sent={"override_key": "override_value"},
    )

    assert result.room_name == "explicit-room-name"
    assert result.room_sid == "RM_explicit"
    assert result.metadata_sent == {"override_key": "override_value"}


# ---------------------------------------------------------------------------
# _coerce_output_to_text
# ---------------------------------------------------------------------------


def test_coerce_output_string_passes_through():
    assert _coerce_output_to_text("hello") == "hello"


def test_coerce_output_none_returns_empty():
    assert _coerce_output_to_text(None) == ""


def test_coerce_output_dict_with_string_content():
    assert _coerce_output_to_text({"role": "assistant", "content": "ok"}) == "ok"


def test_coerce_output_dict_with_list_content():
    out = _coerce_output_to_text(
        {"role": "assistant", "content": [{"type": "text", "text": "part 1"}, {"type": "text", "text": "part 2"}]}
    )
    assert out == "part 1\npart 2"


def test_coerce_output_list_of_messages():
    out = _coerce_output_to_text(
        [{"role": "assistant", "content": "first"}, {"role": "assistant", "content": "second"}]
    )
    assert out == "first\nsecond"


def test_coerce_output_unknown_shape_falls_back_to_repr():
    assert _coerce_output_to_text(42) == "42"
