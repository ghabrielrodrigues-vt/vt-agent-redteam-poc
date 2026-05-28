"""Writes scenario results to Postgres via psycopg.

This is the primary writer for v0.0.2 — it works against both:
- Local Postgres (this prototype, via docker compose)
- Supabase projects (Supabase is Postgres + extras; the SQL is identical)

Configuration via env:
    REDTEAM_DB_URL  (full URL, takes precedence)
or:
    REDTEAM_DB_HOST, REDTEAM_DB_PORT, REDTEAM_DB_USER, REDTEAM_DB_PASSWORD,
    REDTEAM_DB_NAME

Defaults match livekit-local/postgres-compose.yml so the prototype runs without
any env tweaks against the local stack.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any

import psycopg
from rich import print as rprint

from vt_agent_redteam.types import ScenarioResult


@dataclass
class PostgresConfig:
    url: str | None = None
    host: str = "localhost"
    port: int = 54322
    user: str = "redteam"
    password: str = "redteam-local"
    dbname: str = "redteam"

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        url = os.environ.get("REDTEAM_DB_URL")
        if url:
            return cls(url=url)
        return cls(
            host=os.environ.get("REDTEAM_DB_HOST", "localhost"),
            port=int(os.environ.get("REDTEAM_DB_PORT", "54322")),
            user=os.environ.get("REDTEAM_DB_USER", "redteam"),
            password=os.environ.get("REDTEAM_DB_PASSWORD", "redteam-local"),
            dbname=os.environ.get("REDTEAM_DB_NAME", "redteam"),
        )

    def conninfo(self) -> str:
        if self.url:
            return self.url
        return (
            f"host={self.host} port={self.port} user={self.user} "
            f"password={self.password} dbname={self.dbname}"
        )


_INSERT_SQL = """
insert into redteam.redteam_runs (
  run_id, agent_name, agent_commit_sha, agent_environment,
  scenario_category, scenario_id, adversarial_prompt, agent_response,
  scorer_results, passed, failure_reason,
  triggered_by, pr_number, workflow_run_id,
  usd_cost_estimate,
  is_stub_response, transcript_source, response_hash, artifact_uri,
  timeout_flag, retry_count, threshold_passed, run_summary
) values (
  %(run_id)s, %(agent_name)s, %(agent_commit_sha)s, %(agent_environment)s,
  %(scenario_category)s, %(scenario_id)s, %(adversarial_prompt)s, %(agent_response)s,
  %(scorer_results)s, %(passed)s, %(failure_reason)s,
  %(triggered_by)s, %(pr_number)s, %(workflow_run_id)s,
  %(usd_cost_estimate)s,
  %(is_stub_response)s, %(transcript_source)s, %(response_hash)s, %(artifact_uri)s,
  %(timeout_flag)s, %(retry_count)s, %(threshold_passed)s, %(run_summary)s
)
"""


class PostgresWriter:
    def __init__(self, config: PostgresConfig | None = None, *, dry_run: bool = False) -> None:
        self.config = config or PostgresConfig.from_env()
        self.dry_run = dry_run

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
        threshold_passed: bool | None = None,
        run_summary: dict[str, Any] | None = None,
    ) -> int:
        rows: list[dict[str, Any]] = []
        for idx, r in enumerate(results):
            # Per spec: run_summary is attached only to the LAST row of the
            # run so joined queries can fetch it without de-duplication.
            row_summary = (
                json.dumps(run_summary)
                if run_summary is not None and idx == len(results) - 1
                else None
            )
            rows.append({
                "run_id": str(run_id),
                "agent_name": agent_name,
                "agent_commit_sha": agent_commit_sha,
                "agent_environment": agent_environment,
                "scenario_category": r.category,
                "scenario_id": r.scenario_id,
                "adversarial_prompt": "\n---\n".join(r.adversarial_prompts),
                "agent_response": "\n---\n".join(r.agent_responses),
                "scorer_results": json.dumps([sr.model_dump() for sr in r.scorer_results]),
                "passed": r.passed,
                "failure_reason": r.failure_reason,
                "triggered_by": triggered_by,
                "pr_number": pr_number,
                "workflow_run_id": workflow_run_id,
                "usd_cost_estimate": r.usd_cost_estimate,
                "is_stub_response": r.is_stub_response,
                "transcript_source": r.transcript_source,
                "response_hash": r.response_hash,
                "artifact_uri": r.artifact_uri,
                "timeout_flag": r.timeout_flag,
                "retry_count": r.retry_count,
                # Stub-row guarantee: threshold_passed is null for any row
                # where the response is a stub (cannot meaningfully enforce).
                "threshold_passed": (
                    None if r.is_stub_response else threshold_passed
                ),
                "run_summary": row_summary,
            })

        if self.dry_run:
            rprint(
                f"[yellow]DRY-RUN[/yellow] Would insert {len(rows)} row(s) into "
                "redteam.redteam_runs."
            )
            for row in rows[:3]:
                preview = {k: row[k] for k in ("scenario_id", "passed", "failure_reason")}
                rprint(json.dumps(preview, default=str, indent=2))
            if len(rows) > 3:
                rprint(f"... and {len(rows) - 3} more.")
            return len(rows)

        with psycopg.connect(self.config.conninfo()) as conn:
            with conn.cursor() as cur:
                cur.executemany(_INSERT_SQL, rows)
            conn.commit()
        rprint(
            f"[green]✓[/green] Inserted {len(rows)} row(s) into redteam.redteam_runs "
            f"(run_id={run_id})"
        )
        return len(rows)
