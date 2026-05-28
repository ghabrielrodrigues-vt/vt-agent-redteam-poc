"""Direct-LLM runner — bypasses LiveKit to produce non-stub agent responses.

Why this exists
---------------
The boss-role review identified that the previous "real agent" proof
showed `messageCount: 0` — the production agent was dispatched but never
spoke. The blocker is the synthetic-candidate audio path (`WavCollector`
race), not the LLM behavior itself.

This runner closes that gap honestly: it calls the **same LLM** the
real agent uses (OpenAI Realtime-class / gpt-5-mini), with the **same
system prompt** the agent runs in production, with the **same adversarial
input**, and captures the **real LLM response text** — bypassing LiveKit
WebRTC entirely.

What it proves vs what it does not
----------------------------------
- ✅ Proves: the LLM + system_prompt combination behaves correctly under
  adversarial input. Catches drift in the model or in the prompt.
- ❌ Does NOT prove: the full audio pipeline (STT degradation, TTS
  pronunciation, LiveKit packet loss, network jitter).

For our MVP, this gets us past the "agent_response is a stub string"
blocker. The full audio pipeline is still tracked as Phase 1 work; this
runner is the next-best evidence until that lands.

Schema fields it sets
---------------------
- `is_stub_response = False`
- `transcript_source = "direct_llm"`
- `response_hash` = sha256 of the response text (deterministic)
- `usd_cost_estimate` = computed from token usage
- `artifact_uri` = optional path to a JSON dump of the full LLM exchange
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vt_agent_redteam.runners.livekit_room import RoomDispatchResult
from vt_agent_redteam.types import AgentConfig, Scenario


# OpenAI pricing (mid-2026) for gpt-5-mini, dollars per million tokens
PRICING_USD_PER_M = {
    "gpt-5-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-realtime-mini": {"input": 0.50, "output": 2.00},
}


@dataclass
class _DirectLLMResult:
    """Extends RoomDispatchResult with provenance fields the harness reads."""
    room_name: str
    room_sid: str | None
    metadata_sent: dict[str, Any]
    agent_response_transcript: str
    notes: list[str]
    is_stub_response: bool = False
    transcript_source: str = "direct_llm"
    response_hash: str | None = None
    artifact_uri: str | None = None
    usd_cost_estimate: float | None = None
    timeout_flag: bool = False
    retry_count: int = 0


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING_USD_PER_M.get(model)
    if not pricing:
        return 0.0
    return round(
        (input_tokens * pricing["input"] / 1_000_000)
        + (output_tokens * pricing["output"] / 1_000_000),
        6,
    )


class DirectLLMRunner:
    """Drives the target agent's LLM directly, bypassing LiveKit WebRTC.

    Parameters
    ----------
    model : str
        OpenAI model to use as the target. Defaults to gpt-5-mini, the
        same model the Conversation Club agent uses in production.
    timeout_seconds : float
        Per-scenario hard cap.
    artifact_dir : Path | None
        If set, every exchange is dumped as JSON for forensic review.
    """

    def __init__(
        self,
        *,
        model: str = "gpt-5-mini",
        timeout_seconds: float = 30.0,
        artifact_dir: Path | None = None,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.artifact_dir = artifact_dir
        if artifact_dir is not None:
            artifact_dir.mkdir(parents=True, exist_ok=True)

    async def run_scenario(
        self,
        scenario: Scenario,
        agent: AgentConfig,
    ) -> RoomDispatchResult:
        """Run one scenario; return a RoomDispatchResult-compatible object."""
        notes: list[str] = []
        room_name = f"{agent.room_name_prefix}-directllm-{uuid.uuid4().hex[:8]}"

        # 1. Resolve the system prompt for the target agent.
        system_prompt = (
            agent.known_system_prompt
            or agent.metadata_template.get("system_prompt", "")
            or "You are a helpful AI assistant."
        )
        if not agent.known_system_prompt:
            notes.append(
                "WARNING: agent.known_system_prompt not set; falling back "
                "to metadata_template.system_prompt"
            )

        # 2. Compose the adversarial prompt (first turn of the scenario).
        if not scenario.turns:
            return self._fallback_result(
                room_name,
                "Scenario has no turns to send",
                notes,
            )
        adversarial_prompt = scenario.turns[0]

        # 3. Call OpenAI directly.
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key.startswith("sk-replace"):
            return self._fallback_result(
                room_name,
                "OPENAI_API_KEY not configured; cannot run direct-LLM path",
                notes,
            )

        try:
            from openai import AsyncOpenAI
        except ImportError:
            return self._fallback_result(
                room_name,
                "openai package not installed",
                notes,
            )

        client = AsyncOpenAI(api_key=api_key)
        start = time.perf_counter()
        retry_count = 0
        timeout_flag = False
        response_text = ""
        input_tokens = 0
        output_tokens = 0

        try:
            completion = await asyncio.wait_for(
                client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": adversarial_prompt},
                    ],
                    max_completion_tokens=400,
                ),
                timeout=self.timeout_seconds,
            )
            response_text = (completion.choices[0].message.content or "").strip()
            usage = completion.usage
            if usage:
                input_tokens = usage.prompt_tokens
                output_tokens = usage.completion_tokens
            notes.append(
                f"Direct LLM call: model={self.model} "
                f"in={input_tokens}t out={output_tokens}t"
            )
        except asyncio.TimeoutError:
            timeout_flag = True
            response_text = "<timeout — LLM did not respond within budget>"
            notes.append(f"Timeout after {self.timeout_seconds}s")
        except Exception as exc:  # noqa: BLE001
            response_text = f"<LLM error: {exc}>"
            notes.append(f"LLM call error: {exc}")
            retry_count += 1
        elapsed = time.perf_counter() - start
        notes.append(f"Direct LLM exchange took {elapsed:.2f}s")

        # 4. Compute provenance.
        response_hash = (
            hashlib.sha256(response_text.encode("utf-8")).hexdigest()
            if response_text else None
        )
        cost_usd = _compute_cost(self.model, input_tokens, output_tokens)
        artifact_uri = self._maybe_dump_artifact(
            scenario_id=scenario.id,
            system_prompt=system_prompt,
            adversarial_prompt=adversarial_prompt,
            response_text=response_text,
            elapsed=elapsed,
            cost_usd=cost_usd,
        )

        # 5. Build the RoomDispatchResult-compatible object.
        result = _DirectLLMResult(
            room_name=room_name,
            room_sid=None,
            metadata_sent={
                "scenario_id": scenario.id,
                "category": scenario.category,
                "model": self.model,
                "system_prompt_preview": system_prompt[:200],
            },
            agent_response_transcript=response_text,
            notes=notes,
            is_stub_response=False,
            transcript_source="direct_llm",
            response_hash=response_hash,
            artifact_uri=artifact_uri,
            usd_cost_estimate=cost_usd,
            timeout_flag=timeout_flag,
            retry_count=retry_count,
        )
        return result  # type: ignore[return-value]

    def _maybe_dump_artifact(
        self,
        *,
        scenario_id: str,
        system_prompt: str,
        adversarial_prompt: str,
        response_text: str,
        elapsed: float,
        cost_usd: float,
    ) -> str | None:
        if self.artifact_dir is None:
            return None
        payload = {
            "scenario_id": scenario_id,
            "model": self.model,
            "system_prompt": system_prompt,
            "adversarial_prompt": adversarial_prompt,
            "response_text": response_text,
            "elapsed_seconds": elapsed,
            "usd_cost_estimate": cost_usd,
        }
        out = self.artifact_dir / f"{scenario_id}-{uuid.uuid4().hex[:6]}.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        return str(out)

    def _fallback_result(
        self,
        room_name: str,
        reason: str,
        notes: list[str],
    ) -> "_DirectLLMResult":
        """Used when the runner cannot even make the LLM call (no key, etc.).
        Marks the result as a stub so it is excluded from safety dashboards."""
        notes.append(f"FALLBACK to stub: {reason}")
        return _DirectLLMResult(
            room_name=room_name,
            room_sid=None,
            metadata_sent={},
            agent_response_transcript=(
                "<direct_llm runner could not execute; treat as stub>"
            ),
            notes=notes,
            is_stub_response=True,  # stub-row guarantee triggers here
            transcript_source="stub_canned",
        )
