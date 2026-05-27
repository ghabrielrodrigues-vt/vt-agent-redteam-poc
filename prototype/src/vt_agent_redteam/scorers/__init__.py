"""Scorer implementations and registry."""

from vt_agent_redteam.scorers.base import Scorer
from vt_agent_redteam.scorers.expected_verdict_scorer import ExpectedVerdictScorer
from vt_agent_redteam.scorers.forbidden_topics_detector import ForbiddenTopicsDetector
from vt_agent_redteam.scorers.openai_moderation import OpenAIModeration
from vt_agent_redteam.scorers.prompt_leak_detector import PromptLeakDetector
from vt_agent_redteam.scorers.refusal_detector import RefusalDetector


def default_scorers() -> list[Scorer]:
    """The v0.0.3 scorer set — adds forbidden-topics keyword detection
    on top of the v0.1 trio.
    """
    return [
        RefusalDetector(),
        PromptLeakDetector(),
        ForbiddenTopicsDetector(),
        OpenAIModeration(),
    ]


def http_moderation_scorers() -> list[Scorer]:
    """Scorer set for `--mode http-moderation` (Option B).

    Refusal/prompt-leak detectors do not apply: the moderation API returns a
    JSON verdict object, not natural-language agent prose. The
    `ExpectedVerdictScorer` is the primary signal; the forbidden-topics regex
    detector still catches forbidden-topic strings that surface in the
    censored output; OpenAI Moderation gives a second independent opinion.
    """
    return [
        ExpectedVerdictScorer(),
        ForbiddenTopicsDetector(),
        OpenAIModeration(),
    ]


__all__ = [
    "Scorer",
    "RefusalDetector",
    "PromptLeakDetector",
    "ForbiddenTopicsDetector",
    "OpenAIModeration",
    "ExpectedVerdictScorer",
    "default_scorers",
    "http_moderation_scorers",
]
