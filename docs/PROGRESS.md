# Progress

Last updated: 2026-11-07 by Codex / phase 3 delivery
Current phase: 3 - Local search, profiles, queue and results delivered (D-019, D-021)
Status: WAITING_FOR_VALIDATION

## Phase checklist

- [x] 0 Documentation and phase plans approved.
- [x] 1 Python 3.11/auth/TLS/PostgreSQL/Angular foundation validated (D-013).
- [x] 2 Manual sources and confirmed URL/CSV import validated (D-017).
    - LinkedIn, Indeed, Keejob, Tanitjobs and custom sites; no provider automation.
- [x] 3 Approved local scope delivered; owner validation pending.
    - [x] 3.0 Plan approved: vasi (D-019).
    - [x] 3.1 Criteria, profiles CRUD/duplicate and explicit editable examples.
    - [x] 3.2 Additive provenance, conservative groups, candidates and reposts.
    - [x] 3.3 PostgreSQL queue, fenced worker leases, resume/cancel and SSE.
    - [x] 3.4 Angular profiles/search/results, local dashboard and phase report.
- [ ] 4 Private CVs, parsing, editing and profile validation.
- [ ] 5 CV search, explainable matching, calibration, verified linkedin_email.
- [ ] 6 Telegram, scheduling, history and logs.
- [ ] 7 Applications, hardening, local backup/restore tests.

## Last session

Done: phase 3 delivered per docs/reports/phase-3.md. Search only imported offers;
provider logs explicitly skip manual collection. Unknown requirements stay flagged.
Profiles, criteria and immutable result snapshots persist per owner. Multiple
provenances group conservatively without deleting imports or resetting discovery.
Queue claims, fencing, heartbeat, bounded retry, recovery and cancellation tested.
Worker --once now checks DB and processes one bounded task cycle.
Separate-process worker registration defect exposed by E2E, fixed via public
imports and covered by its own integration test. No secret-bearing tracebacks.
Migrations 0004/0005/0006 applied to jobhunter_app; Alembic check reports no drift.
Windows timezone data tzdata 2026.6 locked and hashed (D-020).
Tests: 105 backend passed (92.30s), dedup coverage 100%, filters/novelty 91%;
Ruff/format (86 files) and mypy (71 files) pass. Angular typecheck/build pass,
21 Karma tests and 9 Playwright tests pass (20.7s). Runtime npm/pip audits clear.
Screenshots desktop/mobile/dialog inspected; disposable DB schemas, API, worker
and browser credentials cleaned after E2E. New pages FR/EN retain Velson theme.
Limits: max 500 recent imports and 100 candidates per identity, explicitly PARTIAL
when exceeded; task 3 minutes/execution 15 minutes. No provider collection,
CV extraction, IA score, Telegram or scheduler. GitHub CI/PostgreSQL 16 not run.
Original template and pre-existing angular.json analytics setting preserved;
angular.json excluded from commits. SPEC unchanged. No private data/assets staged.
Docker, Compose, images and hosting remain out of scope (D-012).
Next step: wait for owner validation; then propose the phase 4 CV plan before code.

## Open questions for the owner

- Validate the local phase 3 delivery before phase 4 (AGENTS.md / SPEC 24.2).
