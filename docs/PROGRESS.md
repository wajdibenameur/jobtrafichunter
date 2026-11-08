# Progress

Last updated: 2026-11-08 by Codex / detailed Scraping lot 5 plan (D-032)
Current task: Scraping lot 4 validated; lot 5 interfaces/migrations proposed
Status: WAITING_FOR_LOT_5_PLAN_APPROVAL

## Historical phases

- [x] 0 Original documentation and plans approved.
- [x] 1 Local Python 3.11/auth/TLS/PostgreSQL/Angular foundation validated (D-013).
- [x] 2 Manual sources and confirmed URL/CSV import validated (D-017).
- [x] 3 Local search delivered (D-021) and owner-validated (D-024).
- [x] 4 Private CVs/parsing/candidate validation delivered (D-026).
    - Plan approved D-024; delivery still WAITING_FOR_VALIDATION.
- [ ] 5 CV matching/calibration; module remains absent.
- [ ] 6 Telegram, scheduling and notification history.
- [ ] 7 Applications, hardening, local backup/restore.

## AI Job Agent — shared filters delivered; remaining plan proposed

- [x] Audit: reports/ai-job-agent-audit.md; documentation authorized D-027.
- [x] Plan: PLAN-AI-JOB-AGENT.md, shared filters delivered via Scraping lot 4 D-031.
- [x] Lot 2 shared implementation: strict 2/6/24 h, radios, legacy compatibility.
    - Validated with Scraping lot 4 D-032; do not rebuild these filters.
- [ ] Lot 3: explained/calibrated matching, then scheduling/priorities/alerts.
- [ ] Lot 4: tailored CV, preview, validation and DOCX/PDF export.
- [ ] Lot 5: cover letter, languages/styles/versions/exports.
- [ ] Lot 6: validated ZIP, apply link and confirmed application tracker.
- [ ] Lot 7: complete validation/security/local operations.

These lots do not renumber historical phases. Tailored documents remain absent;
Scraping continuations do not approve the other AI lots or phase 4 CV delivery.

## Scraping Engine — lot 4 validated, lot 5 proposed, sources inactive

- [x] Audit: reports/scraping-engine-audit.md, saved D-028.
- [x] Evidence: sources/scraping-review.md; no PERMITTED source attributed.
- [x] Plan: PLAN-SCRAPING-ENGINE.md; only current lot authorized at each continuation.
- [x] Lot 2 infrastructure delivered D-029, validated D-030.
- [x] Lot 3 generic extraction delivered D-030, validated D-031.
- [x] Lot 4 page/profile preparation/shared filters delivered D-031, validated D-032.
- [ ] Real source adapters pending verified permissions for a concrete scope.
- [x] Lot 5 concrete proposal: PLAN-SCRAPING-LOT-5.md, D-032, not approved for code.
- [ ] Lot 5 worker/DB integration and migrations after explicit plan approval.
- [ ] Shared matching/alerts/documents, then full validation; no duplicate engines.

LinkedIn stays without scraping; Indeed/Tanitjobs manual pending permission.
Keejob Markdown/RSS and enterprise APIs remain candidates, not activated sources.

## Apify — explicit A/B/C workflow

- [x] A Modules/queue/UI/documents reviewed (D-022), recovery/consent/budget proposed.
- [x] Separate card inside Sources proposed; owner waits for matching (D-023).
- [ ] B Deferred until matching, permission review and implementation approval.
- [ ] Actor/method permission verified; currently UNVERIFIED.
- [ ] C Separate explicit approval for a real 10-job run and concrete budget.

## Last session / current evidence

Owner continued after lot 4 report/commit 72143fd: delivery validated D-032.
Prepared PLAN-SCRAPING-LOT-5.md after reviewing current queue/executions/models,
sources/listings public interfaces, transport budgets, Angular and SPEC constraints.
Proposed additive scope, seven new side tables and three append-only migrations;
same queue/worker, durable per-attempt reservations and atomic page ingestion/checkpoint.
Imports preserved; all collection tests simulated. No code/migration executed,
network request, provider activation or new dependency in this documentary session.
Plan approval is required before implementation, independently of source permission.

Prior delivery evidence (D-031), not rerun for this documentation-only change:
Added protected /scraping page to Velson shell, using existing SearchApi/SourceApi
and CriteriaEditor. Profile edits persist through existing PUT; selection restores
from URL; loading/error/server-confirmed success and local history/results links.
Collection launch/stop/test and volume/frequency controls disabled and explained;
unknown source counters remain unknown, no fake external execution or source toggle.

Shared radio editor and filter_fact extended: publication_minutes optional
120/360/1440, exclusive with nonzero publication_days. Strict hourly cutoffs,
unknown/future publication excluded. New Angular profiles default 24 h; backend
legacy default and saved profiles unchanged. Seven/thirty-day and advanced legacy
semantics preserved. No migration, dependency, worker or collection endpoint added.

Historical lot 4 checks:
- Backend complete with .env.test: 248 passed in 155.31s, no skips (29 new).
- Ruff/format passed (123 files); mypy passed (104); Alembic check no drift.
- Angular app/spec/E2E typecheck and production build passed, budgets respected.
- Karma ChromeHeadless: 33 SUCCESS (9 new).
- Playwright real HTTPS API/worker/native parser: 11 passed in 31.2s (1 new).
  New case proves saved/reloaded radios and one real local result instead of
  old/unknown publications, safe disabled collection actions, keyboard/mobile/EN.
- Three synthetic desktop/mobile screenshots inspected; no horizontal overflow.
  Schema, credentials and synthetic CV artifacts cleaned by the harness.
- Earlier locator/fixture-order/mobile-label/style issues corrected; original
  ten browser scenarios remain green. Reports preserve the verification history.
Report: reports/scraping-lot-4.md. No real collection or paid call.

Historical evidence: lot 3 = 219 backend / 38 new JSON-LD tests; lot 2 = 181 backend
/ 50 new transport tests. Audit/docs history D-027/D-028 is in DECISIONS/CHANGELOG.
CV report: reports/phase-4.md; foundations: reports/cv-security-foundation.md.

## Limits / preserved work

- Page is preparation/local search, not an active web collector. Volume/frequency
  are not saved yet; history shows only the last 50 local executions, manual refresh.
- JSON-LD metadata persistence, current authorization loading and durable checkpoints
  remain lot 5. Transport quotas remain in memory; scheduler/alerts are later.
- No matching/notifications/generated application documents or provider activation.
- Strict hourly filters never substitute first_seen_at for publication. Known
  imported dates are declarations, not independent source verification.
- DOC/OCR unavailable; owner-labeled datasets still needed. No external LLM.
- CV code/pypdf changes remain separate and uncommitted; preserve angular.json,
  independent template and CV route/nav changes in shared files. This session
  changes documentation only. Do not describe the whole working tree as clean.
- SPEC unchanged; no Docker/hosting. GitHub CI/PostgreSQL 16 unverified.

## Next step / owner review

Await approval of PLAN-SCRAPING-LOT-5.md before code or migrations. Documentation
links, SPEC hash, matching AGENTS/CLAUDE and diff whitespace checked for this session;
application suites not rerun because code is unchanged. Source permission is
independent of plan approval. Phase 4 CV delivery
and other AI Job Agent lots still need validation. Never alter applied migrations.
Revisit Apify B after matching/permission review, C separately for any real run.
