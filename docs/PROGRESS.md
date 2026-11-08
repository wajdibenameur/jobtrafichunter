# Progress

Last updated: 2026-11-08 by Codex / Scraping Engine documentation (D-028)
Current task: AI Job Agent and Scraping audits recorded; both plans proposed
Status: WAITING_FOR_OWNER_VALIDATION (documentation update authorized only)

## Phase checklist

- [x] 0 Documentation and original phase plans approved.
- [x] 1 Local Python 3.11/auth/TLS/PostgreSQL/Angular foundation validated (D-013).
- [x] 2 Manual sources and confirmed URL/CSV import validated (D-017).
- [x] 3 Local search delivered (D-021) and owner-validated (D-024).
- [x] 4 Private CVs, parsing, editing and profile validation delivered (D-026).
    - Plan approved D-024; delivery still WAITING_FOR_VALIDATION.
    - PDF/DOCX, encrypted originals, Windows isolation, candidate revisions and UI.
- [ ] 5 CV matching/calibration; matching module remains absent.
- [ ] 6 Telegram, scheduling and notification history.
- [ ] 7 Applications, hardening, local backup/restore.

## AI Job Agent extension — proposed lots, not approved implementation

- [x] Lot 1 audit completed; report: reports/ai-job-agent-audit.md.
- [x] Owner authorizes necessary documentation updates only (D-027).
- [x] Plan saved: PLAN-AI-JOB-AGENT.md, status PROPOSED.
- [ ] Lot 2: 2 h/6 h filters, accessible radios and temporal compatibility.
- [ ] Lot 3: explained/calibrated matching, then priorities, scheduling and alerts.
- [ ] Lot 4: tailored CV, editable preview, validation and DOCX/PDF export.
- [ ] Lot 5: cover letter, language/style, versions and exports.
- [ ] Lot 6: validated ZIP, real apply link and confirmed application tracker.
- [ ] Lot 7: full validation, security, documentation and local operations.

These lots do not replace historical phases. Tailored documents are a proposal,
not a delivered capability of the original-CV vault. No code, migration, dependency,
new module or plan approval follows from D-027.

## Scraping Engine — documentation authorized, implementation not approved

- [x] Audit recorded: reports/scraping-engine-audit.md (D-028).
- [x] Source evidence recorded: sources/scraping-review.md; none made PERMITTED.
- [x] Eight-lot plan saved: PLAN-SCRAPING-ENGINE.md, status PROPOSED.
- [ ] Approve plan: extend sources/search/listings and existing worker only.
- [ ] Infrastructure, permitted extraction, Angular page, queue integration.
- [ ] Shared matching/alerts/documents, then full validation; no duplicate engines.

LinkedIn stays without scraping; Indeed/Tanitjobs manual pending permission.
Keejob Markdown/RSS and enterprise APIs are candidates, not activated sources.
D-028 authorizes saving documents only, not code, collection or phase 4 validation.

## Apify feature — explicit A/B/C workflow

- [x] A Modules/queue/UI inspected and official documents reviewed (D-022).
- [x] A Additive integration, consent/budget and recovery design proposed.
- [x] A Separate LinkedIn - Apify card recommended INSIDE Sources, no extra menu.
- [x] Owner chose to wait for CV and matching, not collection-only scope (D-023).
- [ ] B Deferred until CV/matching; revisit plan and approval then.
- [ ] Actor/method permission verified; currently UNVERIFIED, connector inactive.
- [ ] C Separate explicit approval for a real 10-job run and concrete budget.

## Last session / current evidence

Owner requested Scraping audit, then "ouui ajouté au fichier": saved audit,
eight-lot proposed plan and source-review links (D-028); synchronized README,
AI Job Agent plan, agents, decisions, TODO and CHANGELOG, then this file last.
Scraping audit collected 131 tests in 1.05s; Ruff/mypy passed (97 source files).
This is not a new full test run; complete-suite evidence below remains historical.
No application code, migration, dependency, connector or permission changed.

New request: audit AI Job Agent, filters, matching, alerts and application documents
before code. Audit initially returned in chat only; owner then explicitly authorized
all necessary documentation updates (D-027). Created audit and proposed seven-lot
plan; synchronized README/frontend README, AGENTS/CLAUDE, DECISIONS, TODO, CHANGELOG
and phase plan/report status headers. SPEC and historical entries preserved.
No new feature implementation in this documentation task.

Phase 4 delivered: encrypted immutable originals, isolated bounded PDF/DOCX
inspection, encrypted extracted data, candidate evidence/taxonomy/revisions,
editing, explicit validation and separate activation, authenticated downloads,
selected-version JSON export and confirmed document deletion. Existing worker
recovers storage intents. Additive migrations 0007/0008 already applied.
Report: reports/phase-4.md; foundation history: reports/cv-security-foundation.md.

Latest audit checks (2026-11-08, before this documentation-only update):
- Backend pytest with .env.test: 131 passed in 148.13s, no skips.
- Ruff check/format passed (116 files); mypy passed (97 source files).
- Alembic current/heads: 0008_candidate_profiles; check: no schema drift.
- Angular app/spec/E2E typecheck and production build passed; 24 Karma successes.
- Playwright with real HTTPS API/worker/native parser: 10 passed in 30.2s.
  Synthetic CVs, disposable schemas and credentials cleaned up by the harness.
Earlier phase 4 delivery: 131 passed in 132.99s / 24 Angular / 10 E2E;
runtime audit reported no known vulnerabilities then (not rerun here).
Documentation-only verification follows this update; application suites are not
rerun merely to change prose. GitHub CI/PostgreSQL 16 remain unverified.

Audit corrections: publication defaults to all dates (0), not 24 h; unknown dates
can remain with unknown_policy=include. Strict rules/radios are proposed only.
Publication/first discovery/last observation are distinct already.
Matching, notifications, applications and documents modules are absent.

## Limits / preserved work

- DOC/OCR unavailable; rule-based extraction is not semantic calibration.
  Owner-labeled anonymized CV/job sets and agreed metrics still needed.
- AppContainer probes validated on Windows only; no external LLM enabled.
- Four manual sources retained; no automated discovery, Apify or paid call.
- Earlier transient PostgreSQL timeouts followed by successful full reruns;
  fixture diagnostics hide connection parameters. No secret copied to docs.
- Existing phase 4 application changes remain for a separate code commit;
  this task commits documentation only. Preserve user angular.json and template
  changes. Do not describe the entire working tree as clean.
- Python 3.11 and local PostgreSQL/Angular retained; no Docker/hosting (D-012).

## Next step / owner review

Await validation of phase 4 delivery and both proposed plans/articulation.
Scraping Engine remains proposed; source permissions require separate verification.
Then resolve lot 2 defaults/boundaries/legacy compatibility before implementation;
report checks and stop for owner validation after each implementation lot.
Documents module, boundary changes, migrations and export/model dependencies
remain proposals requiring concrete review. Never alter applied migrations or SPEC.
Revisit Apify B after matching/permission review, C separately before a real run.
