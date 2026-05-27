"""Scorer protocol that all scorers implement."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vt_agent_redteam.types import Scenario, ScoreResult


@runtime_checkable
class Scorer(Protocol):
    """A scorer judges whether an agent response to an adversarial prompt is safe."""

    name: str

    def score(
        self,
        scenario: Scenario,
        response: str,
        context: dict | None = None,
    ) -> ScoreResult: ...
