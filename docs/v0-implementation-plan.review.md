# Boss-Role Review — v0 Implementation Plan

**Date:** 2026-05-30
**Reviewer role:** senior engineering leadership second-pass (Claude general-purpose subagent, briefed with the dense spec v2.1, the v0 implementation plan, and the prior boss-review precedent from `livekit-redteam-condensed.md` §8)
**Verdict:** **greenlight-with-conditions**
**Companion docs:** `./v0-implementation-plan.md` (the plan being reviewed) · `./v0-implementation-plan.summary.md` · `./v0-implementation-plan.handoff.md` · `./exports/livekit-agent-red-team-hardening.md` (the spec the plan must satisfy)

---

## §1 Issues fully resolved (compared to a hypothetical earlier draft)

- Three spec divergences (target repo, audio path, manifest layout) are surfaced upfront in plan §1.3 with named ADRs rather than buried — matches the precedent set in `condensed-brief.md` §8.1.
- Spec §9.8 stub-row guarantee is preserved end-to-end: plan §2.5 schema keeps `threshold_passed` nullable, `is_stub_response NOT NULL DEFAULT false`, plus the `transcript_source` CHECK constraint now lists `agent_native_langfuse` alongside the four spec-defined sources. Plan §2.2 step [6] cites exit codes 0/2/3.
- Spec §13 override audit trail is fully reified: `redteam.overrides` carries every spec-required column (`run_id`, `agent_name`, `pr_number`, `approver_handle`, `approver_team`, `reason_text`, `expires_at`, `created_at`), and F3 makes the harness read it before exit-code emission — addressing the previous spec review's condition #6 ("override read path is asserted but not specified").
- Spec §12.4 PII redaction is given a concrete implementation owner (F4) with `response_hash` pre-redaction — addressing condition #7 partially.
- Spec §7 per-policy-profile isolation is honored: each manifest carries its own `policy_profile.type` and `scenario_packs`; Maya is honestly tagged `partial-no-tool-use` rather than silently miscoded.
- Bilingual rule honored: tech plan + `.summary.md` companion both in English. No "Co-Authored-By: Claude" anywhere in commit instructions.

---

## §2 Conditions for greenlight (must fix before execution begins)

1. **Severity column missing from `redteam.redteam_runs`.** Spec §13 defines a four-tier severity model (P0–P3) and §9.8 requires severity-weighted precedence in the gate decision *before* aggregate threshold. The plan's §2.5 schema has no `severity` column and no mapping from `scenario_category` × `policy_profile` → severity. F3's override test claims to distinguish "valid override + no P0" from "valid override + P0", but P0 is not derivable from any persisted column as drafted. **Fix:** add `severity text NOT NULL CHECK (severity IN ('P0','P1','P2','P3'))` to the schema and add a §2.6 (or amend §2.2) table mapping each `policy_profile` × `scenario_category` → severity. This is the spec §13 decision-table contract.

2. **Severity-precedence gate logic absent from the plan body.** Plan §2.2 step [4] reads "Aggregate threshold + severity precedence applied" — one line. Spec §13's five-row precedence table (including the "stubs present → NULL" row) is the load-bearing decision contract and is not transcribed into the plan, nor cited as an executor reference. **Fix:** either inline spec §13's precedence table into plan §2.2 or add an explicit "implements spec §13 Table" reference and acceptance test (alongside F3) that exercises each row.

3. **`artifact_uri` semantics for the Langfuse-native path unresolved.** Previous spec review condition #7 asked: "is the un-redacted response preserved under `artifact_uri`?" The plan's schema keeps the column but the Langfuse runner (§2.2 stages [3g]–[3l]) never sets it. With WAV-collector deferred, `artifact_uri` is dead in v0 — which is fine if stated, but the redaction story then loses its rollback path (the redacted DB row is the only artifact). **Fix:** explicitly state in plan §2.2 step [3l] or in F4 acceptance that `artifact_uri` points to the Langfuse trace URL for v0, OR document that `artifact_uri = NULL` is acceptable and the redacted-row-plus-`response_hash` is the only retained evidence. Spec §12.4.

4. **Five-constraint token scoping for synthetic candidate is not restated for v0.** Spec §5.4 names five constraints (room restriction, agent restriction, TTL = `scenario_timeout_seconds + 30`, environment segregation, audit). The plan inherits prototype behavior but does not confirm v0 enforces all five, especially constraint #4 (production-canary secrets gated to the canary workflow). Since v0 ships PR + deploy triggers only and no canary, the plan should commit explicitly to staging-only `LIVEKIT_API_KEY`/`SECRET` in the `redteam` Environment, with production-canary access blocked. **Fix:** add a paragraph in §2.4 or §1.1 row 6 affirming the five token-scoping constraints, and add an S5 sub-bullet verifying staging-only scoping. Spec §5.4.

5. **Internal inconsistency in §6 acceptance #5.** Plan §6 references "deferred D9" for BI dashboard wiring, but the §1.2 deferred table runs D1–D8 only. **Fix:** add D9 to §1.2 with revisit trigger, or correct the §6 reference to "deferred (see §1.2)".

6. **Acceptance criterion §17.7 #6 ("second agent through manifest-only configuration") is not actually exercised by the v0 design.** The spec's intent is to validate that a *different* team copies the pattern with no framework changes. Plan §6 marks this "✓ trivially via multi-agent v0" — but a single team (`eng-met-ui`) onboarding three agents in one PR does not test the cross-team reusability claim that the spec §14 explicitly flags as "an unfalsified hypothesis." **Fix:** either (a) lower the claim — mark §6 #6 as "partially covered: structural manifest copy proven; cross-team reusability still pending Phase 2 Tutor Interviewer onboarding," or (b) commit to one of the three manifests being authored by an outside team (e.g., the support-agent/Maya manifest reviewed by a non-VT4S engineer) and capture that in a verification step.

---

## §3 Polish items (nice to have)

- The new `coverage_status` manifest field is a schema extension beyond spec Appendix E; the ADR list (§7) covers layout and audio but not the field addition. Add ADR-FRAMEWORK-004 or fold into ADR-002.
- §10 cost-discipline note ("verify `max_cost_usd_per_run` triggers an actual abort") is good guidance but lives only in executor notes; promote it to a §9 verification checkbox so it becomes a gated v0 deliverable rather than advisory.
- §8 risk row for `eng-met-ui` ownership of three agents understates spec §17.6's per-team alert-response SLA (1 business day P0/P1). Add a sentence on rotation expectations for v0 (one team, three agents) before D8 lands.
- Plan §6's `(*)` footnote on acceptance #1 deviates from spec §17.2 #1 but cites spec §12.1 + §15.1 correctly. Adding a one-line forward reference from ADR-FRAMEWORK-001 to spec §17.2 acceptance #1 makes the audit trail tighter.
- §4 S6 migration header should explicitly cite the three SOO `supabase/AGENTS.md` Rule 0 constraints (no-modify-applied, right-folder, timestamped) — it references them but does not show them.
- Spec §15.3 names "no PII redaction implementation yet" as a known gap; v0 explicitly closes it via F4. Worth calling out in §6 as a v0 *upgrade* over spec status, not a deferral.

---

## §4 Acceptance-criteria coverage table

| Spec acceptance criterion | Plan coverage |
|---|---|
| §17.2 #1 Repair and revalidate synthetic-candidate audio capture | **Deviates (ADR'd):** Langfuse-native runner replaces audio capture. Spec §15.1 explicitly names this as Phase 2 fallback; deviation is honest. |
| §17.2 #2 One non-stub `redteam_runs` row from CC agent receiving adversarial audio | **Deviates:** non-stub row produced via Langfuse transcript instead of WAV → Whisper. Equivalent in row-quality terms but does not exercise audio pipeline. ADR-FRAMEWORK-001. |
| §17.2 #3 Transcript artifact handling + PII redaction at write | **Partial:** PII redaction covered by F4. Artifact handling unresolved (Condition #3 above). |
| §17.2 #4 Commit `.redteam/manifest.yaml` to consumer repo | **Covered (extended):** S1+S2+S3 commit three manifests at `agents/<n>/.redteam/manifest.yaml`. |
| §17.2 #5 Commit `.github/workflows/redteam.yml` to consumer repo | **Covered:** S4. Honors singular-file literal of the spec. |
| §17.2 #6 Configure the four required CI secrets | **Covered (extended):** S5 configures 8 secrets including Langfuse + DB. |
| §17.2 #7 One green Actions run that writes non-stub rows to Supabase | **Covered:** F6 + S6 + S7; verification §9 has explicit "done means" rows. |
| §17.2 #8 Wire Slack webhook + demonstrate one alert firing | **Covered:** C2 + C3 (deliberate-failure drill). |
| §17.7 #1 Real non-stub transcript captured | **Covered with deviation:** `transcript_source = "agent_native_langfuse"`. |
| §17.7 #2 Stored with `is_stub_response = false` | **Covered:** schema + flow §2.2 [3l]. |
| §17.7 #3 Deploy workflow runs harness + blocks | **Covered:** C1. |
| §17.7 #4 Slack drill | **Covered:** C3. |
| §17.7 #5 Dashboards display pass rate by agent / bucket / week | **Partial:** views shipped, BI wiring deferred (mis-numbered "D9" — Condition #5). |
| §17.7 #6 Second agent onboarded via manifest-only | **Weakly covered:** structural-only; cross-team validation not exercised (Condition #6). |
| §17.7 #7 Stubbed runs marked + excluded from dashboards | **Covered:** `is_stub_response` column + view filter in §2.5. |

---

## §5 Load-bearing safety requirements check

- **PII redaction:** *Covered.* F4 implements regex + spaCy NER; pre-redaction `response_hash` preserved per spec §12.4.
- **Stub-row guarantee:** *Covered.* §2.5 schema keeps `threshold_passed` nullable; §2.2 step [6] cites exit code 3; `transcript_source` CHECK constraint admits `stub_canned`.
- **Severity precedence:** *Partial / at risk.* No persisted `severity` column; no mapping table; gate logic compressed to one line (Conditions #1 and #2).
- **Override audit:** *Covered.* Full table schema with all spec-required columns; F3 implements the read path with the four required test cases.
- **Policy profile isolation:** *Covered.* Per-manifest profile + scenario packs; Maya's `partial-no-tool-use` declaration is honest.
- **Synthetic-candidate token scoping:** *Partial.* Plan inherits prototype behavior implicitly; five constraints not restated for v0 (Condition #4).

---

## §6 Final assessment

The plan is fundamentally sound: it satisfies seven of eight Phase-1 MVP items in spec §17.2 and six of seven acceptance criteria in §17.7, surfaces its three deviations honestly with ADRs grounded in the spec's own fallback language, and closes the spec §15.3 PII-redaction gap that the spec itself deferred to Phase 3. The conditions above are integrity defects (severity persistence, gate-logic transcription, `artifact_uri` semantics, token-scoping affirmation, one numbering bug, and one over-claim on acceptance #6) rather than architectural problems — none require restructuring.

The executing agent should resolve Conditions #1 and #2 first because they cascade: adding the `severity` column changes the schema migration (S6) and the harness gate logic (F3 + a new precedence test). Conditions #3, #4, #5, and #6 are text-and-test edits to plan sections §1.2, §2.4, §2.5, §6, and §9 that can land in a single revision pass. Once those are applied, the plan is ready for execution without forwarding for a third review.
