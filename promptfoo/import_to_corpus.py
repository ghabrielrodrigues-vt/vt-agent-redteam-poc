#!/usr/bin/env python3.13
"""Convert Promptfoo `redteam generate` YAML output into our corpus format.

Usage:
    python3.13 import_to_corpus.py <promptfoo_output.yaml> <target_corpus.yaml>
    python3.13 import_to_corpus.py <promptfoo_output.yaml> <target> --preview

In preview mode, prints the converted YAML to stdout without writing it,
so a human can review before committing.

Workflow:
  1. `npm run generate` produces `generated/raw-output.yaml`
  2. `npm run preview` prints the converted scenarios for review
  3. `npm run import` writes to corpus/promptfoo_generated.yaml
  4. Reviewer edits / prunes that file by hand, then commits
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml


# Promptfoo plugin id → our corpus category
PLUGIN_TO_CATEGORY: dict[str, str] = {
    # K-12 compliance plugins (FERPA + COPPA both surface PII issues)
    "ferpa": "personal_information",
    "coppa": "personal_information",
    # Harmful content
    "harmful:child-exploitation": "sexual",
    "harmful:child-safety": "sexual",
    "harmful:hate": "hate",
    "harmful:insults": "harassment",
    "harmful:graphic-content": "violence",
    "harmful:violent-crime": "violence",
    "harmful:self-harm": "self_harm",
    "harmful:misinformation-disinformation": "misinformation",
    "harmful:copyright-violations": "cheating_integrity",
    "harmful:intellectual-property": "cheating_integrity",
    "harmful:cybercrime": "illicit",
    "harmful:illegal-drugs": "illicit",
    "harmful:illegal-activities": "illicit",
    "harmful:harassment-bullying": "harassment",
    "harmful:privacy": "personal_information",
    # PII
    "pii": "personal_information",
    "pii:direct": "personal_information",
    "pii:session": "personal_information",
    "pii:social": "personal_information",
    "pii:api-db": "personal_information",
    # Jailbreak / injection — treated as strategies in Promptfoo, but show up as categories sometimes
    "jailbreak": "jailbreak",
    "prompt-injection": "jailbreak",
    # Brand
    "competitors": "brand_protection",
    # Behavioral
    "overreliance": "emotional_manipulation",
    "excessive-agency": "impersonation",
    "hallucination": "misinformation",
    # Politics / forbidden topics
    "politics": "politics",
    "religion": "forbidden_topics",
    "bias:age": "hate",
    "bias:race": "hate",
    "bias:gender": "hate",
    "bias:disability": "hate",
}

# Promptfoo strategy → tag we apply
STRATEGY_TO_TAG: dict[str, str] = {
    "basic": "promptfoo-basic",
    "jailbreak:meta": "promptfoo-jailbreak-meta",
    "jailbreak:composite": "promptfoo-jailbreak-composite",
    "multi-turn": "promptfoo-multi-turn",
}


def _slugify(text: str, max_len: int = 50) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    text = text.strip("-")[:max_len]
    return text or "scenario"


def _resolve_category(metadata: dict[str, Any]) -> str:
    """Pick a corpus category from the Promptfoo metadata."""
    plugin = metadata.get("pluginId") or metadata.get("plugin") or ""
    if plugin in PLUGIN_TO_CATEGORY:
        return PLUGIN_TO_CATEGORY[plugin]
    # Try matching a prefix (e.g. "harmful:hate-targeted" → harmful:hate)
    for known, cat in PLUGIN_TO_CATEGORY.items():
        if plugin.startswith(known):
            return cat
    # Fallback — use the literal Promptfoo category if mapped, else `jailbreak`
    return metadata.get("category", "jailbreak")


def _extract_prompt(test: dict[str, Any]) -> str | None:
    """Promptfoo generated tests put the prompt under `vars.prompt` (or
    whatever `injectVar` is). Some plugins put it under different keys.
    """
    vars_block = test.get("vars") or {}
    for key in ("prompt", "query", "input", "question", "message"):
        if key in vars_block and isinstance(vars_block[key], str):
            return vars_block[key].strip()
    # Fallback: if vars has exactly one string value, use it
    string_values = [v for v in vars_block.values() if isinstance(v, str)]
    if len(string_values) == 1:
        return string_values[0].strip()
    return None


def _derive_id(index: int, category: str, prompt: str) -> str:
    slug = _slugify(prompt, max_len=40)
    return f"pf-{category}-{slug}-{index:03d}"


def _strategy_tag(metadata: dict[str, Any]) -> str | None:
    strategy = metadata.get("strategyId") or metadata.get("strategy")
    if not strategy:
        return None
    return STRATEGY_TO_TAG.get(strategy, f"promptfoo-{_slugify(strategy)}")


def convert(promptfoo_yaml: dict[str, Any]) -> list[dict[str, Any]]:
    tests = promptfoo_yaml.get("tests") or []
    out: list[dict[str, Any]] = []
    for i, test in enumerate(tests, start=1):
        prompt = _extract_prompt(test)
        if not prompt:
            continue
        metadata = test.get("metadata") or {}
        category = _resolve_category(metadata)
        tags = ["full", "promptfoo-generated"]
        strategy_tag = _strategy_tag(metadata)
        if strategy_tag:
            tags.append(strategy_tag)
        plugin_id = metadata.get("pluginId") or metadata.get("plugin") or ""

        scenario = {
            "id": _derive_id(i, category, prompt),
            "category": category,
            "language": metadata.get("language", "en"),
            "tags": tags,
            "turns": [prompt],
            "expected_behavior": {
                "refusal_required": True,
                "must_not_include": [],
            },
            "notes": (
                f"Generated by Promptfoo plugin={plugin_id}. "
                "Reviewer: confirm category mapping and prune duplicates "
                "before committing. Strategy: "
                f"{metadata.get('strategyId', 'basic')}."
            ),
        }
        out.append(scenario)
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    source = Path(argv[1])
    target = Path(argv[2])
    preview = "--preview" in argv

    if not source.exists():
        print(f"ERROR: source file not found: {source}", file=sys.stderr)
        return 1

    with source.open() as fp:
        raw = yaml.safe_load(fp) or {}

    scenarios = convert(raw)
    if not scenarios:
        print(f"WARNING: no scenarios converted from {source}", file=sys.stderr)
        return 1

    yaml_out = yaml.safe_dump(scenarios, sort_keys=False, allow_unicode=True, width=80)

    if preview:
        print(yaml_out)
        print(f"\n[preview only — would write {len(scenarios)} scenario(s) to {target}]",
              file=sys.stderr)
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml_out)
    print(f"Wrote {len(scenarios)} scenarios to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
