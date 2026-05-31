"""Load adversarial scenarios from YAML corpus files."""

from __future__ import annotations

from pathlib import Path

import yaml

from vt_agent_redteam.types import Scenario


def bucket_for_category(category: str) -> str:
    """Mirror the Postgres `category_bucket` generated column in Python."""
    if category in {"violence", "sexual", "self_harm", "hate", "harassment"}:
        return "content_safety"
    if category in {
        "politics", "forbidden_topics", "dating_romance",
        "diversity_framing", "off_topic_academic",
    }:
        return "policy_compliance"
    if category in {
        "personal_information", "cheating_integrity", "prompt_leakage",
        "brand_protection", "impersonation", "stakeholder_protection",
        "emotional_manipulation", "misinformation", "medical_legal_advice",
        "illicit", "jailbreak",
    }:
        return "privacy_integrity"
    return "other"


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
    buckets: list[str] | None = None,
    tags: list[str] | None = None,
    exclude_tags: list[str] | None = None,
    languages: list[str] | None = None,
) -> list[Scenario]:
    """Apply category/tag/language filters. Empty filters mean 'no constraint'."""
    out = scenarios
    if categories:
        out = [s for s in out if s.category in categories]
    if buckets:
        out = [s for s in out if bucket_for_category(s.category) in buckets]
    if tags:
        out = [s for s in out if any(t in s.tags for t in tags)]
    if exclude_tags:
        out = [s for s in out if not any(t in s.tags for t in exclude_tags)]
    if languages:
        out = [s for s in out if s.language in languages]
    return out
