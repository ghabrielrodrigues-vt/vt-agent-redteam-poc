const STATUS_URL = "./data/redteam-status.json";
const REFRESH_MS = 5000;

const $ = (selector) => document.querySelector(selector);

const state = {
  timer: null,
  lastData: null,
  taskOpen: new Map(),
};

function setText(selector, text) {
  const element = $(selector);
  if (element) element.textContent = text ?? "";
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
  if (normalized === "accepted with conditions") return "accepted";
  return status ?? "";
}

function renderMetricGrid(metrics) {
  const grid = $("#metricGrid");
  grid.innerHTML = "";
  for (const metric of metrics.slice(0, 4)) {
    const item = document.createElement("div");
    item.className = "metric";
    item.innerHTML = `
      <strong>${metric.value}</strong>
      <span>${metric.label}</span>
      <small>${metric.detail}</small>
    `;
    grid.appendChild(item);
  }
}

function renderStrategicView(view) {
  if (!view) return;
  setText("#strategicVerdict", view.verdict);
  setText("#strategicSummary", view.summary);

  const root = $("#strategicList");
  root.innerHTML = "";
  const questionItems = view.iterations.filter((item) => Array.isArray(item.questions) && item.questions.length);
  for (const item of questionItems.slice(0, 3)) {
    const card = document.createElement("div");
    card.className = className("strategic-item", item.status);

    const top = document.createElement("div");
    top.className = "strategic-item-top";

    const title = document.createElement("strong");
    title.textContent = item.iteration;

    const status = document.createElement("span");
    status.textContent = strategicStatusLabel(item.status);
    status.title = item.status ?? "";

    const list = document.createElement("ul");
    list.className = "strategic-questions";
    for (const question of item.questions.slice(0, 3)) {
      const li = document.createElement("li");
      li.textContent = question;
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
        <span>${phase.name.replace("Phase ", "")}</span>
        <strong>${phase.done}/${phase.total}</strong>
      </div>
      <div class="bar-track"><span style="width: ${phasePercent}%"></span></div>
    `;
    root.appendChild(row);
  }
}

function renderCriticalPath(data) {
  const tasks = data.phases.flatMap((phase) => phase.tasks);
  const current = data.currentTask;
  const phaseOne = data.phases[0];
  const currentTask = tasks.find((task) => task.id === current.id) ?? current;
  const nextTask = tasks.find((task) => !task.done && task.id !== current.id && task.status !== "manual");
  const phaseOneTasks = phaseOne.tasks.map((task) => task.id);

  setText("#criticalNow", `${current.id}: ${current.title}`);

  const rail = $("#criticalRail");
  rail.innerHTML = "";
  for (const id of phaseOneTasks) {
    const task = tasks.find((item) => item.id === id);
    const node = document.createElement("a");
    node.href = `#task-${id.toLowerCase()}`;
    node.className = className("path-node", task?.status);
    node.textContent = id;
    rail.appendChild(node);
  }

  const badges = $("#criticalBadges");
  badges.innerHTML = "";
  const items = [
    `Current criteria: ${currentTask.criteriaComplete ?? 0}/${currentTask.criteriaTotal ?? 0}`,
    `Next gate: ${nextTask ? nextTask.id : "none"}`,
    `Phase 1A: ${phaseOne.done}/${phaseOne.total}`,
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
        <h3>${phase.name}</h3>
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
          <p>${item.label}</p>
        </li>
      `).join("");
      card.innerHTML = `
        <summary>
          <div class="task-top">
            <span class="task-id">${task.id}</span>
            <span class="tiny-pill ${statusTone(task.status)}">${task.status}</span>
          </div>
          <h3>${task.title}</h3>
          <p class="task-detail">${task.detail}</p>
          <div class="criteria-progress">
            <span>${task.criteriaComplete ?? 0}/${task.criteriaTotal ?? 0} criteria</span>
            <span>Open checklist</span>
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
    item.innerHTML = `<strong>${node.title}</strong><span>${node.detail}</span>`;
    flowRoot.appendChild(item);
  }

  const feedbackRoot = $("#feedbackChannels");
  feedbackRoot.innerHTML = "";
  for (const channel of feedback) {
    const item = document.createElement("div");
    item.className = "feedback-card";
    item.innerHTML = `<h3>${channel.title}</h3><p>${channel.detail}</p>`;
    feedbackRoot.appendChild(item);
  }
}

function renderOverview(blocks) {
  const root = $("#overviewBlocks");
  root.innerHTML = "";
  for (const block of blocks) {
    const item = document.createElement("div");
    item.className = "overview-card";
    item.innerHTML = `<h3>${block.title}</h3><p>${block.detail}</p>`;
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
    section.innerHTML = `<h3>${group.title}</h3><div class="file-list"></div>`;
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
          <strong title="${file.path}">${file.label}</strong>
        </div>
        <div class="file-meta">${file.path}</div>
      `;
      list.appendChild(item);
    }
    root.appendChild(section);
  }

  setText("#fileCountLabel", `${present}/${total} referenced files present`);
}

function renderRisks(risks) {
  const root = $("#riskList");
  root.innerHTML = "";
  for (const risk of risks) {
    const item = document.createElement("div");
    item.className = className("risk-card", risk.level);
    item.innerHTML = `<h3>${risk.title}</h3><p>${risk.detail}</p>`;
    root.appendChild(item);
  }
}

function renderOperationalReadiness(readiness) {
  if (!readiness) return;
  setText("#opsUpdatedAt", `Updated ${formatDate(readiness.updatedAt)}`);
  setText("#opsGuarantee", readiness.serviceGuarantee);

  const summaryRoot = $("#opsSummaryGrid");
  summaryRoot.innerHTML = "";
  for (const item of readiness.summaryCards ?? []) {
    const card = document.createElement("div");
    card.className = className("ops-summary-card", opsTone(item.value));
    const label = document.createElement("span");
    label.textContent = item.label;
    const value = document.createElement("strong");
    value.textContent = item.value;
    const detail = document.createElement("p");
    detail.textContent = item.detail;
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
    title.textContent = phase.phase;
    const status = document.createElement("span");
    status.textContent = phase.status;
    header.append(title, status);

    const evidence = document.createElement("p");
    evidence.className = "ops-evidence";
    evidence.textContent = phase.evidence;

    const checks = document.createElement("div");
    checks.className = "ops-checks";
    for (const check of phase.checks ?? []) {
      const row = document.createElement("div");
      row.className = className("ops-check", opsTone(check.status));
      const name = document.createElement("strong");
      name.textContent = check.name;
      const metric = document.createElement("span");
      metric.textContent = check.metric;
      const next = document.createElement("small");
      next.textContent = check.next;
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
    item.querySelector("strong").textContent = mode.name;
    item.querySelector("span").textContent = mode.status;
    item.querySelector("p").textContent = mode.currentBehavior;
    item.querySelector("small").textContent = `Gap: ${mode.gap}`;
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
    item.querySelector("strong").textContent = bottleneck.name;
    item.querySelector("span").textContent = bottleneck.risk;
    item.querySelector("p").textContent = bottleneck.why;
    item.querySelector("small").textContent = `Measure: ${bottleneck.measurement}`;
    bottleneckRoot.appendChild(item);
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
  const current = data.currentTask;
  const testTone = statusTone(data.testStatus.status);
  const worktreeTone = data.git.isDirty ? "pill-warn" : "pill-live";

  $("#syncState").className = "pill pill-live";
  setText("#syncState", "Live data");

  $("#branchPill").className = "pill";
  setText("#branchPill", data.git.branch);

  $("#worktreePill").className = className("pill", worktreeTone);
  setText("#worktreePill", data.git.isDirty ? "Dirty worktree" : "Clean worktree");

  setText("#currentStageTitle", `${current.id}: ${current.title}`);
  setText("#currentStageBody", current.detail);
  $("#stageDot").className = className("status-dot", current.status === "done" && "done");
  const currentTaskNav = $("#currentTaskNav");
  currentTaskNav.textContent = `#${current.id}`;
  currentTaskNav.href = `#task-${current.id.toLowerCase()}`;

  setText("#progressLabel", `${data.progress.percent}% complete`);
  setText("#taskCountLabel", `${data.progress.done}/${data.progress.total} tasks`);
  $("#progressFill").style.width = `${data.progress.percent}%`;

  setText("#nextActionTitle", data.nextAction.title);
  setText("#nextActionBody", data.nextAction.detail);

  setText("#gitSignal", `${data.git.shortStatus}; ${data.git.aheadBehind}`);
  setText("#testSignal", `${data.testStatus.summary}`);
  setText("#syncSignal", formatDate(data.generatedAt));

  const testPill = $("#testSignal");
  testPill.className = testTone;

  renderStrategicView(data.strategicView);
  renderMetricGrid(data.metrics);
  renderCharts(data);
  renderCriticalPath(data);
  renderPhaseLanes(data.phases);
  renderOperationalReadiness(data.operationalReadiness);
  renderArchitecture(data.architecture.flow, data.architecture.feedbackChannels);
  renderOverview(data.overview);
  renderFileMap(data.fileGroups);
  renderRisks(data.risks);
  renderCommits(data.commits);
}

function renderLoadError(error) {
  $("#syncState").className = "pill pill-danger";
  setText("#syncState", "Data unavailable");
  setText("#currentStageTitle", "Dashboard data not loaded");
  setText(
    "#currentStageBody",
    `Could not read ${STATUS_URL}. Run the dashboard server script or generate the JSON once. ${error.message}`
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

$("#refreshButton").addEventListener("click", loadStatus);
loadStatus();
state.timer = window.setInterval(loadStatus, REFRESH_MS);
