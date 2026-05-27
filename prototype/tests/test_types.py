"""Schema-level tests on the Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from vt_agent_redteam.types import ExpectedBehavior, Scenario, ScoreResult


def test_scenario_requires_id_and_turns():
    with pytest.raises(ValidationError):
        Scenario(category="violence", turns=["foo"])  # missing id
    with pytest.raises(ValidationError):
        Scenario(id="x", category="violence")  # missing turns


def test_scenario_rejects_unknown_category():
    with pytest.raises(ValidationError):
        Scenario(id="x", category="not_a_real_category", turns=["foo"])  # type: ignore[arg-type]


def test_scenario_defaults_to_english_and_full_tag():
    s = Scenario(id="x", category="violence", turns=["foo"])
    assert s.language == "en"
    assert s.tags == ["full"]


def test_expected_behavior_defaults_to_refusal_required():
    eb = ExpectedBehavior()
    assert eb.refusal_required is True
    assert eb.must_not_include == []
    assert eb.must_include == []


def test_score_result_confidence_bounded():
    with pytest.raises(ValidationError):
        ScoreResult(scorer_name="x", passed=True, confidence=1.5)
    with pytest.raises(ValidationError):
        ScoreResult(scorer_name="x", passed=True, confidence=-0.1)
    sr = ScoreResult(scorer_name="x", passed=True, confidence=0.5)
    assert sr.confidence == 0.5
