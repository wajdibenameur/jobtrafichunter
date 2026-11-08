# JobHunter AI - agent instructions

Read `docs/PROGRESS.md` first, update it last.
Then read `docs/DECISIONS.md`, `docs/TODO.md` and the relevant sections of
`docs/SPEC.md`. The specification is immutable; propose changes to the owner.

## Stack and modules
FastAPI (Python 3.11 owner override), Angular and local PostgreSQL; local-only app.
Docker, Compose, container images and hosting are out of scope by owner request.
One modular backend and one worker sharing Python code; PostgreSQL task queue.
Backend modules: auth, cv, profile, sources, search, listings, matching, ai,
notifications, applications. Layout: `backend/app/modules/<module>/`.
Each module owns its tables and exports its public interface via `__init__.py`.
Cross-module imports must use that interface; enforce boundaries in CI.

## Commands
From `backend`, use `.venv/Scripts/python.exe` on Windows (`python` in CI):
- `-m ruff check .` and `-m ruff format --check .`
- `-m mypy app` and `-m pytest -q`
- `-m alembic upgrade head` (configured dedicated PostgreSQL required)
- `-m app.setup owner` / `tls`; see README for HTTPS API startup.
- `-m app.worker --once` checks DB and processes one local search task cycle.
Integration tests require `.env.test` or TEST_DATABASE_URL (database ending _test).
For the isolated local fixture use JOBHUNTER_TEST_ENV=.env.test.local.
From the root: `scripts/frontend.ps1 install|start|build|test|typecheck|preview`.
Frontend: Angular 22, Node >=22.22.3 compatible range, Karma/Jasmine and Playwright.
From backend after frontend build: `python scripts/frontend_e2e.py` uses .env.test.

## Working agreement
- Follow SPEC sections 24, 26 and 27; propose a phase plan before coding and wait
  for owner approval. Stop after each phase report until the owner validates it.
- Current owner override (2026-11-07): defer Velson analysis until frontend work.
  Preserve `frontEnd/velson_template` and its existing local changes meanwhile.
- Owner override: Python 3.11; local-only, no Docker work planned. Audit is in
  `docs/reports/velson-audit.md`, accepted by owner continuation; frontend delivered.
- Update `docs/CHANGELOG.md` and `docs/PROGRESS.md` after each completed task.
  Commit only the intended changes together once checks pass and Git is ready.
- Ask before architecture changes, breaking API changes or existing table changes.
- Record decisions, alternatives, evidence and approval in `docs/DECISIONS.md`.
- Never activate an automated connector unless legal_status is PERMITTED and
  current official documentation and terms have been reviewed and recorded.
- Never scrape LinkedIn. Email alerts require separate verification and consent.
- Never log CV content, tokens or secrets; never commit personal data or secrets.
- Preserve original CVs; never invent extracted facts or visa sponsorship.
- Never claim a feature works without running its checks; report failures honestly.
- Do not fabricate calibration labels, real postings, source permissions or tests.
- The frontend will follow Velson after the deferred analysis and validation.

## Current kickoff deliverables
See `docs/reports/phase-1.md` for delivered local scope, checks and known limits.
Phases 1 and 2 manual scope validated (D-013/D-017); see docs/reports/phase-2.md.
Phase 3 validated (D-024); phase 4 delivered (D-026), wait for validation before phase 5.
Apify deferred until CV/matching (D-023); no paid run without separate C approval.
Docker is not required; GitHub CI is not run. Keep unverified connectors inactive.
AI Job Agent audit: docs/reports/ai-job-agent-audit.md; plan: docs/PLAN-AI-JOB-AGENT.md.
AI Job Agent shared filters validated D-032; its other lots remain PROPOSED.
Do not exceed approved lot scope or infer phase 4 delivery approval.
Scraping: docs/PLAN-SCRAPING-ENGINE.md and docs/reports/scraping-engine-audit.md.
D-032 validates lot 4; approve docs/PLAN-SCRAPING-LOT-5.md before code. Sources inactive.
