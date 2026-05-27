# Comparative Dossier — Tools for LLM Safety Stack

> Thorough survey of 11 tools across 5 layers of LLM protection architecture
> (Testing / Runtime Protection / Observability / Sandboxing / Policy).
> Mid-2026 data verified against official repos and vendor documentation.
> Recommendations applied to VT context: K-12 education, voice/avatar agents via
> LiveKit, Nerdy Tutor + Conversation Club + AI Interviewer.

## Executive summary (TL;DR)

| Layer | Tool | Verdict | One-line rationale |
| --- | --- | --- | --- |
| **Testing** | Promptfoo | **ADOPT** | 157 plugins + native COPPA/FERPA; already integrated in POC v0.0.4. |
| **Testing** | PyRIT | **ADOPT (v0.2)** | Multi-turn orchestrators (TAP/PAIR/Crescendo) + native audio — structural fit for LiveKit. |
| **Testing** | Garak | **PILOT (quarterly)** | "nmap for LLM" scanner — good trust+safety report, but weak multi-turn. |
| **Testing** | DeepTeam | **WATCH** | Deep multi-turn (Crescendo/TAP/Linear) + OWASP/NIST presets, but text-only + forces DeepEval scoring. Attack-template donor. |
| **Runtime** | Guardrails AI | **ADOPT (language-tutor)** | Python middleware with 70+ validators. Clean fit only on Python agent. |
| **Runtime** | Llama Guard 4 | **ADOPT (sidecar)** | Dedicated classifier, multimodal, multilingual, 14 MLCommons categories. |
| **Runtime** | Rebuff | **AVOID** | Archived May 2025; unmaintained security tooling rots. |
| **Observability** | Langfuse | **DEEPEN** | Already in agents. Deepen with LLM-as-judge + datasets-driven CI. |
| **Observability** | Arize Phoenix | **WATCH** | Superior eval rigor, but duplicates Langfuse — adopt only if rubric becomes bottleneck. |
| **Sandboxing** | gVisor | **AVOID** | Solves code-execution isolation — voice agents do not execute code. |
| **Sandboxing** | E2B | **AVOID** | Built for code interpreter / computer use — does not fit voice tutor. |
| **Policy** | OPA | **ADOPT (pilot)** | Only tool on the list covering a real gap — policy-as-code for tool calls + FERPA. |

**Adopt now (or already adopted)**: 4 tools. **Adopt as pilot**: 2.
**Clear avoid**: 3. **Watch**: 2 (Phoenix + DeepTeam). **Already in stack**: 1.

---

## Layer 1 — Testing

### Promptfoo

| Dimension | Value |
| --- | --- |
| License / Stars | MIT / ~21.6k |
| Version mid-2026 | 0.121.12 (May/2026) |
| Runtime | TypeScript / Node.js (≥20.20 or ≥22.22) |
| Line 1 | End-to-end eval + red-team scanner with single CLI and dashboard. |
| Mechanism | YAML config → plugins generate adversarial prompts → strategies wrap (encodings, jailbreak, multi-turn) → run against provider → grader (LLM-judge + assertions). |
| Probes | **157 plugins** + ~20 strategies. K-12 natives: `pii:direct`, `pii:session`, `harmful:child-exploitation`, `harmful:self-harm`, `harmful:sexual-content`, `harmful:hate`, **`compliance:coppa`**, **`compliance:ferpa`**, `bias:age`, `medical:hallucination`. Datasets: Aegis, HarmBench, DoNotAnswer, XSTest, BeaverTails. |
| Multi-turn | Yes — GOAT, Crescendo, Hydra (persistent memory), Mischievous User. |
| Output | JSON + SQLite + dashboard web + SARIF + PDF (Enterprise). |
| Targets | OpenAI/Anthropic/Bedrock/Azure/Ollama/HTTP/WebSocket/Browser/custom JS+Py. **No LiveKit native.** |
| Cost | OSS core + Cloud/Enterprise paid tier (demo-gated). |
| Strengths | Largest plugin catalog; UX cliffhanger; **COPPA/FERPA compliance out-of-the-box** (only one in category). |
| Limitations | Node/TS inside a Python package is awkward; LLM-judge noisy; no audio probes. |

**Fit in `vt-agent-redteam`**: Generator (current in v0.0.4) + optional runner via subprocess. **Already integrated** — produced 70 scenarios in 3 min in the demo.

---

### PyRIT (Microsoft)

| Dimension | Value |
| --- | --- |
| License / Stars | MIT / ~3.9k (microsoft/PyRIT — Azure/PyRIT archived mar/2026) |
| Version mid-2026 | 0.13.0 (Apr/2026) |
| Runtime | Python ≥3.10 — library, not CLI |
| Line 1 | Composable Python framework for multi-turn multimodal red-team. |
| Mechanism | Five pieces: **Targets** + **Converters** (text/audio/image transforms) + **Orchestrators** (attack loops) + **Scorers** + **Memory** (DuckDB/Azure SQL). |
| Probes | No fixed list — composition via converters + datasets (HarmBench, AdvBench, SeedPrompts). Seed prompts cover harm categories. **No native COPPA/FERPA**. |
| Multi-turn | **Best in category**: `RedTeamingOrchestrator`, `CrescendoOrchestrator`, `PAIROrchestrator`, `TreeOfAttacksWithPruningOrchestrator` (TAP), `FlipAttack`, `SkeletonKey`. |
| Output | DuckDB / Azure SQL memory → programmatic JSON/CSV. |
| Targets | OpenAI / AzureOpenAI / AzureML / HF / HTTPTarget / PlaywrightTarget + ABC `PromptTarget`. **Native multimodal** (text + audio + image). No LiveKit out of the box. |
| Cost | 100% OSS (Azure Foundry has paid managed wrapper). |
| Strengths | Orchestrated multi-turn is deepest of the three; **native audio** (critical for LiveKit); clean Python subclass; Microsoft actively maintains. |
| Limitations | No "press play" CLI; smaller community; no compliance taxonomy; API churn between releases. |

**Fit in `vt-agent-redteam`**: **Ideal structural fit**. Subclass `PromptTarget` → `LiveKitAgentTarget` that publishes audio/text to the room. Subclass `Scorer` that delegates to our protocol. Reuse our YAML corpus as PyRIT seed prompts.

---

### Garak (NVIDIA)

| Dimension | Value |
| --- | --- |
| License / Stars | Apache-2.0 / ~7.9k |
| Version mid-2026 | 0.15.0 (May/2026) |
| Runtime | Pure Python 3.10–3.12; CLI `python -m garak` |
| Line 1 | Static "nmap for LLM" scanner — fixed probe battery, pass/fail report. |
| Mechanism | Probe → Generator → Detector pipeline. Templated prompts, classifier-based detectors. Inclui `atkgen` (GPT-2 attacker fine-tuned) e `gcg` (gradient suffix search). |
| Probes | ~25 modules. K-12: `promptinject`, `latentinjection`, `dan`, `realtoxicityprompts`, `lmrc` (bullying/sexual/profanity), `leakreplay`, `sysprompt_extraction`, `donotanswer`, `topic`, `visual_jailbreak`. **No COPPA/FERPA/PII dedicados**. |
| Multi-turn | Limited (added v0.13+); `agent_breaker` tests tools. Predominantly single-shot. |
| Output | JSONL + hit log + HTML report; one line per (probe, prompt, detector, generation). |
| Targets | REST (+mTLS 2026), OpenAI/Azure/Bedrock/Cohere/Groq/HF/NIM/NeMo Guardrails. No LiveKit. |
| Cost | 100% OSS. |
| Strengths | Easiest "point and shoot"; academic paper attacks (GCG, DAN, glitch tokens); NIM/NeMo integration. |
| Limitations | Weak multi-turn; small catalog; coarse detectors (refusal/not); no compliance; no audio. |

**Fit in `vt-agent-redteam`**: Generator-only, quarterly. Run against HTTP shim, extract prompts + responses, pass through our `Scorer`. Do not trust their detectors for K-12.

---

### DeepTeam (Confident AI)

| Dimension | Value |
| --- | --- |
| License / Stars | Apache-2.0 / ~1.8k |
| Version mid-2026 | 1.0.6 (Mar/2026); first stable v1.0.4 Nov/2025 |
| Runtime | Python ≥3.9, <3.14 |
| Line 1 | Full framework — generator + runner + scorer for adversarial tests with risk-assessment reporting. |
| Mechanism | `RedTeamer` orchestrates `simulator_model` (default gpt-3.5-turbo) + `evaluation_model` (default gpt-4o). Vulnerabilities → Goldens → AttackEngine applies single/multi-turn transformations → metrics score user-supplied callback response. Plugin-style: `BaseVulnerability` + `BaseAttack` subclasses. |
| DeepEval relationship | **Hard dependency** (`deepeval>=3.6.2`). Imports `DeepEvalBaseLLM`, `Golden`, `initialize_model`. Not standalone — red-team module spun off from DeepEval. |
| Catalog | **37 vulnerability classes** + framework presets: OWASP LLM Top 10, OWASP Agentic Top 10, NIST, MITRE, EU AI Act, Aegis, BeaverTails. K-12-relevant: `child_protection`, `pii_leakage`, `prompt_leakage`, `bias`, `fairness`, `toxicity`, `graphic_content`, `personal_safety`, `illegal_activity`, `misinformation`, `hallucination`, `ethics`. **No preset FERPA/COPPA native** — composition via `child_protection` + `pii_leakage`. |
| Multi-turn | **First-class**: Crescendo, Tree Jailbreaking (TAP-style), Linear Jailbreaking, Sequential Break, Bad Likert Judge in `deepteam/attacks/multi_turn/`. |
| Multimodal | **Text only.** Docs explicitly warn text-only red-teaming is insufficient for multimodal Gemini deployments — acknowledged gap. |
| Target integration | Custom Python callback `def model_callback(input, turns) -> str | RTTurn`. **No HTTP runner, without OpenAI-shim runner, without LiveKit / WebRTC** (verified via repo code search — zero hits). |
| Output | `RiskAssessment` object → JSON local; optional push to Confident AI cloud. Scoring reuses DeepEval `BaseRedTeamingMetric`. |
| Cost | OSS Apache-2.0 free. Confident AI cloud: Free / Starter $19.99/user/month / Premium $49.99 / Team & Enterprise custom; usage-based $1/GB-month traces + $1/1k online evals. No markup no DeepTeam — you pay your own provider for `simulator_model` + `evaluation_model` (where real cost lives). |
| Strengths | **Best OSS multi-turn catalog in category** (Crescendo + TAP + Linear + SequentialBreak first-class, agent-aware). Best "compliance-framework preset" UX (OWASP/NIST/MITRE/EU-AI-Act one-liners). Tight DeepEval scoring integration. |
| Limitations | Text-only; without LiveKit/WebRTC/audio; **no native COPPA/FERPA preset**; opinionated on DeepEval (hard to swap scorer); simulator default GPT-3.5/GPT-4o (OpenAI lock-in unless wire `DeepEvalBaseLLM`); report is JSON+CLI table, without rich HTML local without Confident AI cloud. |

**Fit in `vt-agent-redteam`**: **WATCH, not ADOPT yet.** Best OSS multi-turn catalog, but does not drive LiveKit voice target, no audio, forces DeepEval scoring path (conflicts with our `Scorer` protocol). **Borrow attack templates + `child_protection` + `pii_leakage` taxonomies for YAML corpus**; keep Promptfoo as runner + our `Scorer` as judge. If adopted offline: ~2-3 days for JSON→YAML adapter + weekly CI job.

---

### Comparative table — Testing layer (4 tools)

| | Promptfoo | PyRIT | Garak | **DeepTeam** |
| --- | --- | --- | --- | --- |
| **Runtime** | Node/TS | Python | Python | Python ≥3.9 |
| **Plugins/probes** | 157 + 20 strategies | Composto | ~25 módulos | **37 vulns + 19 attacks** |
| **Native COPPA/FERPA** | ✅ | ❌ | ❌ | ❌ (`child_protection` + `pii_leakage` primitivos) |
| **Multi-turn** | ✅ (GOAT/Crescendo/Hydra) | **✅✅ (TAP/PAIR/Crescendo)** | ⚠️ Limitado | **✅✅ (Crescendo/TAP/Linear/SequentialBreak)** |
| **Multimodal (audio)** | ❌ | ✅ | ❌ | ❌ |
| **LiveKit native** | ❌ | ❌ (extensível) | ❌ | ❌ |
| **Compliance framework presets** | COPPA/FERPA plugins | ❌ | ❌ | **OWASP/NIST/MITRE/EU AI Act** |
| **Custo** | OSS + paid tier | 100% OSS | 100% OSS | OSS + Confident AI cloud opcional |
| **Where it shines** | Catálogo + UX + compliance | Multi-turn + audio | Smoke scan rápido | **Multi-turn deep + presets compliance** |
| **Where it falls short** | Node in Python code | No CLI | Weak multi-turn | No audio, no LiveKit, forces DeepEval |
| **Verdict** | ✅ adotado | ✅ adopt v0.2 | ⚠️ pilot quarterly | ⚠️ **WATCH** (borrow templates) |

---

## Layer 2 — Runtime Protection

### Guardrails AI

| Dimension | Value |
| --- | --- |
| License / Stars | Apache-2.0 / ~6.9k |
| Version mid-2026 | 0.10.0 (abr/2026) |
| Runtime | Python (99.7%) — embedded or Flask/Gunicorn REST. Drop-in OpenAI-SDK proxy. |
| Line 1 | Wrap LLM calls with "Guards" composáveis que validam input/output via validators. |
| Mechanism | Validator pipeline (heuristic / ML classifier / LLM-as-judge). Failure → `reask`/`fix`/`filter`/`exception`. |
| Catalog | ~70 validators no Hub. K-12: `DetectPII`, `DetectJailbreak` (ML hosted), `ToxicLanguage`, `ProfanityFree`, `NSFWText`, `CompetitorCheck`, `RestrictToTopic`, `UnusualPrompt`, `GroundedAIHallucination`, `SecretsPresent`. No FERPA/COPPA nomeados — composição custom. |
| Input vs Output | Ambos (`Guard.use(... on="prompt")` vs `on="output"`); streaming-aware. |
| Latency | Lexicon/regex 1–5ms; ML local 30–150ms; LLM-judge / Hub hosted 300–1500ms. |
| Integration | Python decorator/wrapper or REST sidecar. Server mode for non-Python stacks. |
| Cost | OSS framework free; Hub básico free; Advanced PII/Jailbreak ML são endpoints hospedados pagos; Guardrails Pro = enterprise. |
| K-12 fit | Not native. `DetectPII` covers FERPA-style; `NSFWText` + `RestrictToTopic` dão scaffolding. No COPPA. Validators custom = 30–80 linhas Python. |
| Limitations | No multi-turn memory (per-call); text only (no audio); jailbreak ML is hosted; Hub validator quality varies (some abandoned). |

**Fit at VT**: Best fit = `agents/language-tutor/` (Python, Nerdy Tutor + Conversation Club). Wrap the OpenAI Realtime/gpt-5-mini em `Guard().use(ToxicLanguage, NSFWText, DetectPII, RestrictToTopic(...))`. **~40–80 LoC + dep**. Medium risk: adiciona 50–200ms p50 in a latency-sensitive voice loop — needs parallel mode + fail-open. **Not viable** no `livekit-agents` TS without running Guardrails como sidecar.

---

### Llama Guard 4 (Meta)

| Dimension | Value |
| --- | --- |
| Licença | Llama 4 Community License (commercial OK até 700M MAU; "Built with Llama" atribuição; California law) |
| Version mid-2026 | Llama Guard 4 12B (abr/2025) — no new variant in 2026 |
| Runtime | Modelo 12B denso (pruned from Llama 4 Scout MoE); BF16 single GPU (~24GB VRAM). Via `transformers` + `Llama4ForConditionalGeneration`. Hosted on Together AI / DeepInfra / Replicate / NVIDIA NIM / Meta. |
| Line 1 | Single-call classifier text+image that emits `safe` / `unsafe + S-categories`. |
| Mechanism | Generative classifier — modelo emite tokens `safe` ou `unsafe\nSx,Sy`. Categorias no prompt template — pode omitir/adicionar custom via schema MLCommons. |
| Catalog | **14 categorias MLCommons**: S1 Violent Crimes, S2 Non-Violent Crimes, S3 Sex-Related Crimes, **S4 Child Sexual Exploitation**, S5 Defamation, S6 Specialized Advice, S7 Privacy, S8 IP, S9 Indiscriminate Weapons, S10 Hate, **S11 Suicide & Self-Harm**, S12 Sexual Content, S13 Elections, S14 Code Interpreter Abuse. K-12: S3/S4/S10/S11/S12 direct; S6/S7 tangential. |
| Input vs Output | Ambos — mesmo modelo, prompt template `User:` vs `Agent:`. |
| Latency | Self-host H100 ≈60–150ms; A10G/L4 250–500ms; hosted 200–600ms. |
| Cost | Pesos free sob licença; compute = GPU bill OU hosted ~$0.18/M tokens (Together/DeepInfra). |
| K-12 fit | **Strongest of the three**: S3/S4/S12 explícitos; S11 critical for student safety; multilingual (EN/ES/PT/FR/DE/HI/IT/TH — useful for Language Tutor). Multimodal text+image future-proof. No FERPA/COPPA (operacional). English F1 ~61%, multilingual ~51% — not complete alone. |
| Limitations | Susceptible to prompt injection (Meta's own caveat); multilingual recall drops; without audio native; fixed categories without fine-tuning; multi-turn limited to chat template. |

**Fit at VT**: Best fit = `agents/language-tutor/` Python + harness `prototype/`. Sidecar via Together AI or NIM self-host. **~30 LoC**: one async HTTP call wrapping `session.llm`, parse `unsafe\nSx`, map S-codes → action (block / soften / escalate). Low risk for offline/eval; medium for production voice loop (200–500ms p50). No `livekit-agents` TS ou Nerdy Tutor moderation, fits as **L4 escalation** over current L1/L2/L3.

---

### Rebuff (Protect AI / Palo Alto Networks)

| Dimension | Value |
| --- | --- |
| License / Stars | Apache-2.0 / ~1.5k. **Archived May 16, 2025**. Protect AI acquired by Palo Alto Networks Jul/2025. |
| Versão final | 0.1.1 (jan/2024) — frozen. |
| Runtime | SDK TS (75%) + Python (17%). Requer Pinecone + OpenAI key. |
| Line 1 | **Prompt injection detection only** — not a general framework. |
| Mechanism | Four input layers: heuristic → LLM-as-judge → Pinecone vector lookup against embeddings of known attacks → canary tokens injected into prompt. |
| Catalog | No taxonomia. Um signal: `injection_score` (0–1) + canary-leak boolean. No PII/toxicity/profanity/hallucination/competitor. |
| Latency | Heurística 1–10ms; vector 50–200ms; LLM-judge 400–1500ms. Pipeline cheia 500ms–2s. |
| Cost | OSS free; operational = Pinecone + tokens LLM. Dashboard hospedado descontinuado. |
| K-12 fit | Nenhum native. Só jailbreak — irrelevant for FERPA/COPPA/age-appropriate. |
| Critical limitations | **No maintenance since 2024, archived 2025** — tooling de segurança unmaintained rots quickly. Heavy infra (Pinecone) for single signal. No multimodal. |

**Fit at VT**: **Do not adopt.** Maintained successors for this problem: LLM Guard, NeMo Guardrails, Lakera (now Check Point). Bringing archived deps into K-12 production path is unjustifiable.

---

### Comparative table — Runtime Protection layer

| | Guardrails AI | Llama Guard 4 | Rebuff |
| --- | --- | --- | --- |
| **Maintained mid-2026** | ✅ ativo (0.10.0) | ✅ (modelo frozen) | ❌ archived mai/2025 |
| **Runtime shape** | Python framework / REST | Modelo 12B (sidecar) | TS/Python SDK |
| **Escopo** | Geral (70+ validators) | Content safety (14 cat.) | **Prompt injection apenas** |
| **Multimodal** | Só texto | **Text + image** | Só texto |
| **Latency p50** | 5–200ms | 200–500ms hosted | 500–2000ms |
| **Direct K-12** | Composável | **Mais forte** (S3/S4/S11/S12) | Irrelevant |
| **PII / FERPA** | DetectPII | Só flag S7 | ❌ |
| **Jailbreak** | ✅ (hosted ML) | ⚠️ próprio modelo injetável | ✅ specialty |
| **Custo** | OSS + Hub paid | Pesos free + compute | OSS + Pinecone |
| **Adopt VT** | language-tutor (~40-80 LoC) | Sidecar L4 (~30 LoC) | **Avoid** |

---

## Layer 3 — Observability

### Langfuse

| Dimension | Value |
| --- | --- |
| License / Stars | MIT (core) + commercial enterprise / ~28k |
| Version mid-2026 | v3.175.0 (mai/2026) |
| Line 1 | LLM engineering platform open-source for tracing, evals, prompt mgmt, datasets. |
| Mechanism | SDKs (Python/JS-TS) emitem trace/span/score/observation events → backend (Postgres + ClickHouse + Redis + S3) → UI. |
| Self-host vs SaaS | **Ambos**. Docker Compose / Helm / cloud templates. Cloud = managed SaaS. |
| LLM features | Trace hierarchies nested for agent loops; token/cost por model; LLM-as-judge evaluators; prompt versioning + A/B; datasets-driven regression CI; sessions grouping (casa with voice turns). |
| LiveKit fit | Works — transport-agnostic. VT already wraps LiveKit agent turns as traces. STT → LLM → TTS = spans. |
| Cost | Self-host = free. Cloud Hobby free (50k units/month, 30d retention). Core $29/mo. Pro $199/mo. Enterprise $2,499+/mo. |
| Maturity | Muito ativo. Users: Khan Academy, Samsara, Twilio, Merck. |
| K-12 limits | No FERPA/COPPA natives; PII redaction via SDK hooks. Cloud is US-hosted → self-host for student data sovereignty. |

**Fit at VT**: **Already in the stack.** Deepening = (a) LLM-as-judge safety scoring per turn, (b) datasets-driven regression CI before prompt changes, (c) sessions view to debug multi-turn jailbreak. No platform switch.

---

### Arize Phoenix

| Dimension | Value |
| --- | --- |
| License / Stars | Elastic License 2.0 (non-OSI; allows self-host, blocks reseller SaaS) / ~9.9k |
| Version mid-2026 | v16.2.0 (mai/2026) |
| Line 1 | OpenTelemetry-native LLM/ML observability + eval toolkit, dev-first. |
| Mechanism | OTel collector via `arize-phoenix-otel`; eval primitives (response, retrieval, hallucination, toxicity) rodam como offline jobs sobre traces. |
| Self-host vs SaaS | Single-container self-host (simpler than Langfuse). Phoenix Cloud = free hosted notebook-tier. Arize AX = produto comercial separado. |
| LLM features | 30+ framework integrations (OpenAI, Claude SDK, LangGraph, LlamaIndex, DSPy); most robust OSS eval rubrics library; RAG retrieval metrics; embedding drift analysis. |
| LiveKit fit | OTel-native — qualquer agent LiveKit emitindo OTLP funciona. No UI específica for voz mas without blocker. |
| Cost | 100% free OSS, no feature-gating. Phoenix Cloud free. Arize AX is enterprise. |
| Maturity | Ativo. Arize AI well-funded. Strong use in eval-heavy shops / RAG-heavy. |
| K-12 limits | Same as Langfuse — without FERPA/COPPA built-in. ELv2 complicates if VT ever resells observability. |

**Fit at VT**: **Complement, not replacement.** Phoenix tem rubrica de eval superior. Poderia rodar ao lado: Langfuse for production tracing/sessions, Phoenix em CI for regression evals contra datasets curados. **Provavelmente overkill** dado que Langfuse already tem eval support.

---

### Comparative table — Observability layer

| | Langfuse | Arize Phoenix |
| --- | --- | --- |
| **License** | MIT (+EE) | Elastic v2 |
| **Stars** | ~28k | ~9.9k |
| **Self-host stack** | Postgres+ClickHouse+Redis+S3 | Single container |
| **Eval depth** | Solid LLM-as-judge | **Best-in-class rubrics** |
| **Prod tracing scale** | High (ClickHouse) | Lower (local-first) |
| **OTel-native** | Partial (adapter) | **Yes (primary)** |
| **Pricing** | Free OSS / Cloud paid | Fully free OSS |
| **VT status** | **Already deployado** | Complement opcional |

---

## Layer 4 — Sandboxing

### gVisor (Google)

| Dimension | Value |
| --- | --- |
| License / Stars | Apache-2.0 / ~18.4k |
| Version mid-2026 | Rolling release; latest tag mai/2026 |
| Line 1 | User-space application kernel isolando containers entre syscall filtering e VM completas. |
| Mechanism | `runsc` OCI runtime intercepta guest syscalls em userspace kernel Go (Sentry), proxia subset narrow for host. Drop-in Docker/containerd/K8s. |
| Self-host | Only — it is runtime, not a service. |
| LLM features | None directly. Used by Modal, Northflank as isolation layer under code-interpreter agents. |
| LiveKit fit | **Irrelevante.** LiveKit agents do not execute untrusted code — chamam LLM APIs. |
| Cost | Grátis. Custo = infra + ops + 2-200× file I/O overhead worst case. |
| Maturity | Production em Google, GKE Sandbox, Cloud Run. |
| K-12 limits | N/A — wrong layer. |

**Fit at VT**: **Resolve problema que not temos.** AVOID.

---

### E2B

| Dimension | Value |
| --- | --- |
| License / Stars | Apache-2.0 / ~12.4k |
| Version mid-2026 | 2.25.0 (mai/2026) |
| Line 1 | Cloud sandboxes for executar código AI-gerado e fornecer "virtual computers" for agents. |
| Mechanism | Firecracker microVMs via SDK (Python/TS); sandbox expõe filesystem/terminal/process/GUI (E2B Desktop). |
| Self-host vs SaaS | Primarily SaaS. Enterprise tier oferece BYOC/on-prem. |
| LLM features | Code Interpreter SDK; computer-use (mouse/keyboard); browser-in-sandbox; concurrent sandbox pools for RL reward functions. User famoso: Manus. |
| LiveKit fit | **Mostly irrelevant.** Could host sandbox for "tutor-runs-student-Python" feature, mas voice tutors do not do that. |
| Cost | Hobby free ($100 credit, 20 concurrent, 1h sessions). Pro $150/mo. Usage ~$0.10/hr por 2vCPU+RAM. |
| Maturity | Ativo, well-funded; favorito de code-agent shops. |
| K-12 limits | No posture K-12. Sandboxes with student work = DPA review necessário. |

**Fit at VT**: **Not applicable to current product.** AVOID until CS-tutoring SKU launches.

---

### Comparative table — Sandboxing

| | gVisor | E2B |
| --- | --- | --- |
| **Layer** | Container runtime | Sandbox-as-a-service |
| **License** | Apache-2.0 | Apache-2.0 |
| **Deployment** | Self-host runtime | SaaS-first |
| **Target** | Multi-tenant infra ops | Code-interpreter / computer-use agents |
| **Pricing** | Free | Hobby free, Pro $150/mo |
| **VT relevância** | ❌ Nenhuma | ❌ Nenhuma (no produto atual) |

---

## Layer 5 — Policy

### OPA (Open Policy Agent)

| Dimension | Value |
| --- | --- |
| License / Stars | Apache-2.0 / ~11.8k (CNCF graduated 2021) |
| Version mid-2026 | v1.x série ativa; 201 releases |
| Line 1 | Policy engine general-purpose decoupling policy de application code via Rego DSL. |
| Mechanism | Application sends JSON input → OPA (sidecar/library/REST) → evaluates Rego rules on input + bundled data → returns allow/deny + obligations. |
| Self-host vs SaaS | Self-hosted. Styra DAS = commercial managed control plane (separate product). |
| LLM features | None native, but emerging pattern (OWASP Agentic Top 10 2026): enforce policy on **tool-calling layer** — argument-level guardrails, RAG document filtering por role, MCP tool allowlists, response content filtering. **Decouples agent code from safety rules**. |
| LiveKit fit | Works on function-call/tool layer independent of transport. Voice agent invoking tool "lookup_grade" can route via OPA pre-execution. |
| Cost | Free. Rego learning curve + sidecar ops. |
| Maturity | Mature, CNCF graduated. Heavy use in K8s admission, API authz @Netflix/Pinterest/Capital One. |
| K-12 fit | Rego encodes FERPA-style rules (student-X data visible only to tutor-Y). Latency ~1-5ms — voice agents tolerate it. |

**Fit at VT**: **Genuinamente covers real gap.** VT atualmente not tem policy-as-code layer; rules de safety/age-gating/PII live ad-hoc em agent code. OPA centraliza: which tools an interviewer may call, which student records a session may read, which content categories the LLM may emit. **ADOPT (piloto)**.

---

## VT stack adoption map

```
                  ┌────────────────────────────────────────┐
                  │  LAYER 1 — TESTING                    │
                  │                                        │
   generator      │  Promptfoo (v0.0.4 ✅ feito)           │
   ─────────────► │     ├─ COPPA/FERPA plugins             │
                  │     └─ corpus donor for nosso YAML     │
                  │                                        │
   multi-turn     │  PyRIT (v0.2 alvo)                     │
   ─────────────► │     ├─ LiveKitAgentTarget custom       │
                  │     └─ TAP/Crescendo orchestrators     │
                  │                                        │
   smoke scan     │  Garak (trimestral)                    │
   ─────────────► │     └─ HTML report for T&S          │
                  └─────────────────┬──────────────────────┘
                                    │ TESTS
                                    ▼
                  ┌────────────────────────────────────────┐
                  │  LAYER 2 — RUNTIME PROTECTION         │
                  │                                        │
   Python agent   │  Guardrails AI (Conversation Club +    │
   ─────────────► │  Nerdy Tutor agents/language-tutor/)   │
                  │     ├─ ToxicLanguage + NSFWText +      │
                  │     │  DetectPII + RestrictToTopic     │
                  │     └─ ~40-80 LoC + dep                │
                  │                                        │
   classifier     │  Llama Guard 4 (sidecar L4)            │
   ─────────────► │     ├─ Together AI ou NIM             │
                  │     ├─ S3/S4/S11/S12 explícitos       │
                  │     └─ ~30 LoC HTTP wrap               │
                  │                                        │
                  │  ❌ Rebuff (archived, AVOID)          │
                  └─────────────────┬──────────────────────┘
                                    │ EMITS TRACES
                                    ▼
                  ┌────────────────────────────────────────┐
                  │  LAYER 3 — OBSERVABILITY              │
                  │                                        │
                  │  Langfuse ✅ already presente               │
                  │     ├─ deepen LLM-as-judge         │
                  │     └─ datasets-driven CI              │
                  │                                        │
                  │  Arize Phoenix (WATCH, complement)     │
                  └─────────────────┬──────────────────────┘
                                    │
                                    ▼
                  ┌────────────────────────────────────────┐
                  │  LAYER 4 — POLICY (real gap)          │
                  │                                        │
   tool calls     │  OPA (piloto)                          │
   ─────────────► │     ├─ Rego rules for FERPA            │
                  │     ├─ allowlist de tool args          │
                  │     └─ ~1-5ms latency budget           │
                  └─────────────────┬──────────────────────┘
                                    │
                                    ▼
                  ┌────────────────────────────────────────┐
                  │  INFRA (existing)                      │
                  │                                        │
                  │  Docker (LiveKit + Postgres + agents)  │
                  │  AWS VPC                               │
                  │  ❌ gVisor / E2B (overkill for voice)     │
                  └────────────────────────────────────────┘
```

---

## Prioritized adoption plan

### Already in production / spike complete
1. **Promptfoo** — integrated in v0.0.4. 70 scenarios generated.
2. **Langfuse** — already presente nos agents `livekit-agents` e `language-tutor`.

### Short term (red-team package v0.2, ~3 weeks)
3. **PyRIT** — subclass `PromptTarget` for LiveKit. Habilita multi-turn (TAP/Crescendo) e audio native. Covers the path "LiveKit agent tests" que the action item mentioned.

### Medium term (dedicated runtime protection sprint, ~4 weeks)
4. **Llama Guard 4** — sidecar via Together AI in `agents/language-tutor/`. Fits as L4 escalation over L1/L2/L3 the user already built. Low cost, high value for K-12.
5. **Guardrails AI** — Python middleware in `agents/language-tutor/`. Refactors L1/L2/L3 as declarative validators. Maior risco (latência), maior valor (auditabilidade).

### Long term (next quarter)
6. **OPA** — pilot na tool-calling layer. Centralizes FERPA rules + tool allowlists. Único item da lista que covers gap arquitetural real.

### Quarterly / on demand
7. **Garak** — standalone quarterly scanner. HTML report for T&S without integrating into the package.

### Watch (revisit in 6 months)
8. **Arize Phoenix** — só se rubrica de eval do Langfuse virar gargalo.
9. **DeepTeam** — borrow offline as **attack-template donor** (Crescendo/TAP/SequentialBreak templates + `child_protection`/`pii_leakage` taxonomies). Revisit when PyRIT v0.2 stabilizes — if PyRIT covers the same multi-turn patterns, DeepTeam becomes redundant; if not, adopt as offline generator.

### Avoid
9. **Rebuff** — archived, sucessores existem (LLM Guard, NeMo Guardrails, Lakera).
10. **gVisor** — solving problema de code-interpreter que VT not tem.
11. **E2B** — built for code execution; voice tutors not executam código.

---

## Ready-made phrases for review meetings

When evaluating **Promptfoo** vs other alternatives:

> "Promptfoo is the **generator** in v0.0.4. PyRIT is the next step for **multi-turn runner** with native audio — perfect structural fit for LiveKit. Garak stays a **quarterly scanner** for T&S reporting, off the package hot path."

If reviewers ask about **runtime protection** or Guardrails AI:

> "I surveyed three: Guardrails AI (Python framework), Llama Guard 4 (multimodal classifier), Rebuff (archived, discarded). I recommend Llama Guard 4 as L4 sidecar (~30 LoC) and Guardrails AI in Python `agents/language-tutor` (~40-80 LoC). The L1/L2/L3 pipeline from PRs #1667/#1669 becomes Guardrails validators — nothing is thrown away."

If reviewers ask about **observability**:

> "Langfuse is already in the stack. Deepening is the path — LLM-as-judge safety scoring per turn + datasets regression CI. Arize Phoenix has superior rubric but duplicates Langfuse responsibility — WATCH, not ADOPT."

If reviewers ask about **sandboxing** or **policy**:

> "Sandboxing (gVisor/E2B) solves code-interpreter problem — VT does not have that. Policy (OPA) covers a real gap: today FERPA/tool authorization rules live ad-hoc in agent code. ADOPT as pilot on tool-calling layer next quarter."

If reviewers ask **"why all this research?"**:

> "I want to ensure we are building the right puzzle piece. The POC targets **testing** (layer 1) — the only real gap in the VT ecosystem today. The rest of the architecture either already exists (Langfuse) or has clear prioritized adoption paths (PyRIT v0.2, Llama Guard v0.3, OPA next quarter). I am not proposing to refactor everything at once."

---

## Verified sources (mid-2026)

- [github.com/promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) · [Promptfoo Red Team plugins](https://www.promptfoo.dev/docs/red-team/plugins/) · [Promptfoo strategies](https://www.promptfoo.dev/docs/red-team/strategies/)
- [github.com/microsoft/PyRIT](https://github.com/microsoft/PyRIT) · [PyRIT multi-turn orchestrators](https://azure.github.io/PyRIT/blog/2024_12_3.html) · [PyRIT paper (arXiv 2410.02828)](https://arxiv.org/html/2410.02828v1)
- [github.com/NVIDIA/garak](https://github.com/NVIDIA/garak) · [Garak probes](https://github.com/NVIDIA/garak/tree/main/garak/probes)
- [github.com/guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails) · [Guardrails Hub](https://guardrailsai.com/hub) · [Guardrails Pro](https://guardrailsai.com/pro)
- [github.com/protectai/rebuff](https://github.com/protectai/rebuff) — archived
- [Llama Guard 4 model card](https://huggingface.co/meta-llama/Llama-Guard-4-12B) · [Welcoming Llama Guard 4 blog](https://huggingface.co/blog/llama-guard-4)
- [Langfuse repo](https://github.com/langfuse/langfuse) · [Langfuse Pricing](https://langfuse.com/pricing)
- [Arize Phoenix repo](https://github.com/Arize-ai/phoenix) · [Phoenix vs Langfuse FAQ](https://arize.com/docs/phoenix/resources/frequently-asked-questions/langfuse-alternative-arize-phoenix-vs-langfuse-key-differences)
- [gVisor repo](https://github.com/google/gvisor) · [E2B repo](https://github.com/e2b-dev) · [E2B Pricing](https://e2b.dev/pricing)
- [OPA repo](https://github.com/open-policy-agent/opa) · [OPA for AI agents (Codilime)](https://codilime.com/blog/why-use-open-policy-agent-for-your-ai-agents/) · [TrueFoundry OPA Guardrails](https://www.truefoundry.com/docs/ai-gateway/opa-guardrails)