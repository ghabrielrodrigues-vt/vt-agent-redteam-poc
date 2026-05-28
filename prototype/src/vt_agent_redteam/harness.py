"""Top-level orchestration: corpus → runner → scorers → storage."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field

from rich import print as rprint
from rich.console import Console
from rich.table import Table

from typing import Any

from vt_agent_redteam.runners import (
    HttpModerationRunner,
    LiveKitRoomRunner,
    SyntheticCandidateRunner,
)
from vt_agent_redteam.scorers import Scorer
from vt_agent_redteam.storage import SupabaseWriter
from vt_agent_redteam.types import (
    AgentConfig,
    Scenario,
    ScenarioResult,
    ScoreResult,
    TranscriptSource,
)


def _bucket_for(category: str) -> str:
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


def build_run_summary(
    *,
    run_id: uuid.UUID,
    agent: AgentConfig,
    agent_environment: str,
    agent_commit_sha: str | None,
    triggered_by: str,
    workflow_run_id: str | None,
    results: list[ScenarioResult],
    pass_threshold: float | None,
) -> dict[str, Any]:
    """Assemble the run_summary.json payload (matches spike doc schema)."""
    passed_count = sum(1 for r in results if r.passed)
    failed_count = len(results) - passed_count
    pass_rate = passed_count / len(results) if results else 1.0
    is_stub_present = any(r.is_stub_response for r in results)
    threshold_passed: bool | None = None
    if pass_threshold is not None and not is_stub_present:
        threshold_passed = pass_rate >= pass_threshold

    bucket_summary: dict[str, dict[str, int]] = {}
    for r in results:
        b = _bucket_for(r.category)
        bucket_summary.setdefault(b, {"passed": 0, "failed": 0})
        if r.passed:
            bucket_summary[b]["passed"] += 1
        else:
            bucket_summary[b]["failed"] += 1

    failure_summaries = [
        {
            "scenario_id": r.scenario_id,
            "category": r.category,
            "bucket": _bucket_for(r.category),
            "reason": r.failure_reason or "scenario failed",
        }
        for r in results if not r.passed
    ]

    estimated_cost = sum(
        (r.usd_cost_estimate or 0.0) for r in results
    )

    return {
        "run_id": str(run_id),
        "agent_name": agent.name,
        "environment": agent_environment,
        "triggered_by": triggered_by,
        "commit_sha": agent_commit_sha,
        "workflow_run_id": workflow_run_id,
        "scenario_count": len(results),
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate": round(pass_rate, 4),
        "pass_threshold": pass_threshold,
        "threshold_passed": threshold_passed,
        "is_stub_response_present": is_stub_present,
        "bucket_summary": bucket_summary,
        "estimated_cost_usd": round(estimated_cost, 4),
        "failure_summaries": failure_summaries,
    }


@dataclass
class RunResult:
    run_id: uuid.UUID
    scenario_results: list[ScenarioResult] = field(default_factory=list)
    summary: dict[str, Any] | None = None

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
        pass_threshold: float | None = None,
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

            # Pull provenance fields off the dispatch result. Runners that
            # don't set these default to stub_canned + is_stub=True for safety.
            is_stub = getattr(dispatch, "is_stub_response", True)
            transcript_source: TranscriptSource = getattr(
                dispatch, "transcript_source", "stub_canned"
            )
            response_hash = getattr(dispatch, "response_hash", None)
            artifact_uri = getattr(dispatch, "artifact_uri", None)
            usd_cost = getattr(dispatch, "usd_cost_estimate", None)
            timeout_flag = getattr(dispatch, "timeout_flag", False)
            retry_count = getattr(dispatch, "retry_count", 0)

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
                    is_stub_response=is_stub,
                    transcript_source=transcript_source,
                    response_hash=response_hash,
                    artifact_uri=artifact_uri,
                    timeout_flag=timeout_flag,
                    retry_count=retry_count,
                    usd_cost_estimate=usd_cost,
                )
            )

        run_result = RunResult(run_id=run_id, scenario_results=results)
        self._print_summary(console, run_result)

        # Compute run_summary + threshold_passed
        summary = build_run_summary(
            run_id=run_id,
            agent=agent,
            agent_environment=agent_environment,
            agent_commit_sha=agent_commit_sha,
            triggered_by=triggered_by,
            workflow_run_id=workflow_run_id,
            results=results,
            pass_threshold=pass_threshold,
        )
        run_result.summary = summary
        threshold_passed = summary["threshold_passed"]

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
                threshold_passed=threshold_passed,
                run_summary=summary,
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
