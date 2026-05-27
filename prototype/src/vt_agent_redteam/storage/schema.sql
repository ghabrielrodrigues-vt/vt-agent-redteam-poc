-- Supabase schema for vt-agent-redteam run results.
-- Lives in the `redteam` schema of the shared VT4S Supabase project.

create schema if not exists redteam;

create table if not exists redteam.redteam_runs (
  id                  uuid primary key default gen_random_uuid(),
  run_id              uuid not null,
  agent_name          text not null,
  agent_commit_sha    text,
  agent_environment   text not null check (agent_environment in
                        ('local', 'staging', 'production-canary')),
  scenario_category   text not null,
  scenario_id         text not null,
  adversarial_prompt  text not null,
  agent_response      text not null,
  scorer_results      jsonb not null default '{}'::jsonb,
  passed              boolean not null,
  failure_reason      text,
  created_at          timestamptz not null default now(),
  triggered_by        text not null check (triggered_by in
                        ('pr', 'deploy', 'weekly_canary', 'manual')),
  pr_number           int,
  workflow_run_id     text
);

create index if not exists idx_redteam_runs_agent_created
  on redteam.redteam_runs (agent_name, created_at desc);

create index if not exists idx_redteam_runs_run_id
  on redteam.redteam_runs (run_id);

create index if not exists idx_redteam_runs_failures
  on redteam.redteam_runs (passed, agent_name, created_at desc)
  where passed = false;

comment on table redteam.redteam_runs is
  'One row per scenario execution. A "run" (run_id) groups all scenarios from one '
  'invocation of the harness (a PR check, a deploy gate, a weekly canary, etc.).';
