"""Load + validate `.redteam/manifest.yaml` files.

Backs the `vt-redteam validate-manifest` CLI command. Returns a typed
`AgentManifest` or raises a `ManifestValidationError` with a concrete
message naming the offending field.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from vt_agent_redteam.types import AgentManifest


class ManifestValidationError(ValueError):
    """Raised when a manifest fails validation. Contains a list of issues."""

    def __init__(self, issues: list[str]) -> None:
        super().__init__("; ".join(issues))
        self.issues = issues


def load_manifest(path: Path) -> AgentManifest:
    """Load and validate a manifest. Raises ManifestValidationError on failure."""
    if not path.exists():
        raise ManifestValidationError([f"manifest file not found: {path}"])

    try:
        with path.open() as fp:
            raw: dict[str, Any] = yaml.safe_load(fp) or {}
    except yaml.YAMLError as exc:
        raise ManifestValidationError([f"YAML parse error: {exc}"]) from exc

    issues: list[str] = []

    # Schema-level Pydantic validation first
    try:
        manifest = AgentManifest(**raw)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            issues.append(f"{loc}: {err['msg']}")
        raise ManifestValidationError(issues)

    # Semantic checks beyond the schema
    if not manifest.livekit.get("agent_name"):
        issues.append("livekit.agent_name is required (per-env mapping)")
    if not manifest.runtime.get("language"):
        issues.append("runtime.language is required (python | typescript)")
    profile_type = manifest.policy_profile.type
    valid_profiles = {
        "k12_learner", "support_navigation", "commerce_checkout",
        "interview_assessment", "b2b_course", "demo_poc",
    }
    if profile_type not in valid_profiles:
        issues.append(
            f"policy_profile.type must be one of {sorted(valid_profiles)}, "
            f"got {profile_type!r}"
        )
    if not manifest.scenario_selection.buckets:
        issues.append("scenario_selection.buckets must list at least one bucket")
    if manifest.thresholds.pr_required_pass_rate < 0 or manifest.thresholds.pr_required_pass_rate > 1:
        issues.append("thresholds.pr_required_pass_rate must be in [0, 1]")

    if issues:
        raise ManifestValidationError(issues)

    return manifest


def validate_manifest_file(path: Path) -> tuple[bool, list[str]]:
    """Returns (is_valid, list_of_issues). Never raises."""
    try:
        load_manifest(path)
        return True, []
    except ManifestValidationError as exc:
        return False, exc.issues
