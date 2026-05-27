"""Persists scenario results to the redteam.redteam_runs Supabase table.

The writer supports two modes:
- live: uses the supabase-py client to insert rows.
- dry: prints what *would* be inserted; no network calls. Used in the prototype and
  by `--dry-run` in CI.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any

from rich import print as rprint

from vt_agent_redteam.types import ScenarioResult


@dataclass
class SupabaseConfig:
    url: str | None
    service_key: str | None

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        return cls(
            url=os.environ.get("SUPABASE_URL"),
            service_key=os.environ.get("SUPABASE_SERVICE_KEY"),
        )

    def is_live(self) -> bool:
        return bool(self.url and self.service_key)


class SupabaseWriter:
    def __init__(self, config: SupabaseConfig | None = None, *, dry_run: bool = False) -> None:
        self.config = config or SupabaseConfig.from_env()
        self.dry_run = dry_run or not self.config.is_live()
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from supabase import create_client
            except ImportError as exc:
                raise RuntimeError(
                    "supabase-py is not installed. Install with: "
                    "pip install 'vt-agent-redteam[supabase]'"
                ) from exc
            self._client = create_client(self.config.url, self.config.service_key)
        return self._client

    def write(
        self,
        *,
        run_id: uuid.UUID,
        agent_name: str,
        agent_commit_sha: str | None,
        agent_environment: str,
        triggered_by: str,
        pr_number: int | None,
        workflow_run_id: str | None,
        results: list[ScenarioResult],
    ) -> int:
        rows = [
            {
                "run_id": str(run_id),
                "agent_name": agent_name,
                "agent_commit_sha": agent_commit_sha,
                "agent_environment": agent_environment,
                "scenario_category": r.category,
                "scenario_id": r.scenario_id,
                "adversarial_prompt": "\n---\n".join(r.adversarial_prompts),
                "agent_response": "\n---\n".join(r.agent_responses),
                "scorer_results": [sr.model_dump() for sr in r.scorer_results],
                "passed": r.passed,
                "failure_reason": r.failure_reason,
                "triggered_by": triggered_by,
                "pr_number": pr_number,
                "workflow_run_id": workflow_run_id,
            }
            for r in results
        ]

        if self.dry_run:
            rprint(f"[yellow]DRY-RUN[/yellow] Would write {len(rows)} row(s) to redteam.redteam_runs:")
            for row in rows[:3]:  # preview first 3 only
                rprint(json.dumps(row, default=str, indent=2))
            if len(rows) > 3:
                rprint(f"... and {len(rows) - 3} more.")
            return len(rows)

        client = self._get_client()
        client.schema("redteam").table("redteam_runs").insert(rows).execute()
        return len(rows)
