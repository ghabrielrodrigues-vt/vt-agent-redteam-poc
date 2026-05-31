"""Schema-level tests on the Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from vt_agent_redteam.types import AgentManifest, ExpectedBehavior, Scenario, ScoreResult


def _minimal_manifest(**overrides):
    manifest = {
        "name": "language-tutor",
        "responsible_team": "conversation-club",
        "livekit": {"agent_name": {"staging": "language-tutor-staging"}},
        "runtime": {"language": "python"},
        "policy_profile": {"type": "k12_learner"},
        "metadata_template": {"redteam": {"run_id": "{{ run.id }}"}},
        "scenario_selection": {"buckets": ["content_safety"]},
    }
    manifest.update(overrides)
    return manifest


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


def test_agent_manifest_defaults_manifest_coverage_fields():
    manifest = AgentManifest(**_minimal_manifest())

    assert manifest.policy_profile.coverage_status == "full"
    assert manifest.scenario_selection.exclude_tags == []


def test_agent_manifest_accepts_coverage_status_values():
    for coverage_status in ("full", "partial-no-tool-use", "partial-other"):
        manifest = AgentManifest(
            **_minimal_manifest(
                policy_profile={
                    "type": "support_navigation",
                    "coverage_status": coverage_status,
                }
            )
        )

        assert manifest.policy_profile.coverage_status == coverage_status


def test_agent_manifest_rejects_unknown_coverage_status():
    with pytest.raises(ValidationError):
        AgentManifest(
            **_minimal_manifest(
                policy_profile={
                    "type": "support_navigation",
                    "coverage_status": "partial",
                }
            )
        )


def test_agent_manifest_accepts_scenario_exclude_tags():
    manifest = AgentManifest(
        **_minimal_manifest(
            scenario_selection={
                "buckets": ["content_safety"],
                "exclude_tags": ["tool-misuse"],
            }
        )
    )

    assert manifest.scenario_selection.exclude_tags == ["tool-misuse"]
