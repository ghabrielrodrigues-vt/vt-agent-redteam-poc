"""Tests for the corpus loader."""

from __future__ import annotations

from vt_agent_redteam.corpus import CORPUS_DIR, filter_scenarios, load_corpus


def test_corpus_loads_without_error():
    scenarios = load_corpus(CORPUS_DIR)
    assert len(scenarios) > 0


def test_every_scenario_has_required_fields():
    scenarios = load_corpus(CORPUS_DIR)
    for s in scenarios:
        assert s.id, f"Scenario missing id: {s}"
        assert s.category, f"Scenario {s.id} missing category"
        assert s.language in ("en", "pt", "es"), f"Scenario {s.id} has unknown language {s.language}"
        assert s.turns, f"Scenario {s.id} has no turns"
        assert isinstance(s.tags, list)


def test_scenario_ids_are_unique():
    scenarios = load_corpus(CORPUS_DIR)
    ids = [s.id for s in scenarios]
    assert len(ids) == len(set(ids)), f"Duplicate scenario IDs: {sorted(ids)}"


def test_filter_by_category():
    scenarios = load_corpus(CORPUS_DIR)
    violence_only = filter_scenarios(scenarios, categories=["violence"])
    assert all(s.category == "violence" for s in violence_only)
    assert len(violence_only) > 0


def test_filter_by_tag():
    scenarios = load_corpus(CORPUS_DIR)
    smoke = filter_scenarios(scenarios, tags=["smoke"])
    assert all("smoke" in s.tags for s in smoke)
    assert len(smoke) >= 10, "smoke set should be at least 10 scenarios"


def test_filter_by_language():
    scenarios = load_corpus(CORPUS_DIR)
    pt_only = filter_scenarios(scenarios, languages=["pt"])
    assert all(s.language == "pt" for s in pt_only)
    assert len(pt_only) > 0, "should have at least one PT scenario"


def test_filter_combinations_intersect():
    scenarios = load_corpus(CORPUS_DIR)
    en_smoke = filter_scenarios(scenarios, languages=["en"], tags=["smoke"])
    for s in en_smoke:
        assert s.language == "en"
        assert "smoke" in s.tags


def test_corpus_covers_critical_categories():
    """All OpenAI Moderation categories plus LiveKit-specific failure modes."""
    scenarios = load_corpus(CORPUS_DIR)
    categories = {s.category for s in scenarios}
    expected = {
        "violence", "sexual", "self_harm", "hate", "harassment", "illicit",
        "jailbreak", "prompt_leakage", "education_specific",
    }
    missing = expected - categories
    assert not missing, f"Corpus missing categories: {missing}"


def test_corpus_covers_k12_content_policy():
    """Every rule in the Nerdy Tutor K-12 CONTENT_MODERATION_PROMPT
    (student-onboarding-orchestration/lib/ai/moderation.ts) must be
    represented in at least one corpus category.
    """
    scenarios = load_corpus(CORPUS_DIR)
    categories = {s.category for s in scenarios}
    k12_required = {
        "politics",                # Modern politicians + elections + 'woke'
        "forbidden_topics",        # Gaza, abortion, climate, COVID, sexuality, transgenderism
        "dating_romance",          # No dating/romance roleplay
        "brand_protection",        # No negative content about VT/Nerdy
        "stakeholder_protection",  # No negative content about student/parent/teacher/school
        "off_topic_academic",      # K-12 academic only
        "diversity_framing",       # No unprompted DEI framing
        "cheating_integrity",      # No cheat instructions
    }
    missing = k12_required - categories
    assert not missing, f"Corpus missing K-12 policy categories: {missing}"


def test_corpus_covers_academic_extensions():
    """OWASP LLM Top 10 + NIST AI RMF derived categories."""
    scenarios = load_corpus(CORPUS_DIR)
    categories = {s.category for s in scenarios}
    extensions = {
        "personal_information",     # OWASP LLM02 + FERPA
        "misinformation",           # OWASP LLM09
        "medical_legal_advice",     # NIST safety
        "impersonation",            # MITRE ATLAS identity
        "emotional_manipulation",   # NIST safety / child-development
    }
    missing = extensions - categories
    assert not missing, f"Corpus missing academic-extension categories: {missing}"


def test_each_category_has_at_least_three_scenarios():
    """Quality bar: every category we ship must have 3+ scenarios for any
    meaningful coverage."""
    scenarios = load_corpus(CORPUS_DIR)
    by_category: dict[str, int] = {}
    for s in scenarios:
        by_category[s.category] = by_category.get(s.category, 0) + 1
    thin = {k: v for k, v in by_category.items() if v < 3}
    assert not thin, f"Categories with fewer than 3 scenarios: {thin}"
