"""Top-level orchestration: corpus → runner → scorers → storage."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field

from rich import print as rprint
from rich.console import Console
from rich.table import Table

from vt_agent_redteam.runners import (
    HttpModerationRunner,
    LiveKitRoomRunner,
    SyntheticCandidateRunner,
)
from vt_agent_redteam.scorers import Scorer
from vt_agent_redteam.storage import SupabaseWriter
from vt_agent_redteam.types import AgentConfig, Scenario, ScenarioResult, ScoreResult


@dataclass
class RunResult:
    run_id: uuid.UUID
    scenario_results: list[ScenarioResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.scenario_results:
            return 1.0
        passed = sum(1 for r in self.scenario_results if r.passed)
        return passed / len(self.scenario_results)

    @property
    def num_failed(self) -> int:
        return sum(1 for r in self.scenario_results if not r.passed)

    def failure_summary(self) -> str:
        lines = [f"{r.scenario_id}: {r.failure_reason or 'failed'}"
                 for r in self.scenario_results if not r.passed]
        return "\n".join(lines) if lines else "(no failures)"


class RedTeamHarness:
    """End-to-end orchestrator. Composes a runner, scorers, and a writer."""

    def __init__(
        self,
        runner: LiveKitRoomRunner | SyntheticCandidateRunner | HttpModerationRunner,
        scorers: list[Scorer],
        writer: SupabaseWriter | None = None,
    ) -> None:
        self.runner = runner
        self.scorers = scorers
        self.writer = writer

    async def run(
        self,
        *,
        scenarios: list[Scenario],
        agent: AgentConfig,
        agent_environment: str = "local",
        agent_commit_sha: str | None = None,
        triggered_by: str = "manual",
        pr_number: int | None = None,
        workflow_run_id: str | None = None,
    ) -> RunResult:
        run_id = uuid.uuid4()
        console = Console()
        console.rule(f"[bold]Red-team run {run_id}[/bold]")
        console.print(
            f"agent=[cyan]{agent.name}[/cyan]  scenarios=[cyan]{len(scenarios)}[/cyan]  "
            f"env=[cyan]{agent_environment}[/cyan]"
        )

        results: list[ScenarioResult] = []
        for scenario in scenarios:
            console.print(f"\n[bold]→[/bold] {scenario.id}  [dim]({scenario.category})[/dim]")
            start = time.perf_counter()
            dispatch = await self.runner.run_scenario(scenario, agent)
            for note in dispatch.notes:
                console.print(f"  [dim]· {note}[/dim]")

            response = dispatch.agent_response_transcript
            context = {"known_system_prompt": agent.known_system_prompt}

            scorer_results: list[ScoreResult] = []
            for scorer in self.scorers:
                sr = scorer.score(scenario, response, context)
                scorer_results.append(sr)
                marker = "[green]PASS[/green]" if sr.passed else "[red]FAIL[/red]"
                console.print(f"  {marker} {sr.scorer_name}: {sr.reasoning}")

            passed = all(s.passed for s in scorer_results)
            failure_reason = (
                None
                if passed
                else "; ".join(s.reasoning or s.scorer_name
                               for s in scorer_results if not s.passed)
            )
            elapsed = time.perf_counter() - start

            results.append(
                ScenarioResult(
                    scenario_id=scenario.id,
                    category=scenario.category,
                    adversarial_prompts=scenario.turns,
                    agent_responses=[response],
                    scorer_results=scorer_results,
                    passed=passed,
                    failure_reason=failure_reason,
                    duration_seconds=elapsed,
                )
            )

        run_result = RunResult(run_id=run_id, scenario_results=results)
        self._print_summary(console, run_result)

        if self.writer is not None:
            written = self.writer.write(
                run_id=run_id,
                agent_name=agent.name,
                agent_commit_sha=agent_commit_sha,
                agent_environment=agent_environment,
                triggered_by=triggered_by,
                pr_number=pr_number,
                workflow_run_id=workflow_run_id,
                results=results,
            )
            rprint(f"[dim]Wrote {written} row(s) to storage.[/dim]")

        return run_result

    def _print_summary(self, console: Console, run: RunResult) -> None:
        table = Table(title=f"Run summary  (pass rate: {run.pass_rate:.0%})")
        table.add_column("Scenario", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Result")
        table.add_column("Time", justify="right")
        for r in run.scenario_results:
            verdict = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
            table.add_row(r.scenario_id, r.category, verdict, f"{r.duration_seconds:.2f}s")
        console.print()
        console.print(table)
        if run.num_failed:
            console.print(f"\n[red bold]{run.num_failed} failure(s)[/red bold]")
            console.print(run.failure_summary())
