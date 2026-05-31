const STATUS_URL = "./data/redteam-status.json";
const REFRESH_MS = 5000;

const $ = (selector) => document.querySelector(selector);

const state = {
  timer: null,
  lastData: null,
  taskOpen: new Map(),
  language: localStorage.getItem("redteam-dashboard-language") || "en",
};

const STATIC_COPY = {
  en: {
    "hero.eyebrow": "LiveKit Agents Red Team MVP",
    "hero.title": "Red Team MVP Control Room",
    "hero.subtitle": "Task-first operating view for framework delivery, SOO integration, deploy gates, canonical docs, and implementation risks.",
    "actions.refresh": "Refresh",
    "nav.current": "Current",
    "nav.phaseMap": "Phase Map",
    "nav.ops": "Ops",
    "nav.risks": "Risks",
    "nav.files": "Files",
    "nav.glossary": "Glossary",
    "labels.currentStage": "Current Stage",
    "labels.nextAction": "Next Action",
    "labels.followingAction": "Following Action",
    "labels.deliveryFocus": "Delivery Focus",
    "labels.complete": "complete",
    "labels.criticalPath": "Critical Path",
    "labels.strategicView": "Strategic View",
    "labels.essentialMetrics": "Essential Metrics",
    "labels.executionRoadmap": "Execution Roadmap",
    "labels.operationalReadiness": "Operational Readiness",
    "labels.health": "Health",
    "labels.tests": "Tests",
    "labels.lastSync": "Last Sync",
    "labels.architecture": "Architecture",
    "labels.projectOverview": "Project Overview",
    "labels.watchItems": "Watch Items",
    "labels.sourceMap": "Source Map",
    "labels.recentActivity": "Recent Activity",
    "labels.glossary": "Glossary",
    "headings.progressTargets": "Progress and targets",
    "headings.atGlance": "At a glance",
    "headings.phaseMap": "Phase map",
    "headings.ops": "Cost, latency, scale, reliability",
    "headings.phaseEndChecks": "Phase-end checks",
    "headings.failureModes": "Failure modes",
    "headings.bottlenecks": "Bottlenecks",
    "headings.runtimeSignals": "Runtime signals",
    "headings.dataPath": "Red-team data path",
    "headings.mvpProves": "What this MVP proves",
    "headings.openRisks": "Open risks",
    "headings.canonicalFiles": "Canonical files and working surfaces",
    "headings.localCommits": "Local commits",
    "headings.termsAcronyms": "Terms and acronyms",
    "notes.phaseMap": "F = framework, S = SOO integration, C = rollout controls.",
    "meta.gitTestsSync": "Git, tests, sync",
    "meta.flowFeedback": "Flow + feedback channels",
    "meta.boundaries": "Boundaries and posture",
    "meta.needsAttention": "Needs attention",
    "meta.latestFive": "Latest 5",
    "meta.glossary": "Dashboard vocabulary",
  },
  pt: {
    "hero.eyebrow": "LiveKit Agents Red Team MVP",
    "hero.title": "Sala de Controle Red Team MVP",
    "hero.subtitle": "Visao operacional centrada em tarefas para framework, integracao SOO, deploy gates, docs canonicos e riscos de implementacao.",
    "actions.refresh": "Atualizar",
    "nav.current": "Atual",
    "nav.phaseMap": "Phase Map",
    "nav.ops": "Ops",
    "nav.risks": "Riscos",
    "nav.files": "Arquivos",
    "nav.glossary": "Glossario",
    "labels.currentStage": "Etapa Atual",
    "labels.nextAction": "Proxima Acao",
    "labels.followingAction": "Acao Seguinte",
    "labels.deliveryFocus": "Foco de Entrega",
    "labels.complete": "completo",
    "labels.criticalPath": "Critical Path",
    "labels.strategicView": "Strategic View",
    "labels.essentialMetrics": "Metricas Essenciais",
    "labels.executionRoadmap": "Roadmap de Execucao",
    "labels.operationalReadiness": "Prontidao Operacional",
    "labels.health": "Saude",
    "labels.tests": "Testes",
    "labels.lastSync": "Ultimo Sync",
    "labels.architecture": "Arquitetura",
    "labels.projectOverview": "Overview do Projeto",
    "labels.watchItems": "Pontos de Atencao",
    "labels.sourceMap": "Mapa de Fontes",
    "labels.recentActivity": "Atividade Recente",
    "labels.glossary": "Glossario",
    "headings.progressTargets": "Progresso e metas",
    "headings.atGlance": "Resumo rapido",
    "headings.phaseMap": "Phase map",
    "headings.ops": "Custo, latencia, escala, confiabilidade",
    "headings.phaseEndChecks": "Checks de fim de fase",
    "headings.failureModes": "Modos de falha",
    "headings.bottlenecks": "Gargalos",
    "headings.runtimeSignals": "Sinais de runtime",
    "headings.dataPath": "Fluxo de dados Red Team",
    "headings.mvpProves": "O que este MVP prova",
    "headings.openRisks": "Riscos abertos",
    "headings.canonicalFiles": "Arquivos canonicos e superficies de trabalho",
    "headings.localCommits": "Commits locais",
    "headings.termsAcronyms": "Termos e siglas",
    "notes.phaseMap": "F = framework, S = integracao SOO, C = controles de rollout.",
    "meta.gitTestsSync": "Git, testes, sync",
    "meta.flowFeedback": "Fluxo + canais de feedback",
    "meta.boundaries": "Limites e postura",
    "meta.needsAttention": "Precisa de atencao",
    "meta.latestFive": "Ultimos 5",
    "meta.glossary": "Vocabulario do dashboard",
  },
};

const STATUS_LABELS = {
  pt: {
    "accepted": "aceito",
    "accepted with conditions": "aceito com condicoes",
    "blocked": "bloqueado",
    "clean": "limpo",
    "current": "atual",
    "dirty": "sujo",
    "done": "concluido",
    "failing": "falhando",
    "greenlight": "greenlight",
    "manual": "manual",
    "measured": "medido",
    "missing": "ausente",
    "mixed": "misto",
    "not tested": "nao testado",
    "not-tested": "nao testado",
    "partial": "parcial",
    "passing": "passando",
    "pending": "pendente",
    "planned": "planejado",
    "risk": "risco",
  },
};

const EXACT_PT = new Map([
  ["Greenlight with active conditions", "Greenlight com condicoes ativas"],
  ["Live data", "Dados ao vivo"],
  ["Data unavailable", "Dados indisponiveis"],
  ["Dashboard data not loaded", "Dados do dashboard nao carregados"],
  ["Dirty worktree", "Working tree suja"],
  ["Clean worktree", "Working tree limpa"],
  ["No queued action", "Sem acao na fila"],
  ["All non-manual implementation tasks are complete.", "Todas as tarefas nao manuais de implementacao estao concluidas."],
  ["Loading", "Carregando"],
  ["Loading stage", "Carregando etapa"],
  ["Loading strategic delivery notes.", "Carregando notas da Strategic View."],
  ["Reading repo state and transfer docs.", "Lendo estado do repo e docs de transferencia."],
  ["The next implementation step will appear here.", "A proxima etapa de implementacao aparece aqui."],
  ["The follow-up implementation step will appear here.", "A etapa seguinte aparece aqui."],
  ["Updated", "Atualizado"],
  ["Gap", "Gap"],
  ["Measure", "Medir"],
  ["OK", "OK"],
  ["MISS", "MISS"],
  ["Current Stage", "Etapa Atual"],
  ["Next Action", "Proxima Acao"],
  ["Following Action", "Acao Seguinte"],
  ["Operational closure", "Fechamento operacional"],
  ["Cost guardrail", "Guardrail de custo"],
  ["API outage behavior", "Comportamento em outage de API"],
  ["Concurrency/load", "Concorrencia/carga"],
  ["Cost", "Custo"],
  ["Latency", "Latencia"],
  ["Scalability", "Escalabilidade"],
  ["Reliability", "Confiabilidade"],
  ["API outage", "Outage de API"],
  ["Bottlenecks", "Gargalos"],
  ["Phase 1A - Framework hardening", "Phase 1A - hardening do framework"],
  ["Phase 1B - SOO integration", "Phase 1B - integracao SOO"],
  ["Phase 1C - Rollout controls", "Phase 1C - controles de rollout"],
  ["Phase 1D - Final release governance", "Phase 1D - governanca final de release"],
  ["Langfuse native transcript runner", "Runner de transcript nativo Langfuse"],
  ["Manifest schema extensions", "Extensoes de schema do manifest"],
  ["Severity gate and overrides", "Gate de severidade e overrides"],
  ["PII redaction at write", "Redacao de PII na escrita"],
  ["CLI modes from manifest", "Modos CLI via manifest"],
  ["Reusable workflow", "Workflow reutilizavel"],
  ["v0.1.0 release tag", "Tag de release v0.1.0"],
  ["language-tutor manifest", "manifest language-tutor"],
  ["language-checkpoint manifest", "manifest language-checkpoint"],
  ["support-agent manifest", "manifest support-agent"],
  ["SOO redteam workflow", "workflow Red Team SOO"],
  ["Secrets and environments", "Secrets e environments"],
  ["Conversation Club schema", "Schema Conversation Club"],
  ["CI DB URL and JWT", "CI DB URL e JWT"],
  ["Deploy hook gate", "Deploy hook gate"],
  ["Slack alert", "Alerta Slack"],
  ["Controlled drill", "Drill controlado"],
  ["PostHog feature-flag release gate", "Release gate com feature flag PostHog"],
  ["Integration and E2E tests", "Testes de integracao e E2E"],
  ["LLM_WIKI NITPICK code review", "Code review NITPICK via LLM_WIKI"],
  ["LLM attack-defense review", "Review de ataque-defesa LLM"],
  ["Strategic triage", "Triagem estrategica"],
  ["vt-agent-redteam cutover", "Cutover vt-agent-redteam"],
  ["DOCX security traceability audit", "Auditoria DOCX de rastreabilidade de seguranca"],
  ["Security pentest and exploitation review", "Pentest de seguranca e review de exploitation"],
  ["Final team report", "Relatorio final para o time"],
  ["S5 - Secrets and environments", "S5 - Secrets e environments"],
  ["Wire Langfuse, OpenAI, Supabase, and Slack secrets in target environments.", "Configurar secrets Langfuse, OpenAI, Supabase e Slack nos environments alvo."],
  ["Scenario target", "Meta de cenarios"],
  ["Target corpus size from spec v2.1.", "Tamanho alvo do corpus na spec v2.1."],
  ["Corpus files", "Arquivos de corpus"],
  ["YAML category files currently in the framework.", "Arquivos YAML de categorias no framework."],
  ["v0 target agents", "Agentes alvo v0"],
  ["Feedback channels", "Canais de feedback"],
  ["GitHub Check, Slack, dashboard views, run_summary.json.", "GitHub Check, Slack, visoes do dashboard, run_summary.json."],
  ["Framework tests", "Testes do framework"],
  ["Last captured pytest suite size.", "Tamanho da suite pytest capturada por ultimo."],
  ["Commits ahead", "Commits a frente"],
  ["Local framework branch versus origin/main.", "Branch local do framework versus origin/main."],
  ["Framework boundary", "Limite do framework"],
  ["This repo owns the reusable red-team runner, manifest schema, corpus, scoring, storage, and release workflow.", "Este repo possui runner Red Team, schema de manifest, corpus, scoring, storage e workflow de release."],
  ["SOO boundary", "Limite SOO"],
  ["student-onboarding-orchestration consumes the framework for the three LiveKit agents selected for v0.", "student-onboarding-orchestration consome o framework para os tres agentes LiveKit selecionados para v0."],
  ["Production moderation", "Moderacao de production"],
  ["Existing app-level input moderation is not replaced; the MVP validates agent output behavior and deploy safety.", "A moderacao de input em nivel de app nao e substituida; o MVP valida comportamento de output dos agentes e seguranca de deploy."],
  ["Decision posture", "Postura de decisao"],
  ["Hard constraints, ADRs, Ask First rules, and bilingual-doc conventions remain binding for every new step.", "Hard constraints, ADRs, regras Ask First e convencoes bilingual-doc continuam obrigatorias em cada nova etapa."],
  ["Langfuse correlation metadata", "Metadata de correlacao Langfuse"],
  ["Plan assumes redteam_run_id and redteam_scenario_id metadata. SOO tracing may need explicit metadata wiring before runner search works reliably.", "O plano assume metadata redteam_run_id e redteam_scenario_id. O tracing SOO pode precisar de wiring explicito antes da busca do runner ficar confiavel."],
  ["SOO Ask First boundaries", "Limites Ask First do SOO"],
  ["DB, auth, deploy, infrastructure, and destructive operations require explicit confirmation inside the consumer repo.", "DB, auth, deploy, infraestrutura e operacoes destrutivas exigem confirmacao explicita dentro do repo consumidor."],
  ["Maya tool-use coverage gap", "Gap de cobertura tool-use da Maya"],
  ["support-agent must declare partial-no-tool-use until scenario/tool traces are proven.", "support-agent deve declarar partial-no-tool-use ate que traces de scenario/tool sejam provados."],
  ["Supabase deploy-killer rules", "Regras deploy-killer do Supabase"],
  ["Conversation Club schema work must follow local migration rules and avoid direct remote mutations.", "Trabalho de schema Conversation Club deve seguir regras locais de migration e evitar mutacoes remotas diretas."],
  ["Deferred audio and BI scope", "Escopo audio e BI postergado"],
  ["WAV collector D1 and BI dashboard D9 remain post-v0 unless priorities change through a new ADR.", "WAV collector D1 e BI dashboard D9 ficam post-v0 salvo mudanca de prioridade via novo ADR."],
  ["Agent profile, policy coverage, scenario selection, thresholds.", "Perfil do agente, cobertura de policy, selecao de cenarios, thresholds."],
  ["Scenarios", "Cenarios"],
  ["Curated corpus buckets plus exclude tags for partial coverage.", "Buckets curados do corpus mais exclude tags para cobertura parcial."],
  ["LiveKit/Langfuse trace path for agent-native transcript evidence.", "Fluxo de trace LiveKit/Langfuse para evidencia de transcript nativo do agente."],
  ["Moderation, refusal, prompt leak, expected verdict, category checks.", "Moderation, refusal, prompt leak, expected verdict e checks de categoria."],
  ["Redacted results persisted to Postgres/Supabase.", "Resultados redigidos persistidos em Postgres/Supabase."],
  ["Severity precedence, overrides, deploy decision, alerts.", "Precedencia de severidade, overrides, decisao de deploy, alertas."],
  ["PR and deploy context with pass/fail and artifact links.", "Contexto de PR e deploy com pass/fail e links de artifact."],
  ["Concise alert for high-severity failures and blocked deploys.", "Alerta conciso para falhas de alta severidade e deploys bloqueados."],
  ["Dashboard Views", "Visoes do dashboard"],
  ["Operational surface for current phase, files, risks, and outcomes.", "Superficie operacional para fase atual, arquivos, riscos e resultados."],
  ["Machine-readable artifact for downstream automation and audits.", "Artifact legivel por maquina para automacao downstream e auditorias."],
  ["S4 SOO redteam workflow is approved with a tracked deviation: direct thin SOO jobs use an explicit framework SHA pin so environment-scoped redteam secrets can be enforced.", "S4 workflow Red Team SOO aprovado com desvio rastreado: jobs diretos e finos no SOO usam pin explicito de SHA do framework para permitir enforcement de secrets com escopo de environment."],
  ["S4 SOO redteam workflow", "S4 workflow Red Team SOO"],
  ["Phase 1B next", "Proximo da Phase 1B"],
  ["S4 operational conditions", "Condicoes operacionais S4"],
  ["Final release governance", "Governanca final de release"],
]);

const PHRASE_PT = [
  [/^(\d+)% complete$/, "$1% completo"],
  [/^(\d+)\/(\d+) tasks$/, "$1/$2 tarefas"],
  [/^(\d+)\/(\d+) criteria$/, "$1/$2 criterios"],
  [/^Current criteria: /, "Criterios atuais: "],
  [/^Next gate: /, "Proximo gate: "],
  [/^Updated /, "Atualizado "],
  [/^Gap: /, "Gap: "],
  [/^Measure: /, "Medir: "],
  [/ referenced files present$/, " arquivos referenciados presentes"],
  [/Open checklist/g, "Abrir checklist"],
  [/criteria/g, "criterios"],
  [/current phase/g, "fase atual"],
  [/implementation/g, "implementacao"],
  [/workflow/g, "workflow"],
  [/staging/g, "staging"],
  [/production/g, "production"],
  [/pending/g, "pendente"],
  [/planned/g, "planejado"],
  [/partial/g, "parcial"],
  [/current/g, "atual"],
  [/done/g, "concluido"],
];

const GLOSSARY = [
  { term: "ADR", en: "Architecture Decision Record. Short document that freezes an architectural decision and rationale.", pt: "Architecture Decision Record. Documento curto que fixa uma decisao arquitetural e sua razao." },
  { term: "API", en: "Application Programming Interface. Contract used by services, tools, or clients to call each other.", pt: "Application Programming Interface. Contrato usado por servicos, ferramentas ou clients para se chamarem." },
  { term: "CI", en: "Continuous Integration. Automated checks that run on pull requests or branches.", pt: "Continuous Integration. Checks automatizados que rodam em pull requests ou branches." },
  { term: "CLI", en: "Command-line interface. Here, the `vt-redteam` terminal tool.", pt: "Command-line interface. Aqui, a ferramenta de terminal `vt-redteam`." },
  { term: "DB", en: "Database. In this project, mainly Supabase/Postgres storage for red-team results.", pt: "Database. Neste projeto, principalmente Supabase/Postgres para resultados Red Team." },
  { term: "DOCX", en: "Microsoft Word document format used by the dense security source documentation.", pt: "Formato Microsoft Word usado pela documentacao densa de seguranca." },
  { term: "E2E", en: "End-to-end test. Test that exercises the full user/tool path instead of a small unit.", pt: "Teste end-to-end. Exercita o fluxo completo do usuario/ferramenta, nao apenas uma unidade pequena." },
  { term: "F1-F7", en: "Framework tasks. Work owned by the vt-agent-redteam framework repo before SOO adoption.", pt: "Tarefas de framework. Trabalho do repo vt-agent-redteam antes da adocao pelo SOO." },
  { term: "JWT", en: "JSON Web Token. Signed token used for scoped service or user authentication.", pt: "JSON Web Token. Token assinado usado para autenticacao com escopo de servico ou usuario." },
  { term: "LLM", en: "Large Language Model. Model class behind the agents and red-team reviewers.", pt: "Large Language Model. Classe de modelo por tras dos agentes e revisores Red Team." },
  { term: "LLM_WIKI", en: "Local architecture and engineering standards vault used as review authority.", pt: "Vault local de padroes de arquitetura e engenharia usado como autoridade de review." },
  { term: "MVP", en: "Minimum Viable Product. Smallest releasable proof that covers the required safety gates.", pt: "Minimum Viable Product. Menor prova liberavel que cobre os safety gates necessarios." },
  { term: "NITPICK", en: "Strict review mode: senior-level detailed review against LLM_WIKI standards.", pt: "Modo de review estrito: revisao detalhada senior contra padroes LLM_WIKI." },
  { term: "OTLP", en: "OpenTelemetry Protocol. Telemetry transport used by some Langfuse tracing paths.", pt: "OpenTelemetry Protocol. Transporte de telemetria usado por alguns fluxos Langfuse." },
  { term: "P0-P3", en: "Priority/severity labels. P0 is highest severity; P3 is lower urgency.", pt: "Labels de prioridade/severidade. P0 e a mais alta; P3 tem menor urgencia." },
  { term: "PII", en: "Personally Identifiable Information. Sensitive user data that must be redacted.", pt: "Personally Identifiable Information. Dado sensivel de usuario que precisa de redacao." },
  { term: "PostHog", en: "Feature-flag and analytics platform used for controlled release gates.", pt: "Plataforma de feature flag e analytics usada para release gates controlados." },
  { term: "PR", en: "Pull Request. Code review/change proposal in GitHub.", pt: "Pull Request. Proposta de mudanca/review no GitHub." },
  { term: "R1-R9", en: "Final release governance tasks. Security, release, audit, and reporting gates.", pt: "Tarefas finais de governanca de release. Gates de seguranca, release, auditoria e relatorio." },
  { term: "RLS", en: "Row-Level Security. Database policy layer that restricts row access.", pt: "Row-Level Security. Camada de policy do banco que restringe acesso por linha." },
  { term: "S1-S7", en: "SOO integration tasks. Consumer-repo onboarding tasks for the Red Team MVP.", pt: "Tarefas de integracao SOO. Onboarding do repo consumidor para o Red Team MVP." },
  { term: "SDK", en: "Software Development Kit. Library package used to integrate with a service.", pt: "Software Development Kit. Pacote de biblioteca usado para integrar com um servico." },
  { term: "SHA", en: "Git commit identifier. Used to pin workflow/package versions immutably.", pt: "Identificador de commit Git. Usado para fixar workflow/package de forma imutavel." },
  { term: "SOO", en: "student-onboarding-orchestration. Target consumer repo for Phase 1B.", pt: "student-onboarding-orchestration. Repo consumidor alvo da Phase 1B." },
  { term: "Supabase", en: "Postgres-backed platform used for application data and red-team result storage.", pt: "Plataforma baseada em Postgres usada para dados da app e storage de resultados Red Team." },
  { term: "URL", en: "Uniform Resource Locator. Address for services, files, APIs, or dashboards.", pt: "Uniform Resource Locator. Endereco de servicos, arquivos, APIs ou dashboards." },
  { term: "VT4S", en: "Varsity Tutors for Schools. Team/context source for this project.", pt: "Varsity Tutors for Schools. Fonte de contexto/time deste projeto." },
  { term: "YAML / JSON", en: "Structured data formats used for manifests, status snapshots, corpus files, and configs.", pt: "Formatos de dados estruturados usados em manifests, snapshots, corpus e configs." },
];

function setText(selector, text) {
  const element = $(selector);
  if (element) element.textContent = text ?? "";
}

function activeCopy() {
  return STATIC_COPY[state.language] ?? STATIC_COPY.en;
}

function t(key) {
  return activeCopy()[key] ?? STATIC_COPY.en[key] ?? key;
}

function translateStatus(status) {
  const text = String(status ?? "");
  if (state.language !== "pt") return text;
  return STATUS_LABELS.pt[text.toLowerCase()] ?? text;
}

function tx(value) {
  const text = String(value ?? "");
  if (state.language !== "pt" || !text) return text;
  if (EXACT_PT.has(text)) return EXACT_PT.get(text);
  let translated = text;
  for (const [pattern, replacement] of PHRASE_PT) {
    translated = translated.replace(pattern, replacement);
  }
  return translated;
}

function applyStaticCopy() {
  document.documentElement.lang = state.language === "pt" ? "pt-BR" : "en";
  document.title = t("hero.title");
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = t(element.dataset.i18n);
  }
  for (const button of document.querySelectorAll("[data-lang-button]")) {
    const active = button.dataset.langButton === state.language;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  }
}

function className(...parts) {
  return parts.filter(Boolean).join(" ");
}

function formatDate(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function statusTone(status) {
  if (status === "done" || status === "passing" || status === "clean") return "pill-live";
  if (status === "current" || status === "manual" || status === "dirty") return "pill-warn";
  if (status === "blocked" || status === "failing" || status === "missing") return "pill-danger";
  return "";
}

function opsTone(status) {
  const normalized = String(status ?? "").toLowerCase().replace(/\s+/g, "-");
  if (["measured", "passing", "green", "ok"].includes(normalized)) return "ok";
  if (["partial", "mixed", "planned"].includes(normalized)) return "warn";
  if (["risk", "blocked", "failing", "not-tested", "pending"].includes(normalized)) return "danger";
  return "neutral";
}

function strategicStatusLabel(status) {
  const normalized = String(status ?? "").toLowerCase();
  if (normalized === "accepted with conditions") return translateStatus("accepted");
  return translateStatus(status ?? "");
}

function renderMetricGrid(metrics) {
  const grid = $("#metricGrid");
  grid.innerHTML = "";
  for (const metric of metrics.slice(0, 4)) {
    const item = document.createElement("div");
    item.className = "metric";
    item.innerHTML = `
      <strong>${metric.value}</strong>
      <span>${tx(metric.label)}</span>
      <small>${tx(metric.detail)}</small>
    `;
    grid.appendChild(item);
  }
}

function renderStrategicView(view) {
  if (!view) return;
  setText("#strategicVerdict", tx(view.verdict));
  setText("#strategicSummary", tx(view.summary));

  const root = $("#strategicList");
  root.innerHTML = "";
  const questionItems = view.iterations.filter((item) => Array.isArray(item.questions) && item.questions.length);
  for (const item of questionItems.slice(0, 3)) {
    const card = document.createElement("div");
    card.className = className("strategic-item", item.status);

    const top = document.createElement("div");
    top.className = "strategic-item-top";

    const title = document.createElement("strong");
    title.textContent = tx(item.iteration);

    const status = document.createElement("span");
    status.textContent = strategicStatusLabel(item.status);
    status.title = item.status ?? "";

    const list = document.createElement("ul");
    list.className = "strategic-questions";
    for (const question of item.questions.slice(0, 3)) {
      const li = document.createElement("li");
      li.textContent = tx(question);
      list.appendChild(li);
    }

    top.append(title, status);
    card.append(top, list);
    root.appendChild(card);
  }
}

function renderCharts(data) {
  const percent = data.progress.percent;
  const ring = $("#progressRing");
  ring.style.setProperty("--progress", `${percent}%`);
  setText("#ringValue", `${percent}%`);

  const root = $("#phaseChart");
  root.innerHTML = "";
  for (const phase of data.phases) {
    const phasePercent = phase.total ? Math.round((phase.done / phase.total) * 100) : 0;
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <div class="bar-row-meta">
        <span>${tx(phase.name).replace("Phase ", "")}</span>
        <strong>${phase.done}/${phase.total}</strong>
      </div>
      <div class="bar-track"><span style="width: ${phasePercent}%"></span></div>
    `;
    root.appendChild(row);
  }
}

function findTaskPhase(phases, taskId) {
  return phases.find((phase) => phase.tasks.some((task) => task.id === taskId));
}

function findFollowingTask(phases, taskId) {
  const tasks = phases.flatMap((phase) => phase.tasks);
  const currentIndex = tasks.findIndex((task) => task.id === taskId);
  return tasks.slice(Math.max(currentIndex + 1, 0)).find((task) => !task.done && task.status !== "manual");
}

function phaseShortName(phase) {
  return phase?.name?.replace(/\s+-\s+.*$/, "")?.replace("Phase ", "Phase ") ?? "Phase";
}

function renderQuickTaskLinks(data) {
  const root = $("#quickTaskLinks");
  if (!root) return;

  const phase = findTaskPhase(data.phases, data.currentTask.id) ?? data.phases.find((item) => item.done < item.total);
  root.innerHTML = "";

  for (const task of phase?.tasks ?? []) {
    const link = document.createElement("a");
    link.href = `#task-${task.id.toLowerCase()}`;
    link.className = className("quick-task-link", task.status);
    link.textContent = `#${task.id}`;
    link.title = task.title;
    root.appendChild(link);
  }
}

function renderCriticalPath(data) {
  const tasks = data.phases.flatMap((phase) => phase.tasks);
  const current = data.currentTask;
  const currentPhase = findTaskPhase(data.phases, current.id) ?? data.phases.find((phase) => phase.done < phase.total) ?? data.phases[0];
  const currentTask = tasks.find((task) => task.id === current.id) ?? current;
  const phaseTasks = currentPhase?.tasks ?? [];
  const nextTask = findFollowingTask(data.phases, current.id);

  setText("#criticalNow", `${current.id}: ${tx(current.title)}`);

  const rail = $("#criticalRail");
  rail.innerHTML = "";
  for (const task of phaseTasks) {
    const node = document.createElement("a");
    node.href = `#task-${task.id.toLowerCase()}`;
    node.className = className("path-node", task?.status);
    node.textContent = task.id;
    node.title = tx(task.title);
    rail.appendChild(node);
  }

  const badges = $("#criticalBadges");
  badges.innerHTML = "";
  const items = [
    tx(`Current criteria: ${currentTask.criteriaComplete ?? 0}/${currentTask.criteriaTotal ?? 0}`),
    tx(`Next gate: ${nextTask ? nextTask.id : "none"}`),
    `${tx(phaseShortName(currentPhase))}: ${currentPhase.done}/${currentPhase.total}`,
  ];
  for (const item of items) {
    const badge = document.createElement("span");
    badge.className = "critical-badge";
    badge.textContent = item;
    badges.appendChild(badge);
  }
}

function renderPhaseLanes(phases) {
  const grid = $("#phaseLanes");
  grid.innerHTML = "";
  for (const phase of phases) {
    const lane = document.createElement("article");
    lane.className = "lane";
    lane.innerHTML = `
      <div class="lane-heading">
        <h3>${tx(phase.name)}</h3>
        <span>${phase.done}/${phase.total}</span>
      </div>
      <div class="task-list"></div>
    `;
    const list = lane.querySelector(".task-list");
    for (const task of phase.tasks) {
      const card = document.createElement("details");
      card.className = className("task-card", task.status);
      card.id = `task-${task.id.toLowerCase()}`;
      const rememberedOpen = state.taskOpen.get(task.id);
      card.open = rememberedOpen ?? task.status === "current";
      const criteria = task.criteria ?? [];
      const criteriaHtml = criteria.map((item) => `
        <li class="criterion ${item.done ? "done" : "pending"}">
          <span class="criterion-mark" aria-hidden="true"></span>
          <p>${tx(item.label)}</p>
        </li>
      `).join("");
      card.innerHTML = `
        <summary>
          <div class="task-top">
            <span class="task-id">${task.id}</span>
          <span class="tiny-pill ${statusTone(task.status)}">${translateStatus(task.status)}</span>
        </div>
          <h3>${tx(task.title)}</h3>
          <p class="task-detail">${tx(task.detail)}</p>
          <div class="criteria-progress">
            <span>${tx(`${task.criteriaComplete ?? 0}/${task.criteriaTotal ?? 0} criteria`)}</span>
            <span>${tx("Open checklist")}</span>
          </div>
        </summary>
        <ul class="criteria-list">${criteriaHtml}</ul>
      `;
      card.addEventListener("toggle", () => {
        state.taskOpen.set(task.id, card.open);
      });
      list.appendChild(card);
    }
    lane.id = phase.id;
    grid.appendChild(lane);
  }
}

function renderArchitecture(flow, feedback) {
  const flowRoot = $("#architectureFlow");
  flowRoot.innerHTML = "";
  for (const node of flow) {
    const item = document.createElement("div");
    item.className = "flow-node";
    item.innerHTML = `<strong>${tx(node.title)}</strong><span>${tx(node.detail)}</span>`;
    flowRoot.appendChild(item);
  }

  const feedbackRoot = $("#feedbackChannels");
  feedbackRoot.innerHTML = "";
  for (const channel of feedback) {
    const item = document.createElement("div");
    item.className = "feedback-card";
    item.innerHTML = `<h3>${tx(channel.title)}</h3><p>${tx(channel.detail)}</p>`;
    feedbackRoot.appendChild(item);
  }
}

function renderOverview(blocks) {
  const root = $("#overviewBlocks");
  root.innerHTML = "";
  for (const block of blocks) {
    const item = document.createElement("div");
    item.className = "overview-card";
    item.innerHTML = `<h3>${tx(block.title)}</h3><p>${tx(block.detail)}</p>`;
    root.appendChild(item);
  }
}

function renderFileMap(groups) {
  const root = $("#fileMap");
  root.innerHTML = "";
  let total = 0;
  let present = 0;

  for (const group of groups) {
    const section = document.createElement("article");
    section.className = "file-group";
    section.innerHTML = `<h3>${tx(group.title)}</h3><div class="file-list"></div>`;
    const list = section.querySelector(".file-list");
    for (const file of group.files) {
      total += 1;
      if (file.exists) present += 1;
      const item = document.createElement(file.href ? "a" : "div");
      item.className = className("file-item", !file.exists && "file-missing");
      if (file.href) item.href = file.href;
      if (file.href) item.target = "_blank";
      item.innerHTML = `
        <div class="file-title">
          <span class="file-badge ${file.exists ? "ok" : "missing"}">${file.exists ? "OK" : "MISS"}</span>
          <strong title="${file.path}">${tx(file.label)}</strong>
        </div>
        <div class="file-meta">${file.path}</div>
      `;
      list.appendChild(item);
    }
    root.appendChild(section);
  }

  setText("#fileCountLabel", tx(`${present}/${total} referenced files present`));
}

function renderRisks(risks) {
  const root = $("#riskList");
  root.innerHTML = "";
  for (const risk of risks) {
    const item = document.createElement("div");
    item.className = className("risk-card", risk.level);
    item.innerHTML = `<h3>${tx(risk.title)}</h3><p>${tx(risk.detail)}</p>`;
    root.appendChild(item);
  }
}

function renderOperationalReadiness(readiness) {
  if (!readiness) return;
  setText("#opsUpdatedAt", tx(`Updated ${formatDate(readiness.updatedAt)}`));
  setText("#opsGuarantee", tx(readiness.serviceGuarantee));

  const summaryRoot = $("#opsSummaryGrid");
  summaryRoot.innerHTML = "";
  for (const item of readiness.summaryCards ?? []) {
    const card = document.createElement("div");
    card.className = className("ops-summary-card", opsTone(item.value));
    const label = document.createElement("span");
    label.textContent = tx(item.label);
    const value = document.createElement("strong");
    value.textContent = translateStatus(item.value);
    const detail = document.createElement("p");
    detail.textContent = tx(item.detail);
    card.append(label, value, detail);
    summaryRoot.appendChild(card);
  }

  const phaseRoot = $("#opsPhaseGrid");
  phaseRoot.innerHTML = "";
  for (const phase of readiness.phaseGates ?? []) {
    const card = document.createElement("article");
    card.className = className("ops-phase-card", opsTone(phase.status));

    const header = document.createElement("div");
    header.className = "ops-card-header";
    const title = document.createElement("strong");
    title.textContent = tx(phase.phase);
    const status = document.createElement("span");
    status.textContent = translateStatus(phase.status);
    header.append(title, status);

    const evidence = document.createElement("p");
    evidence.className = "ops-evidence";
    evidence.textContent = tx(phase.evidence);

    const checks = document.createElement("div");
    checks.className = "ops-checks";
    for (const check of phase.checks ?? []) {
      const row = document.createElement("div");
      row.className = className("ops-check", opsTone(check.status));
      const name = document.createElement("strong");
      name.textContent = tx(check.name);
      const metric = document.createElement("span");
      metric.textContent = tx(check.metric);
      const next = document.createElement("small");
      next.textContent = tx(check.next);
      row.append(name, metric, next);
      checks.appendChild(row);
    }

    card.append(header, evidence, checks);
    phaseRoot.appendChild(card);
  }

  const failureRoot = $("#opsFailureList");
  failureRoot.innerHTML = "";
  for (const mode of readiness.failureModes ?? []) {
    const item = document.createElement("article");
    item.className = className("ops-side-card", opsTone(mode.status));
    item.innerHTML = `
      <div class="ops-card-header">
        <strong></strong>
        <span></span>
      </div>
      <p></p>
      <small></small>
    `;
    item.querySelector("strong").textContent = tx(mode.name);
    item.querySelector("span").textContent = translateStatus(mode.status);
    item.querySelector("p").textContent = tx(mode.currentBehavior);
    item.querySelector("small").textContent = tx(`Gap: ${mode.gap}`);
    failureRoot.appendChild(item);
  }

  const bottleneckRoot = $("#opsBottleneckList");
  bottleneckRoot.innerHTML = "";
  for (const bottleneck of readiness.bottlenecks ?? []) {
    const item = document.createElement("article");
    item.className = className("ops-side-card", opsTone(bottleneck.risk === "high" ? "risk" : "planned"));
    item.innerHTML = `
      <div class="ops-card-header">
        <strong></strong>
        <span></span>
      </div>
      <p></p>
      <small></small>
    `;
    item.querySelector("strong").textContent = tx(bottleneck.name);
    item.querySelector("span").textContent = translateStatus(bottleneck.risk);
    item.querySelector("p").textContent = tx(bottleneck.why);
    item.querySelector("small").textContent = tx(`Measure: ${bottleneck.measurement}`);
    bottleneckRoot.appendChild(item);
  }
}

function renderGlossary() {
  const root = $("#glossaryList");
  if (!root) return;
  root.innerHTML = "";
  for (const item of GLOSSARY) {
    const card = document.createElement("article");
    card.className = "glossary-card";
    const definition = state.language === "pt" ? item.pt : item.en;
    card.innerHTML = `<h3>${item.term}</h3><p>${definition}</p>`;
    root.appendChild(card);
  }
}

function renderCommits(commits) {
  const root = $("#commitList");
  root.innerHTML = "";
  for (const commit of commits) {
    const item = document.createElement("li");
    item.innerHTML = `
      <span class="commit-hash">${commit.hash}</span>
      <span class="commit-message">${commit.message}</span>
    `;
    root.appendChild(item);
  }
}

function renderStatus(data) {
  state.lastData = data;
  applyStaticCopy();
  const current = data.currentTask;
  const testTone = statusTone(data.testStatus.status);
  const worktreeTone = data.git.isDirty ? "pill-warn" : "pill-live";

  $("#syncState").className = "pill pill-live";
  setText("#syncState", tx("Live data"));

  $("#branchPill").className = "pill";
  setText("#branchPill", data.git.branch);

  $("#worktreePill").className = className("pill", worktreeTone);
  setText("#worktreePill", tx(data.git.isDirty ? "Dirty worktree" : "Clean worktree"));

  setText("#currentStageTitle", `${current.id}: ${tx(current.title)}`);
  setText("#currentStageBody", tx(current.detail));
  $("#stageDot").className = className("status-dot", current.status === "done" && "done");
  const currentTaskNav = $("#currentTaskNav");
  currentTaskNav.textContent = `#${current.id}`;
  currentTaskNav.href = `#task-${current.id.toLowerCase()}`;

  setText("#progressLabel", tx(`${data.progress.percent}% complete`));
  setText("#taskCountLabel", tx(`${data.progress.done}/${data.progress.total} tasks`));
  $("#progressFill").style.width = `${data.progress.percent}%`;

  setText("#nextActionTitle", tx(data.nextAction.title));
  setText("#nextActionBody", tx(data.nextAction.detail));
  const followingTask = findFollowingTask(data.phases, current.id);
  setText("#followingActionTitle", followingTask ? `${followingTask.id} - ${tx(followingTask.title)}` : tx("No queued action"));
  setText("#followingActionBody", tx(followingTask?.detail ?? "All non-manual implementation tasks are complete."));

  setText("#gitSignal", `${data.git.shortStatus}; ${data.git.aheadBehind}`);
  setText("#testSignal", tx(`${data.testStatus.summary}`));
  setText("#syncSignal", formatDate(data.generatedAt));

  const testPill = $("#testSignal");
  testPill.className = testTone;

  renderStrategicView(data.strategicView);
  renderMetricGrid(data.metrics);
  renderCharts(data);
  renderQuickTaskLinks(data);
  renderCriticalPath(data);
  renderPhaseLanes(data.phases);
  renderOperationalReadiness(data.operationalReadiness);
  renderArchitecture(data.architecture.flow, data.architecture.feedbackChannels);
  renderOverview(data.overview);
  renderFileMap(data.fileGroups);
  renderRisks(data.risks);
  renderCommits(data.commits);
  renderGlossary();
}

function renderLoadError(error) {
  applyStaticCopy();
  $("#syncState").className = "pill pill-danger";
  setText("#syncState", tx("Data unavailable"));
  setText("#currentStageTitle", tx("Dashboard data not loaded"));
  setText(
    "#currentStageBody",
    tx(`Could not read ${STATUS_URL}. Run the dashboard server script or generate the JSON once. ${error.message}`)
  );
}

async function loadStatus() {
  try {
    const response = await fetch(`${STATUS_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    renderStatus(data);
  } catch (error) {
    renderLoadError(error);
  }
}

function setLanguage(language) {
  state.language = language;
  localStorage.setItem("redteam-dashboard-language", language);
  applyStaticCopy();
  if (state.lastData) renderStatus(state.lastData);
  else renderGlossary();
}

for (const button of document.querySelectorAll("[data-lang-button]")) {
  button.addEventListener("click", () => setLanguage(button.dataset.langButton));
}

$("#refreshButton").addEventListener("click", loadStatus);
applyStaticCopy();
renderGlossary();
loadStatus();
state.timer = window.setInterval(loadStatus, REFRESH_MS);
