"""Load adversarial scenarios from YAML corpus files."""

from __future__ import annotations

from pathlib import Path

import yaml

from vt_agent_redteam.types import Scenario


def load_corpus(corpus_dir: Path) -> list[Scenario]:
    """Load every .yaml file under corpus_dir, returning a flat list of Scenarios."""
    scenarios: list[Scenario] = []
    for yaml_file in sorted(corpus_dir.glob("*.yaml")):
        with yaml_file.open() as fp:
            raw = yaml.safe_load(fp) or []
        for entry in raw:
            scenarios.append(Scenario(**entry))
    return scenarios


def filter_scenarios(
    scenarios: list[Scenario],
    *,
    categories: list[str] | None = None,
    tags: list[str] | None = None,
    languages: list[str] | None = None,
) -> list[Scenario]:
    """Apply category/tag/language filters. Empty filters mean 'no constraint'."""
    out = scenarios
    if categories:
        out = [s for s in out if s.category in categories]
    if tags:
        out = [s for s in out if any(t in s.tags for t in tags)]
    if languages:
        out = [s for s in out if s.language in languages]
    return out
