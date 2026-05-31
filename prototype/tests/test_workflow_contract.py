"""Reusable workflow contract tests."""

from __future__ import annotations

from pathlib import Path

from vt_agent_redteam.manifest_loader import load_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/redteam.yml"
FIXTURE_MANIFEST = REPO_ROOT / ".github/fixtures/redteam/manifest.yaml"


def test_reusable_workflow_exposes_required_contract():
    workflow = WORKFLOW_PATH.read_text()

    assert "workflow_call:" in workflow
    assert "agent_manifest:" in workflow
    assert "mode:" in workflow
    assert "environment:" in workflow
    assert "enforce_threshold:" in workflow
    assert "REDTEAM_DB_URL:" in workflow
    assert "LANGFUSE_PUBLIC_KEY:" in workflow
    assert "LANGFUSE_SECRET_KEY:" in workflow
    assert "REDTEAM_RUN_ID=" in workflow
    assert "--enforce-threshold" in workflow
    assert "--write-results" in workflow
    assert "agent-native-transcript" in workflow


def test_reusable_workflow_supports_fixture_manifest_dispatch():
    workflow = WORKFLOW_PATH.read_text()

    assert "workflow_dispatch:" in workflow
    assert ".github/fixtures/redteam/manifest.yaml" in workflow
    assert "framework_package" in workflow
    assert "local" in workflow


def test_fixture_manifest_validates():
    manifest = load_manifest(FIXTURE_MANIFEST)

    assert manifest.name == "fixture-agent"
    assert manifest.policy_profile.type == "k12_learner"
    assert manifest.known_system_prompt_source == "prompts/"
