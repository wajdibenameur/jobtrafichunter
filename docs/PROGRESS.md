# Progress

Last updated: 2026-11-07 by Codex / phase 2 delivery
Current phase: 2 - Sources and manual import delivered (D-014, D-015)
Status: WAITING_FOR_VALIDATION

## Phase checklist

- [x] 0 Documentation and phase plans approved.
- [x] 1 Local foundation validated by owner continuation (D-013).
    - [x] Python 3.11 backend, authentication, TLS, PostgreSQL and Angular FR/EN.
    - [x] Local .env configured; owner confirmed successful connection.
    - GitHub CI and PostgreSQL 16 prepared but not run; no Git remote.
    - Docker, Compose, images and hosting out of scope (D-012).
- [x] 2 Owner-selected manual sources and import delivered; validation pending.
    - [x] 2.0 Phase plan approved: oui vasi (D-014).
    - [x] 2.1 LinkedIn/Indeed/Keejob/Tanitjobs registry, preferences, custom sources.
    - [x] 2.2 Manual connector contract, registry and typed failures.
    - Automated providers/HTTP transport deferred by owner choice D-015.
    - [x] 2.3 Atomic confirmed import, CSV preview and migration 0003.
    - [x] 2.4 Sources Angular FR/EN, Tunisian filter, tests and phase report.
- [ ] 3 Criteria, profiles, orchestrator, queue, deduplication and results.
- [ ] 4 Private CVs, parsing, editing and profile validation.
- [ ] 5 CV search, explainable matching, calibration, verified linkedin_email.
- [ ] 6 Telegram, scheduling, history and logs.
- [ ] 7 Applications, hardening, local backup/restore tests.

## Last session

Done: delivered docs/reports/phase-2.md and the manual scope approved in D-015.
Sources UI saves selection/settings, prepares encoded links, manages custom sites.
URL/CSV import requires preview and confirmation; errors block invalid CSV batches.
PostgreSQL imports preserve original provenance and first_seen_at, avoid exact
normalized duplicates and roll back ambiguous batches. Missing CSV fields do not
erase known facts. Advanced provided fields are displayed before confirmation.
Migrations 0002/0003 applied to jobhunter_app; Alembic check reports no drift.
Tests: 81 backend passed (48.86s), Ruff/format and mypy (51 files) pass;
Angular build/typecheck pass, 18 Karma tests and 7 Playwright tests pass (12.4s).
Runtime npm/pip audits: no known vulnerabilities reported.
Desktop/mobile screenshots inspected; fixture schemas and credentials cleaned up.
Not done: automated providers, HTTP transport, matching, IA extraction and queue
are outside this manual delivery. GitHub CI/PostgreSQL 16 not executed.
Preserved original template and pre-existing angular.json analytics change;
angular.json excluded from commits. SPEC unchanged; no private assets/secrets staged.
Next step: wait for owner validation; then propose a phase 3 plan before coding.

## Open questions for the owner

- Validate the manual phase 2 delivery before phase 3 (AGENTS.md / SPEC 24.2).
