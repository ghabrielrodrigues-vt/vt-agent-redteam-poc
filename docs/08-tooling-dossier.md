# Dossiê Comparativo — Ferramentas para Stack de LLM Safety

> Pesquisa minuciosa de 11 ferramentas distribuídas em 5 camadas de uma
> arquitetura de proteção a LLMs (Testing / Runtime Protection /
> Observability / Sandboxing / Policy). Dados de mid-2026 verificados
> contra os repos oficiais e documentação dos vendors. Recomendações
> aplicadas ao contexto VT: educação K-12, agents voz/avatar via LiveKit,
> Nerdy Tutor + Conversation Club + AI Interviewer.

## Sumário executivo (TL;DR)

| Camada | Ferramenta | Veredito | Justificativa em 1 linha |
| --- | --- | --- | --- |
| **Testing** | Promptfoo | **ADOPT** | 157 plugins + COPPA/FERPA nativos; já integrado em v0.0.4 da POC. |
| **Testing** | PyRIT | **ADOPT (v0.2)** | Multi-turn orchestrators (TAP/PAIR/Crescendo) + audio nativo — fit estrutural pro LiveKit. |
| **Testing** | Garak | **PILOT (trimestral)** | Scanner "nmap pra LLM" — relatório bom pra trust+safety, mas multi-turn fraco. |
| **Testing** | DeepTeam | **WATCH** | Multi-turn deep (Crescendo/TAP/Linear) + OWASP/NIST presets, mas só texto + força DeepEval scoring. Doador de attack templates. |
| **Runtime** | Guardrails AI | **ADOPT (language-tutor)** | Middleware Python com 70+ validators. Cabe limpo só no agent Python. |
| **Runtime** | Llama Guard 4 | **ADOPT (sidecar)** | Classifier dedicado, multimodal, multilíngue, 14 categorias MLCommons. |
| **Runtime** | Rebuff | **AVOID** | Arquivado em maio/2025; tooling de segurança não-mantido apodrece. |
| **Observability** | Langfuse | **DEEPEN** | Já presente nos agents. Aprofundar com LLM-as-judge + datasets-driven CI. |
| **Observability** | Arize Phoenix | **WATCH** | Eval rigor superior, mas duplica Langfuse — adotar só se rubrica virar gargalo. |
| **Sandboxing** | gVisor | **AVOID** | Resolve isolamento de code execution — agents de voz não executam código. |
| **Sandboxing** | E2B | **AVOID** | Built pra code interpreter / computer use — não casa com tutor de voz. |
| **Policy** | OPA | **ADOPT (piloto)** | Única ferramenta da lista que cobre gap real — policy-as-code pra tool calls + FERPA. |

**Adopt imediato (ou já adotado)**: 4 ferramentas. **Adopt como piloto**: 2.
**Avoid claros**: 3. **Watch**: 2 (Phoenix + DeepTeam). **Já no stack**: 1.

---

## Camada 1 — Testing

### Promptfoo

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | MIT / ~21.6k |
| Versão mid-2026 | 0.121.12 (mai/2026) |
| Runtime | TypeScript / Node.js (≥20.20 ou ≥22.22) |
| Linha 1 | Eval + red-team scanner end-to-end com CLI única e dashboard. |
| Mecanismo | YAML config → plugins geram prompts adversariais → strategies envelopam (encodings, jailbreak, multi-turn) → executa contra provider → grader (LLM-judge + assertions). |
| Probes | **157 plugins** + ~20 strategies. K-12 nativos: `pii:direct`, `pii:session`, `harmful:child-exploitation`, `harmful:self-harm`, `harmful:sexual-content`, `harmful:hate`, **`compliance:coppa`**, **`compliance:ferpa`**, `bias:age`, `medical:hallucination`. Datasets: Aegis, HarmBench, DoNotAnswer, XSTest, BeaverTails. |
| Multi-turn | Sim — GOAT, Crescendo, Hydra (memória persistente), Mischievous User. |
| Output | JSON + SQLite + dashboard web + SARIF + PDF (Enterprise). |
| Targets | OpenAI/Anthropic/Bedrock/Azure/Ollama/HTTP/WebSocket/Browser/custom JS+Py. **Sem LiveKit nativo.** |
| Custo | OSS core + Cloud/Enterprise paid tier (demo-gated). |
| Pontos fortes | Maior catálogo de plugins; UX cliffhanger; **compliance COPPA/FERPA out-of-the-box** (único na categoria). |
| Limitações | Node/TS dentro de um package Python é estranho; LLM-judge noisy; sem audio probes. |

**Encaixe no `vt-agent-redteam`**: Gerador (atual em v0.0.4) + alternativa de runner via subprocess. **Já integrado** — produziu 70 cenários em 3min na demonstração.

---

### PyRIT (Microsoft)

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | MIT / ~3.9k (microsoft/PyRIT — Azure/PyRIT arquivado mar/2026) |
| Versão mid-2026 | 0.13.0 (abr/2026) |
| Runtime | Python ≥3.10 — library, não CLI |
| Linha 1 | Framework Python composable pra red-team multi-turn e multimodal. |
| Mecanismo | Cinco peças: **Targets** + **Converters** (text/audio/image transforms) + **Orchestrators** (loops de ataque) + **Scorers** + **Memory** (DuckDB/Azure SQL). |
| Probes | Sem lista fixa — composição via converters + datasets (HarmBench, AdvBench, SeedPrompts). Seed prompts cobrem harm categories. **Sem COPPA/FERPA nativos**. |
| Multi-turn | **Melhor da categoria**: `RedTeamingOrchestrator`, `CrescendoOrchestrator`, `PAIROrchestrator`, `TreeOfAttacksWithPruningOrchestrator` (TAP), `FlipAttack`, `SkeletonKey`. |
| Output | DuckDB / Azure SQL memory → JSON/CSV programático. |
| Targets | OpenAI / AzureOpenAI / AzureML / HF / HTTPTarget / PlaywrightTarget + ABC `PromptTarget`. **Multimodal nativo** (text + audio + image). Sem LiveKit pronto. |
| Custo | 100% OSS (Azure Foundry tem wrapper managed pago). |
| Pontos fortes | Multi-turn orquestrado é o mais profundo dos três; **audio nativo** (crítico pra LiveKit); subclasse Python limpa; Microsoft mantém ativo. |
| Limitações | Sem CLI de "press play"; comunidade menor; sem taxonomia compliance; API churn entre releases. |

**Encaixe no `vt-agent-redteam`**: **Fit estrutural ideal**. Subclassar `PromptTarget` → `LiveKitAgentTarget` que publica audio/text na room. Subclassar `Scorer` que delega pro nosso protocolo. Reusar nosso corpus YAML como PyRIT seed prompts.

---

### Garak (NVIDIA)

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | Apache-2.0 / ~7.9k |
| Versão mid-2026 | 0.15.0 (mai/2026) |
| Runtime | Python 3.10–3.12 puro; CLI `python -m garak` |
| Linha 1 | Scanner estático "nmap pra LLM" — bateria fixa de probes, relatório pass/fail. |
| Mecanismo | Probe → Generator → Detector pipeline. Templated prompts, classifier-based detectors. Inclui `atkgen` (GPT-2 attacker fine-tuned) e `gcg` (gradient suffix search). |
| Probes | ~25 módulos. K-12: `promptinject`, `latentinjection`, `dan`, `realtoxicityprompts`, `lmrc` (bullying/sexual/profanity), `leakreplay`, `sysprompt_extraction`, `donotanswer`, `topic`, `visual_jailbreak`. **Sem COPPA/FERPA/PII dedicados**. |
| Multi-turn | Limitado (adicionado v0.13+); `agent_breaker` testa tools. Predominantemente single-shot. |
| Output | JSONL + hit log + HTML report; uma linha por (probe, prompt, detector, generation). |
| Targets | REST (+mTLS 2026), OpenAI/Azure/Bedrock/Cohere/Groq/HF/NIM/NeMo Guardrails. Sem LiveKit. |
| Custo | 100% OSS. |
| Pontos fortes | Mais fácil "point and shoot"; ataques de papers acadêmicos (GCG, DAN, glitch tokens); integração NIM/NeMo. |
| Limitações | Multi-turn fraco; catálogo pequeno; detectores coarse (refusal/not); sem compliance; sem audio. |

**Encaixe no `vt-agent-redteam`**: Gerador-only, trimestral. Rodar contra HTTP shim, extrair prompts + responses, passar pelo nosso `Scorer`. Não confiar nos detectors deles pra K-12.

---

### DeepTeam (Confident AI)

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | Apache-2.0 / ~1.8k |
| Versão mid-2026 | 1.0.6 (mar/2026); primeiro stable v1.0.4 nov/2025 |
| Runtime | Python ≥3.9, <3.14 |
| Linha 1 | Framework completo — gerador + runner + scorer de adversarial tests com risk-assessment reporting. |
| Mecanismo | `RedTeamer` orquestra `simulator_model` (default gpt-3.5-turbo) + `evaluation_model` (default gpt-4o). Vulnerabilities → Goldens → AttackEngine aplica transformações single/multi-turn → metrics escoram resposta de callback user-supplied. Plugin-style: `BaseVulnerability` + `BaseAttack` subclasses. |
| Relação DeepEval | **Hard dependency** (`deepeval>=3.6.2`). Importa `DeepEvalBaseLLM`, `Golden`, `initialize_model`. Não é standalone — é o módulo red-team do DeepEval spun-off. |
| Catálogo | **37 vulnerability classes** + framework presets: OWASP LLM Top 10, OWASP Agentic Top 10, NIST, MITRE, EU AI Act, Aegis, BeaverTails. K-12-relevantes: `child_protection`, `pii_leakage`, `prompt_leakage`, `bias`, `fairness`, `toxicity`, `graphic_content`, `personal_safety`, `illegal_activity`, `misinformation`, `hallucination`, `ethics`. **Sem preset FERPA/COPPA nativo** — composição via `child_protection` + `pii_leakage`. |
| Multi-turn | **First-class**: Crescendo, Tree Jailbreaking (TAP-style), Linear Jailbreaking, Sequential Break, Bad Likert Judge em `deepteam/attacks/multi_turn/`. |
| Multimodal | **Apenas texto.** Docs explicitamente avisam que red-teaming text-only é insuficiente pra deployments Gemini multimodais — gap reconhecido. |
| Target integration | Custom Python callback `def model_callback(input, turns) -> str | RTTurn`. **Sem HTTP runner, sem OpenAI-shim runner, sem LiveKit / WebRTC** (verificado via repo code search — zero hits). |
| Output | `RiskAssessment` object → JSON local; push opcional pro Confident AI cloud. Scoring reusa DeepEval `BaseRedTeamingMetric`. |
| Custo | OSS Apache-2.0 grátis. Confident AI cloud: Free / Starter $19.99/user/mês / Premium $49.99 / Team & Enterprise custom; usage-based $1/GB-month traces + $1/1k online evals. Sem markup no DeepTeam — você paga seu próprio provider pra `simulator_model` + `evaluation_model` (onde o custo real mora). |
| Pontos fortes | **Melhor catálogo OSS multi-turn da categoria** (Crescendo + TAP + Linear + SequentialBreak first-class, agent-aware). Melhor "compliance-framework preset" UX (OWASP/NIST/MITRE/EU-AI-Act one-liners). Tight DeepEval scoring integration. |
| Limitações | Text-only; sem LiveKit/WebRTC/audio; **sem preset COPPA/FERPA nativo**; opinionated em DeepEval (não dá pra swap scorer fácil); simulator default GPT-3.5/GPT-4o (OpenAI lock-in unless wire `DeepEvalBaseLLM`); relatório é JSON+CLI table, sem rich HTML local sem Confident AI cloud. |

**Encaixe no `vt-agent-redteam`**: **WATCH, não ADOPT ainda.** Melhor catálogo OSS multi-turn, mas não dirige LiveKit voice target, sem audio, força DeepEval scoring path (conflito com nosso `Scorer` protocol). **Borrow attack templates + taxonomias `child_protection` + `pii_leakage` pro corpus YAML**; manter Promptfoo como runner + nosso `Scorer` como judge. Se adotado offline: ~2-3 dias pra adapter JSON→YAML + CI job semanal.

---

### Tabela comparativa — Camada Testing (4 ferramentas)

| | Promptfoo | PyRIT | Garak | **DeepTeam** |
| --- | --- | --- | --- | --- |
| **Runtime** | Node/TS | Python | Python | Python ≥3.9 |
| **Plugins/probes** | 157 + 20 strategies | Composto | ~25 módulos | **37 vulns + 19 attacks** |
| **COPPA/FERPA nativos** | ✅ | ❌ | ❌ | ❌ (`child_protection` + `pii_leakage` primitivos) |
| **Multi-turn** | ✅ (GOAT/Crescendo/Hydra) | **✅✅ (TAP/PAIR/Crescendo)** | ⚠️ Limitado | **✅✅ (Crescendo/TAP/Linear/SequentialBreak)** |
| **Multimodal (audio)** | ❌ | ✅ | ❌ | ❌ |
| **LiveKit nativo** | ❌ | ❌ (extensível) | ❌ | ❌ |
| **Compliance framework presets** | COPPA/FERPA plugins | ❌ | ❌ | **OWASP/NIST/MITRE/EU AI Act** |
| **Custo** | OSS + paid tier | 100% OSS | 100% OSS | OSS + Confident AI cloud opcional |
| **Onde brilha** | Catálogo + UX + compliance | Multi-turn + audio | Smoke scan rápido | **Multi-turn deep + presets compliance** |
| **Onde falha** | Node em código Python | Sem CLI | Multi-turn fraco | Sem audio, sem LiveKit, força DeepEval |
| **Veredito** | ✅ adotado | ✅ adopt v0.2 | ⚠️ piloto trimestral | ⚠️ **WATCH** (borrow templates) |

---

## Camada 2 — Runtime Protection

### Guardrails AI

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | Apache-2.0 / ~6.9k |
| Versão mid-2026 | 0.10.0 (abr/2026) |
| Runtime | Python (99.7%) — embedded ou Flask/Gunicorn REST. Drop-in OpenAI-SDK proxy. |
| Linha 1 | Wrap LLM calls com "Guards" composáveis que validam input/output via validators. |
| Mecanismo | Pipeline de validators (heurística / ML classifier / LLM-as-judge). Failure → `reask`/`fix`/`filter`/`exception`. |
| Catálogo | ~70 validators no Hub. K-12: `DetectPII`, `DetectJailbreak` (ML hosted), `ToxicLanguage`, `ProfanityFree`, `NSFWText`, `CompetitorCheck`, `RestrictToTopic`, `UnusualPrompt`, `GroundedAIHallucination`, `SecretsPresent`. Sem FERPA/COPPA nomeados — composição custom. |
| Input vs Output | Ambos (`Guard.use(... on="prompt")` vs `on="output"`); streaming-aware. |
| Latência | Lexicon/regex 1–5ms; ML local 30–150ms; LLM-judge / Hub hosted 300–1500ms. |
| Integração | Decorator/wrapper Python ou REST sidecar. Server mode pra non-Python stacks. |
| Custo | OSS framework grátis; Hub básico grátis; Advanced PII/Jailbreak ML são endpoints hospedados pagos; Guardrails Pro = enterprise. |
| K-12 fit | Não nativo. `DetectPII` cobre FERPA-style; `NSFWText` + `RestrictToTopic` dão scaffolding. Sem COPPA. Validators custom = 30–80 linhas Python. |
| Limitações | Sem multi-turn memory (per-call); só texto (sem audio); jailbreak ML é hospedado; qualidade dos Hub validators varia (alguns abandonados). |

**Encaixe na VT**: Melhor fit = `agents/language-tutor/` (Python, Nerdy Tutor + Conversation Club). Wrap a chamada OpenAI Realtime/gpt-5-mini em `Guard().use(ToxicLanguage, NSFWText, DetectPII, RestrictToTopic(...))`. **~40–80 LoC + dep**. Risco médio: adiciona 50–200ms p50 numa voice loop já sensível a latência — precisa parallel mode + fail-open. **Não viável** no `livekit-agents` TS sem rodar Guardrails como sidecar.

---

### Llama Guard 4 (Meta)

| Dimensão | Valor |
| --- | --- |
| Licença | Llama 4 Community License (commercial OK até 700M MAU; "Built with Llama" atribuição; California law) |
| Versão mid-2026 | Llama Guard 4 12B (abr/2025) — sem variante nova em 2026 |
| Runtime | Modelo 12B denso (pruned de Llama 4 Scout MoE); BF16 single GPU (~24GB VRAM). Via `transformers` + `Llama4ForConditionalGeneration`. Hospedado em Together AI / DeepInfra / Replicate / NVIDIA NIM / Meta. |
| Linha 1 | Classificador single-call text+image que emite `safe` / `unsafe + S-categories`. |
| Mecanismo | Generative classifier — modelo emite tokens `safe` ou `unsafe\nSx,Sy`. Categorias no prompt template — pode omitir/adicionar custom via schema MLCommons. |
| Catálogo | **14 categorias MLCommons**: S1 Violent Crimes, S2 Non-Violent Crimes, S3 Sex-Related Crimes, **S4 Child Sexual Exploitation**, S5 Defamation, S6 Specialized Advice, S7 Privacy, S8 IP, S9 Indiscriminate Weapons, S10 Hate, **S11 Suicide & Self-Harm**, S12 Sexual Content, S13 Elections, S14 Code Interpreter Abuse. K-12: S3/S4/S10/S11/S12 direto; S6/S7 tangencial. |
| Input vs Output | Ambos — mesmo modelo, prompt template `User:` vs `Agent:`. |
| Latência | Self-host H100 ≈60–150ms; A10G/L4 250–500ms; hosted 200–600ms. |
| Custo | Pesos grátis sob licença; compute = GPU bill OU hosted ~$0.18/M tokens (Together/DeepInfra). |
| K-12 fit | **Mais forte dos três**: S3/S4/S12 explícitos; S11 crítico pra segurança estudantil; multilíngue (EN/ES/PT/FR/DE/HI/IT/TH — útil pro Language Tutor). Multimodal text+image future-proof. Sem FERPA/COPPA (operacional). F1 inglês ~61%, multilíngue ~51% — não é completo sozinho. |
| Limitações | Suscetível a prompt injection (caveat do próprio Meta); multilíngue recall cai; sem audio nativo; categorias fixas sem fine-tuning; multi-turn limitado ao chat template. |

**Encaixe na VT**: Melhor fit = `agents/language-tutor/` Python + harness `prototype/`. Sidecar via Together AI ou NIM self-host. **~30 LoC**: uma async HTTP call wrapping output do `session.llm`, parse `unsafe\nSx`, mapear S-codes → action (block / soften / escalate). Risco baixo pra offline/eval; médio pra voice loop produção (200–500ms p50). No `livekit-agents` TS ou Nerdy Tutor moderation, encaixa como **L4 escalation** sobre L1/L2/L3 atuais.

---

### Rebuff (Protect AI / Palo Alto Networks)

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | Apache-2.0 / ~1.5k. **Arquivado 16/mai/2025**. Protect AI adquirido por Palo Alto Networks em jul/2025. |
| Versão final | 0.1.1 (jan/2024) — frozen. |
| Runtime | SDK TS (75%) + Python (17%). Requer Pinecone + OpenAI key. |
| Linha 1 | **Detecção de prompt injection apenas** — não é framework geral. |
| Mecanismo | Quatro camadas em input: heurística → LLM-as-judge → Pinecone vector lookup contra embeddings de ataques conhecidos → canary tokens injetados no prompt. |
| Catálogo | Sem taxonomia. Um signal: `injection_score` (0–1) + canary-leak boolean. Sem PII/toxicity/profanity/hallucination/competitor. |
| Latência | Heurística 1–10ms; vector 50–200ms; LLM-judge 400–1500ms. Pipeline cheia 500ms–2s. |
| Custo | OSS free; operacional = Pinecone + tokens LLM. Dashboard hospedado descontinuado. |
| K-12 fit | Nenhum nativo. Só jailbreak — irrelevante pra FERPA/COPPA/age-appropriate. |
| Limitações críticas | **Sem manutenção desde 2024, arquivado 2025** — tooling de segurança não-mantido apodrece rápido. Heavy infra (Pinecone) por single signal. Sem multimodal. |

**Encaixe na VT**: **Não adotar.** Sucessores mantidos pra esse problema: LLM Guard, NeMo Guardrails, Lakera (agora Check Point). Trazer dep arquivada pra path K-12 produção é injustificável.

---

### Tabela comparativa — Camada Runtime Protection

| | Guardrails AI | Llama Guard 4 | Rebuff |
| --- | --- | --- | --- |
| **Mantido mid-2026** | ✅ ativo (0.10.0) | ✅ (modelo frozen) | ❌ arquivado mai/2025 |
| **Runtime shape** | Python framework / REST | Modelo 12B (sidecar) | TS/Python SDK |
| **Escopo** | Geral (70+ validators) | Content safety (14 cat.) | **Prompt injection apenas** |
| **Multimodal** | Só texto | **Text + image** | Só texto |
| **Latência p50** | 5–200ms | 200–500ms hosted | 500–2000ms |
| **K-12 direto** | Composável | **Mais forte** (S3/S4/S11/S12) | Irrelevante |
| **PII / FERPA** | DetectPII | Só flag S7 | ❌ |
| **Jailbreak** | ✅ (hosted ML) | ⚠️ próprio modelo injetável | ✅ specialty |
| **Custo** | OSS + Hub paid | Pesos grátis + compute | OSS + Pinecone |
| **Adopt VT** | language-tutor (~40-80 LoC) | Sidecar L4 (~30 LoC) | **Avoid** |

---

## Camada 3 — Observabilidade

### Langfuse

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | MIT (core) + commercial enterprise / ~28k |
| Versão mid-2026 | v3.175.0 (mai/2026) |
| Linha 1 | LLM engineering platform open-source pra tracing, evals, prompt mgmt, datasets. |
| Mecanismo | SDKs (Python/JS-TS) emitem trace/span/score/observation events → backend (Postgres + ClickHouse + Redis + S3) → UI. |
| Self-host vs SaaS | **Ambos**. Docker Compose / Helm / cloud templates. Cloud = managed SaaS. |
| Features LLM | Trace hierarchies nested pra agent loops; token/cost por model; LLM-as-judge evaluators; prompt versioning + A/B; datasets-driven regression CI; sessions grouping (casa com voice turns). |
| LiveKit fit | Funciona — transport-agnostic. VT já wrappa LiveKit agent turns como traces. STT → LLM → TTS = spans. |
| Custo | Self-host = grátis. Cloud Hobby grátis (50k units/mês, 30d retention). Core $29/mo. Pro $199/mo. Enterprise $2,499+/mo. |
| Maturidade | Muito ativo. Users: Khan Academy, Samsara, Twilio, Merck. |
| K-12 limites | Sem FERPA/COPPA nativos; PII redaction via SDK hooks. Cloud é US-hosted → self-host pra student data sovereignty. |

**Encaixe na VT**: **Já está no stack.** Deepening = (a) LLM-as-judge safety scoring por turn, (b) datasets-driven regression CI antes de mudanças de prompt, (c) sessions view pra debugar multi-turn jailbreak. Sem switch de platform.

---

### Arize Phoenix

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | Elastic License 2.0 (não-OSI; permite self-host, bloqueia reseller SaaS) / ~9.9k |
| Versão mid-2026 | v16.2.0 (mai/2026) |
| Linha 1 | OpenTelemetry-native LLM/ML observability + eval toolkit, dev-first. |
| Mecanismo | OTel collector via `arize-phoenix-otel`; eval primitives (response, retrieval, hallucination, toxicity) rodam como offline jobs sobre traces. |
| Self-host vs SaaS | Single-container self-host (mais simples que Langfuse). Phoenix Cloud = free hosted notebook-tier. Arize AX = produto comercial separado. |
| Features LLM | 30+ framework integrations (OpenAI, Claude SDK, LangGraph, LlamaIndex, DSPy); biblioteca de eval rubrics mais robusta do OSS; RAG retrieval metrics; embedding drift analysis. |
| LiveKit fit | OTel-native — qualquer agent LiveKit emitindo OTLP funciona. Sem UI específica pra voz mas sem blocker. |
| Custo | 100% free OSS, sem feature-gating. Phoenix Cloud free. Arize AX é enterprise. |
| Maturidade | Ativo. Arize AI well-funded. Uso forte em shops eval-heavy / RAG-heavy. |
| K-12 limites | Mesmo que Langfuse — sem FERPA/COPPA built-in. ELv2 complica se VT um dia revender observability. |

**Encaixe na VT**: **Complement, não replacement.** Phoenix tem rubrica de eval superior. Poderia rodar ao lado: Langfuse pra production tracing/sessions, Phoenix em CI pra regression evals contra datasets curados. **Provavelmente overkill** dado que Langfuse já tem eval support.

---

### Tabela comparativa — Camada Observabilidade

| | Langfuse | Arize Phoenix |
| --- | --- | --- |
| **Licença** | MIT (+EE) | Elastic v2 |
| **Stars** | ~28k | ~9.9k |
| **Self-host stack** | Postgres+ClickHouse+Redis+S3 | Single container |
| **Eval depth** | Solid LLM-as-judge | **Best-in-class rubrics** |
| **Prod tracing scale** | High (ClickHouse) | Lower (local-first) |
| **OTel-native** | Partial (adapter) | **Yes (primary)** |
| **Pricing** | Free OSS / Cloud paid | Fully free OSS |
| **VT status** | **Já deployado** | Complement opcional |

---

## Camada 4 — Sandboxing

### gVisor (Google)

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | Apache-2.0 / ~18.4k |
| Versão mid-2026 | Rolling release; latest tag mai/2026 |
| Linha 1 | User-space application kernel isolando containers entre syscall filtering e VM completas. |
| Mecanismo | `runsc` OCI runtime intercepta guest syscalls em userspace kernel Go (Sentry), proxia subset narrow pro host. Drop-in Docker/containerd/K8s. |
| Self-host | Apenas — é runtime, não service. |
| Features LLM | Nenhuma direta. Usado por Modal, Northflank como isolation layer sob code-interpreter agents. |
| LiveKit fit | **Irrelevante.** Agents LiveKit não executam código untrusted — chamam LLM APIs. |
| Custo | Grátis. Custo = infra + ops + 2-200× file I/O overhead worst case. |
| Maturidade | Production em Google, GKE Sandbox, Cloud Run. |
| K-12 limites | N/A — wrong layer. |

**Encaixe na VT**: **Resolve problema que não temos.** AVOID.

---

### E2B

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | Apache-2.0 / ~12.4k |
| Versão mid-2026 | 2.25.0 (mai/2026) |
| Linha 1 | Cloud sandboxes pra executar código AI-gerado e fornecer "virtual computers" pra agents. |
| Mecanismo | Firecracker microVMs via SDK (Python/TS); sandbox expõe filesystem/terminal/process/GUI (E2B Desktop). |
| Self-host vs SaaS | Primariamente SaaS. Enterprise tier oferece BYOC/on-prem. |
| Features LLM | Code Interpreter SDK; computer-use (mouse/keyboard); browser-in-sandbox; concurrent sandbox pools pra RL reward functions. User famoso: Manus. |
| LiveKit fit | **Mostly irrelevant.** Poderia hospedar sandbox pra "tutor-runs-student-Python" feature, mas voice tutors não fazem isso. |
| Custo | Hobby grátis ($100 credit, 20 concurrent, 1h sessions). Pro $150/mo. Usage ~$0.10/hr por 2vCPU+RAM. |
| Maturidade | Ativo, well-funded; favorito de code-agent shops. |
| K-12 limites | Sem posture K-12. Sandboxes com student work = DPA review necessário. |

**Encaixe na VT**: **Not applicable ao produto atual.** AVOID até CS-tutoring SKU lançar.

---

### Tabela comparativa — Sandboxing

| | gVisor | E2B |
| --- | --- | --- |
| **Layer** | Container runtime | Sandbox-as-a-service |
| **Licença** | Apache-2.0 | Apache-2.0 |
| **Deployment** | Self-host runtime | SaaS-first |
| **Target** | Multi-tenant infra ops | Code-interpreter / computer-use agents |
| **Pricing** | Free | Hobby free, Pro $150/mo |
| **VT relevância** | ❌ Nenhuma | ❌ Nenhuma (no produto atual) |

---

## Camada 5 — Policy

### OPA (Open Policy Agent)

| Dimensão | Valor |
| --- | --- |
| Licença / Stars | Apache-2.0 / ~11.8k (CNCF graduated 2021) |
| Versão mid-2026 | v1.x série ativa; 201 releases |
| Linha 1 | Policy engine general-purpose decoupling policy de application code via Rego DSL. |
| Mecanismo | Application manda JSON input → OPA (sidecar/library/REST) → evalua Rego rules sobre input + bundled data → returns allow/deny + obligations. |
| Self-host vs SaaS | Self-hosted. Styra DAS = commercial managed control plane (produto separado). |
| Features LLM | Nenhuma nativa, mas pattern emergente (OWASP Agentic Top 10 2026): enforce policy no **tool-calling layer** — argument-level guardrails, RAG document filtering por role, MCP tool allowlists, response content filtering. **Desacopla agent code de safety rules**. |
| LiveKit fit | Funciona na function-call/tool layer independente de transport. Voice agent invocando tool "lookup_grade" pode rotear via OPA pre-execution. |
| Custo | Grátis. Curva de Rego + sidecar ops. |
| Maturidade | Mature, CNCF graduated. Heavy use em K8s admission, API authz @Netflix/Pinterest/Capital One. |
| K-12 fit | Rego encoda FERPA-style rules (student-X data só visível a tutor-Y). Latência ~1-5ms — voice agents toleram. |

**Encaixe na VT**: **Genuinamente cobre gap real.** VT atualmente não tem policy-as-code layer; rules de safety/age-gating/PII vivem ad-hoc em agent code. OPA centraliza: quais tools um interviewer pode chamar, quais student records uma session pode ler, quais content categories o LLM pode emitir. **ADOPT (piloto)**.

---

## Mapa de adoção pro VT stack

```
                  ┌────────────────────────────────────────┐
                  │  CAMADA 1 — TESTING                    │
                  │                                        │
   gerador        │  Promptfoo (v0.0.4 ✅ feito)           │
   ─────────────► │     ├─ COPPA/FERPA plugins             │
                  │     └─ corpus donor pro nosso YAML     │
                  │                                        │
   multi-turn     │  PyRIT (v0.2 alvo)                     │
   ─────────────► │     ├─ LiveKitAgentTarget custom       │
                  │     └─ TAP/Crescendo orchestrators     │
                  │                                        │
   smoke scan     │  Garak (trimestral)                    │
   ─────────────► │     └─ relatório HTML pra T&S          │
                  └─────────────────┬──────────────────────┘
                                    │ TESTA
                                    ▼
                  ┌────────────────────────────────────────┐
                  │  CAMADA 2 — RUNTIME PROTECTION         │
                  │                                        │
   agent Python   │  Guardrails AI (Conversation Club +    │
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
                  │  ❌ Rebuff (arquivado, AVOID)          │
                  └─────────────────┬──────────────────────┘
                                    │ EMITE TRACES
                                    ▼
                  ┌────────────────────────────────────────┐
                  │  CAMADA 3 — OBSERVABILITY              │
                  │                                        │
                  │  Langfuse ✅ já presente               │
                  │     ├─ aprofundar LLM-as-judge         │
                  │     └─ datasets-driven CI              │
                  │                                        │
                  │  Arize Phoenix (WATCH, complement)     │
                  └─────────────────┬──────────────────────┘
                                    │
                                    ▼
                  ┌────────────────────────────────────────┐
                  │  CAMADA 4 — POLICY (gap real)          │
                  │                                        │
   tool calls     │  OPA (piloto)                          │
   ─────────────► │     ├─ Rego rules pra FERPA            │
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
                  │  ❌ gVisor / E2B (overkill p/ voz)     │
                  └────────────────────────────────────────┘
```

---

## Plano de adoção priorizado

### Já em produção / spike completo
1. **Promptfoo** — integrado na v0.0.4. 70 cenários gerados.
2. **Langfuse** — já presente nos agents `livekit-agents` e `language-tutor`.

### Curto prazo (v0.2 do red-team package, ~3 semanas)
3. **PyRIT** — subclassar `PromptTarget` pra LiveKit. Habilita multi-turn (TAP/Crescendo) e audio nativo. Cobre o caminho "LiveKit agent tests" que o chefe mencionou.

### Médio prazo (sprint dedicado de runtime protection, ~4 semanas)
4. **Llama Guard 4** — sidecar via Together AI no `agents/language-tutor/`. Encaixe como L4 escalation sobre L1/L2/L3 que o user já fez. Custo baixo, valor alto pra K-12.
5. **Guardrails AI** — middleware Python no `agents/language-tutor/`. Refatora L1/L2/L3 como validators declarativos. Maior risco (latência), maior valor (auditabilidade).

### Longo prazo (próximo quarter)
6. **OPA** — piloto na tool-calling layer. Centraliza FERPA rules + tool allowlists. Único item da lista que cobre gap arquitetural real.

### Trimestral / sob demanda
7. **Garak** — scanner standalone trimestral. Relatório HTML pra T&S sem integrar no package.

### Watch (revisitar em 6 meses)
8. **Arize Phoenix** — só se rubrica de eval do Langfuse virar gargalo.
9. **DeepTeam** — borrow offline as **attack-template donor** (Crescendo/TAP/SequentialBreak templates + `child_protection`/`pii_leakage` taxonomias). Revisitar quando v0.2 do PyRIT estabilizar — se PyRIT cobrir os mesmos multi-turn patterns, DeepTeam fica redundante; se não, virar adopt como gerador offline.

### Avoid
9. **Rebuff** — arquivado, sucessores existem (LLM Guard, NeMo Guardrails, Lakera).
10. **gVisor** — solving problema de code-interpreter que VT não tem.
11. **E2B** — built pra code execution; voice tutors não executam código.

---

## Frases prontas pra reunião

Se o chefe perguntar sobre **Promptfoo** vs outras alternativas:

> "Promptfoo é o **gerador** que está no v0.0.4. PyRIT é o próximo passo pra **runner multi-turn** com audio nativo — fit estrutural perfeito pro LiveKit. Garak fica como **scanner trimestral** pra relatório de T&S, fora do hot path do package."

Se ele perguntar sobre **runtime protection** ou Guardrails AI:

> "Pesquisei três: Guardrails AI (Python framework), Llama Guard 4 (classifier multimodal), Rebuff (arquivado, descartado). Recomendo Llama Guard 4 como sidecar L4 (~30 LoC) e Guardrails AI no `agents/language-tutor` Python (~40-80 LoC). A pipeline L1/L2/L3 que eu já fiz nos PRs #1667/#1669 vira validators do Guardrails — não joga fora."

Se ele perguntar sobre **observabilidade**:

> "Langfuse já está no stack. Aprofundar é o caminho — LLM-as-judge safety scoring por turn + datasets regression CI. Arize Phoenix tem rubrica superior mas duplica responsabilidade do Langfuse — WATCH, não ADOPT."

Se ele perguntar sobre **sandboxing** ou **policy**:

> "Sandboxing (gVisor/E2B) resolve problema de code-interpreter — VT não tem. Policy (OPA) cobre um gap real: hoje rules de FERPA/tool authorization vivem ad-hoc em agent code. ADOPT como piloto na tool-calling layer no próximo quarter."

Se ele perguntar **"por que essa pesquisa toda?"**:

> "Quero garantir que estamos construindo a peça certa do quebra-cabeça. A POC mira **testing** (camada 1) — a única lacuna real do ecossistema VT hoje. O resto da arquitetura ou já existe (Langfuse) ou tem caminhos claros de adoção priorizada (PyRIT v0.2, Llama Guard v0.3, OPA quarter seguinte). Não tô propondo refatorar tudo de uma vez."

---

## Fontes verificadas (mid-2026)

- [github.com/promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) · [Promptfoo Red Team plugins](https://www.promptfoo.dev/docs/red-team/plugins/) · [Promptfoo strategies](https://www.promptfoo.dev/docs/red-team/strategies/)
- [github.com/microsoft/PyRIT](https://github.com/microsoft/PyRIT) · [PyRIT multi-turn orchestrators](https://azure.github.io/PyRIT/blog/2024_12_3.html) · [PyRIT paper (arXiv 2410.02828)](https://arxiv.org/html/2410.02828v1)
- [github.com/NVIDIA/garak](https://github.com/NVIDIA/garak) · [Garak probes](https://github.com/NVIDIA/garak/tree/main/garak/probes)
- [github.com/guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails) · [Guardrails Hub](https://guardrailsai.com/hub) · [Guardrails Pro](https://guardrailsai.com/pro)
- [github.com/protectai/rebuff](https://github.com/protectai/rebuff) — arquivado
- [Llama Guard 4 model card](https://huggingface.co/meta-llama/Llama-Guard-4-12B) · [Welcoming Llama Guard 4 blog](https://huggingface.co/blog/llama-guard-4)
- [Langfuse repo](https://github.com/langfuse/langfuse) · [Langfuse Pricing](https://langfuse.com/pricing)
- [Arize Phoenix repo](https://github.com/Arize-ai/phoenix) · [Phoenix vs Langfuse FAQ](https://arize.com/docs/phoenix/resources/frequently-asked-questions/langfuse-alternative-arize-phoenix-vs-langfuse-key-differences)
- [gVisor repo](https://github.com/google/gvisor) · [E2B repo](https://github.com/e2b-dev) · [E2B Pricing](https://e2b.dev/pricing)
- [OPA repo](https://github.com/open-policy-agent/opa) · [OPA for AI agents (Codilime)](https://codilime.com/blog/why-use-open-policy-agent-for-your-ai-agents/) · [TrueFoundry OPA Guardrails](https://www.truefoundry.com/docs/ai-gateway/opa-guardrails)
