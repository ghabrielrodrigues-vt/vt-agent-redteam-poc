# Consolidated Guide — LiveKit Agent Red-Team POC (Promptfoo Edition)

**Start here.** One document for reviewers who should not read fifteen separate
files. Detailed references remain under `docs/` and folder READMEs.

**Repository:** https://github.com/ghabrielrodrigues-vt/vt-agent-redteam-poc

---

## 1. What this is

The **extended spike + working prototype** for reusable red-team testing of
LiveKit-hosted K–12 AI agents (Nerdy Tutor, AI Interviewer, Lemon Slice).

Adds to the base POC:

- **Promptfoo** — automated adversarial scenario *generation* (15 plugins, 3 strategies).
- **PyRIT** — multi-turn attack orchestration (Crescendo demo validated).
- **HTTP moderation runner** — tests Nerdy Tutor `/api/nerd-tutor/moderate-text` directly.
- **Tooling dossier** — comparison of 12 safety tools across a 5-layer architecture.

Target deliverable: Python package `vt-agent-redteam`, plug-and-play for any team
deploying a LiveKit agent.

---

## 2. Two safety layers

| | Nerdy Tutor moderation (production) | Red-team (this POC) |
|---|-------------------------------------|---------------------|
| **When** | Before LLM sees input | After LLM responds |
| **Measures** | User input safety | Agent response safety |
| **Channel** | Text | Voice / avatar |

Input moderation (L1 static → L2 DB → L3 OpenAI, with DB learning loop) stays in
`student-onboarding-orchestration`. This repo tests **output** behavior and can also
**exercise the moderation API** via the HTTP runner.

Diagrams: `docs/09-nerdy-moderation-architecture-diagrams.md`.

---

## 3. What has been validated (evidence)

| # | Path | Evidence |
|---|------|----------|
| 1 | **Pipeline + Postgres** | 40 rows in `redteam.redteam_runs`; 4 scorers parallel |
| 2 | **HTTP moderation** | `vt-redteam run --mode http-moderation --dry-run`; 26 scenarios with `expected_moderation_verdict`; 45/45 pytest |
| 3 | **Real TS worker** | `livekit-agents` registered locally, dispatch accepted, OpenAI Realtime session ~178s — see `docs/10-livekit-real-agent-proof.md` |
| 4 | **PyRIT Crescendo** | 3-turn escalation failed to extract PII; target refused (~$0.03) |

---

## 4. Corpus (195 scenarios)

| Source | Count | Role |
|--------|-------|------|
| Hand-curated YAML | 125 | Seeded from moderation blocklist + OpenAI taxonomy |
| Promptfoo generated | 69 | FERPA, COPPA, jailbreak, brand, copyright, etc. |
| PyRIT Crescendo | 1 | Multi-turn sample |

Coverage: 100% of Nerdy Tutor `CONTENT_MODERATION_PROMPT` lines + OWASP / NIST /
MITRE / FERPA / COPPA extensions. Mapping: `docs/07-corpus-policy-coverage.md`.

---

## 5. Promptfoo workflow (generation only)

Promptfoo does **not** run agents — it **generates** test cases:

```bash
cd promptfoo
npm run generate:small          # → generated/raw-output.yaml (~70 cases)
python import_to_corpus.py      # → corpus/promptfoo_generated.yaml
cd ../prototype
vt-redteam run --tags promptfoo-generated --dry-run
```

**Plugins (15):** ferpa, coppa, harmful:*, pii:*, competitors, overreliance,
excessive-agency, hallucination, etc.

**Strategies (3):** basic, jailbreak:composite, prompt-injection.

Config: `promptfoo/promptfooconfig.yaml`. Target persona: `promptfoo/purpose.md`.

---

## 6. PyRIT (multi-turn attacks)

`pyrit/crescendo_demo.py` runs CrescendoOrchestrator against a K-12 stub target.
Validated refusal under escalation. v0.2 work: `LiveKitAgentTarget` subclass to
drive the real agent (~3–5 days).

---

## 7. HTTP moderation runner

`vt-redteam run --mode http-moderation` POSTs scenario text to
`/api/nerd-tutor/moderate-text`, reads `{ layer, terms, text }`, compares coarse
`block | mask | pass` to `expected_moderation_verdict` on each scenario.

Useful for testing **input moderation** without LiveKit. Scorers:
`ExpectedVerdictScorer`, `ForbiddenTopicsDetector`, `OpenAIModeration`.

---

## 8. Package architecture

Same core as base POC:

```
YAML corpus → Runner (LiveKit | HTTP | audio) → Scorers → Postgres/Supabase
```

**Run modes:**

| Mode | Command | Needs |
|------|---------|-------|
| Dry run | `--dry-run` | Nothing |
| LiveKit stub | default | Local LiveKit |
| Audio E2E | `--audio` | Mock or real agent |
| HTTP moderation | `--mode http-moderation` | Moderation API (or mock) |

**Scorers:** refusal, prompt-leak, forbidden-topics, openai_moderation (+ HTTP-specific set).

---

## 9. Run locally

**Read `SETUP.md` first.** Short version:

```bash
cd livekit-local && docker compose up -d
docker compose -f postgres-compose.yml up -d
# apply schema.sql (once)

cd ../prototype
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.template .env.local   # OPENAI_API_KEY — local only, never commit

pytest tests/                              # 45/45
vt-redteam list-scenarios                  # 195
vt-redteam run --tags smoke --dry-run
vt-redteam run --mode http-moderation --dry-run
```

Real agent: clone `livekit-agents` into `livekit-local/livekit-agents/` per
`SETUP.md` + `docs/10-livekit-real-agent-proof.md`.

---

## 10. Tooling research (5-layer model)

`docs/08-tooling-dossier.md` compares 12 tools:

| Layer | Examples | v0.1 verdict |
|-------|----------|--------------|
| Testing | Promptfoo, PyRIT, Garak, DeepTeam | Adopt Promptfoo (gen), PyRIT (multi-turn) |
| Runtime protection | Guardrails, Llama Guard, Rebuff | Watch |
| Observability | Langfuse, Phoenix | Watch |
| Sandboxing | gVisor, E2B | Avoid for now |
| Policy | OPA | Watch |

This POC implements **Layer 1 (Testing)** only.

---

## 11. Status & pending work

| Item | State |
|------|--------|
| Corpus + scorers + pytest | Green |
| Promptfoo → corpus bridge | Validated (69 scenarios) |
| Postgres writes | Validated |
| Real TS agent lifecycle | Validated (Option D) |
| WavCollector E2E audio | Fix applied; live re-validation pending |
| PyRIT → LiveKit target | v0.2 |
| GitHub Actions canary | Designed, not active |
| Notification alerting | Designed, not wired |

Details: `STATUS.md`.

---

## 12. Phased roadmap

| Phase | Deliverables |
|-------|----------------|
| **0 Spike** | Docs + skeleton (done) |
| **1 MVP v0.1** | Audio E2E, package publish, live writes, cover Conversation Club + Tutor Interviewer + Nerdy Avatar (3 of 6 prod agents) — see `docs/11` (~3 wk) |
| **2 Canary** | Weekly run vs staging-focused (also prod), Promptfoo in CI, Maya + Course Platform + Checkout Avatar onboarded (~2 wk) |
| **3 Hardening** | Dashboards (3 buckets: content_safety / policy_compliance / privacy_integrity), Slack alerting, multi-language, Brain scoring |

**Decisions locked in this round** (revisit if needed):
- Ownership: VT4S provisional (reviewable)
- Canary cadence: weekly against staging + production, focus on staging
- CI: GitHub Actions hooks (no specific tooling chosen for red-team layer yet)
- Slack alerting: deferred to Phase 3 (not summarily required)
- Cost tracking: `usd_cost_estimate` column added to `redteam_runs` schema (per scenario, summed per run)
- Exec dashboard buckets: content_safety / policy_compliance / privacy_integrity (3 high-level groups)
- Metrics: none pre-defined by leadership; capture all and iterate after first 4 weeks of data

---

## 13. Repository map

| Path | Purpose |
|------|---------|
| **`docs/GUIDE.md`** | **This file** |
| `SETUP.md` | Step-by-step local setup |
| `STATUS.md` | Component-level status |
| `docs/00-spike-overview.md` | Executive summary |
| `docs/04-poc-design.md` | Package API + schema |
| `docs/08-tooling-dossier.md` | 12-tool comparison |
| `docs/09`–`10` | Moderation diagrams + real-agent proof |
| `docs/11-agent-coverage-matrix.md` | 16 LiveKit agents in varsitytutors + MVP priorities |
| `promptfoo/` | Scenario generator |
| `pyrit/` | Multi-turn attacks |
| `prototype/` | `vt_agent_redteam` Python package |
| `livekit-local/` | Docker + mock agent |

---

## 14. Security

- No secrets in git. Use `*.env.template` only.
- `.env.local`, `node_modules/`, `livekit-agents/` clone are gitignored.
- Run `gitleaks detect` before pushing if you add local files.

---

## 15. Related repository

**Lighter docs-first sibling (no Promptfoo/PyRIT):**  
https://github.com/ghabrielrodrigues-vt/poc-moderation-red-team
