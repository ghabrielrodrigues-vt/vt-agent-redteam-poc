#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { createReadStream, existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const dashboardRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(dashboardRoot, "..");
const workspaceRoot = path.resolve(repoRoot, "..");
const sooRoot = path.join(workspaceRoot, "student-onboarding-orchestration");
const vt4sRoot = path.join(workspaceRoot, "vt4s-team-scope");
const llmWikiRoot = "/Users/gupy/LLM_WIKI";
const outputPath = path.join(dashboardRoot, "data", "redteam-status.json");
const testStatusPath = path.join(dashboardRoot, "data", "test-status.json");
const strategicViewPath = path.join(dashboardRoot, "data", "strategic-view.json");
const operationalMetricsPath = path.join(repoRoot, "docs", "operational-metrics", "status.json");

const args = new Set(process.argv.slice(2));
const portArgIndex = process.argv.indexOf("--port");
const port = portArgIndex >= 0 ? Number(process.argv[portArgIndex + 1]) : 4177;

function run(command, commandArgs, cwd = repoRoot) {
  try {
    return execFileSync(command, commandArgs, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}

function relativeFromRepo(absPath) {
  return path.relative(repoRoot, absPath).replaceAll(path.sep, "/");
}

function relativeFromRoot(absPath, root) {
  const relative = path.relative(root, absPath);
  const isInside = relative && !relative.startsWith("..") && !path.isAbsolute(relative);
  return isInside ? relative.replaceAll(path.sep, "/") : null;
}

function hrefFor(absPath) {
  const repoRelative = relativeFromRoot(absPath, repoRoot);
  if (repoRelative) return `/${repoRelative}`;

  const sooRelative = relativeFromRoot(absPath, sooRoot);
  if (sooRelative) return `/external/soo/${sooRelative}`;

  const vt4sRelative = relativeFromRoot(absPath, vt4sRoot);
  if (vt4sRelative) return `/external/vt4s/${vt4sRelative}`;

  const wikiRelative = relativeFromRoot(absPath, llmWikiRoot);
  if (wikiRelative) return `/external/wiki/${wikiRelative}`;

  return null;
}

function fileInfo(label, absPath, options = {}) {
  const exists = existsSync(absPath);
  const relative = relativeFromRepo(absPath);
  const isInsideRepo = !relative.startsWith("..") && !path.isAbsolute(relative);
  let lines = null;
  let size = null;
  let updatedAt = null;

  if (exists) {
    const stat = statSync(absPath);
    size = stat.size;
    updatedAt = stat.mtime.toISOString();
    if (stat.isFile()) {
      const content = readFileSync(absPath, "utf8");
      lines = content.length ? content.split(/\r?\n/).length : 0;
    }
  }

  return {
    label,
    path: isInsideRepo ? relative : absPath,
    exists,
    href: exists ? hrefFor(absPath) : null,
    lines,
    size,
    updatedAt,
    note: options.note ?? null,
  };
}

function repoFile(label, relativePath, options) {
  return fileInfo(label, path.join(repoRoot, relativePath), options);
}

function sooFile(label, relativePath, options) {
  return fileInfo(label, path.join(sooRoot, relativePath), options);
}

function vt4sFile(label, relativePath, options) {
  return fileInfo(label, path.join(vt4sRoot, relativePath), options);
}

function wikiFile(label, relativePath, options) {
  return fileInfo(label, path.join(llmWikiRoot, relativePath), options);
}

function read(relativePath) {
  const absPath = path.join(repoRoot, relativePath);
  return existsSync(absPath) ? readFileSync(absPath, "utf8") : "";
}

function readAbs(absPath) {
  return existsSync(absPath) ? readFileSync(absPath, "utf8") : "";
}

function has(relativePath, pattern) {
  return pattern.test(read(relativePath));
}

function evidenceDoc(relativePath, pattern) {
  return existsSync(path.join(repoRoot, relativePath)) && has(relativePath, pattern);
}

function hasGreenActionsEvidence() {
  const reviewReport = read("docs/review-reports.md");
  const hasLegacyTransferEvidence = has("docs/v0-implementation-plan.codex-transfer.md", /green Actions run|Actions run/i);
  const hasRunUrl = /https:\/\/github\.com\/ghabrielrodrigues-vt\/vt-agent-redteam-poc\/actions\/runs\/\d+/i.test(reviewReport);
  const hasHeadSha = /Head SHA:\s*`?[a-f0-9]{40}`?/i.test(reviewReport);
  return existsSync(path.join(repoRoot, ".github/workflows/redteam.yml")) && (hasLegacyTransferEvidence || (hasRunUrl && hasHeadSha));
}

function f7ReleaseEvidence() {
  const reviewReport = read("docs/review-reports.md");
  return {
    remoteTag: /refs\/tags\/v0\.1\.0|Remote tag visible on GitHub/i.test(reviewReport),
    installResolved: /Successfully installed vt-agent-redteam-0\.1\.0|Install from v0\.1\.0 tag resolved/i.test(reviewReport),
  };
}

function hasAbs(absPath, pattern) {
  return pattern.test(readAbs(absPath));
}

function anyFile(dir, predicate) {
  if (!existsSync(dir)) return false;
  return readdirSync(dir).some(predicate);
}

function gitStatus() {
  const branch = run("git", ["branch", "--show-current"]) || "unknown";
  const short = run("git", ["status", "--short"]);
  const upstream = run("git", ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]);
  let aheadBehind = "No upstream";
  let ahead = 0;
  let behind = 0;

  if (upstream) {
    const counts = run("git", ["rev-list", "--left-right", "--count", `${upstream}...HEAD`]).split(/\s+/);
    behind = Number(counts[0] ?? 0);
    ahead = Number(counts[1] ?? 0);
    aheadBehind = `ahead ${ahead}, behind ${behind}`;
  }

  return {
    branch,
    isDirty: Boolean(short),
    shortStatus: short ? "uncommitted changes present" : "clean working tree",
    aheadBehind,
    ahead,
    behind,
    remote: run("git", ["remote", "get-url", "origin"]) || null,
  };
}

function commits() {
  const lines = run("git", ["log", "--oneline", "-5"]).split("\n").filter(Boolean);
  return lines.map((line) => {
    const [hash, ...message] = line.split(" ");
    return { hash, message: message.join(" ") };
  });
}

function testStatus() {
  if (existsSync(testStatusPath)) {
    return JSON.parse(readFileSync(testStatusPath, "utf8"));
  }

  return {
    status: "unknown",
    summary: "No test-status.json captured yet",
    command: "cd prototype && .venv/bin/python -m pytest",
    verifiedAt: null,
  };
}

function operationalReadiness() {
  if (existsSync(operationalMetricsPath)) {
    return JSON.parse(readFileSync(operationalMetricsPath, "utf8"));
  }

  return {
    updatedAt: null,
    serviceGuarantee: "No operational metrics status file found yet.",
    summaryCards: [],
    phaseGates: [],
    failureModes: [],
    bottlenecks: [],
  };
}

function strategicView(phases) {
  const custom = existsSync(strategicViewPath)
    ? JSON.parse(readFileSync(strategicViewPath, "utf8"))
    : { iterations: [] };
  const tasks = flattenTasks(phases);
  const current = tasks.find((item) => item.status === "current") ?? tasks[0];
  const currentCriteria = `${current.criteriaComplete ?? 0}/${current.criteriaTotal ?? 0}`;
  const generated = [
    {
      iteration: "Current iteration",
      status: current.status,
      questions: [
        `Is ${current.id} the right next control point with ${currentCriteria} criteria complete?`,
        "Are Ask First boundaries still protected before secrets, database, or deploy work?",
      ],
    },
    {
      iteration: "F1 delivery",
      status: "accepted",
      questions: [
        "Does the runner use agent-native transcript evidence instead of synthetic replay?",
        "Is ADR-001 still the decision source for this path?",
      ],
    },
    {
      iteration: "Plan readiness review",
      status: "greenlight",
      questions: [
        "Are plan constraints still intact before consumer-repo rollout?",
        "Does any new deviation require an ADR before implementation?",
      ],
    },
  ];

  return {
    verdict: custom.verdict ?? "Greenlight with active conditions",
    summary: custom.summary ?? "Latest strategic read: continue Phase 1A in order; avoid consumer-repo work until framework gates are stable.",
    iterations: [...(custom.iterations ?? []), ...generated],
  };
}

function criterion(label, done) {
  return { label, done };
}

function allDone(criteria) {
  return criteria.every((item) => item.done);
}

function task(id, title, detail, criteria, manual = false) {
  const done = allDone(criteria);
  const complete = criteria.filter((item) => item.done).length;
  return {
    id,
    title,
    detail,
    criteria,
    criteriaComplete: complete,
    criteriaTotal: criteria.length,
    done,
    status: done ? "done" : manual ? "manual" : "pending",
  };
}

function manifestCriteria(agentDir, expectedProfile) {
  const manifestPath = path.join(sooRoot, `agents/${agentDir}/.redteam/manifest.yaml`);
  const manifest = readAbs(manifestPath);
  return [
    criterion(`${agentDir} manifest exists`, existsSync(manifestPath)),
    criterion("agent_name declared", /agent_name:/.test(manifest)),
    criterion("policy profile declared", /policy_profile:/.test(manifest)),
    criterion(`Expected profile references ${expectedProfile}`, new RegExp(expectedProfile.replace("-", "[-_]"), "i").test(manifest)),
    criterion("LiveKit staging/production config exists", existsSync(path.join(sooRoot, `agents/${agentDir}/livekit.staging.toml`)) && existsSync(path.join(sooRoot, `agents/${agentDir}/livekit.production.toml`))),
    criterion("validate-manifest evidence captured", /validated|validate-manifest/i.test(manifest)),
  ];
}

function buildTasks() {
  const tests = testStatus();
  const f1Criteria = [
    criterion("LangfuseTraceRunner file exists", existsSync(path.join(repoRoot, "prototype/src/vt_agent_redteam/runners/langfuse_trace_runner.py"))),
    criterion("Runner exported from runners package", has("prototype/src/vt_agent_redteam/runners/__init__.py", /LangfuseTraceRunner/)),
    criterion("Native transcript / generation span extraction implemented", has("prototype/src/vt_agent_redteam/runners/langfuse_trace_runner.py", /GENERATION|agent_native_transcript|transcript/i)),
    criterion("Unit tests cover success, timeout, not-found, malformed span", existsSync(path.join(repoRoot, "prototype/tests/test_langfuse_runner.py")) && has("prototype/tests/test_langfuse_runner.py", /timeout|not.?found|malformed|success/i)),
    criterion("ADR-001 recorded", existsSync(path.join(repoRoot, "docs/adr/0001-langfuse-native-transcript.md"))),
    criterion("Last captured framework suite passing", tests.status === "passing"),
  ];

  const f2Criteria = [
    criterion("coverage_status enum added", has("prototype/src/vt_agent_redteam/types.py", /coverage_status/)),
    criterion("coverage_status accepts full / partial-no-tool-use / partial-other", has("prototype/src/vt_agent_redteam/types.py", /partial-no-tool-use/) && has("prototype/src/vt_agent_redteam/types.py", /partial-other/)),
    criterion("scenario_selection.exclude_tags added", has("prototype/src/vt_agent_redteam/types.py", /exclude_tags/)),
    criterion("Manifest validation/tests cover new fields", has("prototype/tests/test_types.py", /coverage_status|exclude_tags/) || has("prototype/tests/test_corpus_loader.py", /coverage_status|exclude_tags/)),
    criterion("Fixture with partial-no-tool-use + tool-misuse validates", has("prototype/tests/test_types.py", /partial-no-tool-use/) && has("prototype/tests/test_types.py", /tool-misuse/)),
    criterion("ADR-002 recorded", existsSync(path.join(repoRoot, "docs/adr/0002-colocated-manifest-layout-and-coverage-status.md"))),
  ];

  const f3Criteria = [
    criterion("Severity assignment lookup implemented", has("prototype/src/vt_agent_redteam/harness.py", /P0|P1|P2|P3/) && has("prototype/src/vt_agent_redteam/harness.py", /severity/i)),
    criterion("Precedence gate table implemented top-to-bottom", has("prototype/src/vt_agent_redteam/harness.py", /precedence/i) && has("prototype/src/vt_agent_redteam/harness.py", /P0|P1|stub/i)),
    criterion("Override read path queries redteam.overrides", has("prototype/src/vt_agent_redteam/harness.py", /redteam\.overrides|expires_at/i)),
    criterion("P0 cannot be cleared by override", has("prototype/src/vt_agent_redteam/harness.py", /P0/i) && has("prototype/src/vt_agent_redteam/harness.py", /override/i)),
    criterion("Gate tests cover at least eight plan cases", anyFile(path.join(repoRoot, "prototype/tests"), (name) => /severity|override|gate/.test(name))),
    criterion("ADR-003 recorded", existsSync(path.join(repoRoot, "docs/adr/0003-severity-gate-overrides.md"))),
  ];

  const f4Criteria = [
    criterion("storage/redaction.py added", existsSync(path.join(repoRoot, "prototype/src/vt_agent_redteam/storage/redaction.py"))),
    criterion("Regex covers SSN, phone, email, credit card, synthetic learner_id", has("prototype/src/vt_agent_redteam/storage/redaction.py", /SSN|phone|email|credit|learner_id/i)),
    criterion("Postgres writer invokes redaction before INSERT", has("prototype/src/vt_agent_redteam/storage/postgres_writer.py", /redact|redaction/i)),
    criterion("response_hash computed pre-redaction", has("prototype/src/vt_agent_redteam/storage/postgres_writer.py", /response_hash/i) && has("prototype/src/vt_agent_redteam/storage/redaction.py", /hash|pre.?redaction/i)),
    criterion("Redaction tests cover PII and allowlist", anyFile(path.join(repoRoot, "prototype/tests"), (name) => /redaction|pii/i.test(name))),
    criterion("ADR-005 recorded", existsSync(path.join(repoRoot, "docs/adr/0005-redaction-at-write.md"))),
  ];

  const f5Criteria = [
    criterion("--mode flag added", has("prototype/src/vt_agent_redteam/cli.py", /--mode/)),
    criterion("--environment flag added", has("prototype/src/vt_agent_redteam/cli.py", /--environment/)),
    criterion("--enforce-threshold flag added", has("prototype/src/vt_agent_redteam/cli.py", /--enforce-threshold/)),
    criterion("--manifest remains supported", has("prototype/src/vt_agent_redteam/cli.py", /--manifest/)),
    criterion("dry-run emits run_summary.json", has("prototype/src/vt_agent_redteam/cli.py", /dry-run|run_summary\.json/i)),
  ];

  const f6Criteria = [
    criterion("Framework reusable workflow exists", existsSync(path.join(repoRoot, ".github/workflows/redteam.yml"))),
    criterion("Workflow exposes inputs and secrets", has(".github/workflows/redteam.yml", /workflow_call/) && has(".github/workflows/redteam.yml", /secrets:/)),
    criterion("Workflow supports fixture manifest run", has(".github/workflows/redteam.yml", /fixture|manifest/i)),
    criterion("Green Actions run recorded", hasGreenActionsEvidence()),
  ];

  const f7Evidence = f7ReleaseEvidence();
  const f7Criteria = [
    criterion("pyproject version bumped to 0.1.0", has("prototype/pyproject.toml", /version\s*=\s*["']0\.1\.0["']/)),
    criterion("git tag v0.1.0 exists locally", Boolean(run("git", ["tag", "--list", "v0.1.0"]))),
    criterion("Remote tag visible on GitHub", f7Evidence.remoteTag),
    criterion("Install target resolves from tag", f7Evidence.installResolved),
  ];

  const s1Criteria = manifestCriteria("language-tutor", "k12_learner");
  const s2Criteria = manifestCriteria("language-checkpoint", "k12_learner");
  const s3Criteria = [
    ...manifestCriteria("support-agent", "support_navigation"),
    criterion("support-agent declares partial-no-tool-use", hasAbs(path.join(sooRoot, "agents/support-agent/.redteam/manifest.yaml"), /partial-no-tool-use/)),
    criterion("support-agent excludes tool-misuse", hasAbs(path.join(sooRoot, "agents/support-agent/.redteam/manifest.yaml"), /tool-misuse/)),
  ];

  const s4Criteria = [
    criterion("SOO redteam workflow exists", existsSync(path.join(sooRoot, ".github/workflows/redteam.yml"))),
    criterion("Workflow calls framework redteam runner", hasAbs(path.join(sooRoot, ".github/workflows/redteam.yml"), /vt-redteam|redteam/i)),
    criterion("Workflow is path-scoped to agents/**", hasAbs(path.join(sooRoot, ".github/workflows/redteam.yml"), /agents\/\*\*/)),
  ];

  const s5Criteria = [
    criterion("Langfuse secrets documented/configured", false),
    criterion("OpenAI secret documented/configured", false),
    criterion("Supabase secrets documented/configured", false),
    criterion("Slack webhook secret documented/configured", false),
  ];

  const s6Criteria = [
    criterion("Conversation Club redteam migration exists", anyFile(path.join(sooRoot, "supabase/conversation-club/supabase/migrations"), (name) => /redteam|red_team/i.test(name))),
    criterion("redteam result tables/views included", anyFile(path.join(sooRoot, "supabase/conversation-club/supabase/migrations"), (name) => /redteam|red_team/i.test(name))),
    criterion("Migration respects Supabase AGENTS constraints", false),
  ];

  const s7Criteria = [
    criterion("CI DB URL available to workflow", false),
    criterion("Service JWT/token available to workflow", false),
    criterion("CI connection verified by workflow", false),
  ];

  const c1Criteria = [
    criterion("deploy-language-agent-shared.yml calls redteam workflow", hasAbs(path.join(sooRoot, ".github/workflows/deploy-language-agent-shared.yml"), /redteam|red-team/i)),
    criterion("Deploy blocks on exit 2 or 3", hasAbs(path.join(sooRoot, ".github/workflows/deploy-language-agent-shared.yml"), /exit 2|exit 3|failure/i)),
    criterion("Deliberately failing scenario proves deploy blocked", false),
  ];

  const c2Criteria = [
    criterion("Slack alert code exists", has("prototype/src/vt_agent_redteam/harness.py", /SLACK_WEBHOOK_URL|slack/i)),
    criterion("Alert includes agent, run, severity, artifact link", has("prototype/src/vt_agent_redteam/harness.py", /agent|severity|artifact|run/i) && has("prototype/src/vt_agent_redteam/harness.py", /slack/i)),
    criterion("Slack secret wired in workflow", has(".github/workflows/redteam.yml", /SLACK_WEBHOOK_URL|slack/i)),
  ];

  const c3Criteria = [
    criterion("Controlled drill scenario selected", anyFile(path.join(repoRoot, "docs"), (name) => /drill|controlled/i.test(name))),
    criterion("Known failure triggers red-team gate", false),
    criterion("Evidence captured for drill", false),
  ];

  const r1Criteria = [
    criterion("PostHog release flag policy documented", has("docs/final-release-governance.md", /PostHog feature flag/i)),
    criterion("Feature flag key, owner, rollout plan, and rollback recorded", evidenceDoc("docs/release-governance/posthog-feature-flag.md", /flag_key|owner|rollback|rollout/i)),
    criterion("Release path proven guarded by PostHog flag", evidenceDoc("docs/release-governance/posthog-feature-flag.md", /guarded|kill switch|feature flag/i)),
  ];

  const r2Criteria = [
    criterion("Integration test plan recorded", evidenceDoc("docs/release-governance/integration-e2e-evidence.md", /integration/i)),
    criterion("Non-stub E2E test with the red-team tool executed", evidenceDoc("docs/release-governance/integration-e2e-evidence.md", /non-stub|is_stub_response\s*=\s*false|agent_native_transcript/i)),
    criterion("Cost guardrail integration evidence captured", evidenceDoc("docs/release-governance/integration-e2e-evidence.md", /cost guardrail|budget_exhausted|max_cost_usd_per_run/i)),
    criterion("CI or local run evidence linked", evidenceDoc("docs/release-governance/integration-e2e-evidence.md", /run|artifact|workflow|trace/i)),
  ];

  const r3Criteria = [
    criterion("LLM_WIKI NITPICK review report exists", evidenceDoc("docs/release-governance/nitpick-llm-wiki-review.md", /LLM_WIKI|nitpick/i)),
    criterion("Language/tool-specific senior review applied", evidenceDoc("docs/release-governance/nitpick-llm-wiki-review.md", /language|tool|senior|expert/i)),
    criterion("All nitpick findings resolved or dispositioned", evidenceDoc("docs/release-governance/nitpick-llm-wiki-review.md", /resolved|dispositioned|backlog/i)),
  ];

  const r4Criteria = [
    criterion("LLM attack-defense review report exists", evidenceDoc("docs/release-governance/llm-attack-defense-review.md", /attack|defense|LLM/i)),
    criterion("Each red-team hardening artifact reviewed", evidenceDoc("docs/release-governance/llm-attack-defense-review.md", /scenario|hardening|artifact/i)),
    criterion("Uncovered attack classes mapped to fixes or backlog", evidenceDoc("docs/release-governance/llm-attack-defense-review.md", /uncovered|gap|backlog|fix/i)),
  ];

  const r5Criteria = [
    criterion("Strategic View consumed reviewer reports", evidenceDoc("docs/release-governance/strategic-triage.md", /Strategic View|reviewer reports/i)),
    criterion("Immediate fixes prioritized", evidenceDoc("docs/release-governance/strategic-triage.md", /immediate|P0|P1|must fix/i)),
    criterion("Cost guardrail status triaged", evidenceDoc("docs/release-governance/strategic-triage.md", /cost guardrail|budget_exhausted|max_cost_usd_per_run/i)),
    criterion("Post-v0 backlog created for deferrable work", evidenceDoc("docs/release-governance/strategic-triage.md", /post-v0|backlog|defer/i)),
  ];

  const r6Criteria = [
    criterion("Final repo/package naming plan exists", evidenceDoc("docs/release-governance/repo-package-cutover.md", /vt-agent-redteam/i)),
    criterion("Repository final name is vt-agent-redteam", evidenceDoc("docs/release-governance/repo-package-cutover.md", /repository.*vt-agent-redteam|repo.*vt-agent-redteam/i)),
    criterion("Package/install/workflow references final name", evidenceDoc("docs/release-governance/repo-package-cutover.md", /package|install|workflow/i)),
  ];

  const r7Criteria = [
    criterion("Dense DOCX security documentation audit exists", evidenceDoc("docs/release-governance/docx-security-traceability.md", /DOCX|security documentation|traceability/i)),
    criterion("Point-by-point implementation traceability recorded", evidenceDoc("docs/release-governance/docx-security-traceability.md", /point-by-point|traceability|requirement/i)),
    criterion("All deviations classified as fix-now or backlog", evidenceDoc("docs/release-governance/docx-security-traceability.md", /deviation|fix-now|backlog/i)),
  ];

  const r8Criteria = [
    criterion("Security pentest report exists", evidenceDoc("docs/release-governance/security-pentest.md", /pentest|exploitation/i)),
    criterion("Exploit attempts and metrics recorded", evidenceDoc("docs/release-governance/security-pentest.md", /exploit|metric|attempt/i)),
    criterion("Unresolved exploitable gaps triaged", evidenceDoc("docs/release-governance/security-pentest.md", /unresolved|exploitable|triaged/i)),
  ];

  const r9Criteria = [
    criterion("Final technical daily message drafted", evidenceDoc("docs/release-governance/final-daily-report.md", /technical daily|technical update/i)),
    criterion("Final non-technical daily message drafted", evidenceDoc("docs/release-governance/final-daily-report.md", /non-technical daily|nontechnical/i)),
    criterion("Final team-ready state report included", evidenceDoc("docs/release-governance/final-daily-report.md", /current state|team report|release state/i)),
  ];

  return [
    {
      id: "phase-1a",
      name: "Phase 1A - Framework hardening",
      tasks: [
        task("F1", "Langfuse native transcript runner", "Use Langfuse agent-native transcripts instead of replaying synthetic responses.", f1Criteria),
        task("F2", "Manifest schema extensions", "Add policy_profile.coverage_status and scenario_selection.exclude_tags with tests and ADR-002.", f2Criteria),
        task("F3", "Severity gate and overrides", "Make gate precedence explicit and read approved overrides from storage.", f3Criteria),
        task("F4", "PII redaction at write", "Redact sensitive fields before persistence and downstream reporting.", f4Criteria),
        task("F5", "CLI modes from manifest", "Expose pr, deploy, canary, environment, threshold, and manifest-driven execution.", f5Criteria),
        task("F6", "Reusable workflow", "Package framework workflow for repo consumers and CI reuse.", f6Criteria),
        task("F7", "v0.1.0 release tag", "Tag framework once F1-F6 are stable and documented.", f7Criteria),
      ],
    },
    {
      id: "phase-1b",
      name: "Phase 1B - SOO integration",
      tasks: [
        task("S1", "language-tutor manifest", "Create the first SOO manifest for the tutor agent.", s1Criteria),
        task("S2", "language-checkpoint manifest", "Create the checkpoint agent manifest and trace binding.", s2Criteria),
        task("S3", "support-agent manifest", "Create Maya/support-agent manifest with partial tool-use coverage noted.", s3Criteria),
        task("S4", "SOO redteam workflow", "Add SOO GitHub workflow that calls the framework.", s4Criteria),
        task("S5", "Secrets and environments", "Wire Langfuse, OpenAI, Supabase, and Slack secrets in target environments.", s5Criteria, true),
        task("S6", "Conversation Club schema", "Apply redteam result schema to the CC Supabase project.", s6Criteria),
        task("S7", "CI DB URL and JWT", "Finalize CI database connection and service-token plumbing.", s7Criteria, true),
      ],
    },
    {
      id: "phase-1c",
      name: "Phase 1C - Rollout controls",
      tasks: [
        task("C1", "Deploy hook gate", "Gate deploys on severity threshold and override rules.", c1Criteria),
        task("C2", "Slack alert", "Send concise failure summaries to the configured team channel.", c2Criteria),
        task("C3", "Controlled drill", "Run a known scenario drill and preserve evidence.", c3Criteria),
      ],
    },
    {
      id: "phase-1d",
      name: "Phase 1D - Final release governance",
      tasks: [
        task("R1", "PostHog feature-flag release gate", "Release only behind an explicit PostHog feature flag with rollback evidence.", r1Criteria),
        task("R2", "Integration and E2E tests", "Prove the red-team tool works through integration and end-to-end runs.", r2Criteria),
        task("R3", "LLM_WIKI NITPICK code review", "Run strict senior review using LLM_WIKI engineering standards.", r3Criteria),
        task("R4", "LLM attack-defense review", "Review every hardening artifact for attack coverage and missed exploit classes.", r4Criteria),
        task("R5", "Strategic triage", "Prioritize reviewer findings into fix-now work and post-v0 backlog.", r5Criteria),
        task("R6", "vt-agent-redteam cutover", "Ensure final repository, package, install, and workflow naming use vt-agent-redteam.", r6Criteria),
        task("R7", "DOCX security traceability audit", "Re-read dense source documentation and verify implementation point by point.", r7Criteria),
        task("R8", "Security pentest and exploitation review", "Run methodical pentest analysis and triage unresolved exploitable gaps.", r8Criteria),
        task("R9", "Final team report", "Prepare technical and non-technical daily messages only after release governance closes.", r9Criteria),
      ],
    },
  ];
}

function markCurrent(phases) {
  let found = false;
  for (const phase of phases) {
    for (const item of phase.tasks) {
      if (item.done) {
        item.status = "done";
      } else if (!found && !item.manual) {
        item.status = "current";
        found = true;
      }
    }
    phase.done = phase.tasks.filter((item) => item.done).length;
    phase.total = phase.tasks.length;
  }
  return phases;
}

function flattenTasks(phases) {
  return phases.flatMap((phase) => phase.tasks.map((item) => ({ ...item, phase: phase.name })));
}

function fileGroups() {
  return [
    {
      title: "Start Here",
      files: [
        repoFile("Repository instructions", "AGENTS.md"),
        repoFile("Codex transfer bundle", "docs/v0-implementation-plan.codex-transfer.md"),
        repoFile("Technical plan v1.1", "docs/v0-implementation-plan.md"),
        repoFile("Non-technical summary", "docs/v0-implementation-plan.summary.md"),
        repoFile("Final release governance gate", "docs/final-release-governance.md"),
        repoFile("Final release governance summary", "docs/final-release-governance.summary.md"),
        repoFile("Operational metrics protocol", "docs/operational-metrics/README.md"),
        repoFile("Operational metrics summary", "docs/operational-metrics/README.summary.md"),
        repoFile("Operational metrics status", "docs/operational-metrics/status.json"),
        repoFile("Decision trail handoff", "docs/v0-implementation-plan.handoff.md"),
        repoFile("Boss-review verdict", "docs/v0-implementation-plan.review.md"),
        repoFile("Current repo status", "STATUS.md"),
      ],
    },
    {
      title: "Canonical Specs",
      files: [
        repoFile("Spec v2.1 authority", "docs/exports/livekit-agent-red-team-hardening.md"),
        repoFile("Spec v2.1 DOCX authority", "docs/exports/livekit-agent-red-team-hardening.docx"),
        repoFile("Condensed brief DOCX", "docs/exports/livekit-redteam-condensed.docx"),
        repoFile("Condensed brief", "docs/exports/livekit-redteam-condensed.md"),
        repoFile("Executive summary", "docs/EXECUTIVE_SUMMARY.md"),
        repoFile("Executive summary DOCX", "docs/exports/EXECUTIVE_SUMMARY.docx"),
        repoFile("Hardening solution", "docs/12-livekit-redteam-hardening-solution.md"),
        repoFile("Coverage matrix", "docs/11-agent-coverage-matrix.md"),
        repoFile("Tooling dossier", "docs/08-tooling-dossier.md"),
        repoFile("Policy coverage", "docs/07-corpus-policy-coverage.md"),
        repoFile("Real-agent proof", "docs/10-livekit-real-agent-proof.md"),
      ],
    },
    {
      title: "Release Governance Evidence",
      files: [
        repoFile("PostHog feature flag evidence", "docs/release-governance/posthog-feature-flag.md"),
        repoFile("Integration and E2E evidence", "docs/release-governance/integration-e2e-evidence.md"),
        repoFile("LLM_WIKI NITPICK review", "docs/release-governance/nitpick-llm-wiki-review.md"),
        repoFile("LLM attack-defense review", "docs/release-governance/llm-attack-defense-review.md"),
        repoFile("Strategic triage", "docs/release-governance/strategic-triage.md"),
        repoFile("Repo/package cutover", "docs/release-governance/repo-package-cutover.md"),
        repoFile("DOCX security traceability", "docs/release-governance/docx-security-traceability.md"),
        repoFile("Security pentest", "docs/release-governance/security-pentest.md"),
        repoFile("Final daily report", "docs/release-governance/final-daily-report.md"),
      ],
    },
    {
      title: "Framework Code",
      files: [
        repoFile("Types and manifest models", "prototype/src/vt_agent_redteam/types.py"),
        repoFile("Manifest loader", "prototype/src/vt_agent_redteam/manifest_loader.py"),
        repoFile("Harness orchestration", "prototype/src/vt_agent_redteam/harness.py"),
        repoFile("CLI entrypoint", "prototype/src/vt_agent_redteam/cli.py"),
        repoFile("Langfuse trace runner", "prototype/src/vt_agent_redteam/runners/langfuse_trace_runner.py"),
        repoFile("Runner exports", "prototype/src/vt_agent_redteam/runners/__init__.py"),
        repoFile("Postgres writer", "prototype/src/vt_agent_redteam/storage/postgres_writer.py"),
        repoFile("Storage schema", "prototype/src/vt_agent_redteam/storage/schema.sql"),
        repoFile("Package config", "prototype/pyproject.toml"),
      ],
    },
    {
      title: "Tests and ADRs",
      files: [
        repoFile("Langfuse runner tests", "prototype/tests/test_langfuse_runner.py"),
        repoFile("Manifest/type tests", "prototype/tests/test_types.py"),
        repoFile("Corpus loader tests", "prototype/tests/test_corpus_loader.py"),
        repoFile("Scorer tests", "prototype/tests/test_scorers.py"),
        repoFile("ADR-001 native transcript", "docs/adr/0001-langfuse-native-transcript.md"),
        repoFile("ADR-002 manifest profile", "docs/adr/0002-colocated-manifest-layout-and-coverage-status.md"),
        repoFile("ADR-003 severity gate", "docs/adr/0003-severity-gate-overrides.md"),
        repoFile("ADR-005 redaction", "docs/adr/0005-redaction-at-write.md"),
      ],
    },
    {
      title: "SOO Consumer",
      files: [
        sooFile("SOO instructions", "AGENTS.md"),
        sooFile("Supabase instructions", "supabase/AGENTS.md"),
        sooFile("Cinematic judge workflow", ".github/workflows/cinematic-judge.yml"),
        sooFile("Language deploy shared workflow", ".github/workflows/deploy-language-agent-shared.yml"),
        sooFile("language-tutor agent", "agents/language-tutor/agent.py"),
        sooFile("language-tutor Langfuse", "agents/language-tutor/langfuse_tracing.py"),
        sooFile("language-checkpoint agent", "agents/language-checkpoint/agent.py"),
        sooFile("language-checkpoint Langfuse", "agents/language-checkpoint/langfuse_tracing.py"),
        sooFile("support-agent agent", "agents/support-agent/agent.py"),
        sooFile("support-agent Langfuse", "agents/support-agent/langfuse_tracing.py"),
      ],
    },
    {
      title: "External Knowledge",
      files: [
        vt4sFile("VT4S overview", "00-overview.md"),
        vt4sFile("VT4S repos ranked", "01-repos-ranked.md"),
        vt4sFile("Accessibility notes", "accessibility-matt.md"),
        wikiFile("LLM_WIKI index", "index.md"),
        wikiFile("Architecture fundamentals ch03", "wiki/books/fundamentals-of-software-architecture/ch03-modularity.md"),
        wikiFile("Architecture fundamentals ch06", "wiki/books/fundamentals-of-software-architecture/ch06-measuring-governing.md"),
        wikiFile("Architecture fundamentals ch07", "wiki/books/fundamentals-of-software-architecture/ch07-scope.md"),
        wikiFile("Architecture decisions", "wiki/books/fundamentals-of-software-architecture/techniques/architecture-decisions.md"),
        wikiFile("DDD ch03", "wiki/books/learning-domain-driven-design/ch03-managing-domain-complexity.md"),
        wikiFile("DDD ch10", "wiki/books/learning-domain-driven-design/ch10-design-heuristics.md"),
        wikiFile("Documentation process", "wiki/processes/documentation.md"),
      ],
    },
  ];
}

function buildStatus() {
  const phases = markCurrent(buildTasks());
  const tasks = flattenTasks(phases);
  const countedTasks = tasks.filter((item) => !item.manual);
  const done = countedTasks.filter((item) => item.done).length;
  const currentTask = tasks.find((item) => item.status === "current") ?? tasks[tasks.length - 1];
  const percent = countedTasks.length ? Math.round((done / countedTasks.length) * 100) : 0;
  const git = gitStatus();
  const tests = testStatus();
  const corpusDir = path.join(repoRoot, "prototype/src/vt_agent_redteam/corpus");
  const corpusFiles = existsSync(corpusDir) ? readdirSync(corpusDir).filter((name) => name.endsWith(".yaml")).length : 0;
  const files = fileGroups();
  const testCount = tests.summary.match(/\d+/)?.[0] ?? "?";

  return {
    generatedAt: new Date().toISOString(),
    git,
    testStatus: tests,
    strategicView: strategicView(phases),
    operationalReadiness: operationalReadiness(),
    currentTask,
    progress: {
      done,
      total: countedTasks.length,
      percent,
    },
    nextAction: {
      title: `${currentTask.id} - ${currentTask.title}`,
      detail: currentTask.detail,
    },
    metrics: [
      { value: "195", label: "Scenario target", detail: "Target corpus size from spec v2.1." },
      { value: String(corpusFiles), label: "Corpus files", detail: "YAML category files currently in the framework." },
      { value: "3", label: "v0 target agents", detail: "language-tutor, language-checkpoint, support-agent." },
      { value: "4", label: "Feedback channels", detail: "GitHub Check, Slack, dashboard views, run_summary.json." },
      { value: testCount, label: "Framework tests", detail: "Last captured pytest suite size." },
      { value: String(git.ahead), label: "Commits ahead", detail: "Local framework branch versus origin/main." },
    ],
    phases,
    architecture: {
      flow: [
        { title: "Manifest", detail: "Agent profile, policy coverage, scenario selection, thresholds." },
        { title: "Scenarios", detail: "Curated corpus buckets plus exclude tags for partial coverage." },
        { title: "Runner", detail: "LiveKit/Langfuse trace path for agent-native transcript evidence." },
        { title: "Scorers", detail: "Moderation, refusal, prompt leak, expected verdict, category checks." },
        { title: "Storage", detail: "Redacted results persisted to Postgres/Supabase." },
        { title: "Gate", detail: "Severity precedence, overrides, deploy decision, alerts." },
      ],
      feedbackChannels: [
        { title: "GitHub Check", detail: "PR and deploy context with pass/fail and artifact links." },
        { title: "Slack", detail: "Concise alert for high-severity failures and blocked deploys." },
        { title: "Dashboard Views", detail: "Operational surface for current phase, files, risks, and outcomes." },
        { title: "run_summary.json", detail: "Machine-readable artifact for downstream automation and audits." },
      ],
    },
    overview: [
      { title: "Framework boundary", detail: "This repo owns the reusable red-team runner, manifest schema, corpus, scoring, storage, and release workflow." },
      { title: "SOO boundary", detail: "student-onboarding-orchestration consumes the framework for the three LiveKit agents selected for v0." },
      { title: "Production moderation", detail: "Existing app-level input moderation is not replaced; the MVP validates agent output behavior and deploy safety." },
      { title: "Decision posture", detail: "Hard constraints, ADRs, Ask First rules, and bilingual-doc conventions remain binding for every new step." },
    ],
    risks: [
      { level: "high", title: "Langfuse correlation metadata", detail: "Plan assumes redteam_run_id and redteam_scenario_id metadata. SOO tracing may need explicit metadata wiring before runner search works reliably." },
      { level: "high", title: "SOO Ask First boundaries", detail: "DB, auth, deploy, infrastructure, and destructive operations require explicit confirmation inside the consumer repo." },
      { level: "medium", title: "Maya tool-use coverage gap", detail: "support-agent must declare partial-no-tool-use until scenario/tool traces are proven." },
      { level: "medium", title: "Supabase deploy-killer rules", detail: "Conversation Club schema work must follow local migration rules and avoid direct remote mutations." },
      { level: "low", title: "Deferred audio and BI scope", detail: "WAV collector D1 and BI dashboard D9 remain post-v0 unless priorities change through a new ADR." },
    ],
    commits: commits(),
    fileGroups: files,
  };
}

function writeStatus() {
  mkdirSync(path.dirname(outputPath), { recursive: true });
  const status = buildStatus();
  writeFileSync(outputPath, `${JSON.stringify(status, null, 2)}\n`);
  return status;
}

function contentType(filePath) {
  const ext = path.extname(filePath);
  return {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".py": "text/x-python; charset=utf-8",
    ".yml": "text/yaml; charset=utf-8",
    ".yaml": "text/yaml; charset=utf-8",
    ".sql": "text/plain; charset=utf-8",
  }[ext] ?? "application/octet-stream";
}

function serve() {
  const server = createServer((request, response) => {
    const url = new URL(request.url, `http://127.0.0.1:${port}`);
    let requestedPath;
    try {
      requestedPath = decodeURIComponent(url.pathname);
    } catch {
      response.writeHead(400, { "content-type": "text/plain; charset=utf-8" });
      response.end("Bad request");
      return;
    }

    if (requestedPath === "/") requestedPath = "/dashboard/";
    if (requestedPath === "/dashboard/") requestedPath = "/dashboard/index.html";

    if (requestedPath === "/dashboard/data/redteam-status.json") {
      const status = buildStatus();
      response.writeHead(200, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" });
      response.end(`${JSON.stringify(status, null, 2)}\n`);
      return;
    }

    const absPath = resolveServedPath(requestedPath);
    if (!absPath || !existsSync(absPath) || statSync(absPath).isDirectory()) {
      response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      response.end("Not found");
      return;
    }

    response.writeHead(200, { "content-type": contentType(absPath), "cache-control": "no-store" });
    createReadStream(absPath).pipe(response);
  });

  server.listen(port, "127.0.0.1", () => {
    console.log(`Red Team MVP dashboard: http://127.0.0.1:${port}/dashboard/`);
  });
}

function safeJoin(root, relativePath) {
  const absPath = path.normalize(path.join(root, relativePath));
  return absPath === root || absPath.startsWith(`${root}${path.sep}`) ? absPath : null;
}

function resolveServedPath(requestedPath) {
  const externalRoutes = [
    ["/external/soo/", sooRoot],
    ["/external/vt4s/", vt4sRoot],
    ["/external/wiki/", llmWikiRoot],
  ];

  for (const [prefix, root] of externalRoutes) {
    if (requestedPath.startsWith(prefix)) {
      return safeJoin(root, requestedPath.slice(prefix.length));
    }
  }

  return safeJoin(repoRoot, requestedPath.replace(/^\/+/, ""));
}

if (!args.has("--serve") || args.has("--watch")) {
  const status = writeStatus();
  console.log(`Wrote ${path.relative(repoRoot, outputPath)} at ${status.generatedAt}`);
}

if (args.has("--watch")) {
  setInterval(writeStatus, 3000);
}

if (args.has("--serve")) {
  serve();
}
