# Progress

Last updated: 2026-11-08 by Codex / generic JSON-LD extraction (D-030)
Current task: Scraping lot 2 validated; lot 3 generic extraction delivered
Status: WAITING_FOR_LOT_3_VALIDATION

## Historical phases

- [x] 0 Original documentation and plans approved.
- [x] 1 Local Python 3.11/auth/TLS/PostgreSQL/Angular foundation validated (D-013).
- [x] 2 Manual sources and confirmed URL/CSV import validated (D-017).
- [x] 3 Local search delivered (D-021) and owner-validated (D-024).
- [x] 4 Private CVs, parsing, editing and candidate validation delivered (D-026).
    - Plan approved D-024; delivery still WAITING_FOR_VALIDATION.
- [ ] 5 CV matching/calibration; module remains absent.
- [ ] 6 Telegram, scheduling and notification history.
- [ ] 7 Applications, hardening, local backup/restore.

## AI Job Agent — proposed implementation, not approved

- [x] Audit saved: reports/ai-job-agent-audit.md; documentation authorized D-027.
- [x] Seven-lot plan saved: PLAN-AI-JOB-AGENT.md, status PROPOSED.
- [ ] Lot 2: strict 2 h/6 h filters and radios, temporal/legacy compatibility.
- [ ] Lot 3: explained/calibrated matching, then scheduling/priorities/alerts.
- [ ] Lot 4: tailored CV, preview, validation and DOCX/PDF export.
- [ ] Lot 5: cover letter, languages/styles/versions/exports.
- [ ] Lot 6: validated ZIP, apply link and confirmed application tracker.
- [ ] Lot 7: complete validation/security/local operations.

These lots do not renumber historical phases. Tailored CV/letters remain absent;
Scraping continuations do not approve the whole AI Job Agent plan or phase 4 delivery.

## Scraping Engine — generic lot 3 delivered, sources inactive

- [x] Audit: reports/scraping-engine-audit.md; documentation saved D-028.
- [x] Evidence: sources/scraping-review.md; no PERMITTED source attributed.
- [x] Plan: PLAN-SCRAPING-ENGINE.md, only current lot authorized at each continuation.
- [x] Lot 2 infrastructure delivered D-029, validated by continuation D-030.
- [x] Lot 3 generic extraction delivered D-030, awaiting validation.
- [ ] Real source adapters: pending verified permissions for a concrete scope.
- [ ] Lot 4 Angular; lot 5 worker/DB integration; not started.
- [ ] Shared matching/alerts/documents, then full validation; no duplicate engines.

LinkedIn stays without scraping; Indeed/Tanitjobs manual pending permission.
Keejob Markdown/RSS and enterprise APIs remain candidates, not activated sources.

## Apify — explicit A/B/C workflow

- [x] A Modules/queue/UI and official documents reviewed (D-022).
- [x] A Recovery/consent/budget design and separate card inside Sources proposed.
- [x] Owner chose to wait for CV/matching, not collection-only scope (D-023).
- [ ] B Deferred until matching, permission review and implementation approval.
- [ ] Actor/method permission verified; currently UNVERIFIED.
- [ ] C Separate explicit approval for a real 10-job run and concrete budget.

## Last session / current evidence

Owner continued after lot 2 report: validated lot 2 and authorized lot 3 (D-030).
Added offline jsonld.py and internal normalized metadata: locations, contract,
explicit skill/experience text, publication precision, provenance and warnings.
HTML/JSON bounded; no JavaScript, remote contexts or links executed/fetched.
Page preparation reuses authorization, limits and result budget; ambiguous/invalid
records are visible, truncation cannot silently skip to the next document.
No source adapter, UI, API route, worker integration or migration added.

Current checks:
- Complete backend with .env.test: 219 passed in 132.68s, no skips.
- Targeted transport/extraction: 88 passed in 3.51s, 38 new JSON-LD tests.
- Ruff/format passed (122 files); mypy passed (103 source files).
- Alembic check: no schema drift; pip-audit runtime: no known vulnerabilities.
- Existing dependency versions preserved; Beautiful Soup 4.15.0/SoupSieve 4.0.1
  added, hashed locks and Python 3.11.9 environment verified.
- No frontend change/rerun. Historical evidence: 24 Angular / 10 E2E in 30.2s.
Report: reports/scraping-lot-3.md. Lot 2 history: reports/scraping-lot-2.md
(181 backend / 50 new tests, current transport still tested in full suite).

Earlier audit/docs tasks D-027/D-028 are recorded in DECISIONS/CHANGELOG and the
linked audit reports; their test counts are historical, not new full executions.
Phase 4 report: reports/phase-4.md; foundation: reports/cv-security-foundation.md.
CV originals/encrypted data/revisions/validation/activation delivered; not tailored CVs.

## Limits / preserved work

- DTO metadata only: DB persistence and current authorization loading remain lot 5.
- Quotas in memory, no guarantee between restarts/multiple processes yet.
- UTF-8 and supported bounded JSON-LD only, not a full JSON-LD processor.
- Date-only/naive publication cannot become an instant for strict hourly filters.
- Existing date filters still default all dates; unknown_policy may include unknowns.
  Radios/strict windows are future UI/filter work, not delivered by internal DTOs.
- DOC/OCR unavailable, extraction quality not calibrated; owner-labeled datasets
  still needed. No external LLM, real job dataset or invented calibration labels.
- No real collection, source activation or paid Apify call. Four manual paths intact.
- CV code/pypdf changes remain separate and uncommitted; preserve angular.json and
  independent template changes. Only intended extraction/dependency/docs lot committed.
- SPEC unchanged; no Docker/hosting. GitHub CI/PostgreSQL 16 unverified.

## Next step / owner review

Await validation of generic extraction lot 3 before lot 4 Angular.
Real adapters require source permission independently of plan approval.
Phase 4 delivery and AI Job Agent implementation plan still need validation.
Before persistence/boundary changes, propose concrete additive migrations/interfaces.
Revisit Apify B after matching/permission review, C separately for any real run.
