# `vt-agent-redteam` — MVP prototype (v0.0.3)

This folder is the scaffolded Python package proposed in
`../docs/04-poc-design.md` and planned in `../docs/06-implementation-plan.md`.

## What works today (v0.0.3)

- **125 scenarios** across 22 categories with EN + PT variants, covering:
  - **CONTENT_MODERATION_PROMPT (Nerdy Tutor production K-12 policy)** —
    line-by-line: politics, forbidden_topics, dating_romance,
    brand_protection, stakeholder_protection, off_topic_academic,
    diversity_framing, cheating_integrity
  - **Academic extensions** from OWASP LLM Top 10 (2025), NIST AI RMF,
    MITRE ATLAS: personal_information, misinformation,
    medical_legal_advice, impersonation, emotional_manipulation
  - OpenAI Moderation taxonomy + LiveKit failure modes (carried over from
    v0.0.1)
- **4 scorers**: `RefusalDetector` (regex, bilingual EN+PT),
  `PromptLeakDetector` (n-gram overlap), `ForbiddenTopicsDetector`
  (keyword/regex against K-12 forbidden-topic list), `OpenAIModeration`
  (real API calls when `OPENAI_API_KEY` is present, graceful skip otherwise)
- **Two runners**:
  - `LiveKitRoomRunner` (v0.0.1): creates a room, uses bilingual stub agent
    responses. Useful for fast CI / dry-runs.
  - `SyntheticCandidateRunner` (v0.0.2): real-audio path. Synthesises the
    adversarial prompt via local TTS (`say`), publishes as an audio track,
    captures the agent's reply, transcribes via Whisper.
- **Two writers**:
  - `PostgresWriter` (primary): writes via psycopg. Works against the local
    Postgres stack and Supabase projects identically.
  - `SupabaseWriter` (legacy): writes via supabase-py.
- **Mock agent** (`../livekit-local/mock-agent/`): Python worker that joins
  rooms with prefix `interview-redteam-`, reads scenario metadata, publishes a
  canned response WAV. Lets the harness test against real WebRTC + audio
  pipeline without an OpenAI Realtime API key.
- **35 pytest tests** covering corpus loading, K-12 policy coverage,
  academic-extension coverage, scorers (EN+PT, forbidden-topics, brand
  neutrality), schema validation
- **Typer CLI** with four modes:
  - `vt-redteam run --dry-run` — bilingual stubs, no audio (fastest)
  - `vt-redteam run` — creates real rooms, uses fallback canned response
  - `vt-redteam run --audio` — real audio path against the mock agent (or real agent)
  - `vt-redteam run --mode http-moderation` — **Option B**: POST scenario
    text directly at the Nerdy Tutor input-side moderation endpoint
    (`/api/nerd-tutor/moderate-text`) and score the API's `block | mask |
    pass` verdict against each scenario's `expected_moderation_verdict`.
    Uses the `ExpectedVerdictScorer` + `ForbiddenTopicsDetector` +
    `OpenAIModeration` set; refusal/leak detectors do not apply to a JSON
    verdict. Scenarios without `expected_moderation_verdict` are skipped
    with a clear log line. `--dry-run` short-circuits the HTTP call so the
    pipeline can be validated without a live `next dev`.

## Quick start

### Dry-run pipeline (no Docker required beyond LiveKit Server)

```bash
cd ../livekit-local
docker compose up -d                       # LiveKit Server
docker compose -f postgres-compose.yml up -d   # Postgres
cd ../prototype
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e '.[supabase,dev]'
docker exec -i poc-redteam-postgres psql -U redteam -d redteam \
    < src/vt_agent_redteam/storage/schema.sql

vt-redteam list-scenarios                  # 49 scenarios
vt-redteam run --tags smoke --dry-run      # ~16 scenarios in <2s
vt-redteam run --tags smoke --write-results   # writes real rows to Postgres
```

### Real audio path (Mock agent in another terminal)

```bash
# Terminal 1: generate mock response WAVs once, then run the mock agent worker
cd ../livekit-local/mock-agent
./generate-mock-responses.sh
python mock_agent.py --verbose

# Terminal 2: run a single audio scenario
cd ../../prototype
source .venv/bin/activate
set -a && source .env.local && set +a   # OPENAI_API_KEY for Whisper
vt-redteam run --audio --category violence --tags smoke
```

The candidate side synthesises the prompt with `say`, publishes it into the
room, subscribes to the mock agent's audio track, captures until silence,
transcribes the captured WAV with OpenAI Whisper, then runs scorers against
the transcript.

## Layout

```
prototype/
├── pyproject.toml
├── README.md
├── .gitignore                              ← excludes .env.local, .venv, etc.
└── src/vt_agent_redteam/
    ├── __init__.py
    ├── cli.py                              ← Typer CLI
    ├── harness.py                          ← orchestration
    ├── types.py                            ← Pydantic models
    ├── corpus/                             ← 9 YAML files, 49 scenarios
    ├── scorers/                            ← base + 3 implementations
    ├── runners/
    │   ├── livekit_room.py                 ← stub runner (v0.0.1)
    │   └── synthetic_candidate.py          ← real audio runner (v0.0.2)
    ├── audio/                              ← TTS, publish, collect (v0.0.2)
    │   ├── tts_local.py
    │   ├── wav_publisher.py
    │   └── wav_collector.py
    └── storage/
        ├── schema.sql
        ├── postgres_writer.py              ← v0.0.2 primary writer
        └── supabase_writer.py              ← legacy
tests/                                       ← 24 pytest tests
```

## What is intentionally deferred to v0.1

- **LLM-as-judge** layer on top of the refusal heuristic (the design has it; v0.0.2 ships only the regex path)
- **3x replay** per scenario for non-determinism mitigation
- **Real `livekit-agents` integration** (requires an active OpenAI Realtime API key on the agent side and a few wiring tweaks; today the audio path validates against the mock agent)
- **GitHub Actions workflow** for the consuming `livekit-agents` repo
- **Promptfoo-generated scenarios** committed to the corpus

These are documented in `../docs/06-implementation-plan.md` §8.

## Relationship to the docs

| Doc | What it maps to |
| --- | --- |
| `../docs/04-poc-design.md` §Public API | `vt_agent_redteam.RedTeamHarness` |
| `../docs/04-poc-design.md` §Lifecycle | `runners/synthetic_candidate.py` |
| `../docs/04-poc-design.md` §Supabase schema | `src/.../storage/schema.sql` |
| `../docs/05-moderation-connection.md` §Corpus | `src/.../corpus/education_specific.yaml` |
| `../docs/06-implementation-plan.md` §MVP DoD | this README's "What works today" section |
