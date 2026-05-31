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
  for (const item of view.iterations.slice(0, 3)) {
    const card = document.createElement("div");
    card.className = className("strategic-item", item.status);
    card.innerHTML = `
      <div class="strategic-item-top">
        <strong>${item.iteration}</strong>
        <span>${item.status}</span>
      </div>
      <p>${item.result}</p>
    `;
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
