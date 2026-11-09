# Progress

Last updated: 2026-11-09 by Codex / verified GitHub CI (D-035)
Current task: Linux and native Windows CI verified; await functional delivery validation
Status: CI_VERIFIED_LINUX_AND_WINDOWS / FUNCTIONAL_VALIDATIONS_PENDING

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

## AI Job Agent - common modules, separate approvals

- [x] Audit reports/ai-job-agent-audit.md; documentation authorized D-027.
- [x] PLAN-AI-JOB-AGENT.md; shared filters via Scraping lot 4 D-031/D-032.
- [x] Strict 2/6/24 h radios and legacy compatibility delivered and validated.
- [ ] Explained/calibrated matching, scheduling, priorities and alerts.
- [ ] Tailored CV, preview/validation and DOCX/PDF export.
- [ ] Cover letter, languages/styles/versions/exports.
- [ ] Validated ZIP, apply link and confirmed application tracker.
- [ ] Complete validation/security/local operations.

These lots do not renumber historical phases. Scraping continuation approves neither
phase 4 CV delivery nor the other AI Job Agent lots. No duplicate filter/matching engine.

## Scraping Engine - lot 5 locally delivered, sources inactive

- [x] Audit reports/scraping-engine-audit.md and source evidence D-028.
- [x] PLAN-SCRAPING-ENGINE.md; permissions independent of lot approval.
- [x] Lot 2 infrastructure D-029, validated D-030.
- [x] Lot 3 generic extraction D-030, validated D-031.
- [x] Lot 4 Angular/shared filters D-031, validated D-032; commit 72143fd.
- [x] Lot 5 detailed plan D-032, commit 5b7201a, approved by continuation D-033.
- [x] Lot 5 local implementation/checks: reports/scraping-lot-5.md; validation pending.
- [x] CV migration base versioned separately in 2b34645 for GitHub publication D-034.
- [ ] Real adapters only after verified permission for a concrete scope.
- [ ] Shared matching/alerts/documents after their prerequisites and plan approval.

LinkedIn without scraping; Indeed/Tanitjobs manual pending permission. Keejob/RSS
and career APIs are candidates only. Four manual workflows remain available.

## Apify - separate A/B/C workflow

- [x] A reviewed/proposed: reports/apify-phase-a.md (D-022).
- [x] Separate card in Sources proposed; owner waits for matching (D-023).
- [ ] B deferred until matching, source permission and implementation approval.
- [ ] Actor/method permission verified; currently UNVERIFIED.
- [ ] C separate explicit approval for a real 10-job run and concrete budget.

## Last session / implementation

Owner continued after the detailed lot 5 proposal: approved D-033 on 2026-11-08.
Local delivery/checks completed 2026-11-09. Same SearchQueue/worker, explicit
COLLECTED_OFFERS scope, COLLECT -> SCAN -> FILTER, historical local default unchanged.
Public CollectionService and listings ingestion; no cross-module private imports.
Seven annex tables, additive migrations 0009/0010/0011, no historical table changes.

Atomic ingestion/receipt/checkpoint; canonicalization/grouping reused. Original
manual fields/imports/first_seen_at preserved; collected metadata in observations.
Durable HTTP reservations, source slot and Retry-After shared between profiles;
active reservation id prevents a late settlement from releasing a newer attempt.
Current permission/limits rechecked at network/ingestion boundaries, lease fenced,
cancellation terminal, no late commits. Network remains at-least-once, not exactly-once.

Angular actions/volume use real capabilities; start opens existing Search SSE.
History/reload/cancel/results reused, collection scope/status/counts distinguished.
No production automatic adapter registered: actions stay unavailable normally.
Frequency/matching/notifications remain absent. Mock adapters injected only by tests.

## Final evidence

- Backend complete with .env.test and native Windows parser: 272 passed in 259.13s.
  No skips. Includes 24 new collection/migration tests, also 24 passed in 107.95s targeted.
- Ruff check and format --check passed (131 files); mypy passed (109 files).
- Alembic check, downgrade to 0008, upgrade head and check passed in disposable schema;
  original imported offers preserved. Personal application database not migrated.
- Angular app/spec/E2E typecheck and production build passed, budgets respected.
- Karma ChromeHeadless: 37 SUCCESS, including 4 new action tests.
- Playwright API HTTPS/worker/native parser + browser simulation: 12 passed in 40.9s.
  One new scenario: limits, existing SSE, reload/cancel/mobile; prior 11 remain green.
- Desktop/mobile captures inspected; no overflow, sidebar transition complete.
  Disposable E2E schema/credentials/synthetic CV artifacts cleaned by harness.
- Corrected HTTP fixture stream, legacy label/select locator, source-slot timing race.
  Initial sandbox full run interrupted after native-test errors; final run escalated.
- SPEC SHA256 unchanged; no dependency, provider activation, real or paid collection.

Historical evidence: lot 4 = 248 backend / 33 Angular / 11 E2E; lot 3 = 219 backend;
lot 2 = 181 backend. Their reports remain under docs/reports. Consult GitHub for CI results.

## Limits / Git / next owner review

Report: reports/scraping-lot-5.md. Local delivery needs owner validation before lot 6.
Owner supplied https://github.com/wajdibenameur/jobtrafichunter.git and explicitly
chose to keep it public. Remote empty/access verified; origin configured. D-034
authorizes versioning/publication, not functional phase acceptance. CV base 0007/0008
committed separately in 2b34645; lot 5 committed in 56ba4f9, complete Alembic chain.
Prepublish scan: 267 worktree files / 535 historical blobs, no secrets detected;
local secrets/CVs/TLS keys/cache/tools/template excluded. Lint/typing rechecked.
Initial push main succeeded; initial remote SHA verified against local 56ba4f9.
Report: reports/github-publication.md; CI report: reports/ci-validation.md.
D-035 fixed the systemd cluster name and added real native Windows CI alongside Linux.
Native CV parsing runs on Windows; Linux tests its fail-closed refusal. Browser
navigation waits for /search before profile selection, with original assertions kept.
Run 42611520631 on code/workflow/test commit 73bd53a: BOTH JOBS SUCCESS.
- Linux PostgreSQL 16: 267 passed / 5 Windows-only exclusions, 90.04% coverage;
  37 Angular, Python/npm audits green; 12 E2E passed in 19.3s / 1 native exclusion.
- Windows PostgreSQL 17: real AppContainer prepared, 272 passed in 93.35s;
  12 E2E passed in 28.6s / 1 Linux-only exclusion; isolated cluster stopped.
- Local post-fix E2E: 12 passed in 37.8s / 1 Linux exclusion, typechecks passed.
Final report commit is docs-only [skip ci]; no code/tests/workflow changed after
that successful remote run. No Dependabot PR merged or dependencies changed.
No real collection, paid call or hosting; publication does not validate phase delivery.

No migration applied to the personal DB. After reviewing the versioned migrations,
apply alembic upgrade head before API/worker restart; old schemas lack annex tables.
During COLLECT cancellation, committed offers remain in the catalog; filtered
results may not yet exist. Known listing content is not enriched from observations.
Retention policy future; conservative crash reservations may reduce useful volume.
No matching/calibration/notifications/generated documents, scheduler, source activation,
Docker or hosting. Source permission and any paid run remain separately gated.
Await lot 5 validation before common matching/alerts work with
phase 4 CV prerequisite and owner-labelled datasets. Do not infer their approval.
