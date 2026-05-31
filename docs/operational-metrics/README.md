# Phase-End Operational Metrics

## Purpose

Every implementation phase must end with operational validation, not only
feature acceptance. The dashboard reads `status.json` from this directory and
shows the current evidence level for cost, latency, scalability, reliability,
API-outage behavior, and bottlenecks.

## Required Checks Per Phase

Each phase-end review must answer:

- **Cost:** What did the run cost? Did it stay below budget? Did the
  `max_cost_usd_per_run` guardrail abort runaway execution?
- **Latency:** What are p50/p95 run and scenario durations? Does the run stay
  inside `scenario_timeout_seconds`?
- **Scalability:** What happens when many checks run at the same time? Which
  concurrency level was tested?
- **Reliability:** What proves the service still works after the phase changes?
  Which deterministic, integration, and E2E tests passed?
- **API outage:** What happens when Langfuse, OpenAI, LiveKit, Postgres, or
  Slack does not respond?
- **Bottlenecks:** What slows or limits the system: Langfuse polling, LiveKit
  room creation, OpenAI scoring, database writes, workflow fan-out, or dashboard
  generation?

## Evidence Rule

Update `status.json` after each phase. A phase is not operationally closed until
all six checks are measured or explicitly triaged as a release blocker or
post-v0 backlog item.

## Current Known Behavior

- Langfuse trace lookup uses bounded polling with exponential backoff. If no
  trace appears, the runner returns a stub-marked timeout result so the gate does
  not silently treat missing evidence as a valid pass.
- OpenAI Moderation scorer currently treats API failure as inconclusive/pass.
  This is a reliability risk that needs explicit triage before final release.
- LiveKit, Postgres/Supabase, and Slack outage behavior must be measured during
  Phase 1B/1C integration. Do not assume these paths are safe until evidence is
  captured.
- The harness currently runs scenarios sequentially inside one process. Workflow
  fan-out can parallelize by agent/job, but scenario-level concurrency has not
  yet been load-tested.
- Cost is summarized in `run_summary.json`, but the cost guardrail still needs
  an integration test that proves `max_cost_usd_per_run` aborts runaway runs.
