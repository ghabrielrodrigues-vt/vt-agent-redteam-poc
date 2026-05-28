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
  workflow_run_id     text,
  -- Cost tracking (USD estimate per scenario; sum per run_id for budgeting)
  usd_cost_estimate   numeric(10,4),
  -- Provenance + quality columns (Phase 1; addresses boss-review blockers)
  is_stub_response    boolean not null default true,
  transcript_source   text,            -- stub_canned, livekit_audio, direct_llm, etc.
  response_hash       text,            -- deterministic fingerprint for dedupe
  artifact_uri        text,            -- pointer to captured WAV / raw transcript
  timeout_flag        boolean not null default false,
  retry_count         int not null default 0,
  threshold_passed    boolean,         -- nullable: null = could not enforce (stubs)
  run_summary         jsonb,           -- attached at last row of run; null elsewhere
  -- High-level bucket for exec dashboards (generated from scenario_category)
  category_bucket     text generated always as (case
    when scenario_category in
      ('violence','sexual','self_harm','hate','harassment')
        then 'content_safety'
    when scenario_category in
      ('politics','forbidden_topics','dating_romance','diversity_framing','off_topic_academic')
        then 'policy_compliance'
    when scenario_category in
      ('personal_information','cheating_integrity','prompt_leakage','brand_protection',
       'impersonation','stakeholder_protection','emotional_manipulation','misinformation',
       'medical_legal_advice','illicit','jailbreak')
        then 'privacy_integrity'
    else 'other'
  end) stored
);

-- Aggregated views for dashboards.
-- IMPORTANT: stubbed rows (is_stub_response = true) are excluded from
-- summary-level safety dashboards by default. Use the *_with_stubs views
-- (defined below) when you specifically need to inspect stub behavior.
create or replace view redteam.pass_rate_by_bucket as
select
  agent_name,
  agent_environment,
  category_bucket,
  date_trunc('week', created_at) as week,
  count(*) filter (where passed) * 100.0 / nullif(count(*), 0) as pass_rate_pct,
  count(*) as scenarios,
  sum(usd_cost_estimate) as week_cost_usd
from redteam.redteam_runs
where is_stub_response = false
group by 1, 2, 3, 4;

create or replace view redteam.pass_rate_by_bucket_with_stubs as
select
  agent_name,
  agent_environment,
  category_bucket,
  date_trunc('week', created_at) as week,
  is_stub_response,
  count(*) filter (where passed) * 100.0 / nullif(count(*), 0) as pass_rate_pct,
  count(*) as scenarios
from redteam.redteam_runs
group by 1, 2, 3, 4, 5;

create or replace view redteam.recent_failures as
select
  agent_name,
  scenario_category,
  scenario_id,
  failure_reason,
  agent_response,
  created_at,
  pr_number,
  workflow_run_id
from redteam.redteam_runs
where passed = false
order by created_at desc
limit 200;

create or replace view redteam.cost_by_run as
select
  run_id,
  agent_name,
  agent_environment,
  triggered_by,
  min(created_at) as started_at,
  count(*) as scenarios,
  sum(usd_cost_estimate) as total_usd
from redteam.redteam_runs
group by 1, 2, 3, 4;

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
