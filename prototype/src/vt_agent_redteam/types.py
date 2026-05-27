"""Shared dataclasses and Pydantic models used across the harness."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ScenarioCategory = Literal[
    # Original OpenAI Moderation taxonomy
    "violence",
    "sexual",
    "self_harm",
    "hate",
    "harassment",
    "illicit",
    # LiveKit-specific failure modes
    "jailbreak",
    "prompt_leakage",
    "education_specific",
    # K-12 Nerdy Tutor content policy coverage (lib/ai/moderation.ts)
    "politics",
    "forbidden_topics",
    "dating_romance",
    "brand_protection",
    "stakeholder_protection",
    "off_topic_academic",
    "diversity_framing",
    "cheating_integrity",
    # Academic extensions (OWASP LLM Top 10, NIST AI RMF, MITRE ATLAS)
    "personal_information",
    "misinformation",
    "medical_legal_advice",
    "impersonation",
    "emotional_manipulation",
]


ModerationVerdict = Literal["block", "mask", "pass"]


class ExpectedBehavior(BaseModel):
    refusal_required: bool = True
    redirect_topic: str | None = None
    must_not_include: list[str] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)
    # Used only by the http-moderation mode (Option B). Encodes whether the
    # Nerdy Tutor input-side moderation pipeline should block, mask, or pass
    # the scenario's first turn. Existing voice-side scenarios leave this
    # unset and are filtered out of the http-moderation run.
    expected_moderation_verdict: ModerationVerdict | None = None


class Scenario(BaseModel):
    """A single adversarial test case loaded from the corpus."""

    id: str
    category: ScenarioCategory
    language: str = "en"
    tags: list[str] = Field(default_factory=lambda: ["full"])
    turns: list[str]
    expected_behavior: ExpectedBehavior = Field(default_factory=ExpectedBehavior)
    notes: str | None = None


class ScoreResult(BaseModel):
    """The output of a single scorer applied to one agent response."""

    scorer_name: str
    passed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    detail: dict[str, Any] = Field(default_factory=dict)
    reasoning: str | None = None


class ScenarioResult(BaseModel):
    """Aggregate result of one scenario run across all configured scorers."""

    scenario_id: str
    category: ScenarioCategory
    adversarial_prompts: list[str]
    agent_responses: list[str]
    scorer_results: list[ScoreResult]
    passed: bool
    failure_reason: str | None = None
    duration_seconds: float = 0.0
    run_at: datetime = Field(default_factory=datetime.utcnow)


class AgentConfig(BaseModel):
    """Connection and metadata template for a target agent."""

    name: str
    livekit_agent_name: str
    room_name_prefix: str
    metadata_template: dict[str, Any]
    known_system_prompt: str | None = None
