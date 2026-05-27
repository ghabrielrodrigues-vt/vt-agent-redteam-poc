# SETUP — Secrets You Must Configure Before Running

This repo contains **zero real credentials**. Every secret-shaped string
in source files is a placeholder (`sk-replace-me`, `sk-...your-key...`,
etc.). Before any local run, copy the templates below and fill them in.

## Required: OpenAI API key

Used by:
- The `OpenAIModeration` scorer in `prototype/src/vt_agent_redteam/scorers/openai_moderation.py`
- The synthetic-candidate Whisper transcription in `prototype/src/vt_agent_redteam/runners/synthetic_candidate.py`
- The Promptfoo redteam generator (`promptfoo/`)
- The PyRIT Crescendo demo (`pyrit/crescendo_demo.py`)
- The real `livekit-agents` TS worker (OpenAI Realtime API)

### Steps

```bash
# 1. Python harness env
cp prototype/.env.template prototype/.env.local
# Edit prototype/.env.local and replace `sk-replace-me` with your real OpenAI key.

# 2. Promptfoo generator (reads from process env, not a file)
export OPENAI_API_KEY=sk-...your-real-key...

# 3. PyRIT demo reads the same env. After `set -a && source prototype/.env.local && set +a`
#    the export above is automatic.

# 4. (Optional) Real livekit-agents TS worker
# The Option D path requires its own .env.local. Pattern provided in
# REAL_AGENT_PROOF.md inside livekit-local/livekit-agents/ (when that
# folder is present locally; it is gitignored).
```

## Required if running the real LiveKit agent (Option D)

The `varsitytutors/livekit-agents` repo is **not** cloned into this
project — it is gitignored at `livekit-local/livekit-agents/` because of
its size (1.7 GB of `node_modules`) and because the upstream repo is the
source of truth. To run Option D:

```bash
cd livekit-local
git clone git@github.com:varsitytutors/livekit-agents.git
cd livekit-agents
npm install
# Create .env.local with the local LiveKit + OpenAI vars
cat > .env.local <<'EOF'
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
OPENAI_API_KEY=sk-...your-real-key...
GOOGLE_API_KEY=unused-local-dev
NODE_ENV=development
LOG_LEVEL=info
OTEL_ENABLED=false
LANGFUSE_PUBLIC_KEY=pk-lf-local-dev-dummy
LANGFUSE_SECRET_KEY=sk-lf-local-dev-dummy
LANGFUSE_BASEURL=http://localhost:39999
DISABLE_EGRESS=true
EOF
# Apply the one-line guard to src/lib/egress.ts (see REAL_AGENT_PROOF.md)
bash run-local.sh
```

## Required if running HTTP moderation runner (Option B)

The `student-onboarding-orchestration` Next.js dev server must be
running on `http://localhost:3000` against a branch that ships the
`/api/nerd-tutor/moderate-text` endpoint (e.g.
`vt4s-10659-nerdy-tutor-moderation-plus`, PR #1667). That repo and its
Supabase + Stripe + Posthog credentials are out of scope here.

## Required if running the Promptfoo generator

The first run of `promptfoo redteam generate` prompts for an email to
verify against Promptfoo Cloud TOS:

```bash
cd promptfoo
echo "your-email@varsitytutors.com" | npm run generate
```

## Supabase / Postgres

The local stack uses dev credentials in `livekit-local/postgres-compose.yml`
(`user=redteam` / `password=redteam-local`). These are intentionally
weak and local-only. **Do not use against any production database.**

For production `vt4s-supabase`, real credentials must come from the VT
secret store; the writer (`prototype/.../storage/postgres_writer.py`)
reads `REDTEAM_DB_URL` or `REDTEAM_DB_HOST` env vars.

## Quick verification that you have all secrets

```bash
cd prototype
source .venv/bin/activate
set -a && source .env.local && set +a
python -c "import os; assert os.environ.get('OPENAI_API_KEY', '').startswith('sk-') and not os.environ['OPENAI_API_KEY'].startswith('sk-replace'), 'OPENAI_API_KEY missing or still placeholder'"
echo "Secrets OK"
```

If that prints `Secrets OK`, the package can run end-to-end (subject to
local Docker services being up — see `livekit-local/README.md`).
