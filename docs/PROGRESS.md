# Progress

Last updated: 2026-11-07 by Codex / phase 3 plan
Current phase: 3 - Plan prepared; implementation not started (D-018)
Status: WAITING_FOR_PLAN_APPROVAL

## Phase checklist

- [x] 0 Documentation and phase plans approved.
- [x] 1 Local foundation validated by owner continuation (D-013).
    - [x] Python 3.11 backend, authentication, TLS, PostgreSQL and Angular FR/EN.
    - [x] Local .env configured; owner confirmed successful connection.
    - GitHub CI and PostgreSQL 16 prepared but not run; no Git remote.
    - Docker, Compose, images and hosting out of scope (D-012).
- [x] 2 Owner-selected manual sources and import delivered; owner validated D-017.
    - [x] 2.0 Phase plan approved: oui vasi (D-014).
    - [x] 2.1 LinkedIn/Indeed/Keejob/Tanitjobs registry, preferences, custom sources.
    - [x] 2.2 Manual connector contract, registry and typed failures.
    - Automated providers/HTTP transport deferred by owner choice D-015.
    - [x] 2.3 Atomic confirmed import, CSV preview and migration 0003.
    - [x] 2.4 Sources Angular FR/EN, Tunisian filter, tests and phase report.
- [ ] 3 Criteria, profiles, orchestrator, queue, deduplication and results.
    - [x] 3.0 Continuation confirmed; docs/PLAN-PHASE-3.md proposed.
    - [ ] 3.1 Criteria and saved search profiles.
    - [ ] 3.2 Conservative deduplication, provenance and repost relations.
    - [ ] 3.3 PostgreSQL queue, local execution, resume/cancel and SSE.
    - [ ] 3.4 Search/profiles/results Angular pages and final report.
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
Owner confirmed continuation with phase 3 (D-018); CV management remains phase 4.
Prepared docs/PLAN-PHASE-3.md: search imported offers, saved criteria/profiles,
additive listing provenance/grouping and persistent PostgreSQL queue/results.
No code, migration, dependency or provider access changed. Documentation checks
only for this task; the above application results are from phase 2, not rerun.
Next step: obtain approval of the concrete phase 3 plan before implementation.

## Open questions for the owner

- Approve docs/PLAN-PHASE-3.md, including local imported-offer search and additive tables.
