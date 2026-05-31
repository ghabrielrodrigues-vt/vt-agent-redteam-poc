"""Tests for manifest loading and semantic validation."""

from __future__ import annotations

import pytest

from vt_agent_redteam.manifest_loader import ManifestValidationError, load_manifest


def _write_manifest(tmp_path, policy_profile: str) -> object:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        f"""
schema_version: 1
name: support-agent
responsible_team: eng-met-ui

livekit:
  agent_name:
    staging: support-agent-staging

runtime:
  language: python

policy_profile:
  type: support_navigation
  coverage_status: {policy_profile}
  scenario_packs:
    - support_navigation

metadata_template:
  redteam:
    run_id: "{{{{ run.id }}}}"

scenario_selection:
  buckets:
    - content_safety
  exclude_tags:
    - tool-misuse
""".lstrip()
    )
    return manifest_path


def test_load_manifest_accepts_partial_coverage_and_exclude_tags(tmp_path):
    manifest = load_manifest(_write_manifest(tmp_path, "partial-no-tool-use"))

    assert manifest.policy_profile.coverage_status == "partial-no-tool-use"
    assert manifest.scenario_selection.exclude_tags == ["tool-misuse"]


def test_load_manifest_rejects_unknown_coverage_status(tmp_path):
    with pytest.raises(ManifestValidationError) as exc:
        load_manifest(_write_manifest(tmp_path, "partial"))

    assert "policy_profile.coverage_status" in str(exc.value)
