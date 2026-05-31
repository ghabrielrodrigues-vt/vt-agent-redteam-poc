"""vt-agent-redteam — red-team harness for LiveKit-hosted agents."""

__version__ = "0.1.0"

from vt_agent_redteam.harness import RedTeamHarness, RunResult
from vt_agent_redteam.types import Scenario, ScoreResult, ScenarioResult

__all__ = [
    "RedTeamHarness",
    "RunResult",
    "Scenario",
    "ScoreResult",
    "ScenarioResult",
]
