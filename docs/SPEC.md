# JobHunter AI — Master Prompt (version révisée)

À donner tel quel à Claude Code, Codex ou Cursor. Remplacer la section 3 une fois la maquette envoyée.

**Stack decision (final):** single-owner tool, built to ship fast: **FastAPI (Python) + Angular + PostgreSQL**, Docker. There is one Python backend; the CV parser and matcher are internal modules, not a separate service. Wherever older text mentions Spring Boot, JPA, Flyway, JUnit, Testcontainers-Java or a separate `ai-service`, read FastAPI, SQLAlchemy, Alembic, pytest, testcontainers-python and the in-process `ai` module.

---

## 1. Role and objective

You are a senior full-stack architect and engineer. Build **JobHunter AI**, a production-quality, configurable job-search platform for IT candidates. It is **not** a hardcoded scraper: sources, domains, locations, filters and CV-derived criteria are all stored in the database and editable from the UI.

Core value: the user uploads a CV, validates the extracted profile once, chooses sources and preferences, and the system finds, de-duplicates, scores and ranks **new** job offers, then notifies via Telegram.

Work incrementally. After each phase: compile, run tests, summarize what exists, and only then continue. Never claim a feature works without running it.

## 2. Technology stack

- **Backend:** Python 3.12, FastAPI (async), Pydantic v2 for schemas and settings, SQLAlchemy 2.0 + Alembic migrations, httpx for outbound calls, APScheduler (or Arq) for scheduled and background jobs, OpenAPI docs generated automatically.
- **Frontend:** Angular (latest stable), TypeScript strict, Angular Material or the component library implied by the mockup, RxJS, reactive forms, lazy-loaded routes, responsive.
- **AI/NLP:** internal Python package `app/ai` inside the backend (CV parsing with PyMuPDF/pdfplumber/python-docx, skill normalization, job extraction, scoring). No separate microservice; the module boundary stays clean so it can be extracted later if needed.
- **Database:** PostgreSQL 16, Alembic migrations (no hardcoded preferences), optional pgvector for embeddings.
- **Infra:** Docker + docker-compose (frontend, backend, worker, postgres), `.env.example`, health checks, GitHub Actions CI (lint, type-check, tests, image build).
- **Notifications:** Telegram Bot API.
- **LLM access:** abstracted behind an interface (provider configurable via env). Must work in a degraded rule-based mode if no LLM key is configured.

## 3. UI/UX reference (mockup)

The provided mockup is the **official UI/UX reference**.

1. Analyze every page and component of the mockup first.
2. Reproduce faithfully: colors, typography, spacing, navigation, icons, states, responsive behavior.
3. Extract design tokens (CSS variables / theme) and reusable components.
4. Connect screens to the FastAPI endpoints.
5. List any screens required by this spec but missing from the mockup, and propose them in the same visual style. Do not alter the existing design.

**Mockup location (local folder):** `C:\Users\kbakh\OneDrive\Bureau\PFE\JobHunter\frontEnd\velson_template`

First task, before any code: open this folder and report what it is (static HTML/CSS template, Angular project, Figma export or screenshots), its pages, layouts, reusable components, styles, fonts and assets, and which screens of section 11 it covers or lacks. Wait for validation of that report. If it is a purchased UI template, reuse its layout, components and styles inside the Angular app, keep its license terms (no redistribution of the template files in a public repository), and do not copy unused demo pages or vendor code that is not needed.

## 4. Architecture rules

- Layered backend: routers → services → repositories; Pydantic schemas separate from SQLAlchemy models; dependency injection with FastAPI `Depends`; no ORM objects in API responses; full type hints, checked with mypy (strict on `app/`) and formatted/linted with Ruff.
- Connector pattern: each job source implements `JobSourceConnector` (`fetch`, `normalize`, `health_check`, `capabilities`). New sources are added without touching the orchestrator.
- Clear separation of three concerns: **JobSource** (what to query), **SearchProfile / SearchConfiguration** (how to query), **SearchExecution** (one run and its results). Changing criteria never requires a code change; executions can be compared over time.
- CV pipeline split in three independent stages: **CV Parser → Candidate Profile (human-validated) → AI Job Matcher**. Editing a CV recomputes criteria without losing application history.
- Centralized exception handlers, structured JSON logging, correlation id per search execution.
- Secrets only via environment variables (Pydantic Settings). Never commit credentials.

## 5. Legal and ethical constraints (mandatory)

- Only activate connectors with a **supported and permitted** collection method: official APIs, public RSS/feeds, partner or open-data APIs (e.g., France Travail API, EURES, RemoteOK/Remotive/WeWorkRemotely feeds where terms allow), or company career pages whose terms and robots.txt allow it.
- Respect robots.txt, terms of service, rate limits and caching. No login bypass, no CAPTCHA circumvention, no credential scraping.
- For sources without a permitted automated method (e.g., LinkedIn, Indeed, Keejob, Tanitjobs unless an official/permitted route exists), provide: (a) a generated **deep search link** opening the site with the user's criteria, and (b) **manual import** (paste URL / paste description / browser-extension-free CSV import).
- A source being selectable never implies scraping is allowed. Each source has a visible integration status: `API`, `FEED`, `LINK_ONLY`, `MANUAL_IMPORT`, `DISABLED`.
- Never infer confirmed visa sponsorship without reliable textual evidence.
- Never invent CV data. Never modify the user's original CV file.

## 6. Domain model (Alembic migrations)

Entities: `AppUser`, `JobSource`, `JobListing`, `JobSkill`, `JobDomain`, `SearchProfile`, `SearchConfiguration`, `SearchExecution`, `SourceExecutionLog`, `CandidateCv`, `CandidateProfile`, `CvExperience`, `CvEducation`, `JobMatch`, `JobApplication`, `Notification`, `NotificationPreference`.

Key fields for `JobListing`: id, source\_id, source\_job\_id, canonical\_url, title, company, country, city, work\_mode (remote/hybrid/onsite), domain, experience\_level, min/max years, description, skills (mandatory vs optional), visa\_status (`CONFIRMED`, `POSSIBLE`, `RELOCATION`, `NOT_SPECIFIED`, `NONE`), published\_at, **first\_seen\_at**, **last\_seen\_at**, status (`ACTIVE`, `EXPIRED`, `REPOSTED`, `CLOSED`), fingerprint hash, repost\_of\_id.

Use unique constraints and indexes on (source\_id, source\_job\_id), canonical\_url, fingerprint.

## 7. Search configuration

### 7.1 Sources page

- Cards per source with enable/disable switch, Select all / Deselect all.
- Show integration status, last successful sync, jobs collected per source, errors, manual sync button, source-specific settings.
- Initial Tunisia: Keejob, Tanitjobs, LinkedIn Jobs, Indeed, company career pages, other Tunisian boards.
- Initial Europe/International: LinkedIn Jobs, Indeed, EURES, Welcome to the Jungle, France Travail, Make it in Germany, Wellfound, RemoteOK, Remotive, We Work Remotely, company career pages.
- Sources are seeded by migration but manageable from the UI.

### 7.2 Domains and job titles

Multi-select categories and individual titles, plus custom include keywords and exclude keywords:

- **Software Development:** Java, Spring Boot, Angular, Full Stack, Backend, Frontend, Python, Software Engineer.
- **DevOps & Cloud:** Junior DevOps, DevOps, Cloud, AWS, Azure, CI/CD, Platform Engineer, SRE, Docker, Kubernetes.
- **Data Engineering & Analytics:** Junior Data Engineer, Data Engineer, ETL, Analytics Engineer, Data Analyst, BI/Power BI, SQL, Big Data, Data Warehouse, PySpark, Databricks.
- **AI:** Junior AI, Machine Learning, Generative AI, LLM, RAG, Python AI.
- **Business & IT Consulting:** Junior Business Analyst, IT Business Analyst, Functional/Technical Consultant, Application Support.

### 7.3 Experience

Levels: Internship, Graduate, Entry Level, Junior, Associate, Mid-Level, Senior. Defaults: Graduate, Entry Level, Junior (Internship optional). Configurable max years, default 3. **Analyze real requirements**, do not reject a job just because the title lacks "Junior", and do not accept one just because it has it.

### 7.4 Location

Multi-country and city selection (Tunisia: Tunis, Ariana, Sfax, Sousse, Monastir, others; International: France, Germany, Portugal, Belgium, Netherlands, Luxembourg, Ireland, Finland, Sweden, Poland, Canada, UK, UAE, Saudi Arabia, Qatar). Work mode: Remote / Hybrid / On-site.

### 7.5 Visa

Filters: Confirmed, Possible, Relocation assistance, Not specified, No sponsorship. Option to prioritize confirmed sponsorship in ranking.

### 7.6 Publication date and novelty

Publication filters: 24h, 3 days, 7 days, 30 days, all. Novelty filters: New Today, 24h, 3d, 7d, 30d, All. **"New" is based on first verified discovery (`first_seen_at`)**, displayed separately from the original publication date. Re-collecting an old job never makes it new. Detect reposts (same fingerprint, new date) and label them `REPOSTED`.

### 7.7 Deduplication

URL normalization (strip tracking params), source id tracking, cross-site fuzzy matching (normalized title + company + city + description similarity), fingerprint hash. Merge duplicates into one listing with multiple source links.

### 7.8 Search profiles

Save, edit, delete, duplicate. Each stores sources, domains, keywords, exclusions, countries, cities, work mode, experience, visa filters, date filters, min matching score, search mode, linked CV, notification settings. Provide editable (non-hardcoded) seed examples: *Tunisia Junior Developer*, *Europe Visa Sponsorship*, *Remote International*.

## 8. Search orchestration

On "Start Search":

1. Load the selected profile/configuration.
2. Resolve keywords according to mode: **A – CV automatic**, **B – Manual**, **C – Hybrid**.
3. Run only enabled and available connectors, in parallel, with timeouts, retries, rate limiting.
4. Normalize → deduplicate → apply eligibility filters → AI matching → persist.
5. Compute counters: sources checked/failed, collected, new, duplicates, matching.
6. Trigger Telegram notifications per saved preferences.

Also: manual and scheduled daily search (configurable frequency), search history, per-source execution logs, cancellation when technically possible, live progress (SSE or WebSocket).

**Failures must be visible.** A source that errors or times out is reported as failed, never as "0 results". The UI distinguishes "no results" from "source unavailable".

## 9. CV Intelligence

### 9.1 CV management

Upload PDF/DOCX/DOC, preview, download, replace, delete, multiple versions, one active CV, selectable CV per search profile. Store files privately (never public URLs; authenticated download only; size/type validation; antivirus hook optional). Original file is immutable.

### 9.2 Parsing (Python module)

Extract: professional title, summary, education, experiences (title, company, dates, responsibilities, achievements, technologies), years of experience, languages, certifications, and categorized skills (languages, frameworks, backend, frontend, databases, DevOps, cloud, AI/ML, data engineering, business analysis tools). Handle FR/EN/AR-origin names and French or English CVs. **Never invent missing information**; unknown fields stay empty and flagged.

### 9.3 Candidate Profile

Generate a structured profile (title, level, domains, skills with source evidence, preferred locations, target levels, visa need). The user **must review, edit and validate** before activation. Keep versions; re-parsing a new CV proposes a diff rather than overwriting.

### 9.4 CV-based search

Button **"SEARCH JOBS BASED ON MY CV"**: read the active validated profile, derive job titles, domains and keywords (including synonyms and adjacent roles), combine with source/location/experience/visa/date filters, collect, analyze, score, save and show the most relevant new opportunities.

### 9.5 AI matching

Score 0–100 comparing CV and job: skills, experience, seniority, education, languages, frameworks, industry, spoken-language requirements, location, remote eligibility, visa. Distinguish **mandatory** from **optional** requirements. Output for each job:

- **Why this job matches** (skills found, relevant experience, qualifications),
- **What is missing** (skills, experience gaps, language, mandatory requirements),
- sub-scores and confidence.

No inflated scores from title match alone. Scoring must be deterministic and explainable; LLM use is limited to extraction/explanation and is validated against structured output schemas. Store the model/version used.

## 10. Telegram notifications

Per-user bot token/chat id configuration with a test button. Send only **new qualifying** jobs (above min score, matching filters). Message contains: title, company, location, source, publication date, score, matching skills, missing skills, visa status, original application URL. Options: instant, batched, daily summary, quiet hours. Never resend the same job.

## 11. Frontend pages

1. Login / account.
2. Dashboard (new today, top matches, last execution, source health).
3. Search Configuration (sources, domains, location, experience, visa, publication date, search execution panel with progress and counters).
4. Search Profiles.
5. CV Management (active CV, versions, extracted profile editor, generated keywords, validation status; buttons Upload CV, Analyze CV, Edit Extracted Profile, Activate CV, Start CV-Based Search, View Matching Results).
6. Results (title, company, country/city, domain, level, visa status, publication date, first discovered date, source(s), AI score, original link; sort by newest, highest score, best sponsorship, country, domain; filters; detail drawer with match explanation).
7. Applications tracker (saved, applied, interview, rejected, offer, notes).
8. Search history and execution logs.
9. Notification settings.
10. Source management and health.

Angular requirements: standalone components, typed API client, error/empty/loading states, accessibility, FR/EN i18n.

## 12. Security and quality

**Authentication (single owner, simple and careful):** one owner account created at first start (setup command or first-run screen that locks afterwards); the `user_id` column stays in the schema so multi-user remains possible later. Password hashed with Argon2id; short-lived access token (15 min) plus rotating refresh token, both in `httpOnly`, `Secure`, `SameSite=Strict` cookies; login rate limiting and temporary lockout; optional TOTP two-factor; strict CORS; security headers (CSP, HSTS, X-Content-Type-Options); input validation with Pydantic; audit log for CV access; GDPR-style export and deletion of CVs and profiles. No roles or admin panel in v1. **Tests:** pytest unit tests (services, dedup, novelty, scoring), integration tests against real PostgreSQL (testcontainers-python), connector tests on recorded fixtures, Angular component tests, and one minimal end-to-end flow (upload CV → validate → search → see new results).

## 13. Delivery phases

1. Repo scaffolding, docker-compose, CI, auth, base migrations, design tokens from mockup.
2. Source management and connector framework with 2–3 permitted connectors (feeds/APIs) plus link-only and manual import.
3. Search configuration, profiles, orchestrator, dedup, novelty tracking, results page.
4. CV upload, Python parser, profile review/validation.
5. CV-based search, AI matching with explanations.
6. Telegram, scheduling, history, logs.
7. Applications tracker, hardening, tests, documentation (README, architecture, API docs, runbook).

At the end of each phase, output: what was built, how to run it, what was tested, known limitations, and the next step.

## 14. Acceptance criteria

The project is complete only when:

- individual sources can be enabled/disabled and only selected, available connectors run;
- multiple domains, countries, experience levels, visa filters and publication ranges are selectable and persisted;
- search profiles can be saved, edited, deleted and reused;
- new jobs are distinguished from previously collected ones, duplicates and reposts are detected;
- a PDF or DOCX CV can be uploaded, parsed, edited, validated and activated; multiple CVs are supported and the original is preserved;
- search modes A, B and C work and can be combined with manual filters;
- every match score has a "why" and a "missing" explanation, mandatory vs optional requirements are separated;
- results are displayed in Angular following the mockup;
- Telegram notifications respect saved preferences and never duplicate;
- source failures are visible and never produce misleading empty results;
- no connector violates a source's terms; non-permitted sources fall back to link or manual import;
- the stack starts with a single `docker compose up` and tests pass in CI.

* the `linkedin_email` connector passes its integration tests (fixtures, no duplicate processing, visible parse errors, provisional-score rules) and stays disabled until its legal verification is recorded.

---

# Technical Annex (binding details)

The sections below refine and, where they differ, override the earlier sections.

## 15. Technical architecture

**Deployable units (docker-compose services):**

- `frontend`: Angular build served by Nginx (reverse proxy for `/api`, TLS termination in production).
- `backend`: FastAPI app (REST API, SSE progress, Telegram client, connector framework, in-process `app/ai` module for CV parsing and matching).
- `worker`: same image as `backend`, started with a different command (`python -m app.worker`); runs search tasks, scheduled searches and matching from the PostgreSQL-backed queue.
- `postgres`: PostgreSQL 16 with the pgvector extension.
- `minio` (optional): private object storage for CV files; default is an encrypted private volume.
- `redis`: not required in v1; add only if the PostgreSQL queue becomes a bottleneck.

**Communication:**

- Browser to backend: REST/JSON over HTTPS, SSE for search progress.
- Backend to worker: through the database queue only (no direct calls). LLM and external API calls use httpx with timeouts (parse 30 s, match 15 s), retries with backoff (tenacity) and a circuit breaker per provider.
- Search execution is asynchronous: `POST /searches` returns an execution id immediately; progress via `GET /searches/{id}/events` (SSE); results via `GET /searches/{id}/results`.

**Backend structure: modular monolith.** One deployable codebase (API and worker share it), but every business area lives in its own module folder with a clear public interface. Nothing is dumped into shared "utils" or one big services file.

```text
backend/
  alembic/                      migrations (one folder per module under versions/ or prefixed names)
  app/
    main.py                     FastAPI app, mounts each module's router
    worker.py                   worker entry point (same codebase)
    core/                       settings, security, logging, db session, error handlers
    shared/                     tiny cross-cutting types: ids, pagination, domain events, clock
    modules/
      auth/                     owner account, login, tokens, 2FA
      cv/                       upload, storage, encryption, versions, download
      profile/                  candidate profile, validation, generated keywords
      sources/                  source registry, legal_status, verification checklist
        connectors/
          france_travail/       one folder per connector: client, mapper, fixtures/, README
          remoteok/
          remotive/
          linkedin_email/
          career_pages/
          manual_import/
      search/                   configurations, profiles, orchestrator, scheduler, task queue
      listings/                 normalization, fingerprint, dedup, novelty, reposts
      matching/                 scoring, weights, calibration, explanations
      ai/                       LlmProvider, CV parser, job extractor, taxonomy, embeddings
      notifications/            Telegram, preferences, daily summary
      applications/             application tracker
```

**Every module has the same layout:** `api.py` (router), `service.py` (use cases), `repository.py` (database access), `models.py` (SQLAlchemy), `schemas.py` (Pydantic), `events.py` (events it publishes), `__init__.py` (the only public entry: exports what other modules may use), and `tests/` next to the code.

**Boundary rules (enforced, not just written):**

- A module imports another module only through that module's `__init__.py` (public service interface or event types), never its `repository`, `models` or internal files.
- Each module owns its tables; other modules reference them by id and never query or write them directly.
- Dependency direction is one-way with no cycles: `search` uses `sources`, `listings`, `matching` and `notifications`; `matching` uses `profile` and `ai`; `profile` uses `cv` and `ai`; `core` and `shared` depend on nothing.
- Loose coupling through in-process domain events (for example `ListingCreated` handled by `matching`, `MatchScored` handled by `notifications`), so a module can be tested alone.
- Architecture tests in CI with import-linter (or equivalent) fail the build when a forbidden import appears.
- A connector is a self-contained folder: adding a source means adding a folder and registering it, with no change elsewhere.
- If a module later needs its own service (for example `ai`), its public interface is already the contract to extract.

**Orchestrator flow per execution:** create `SearchExecution` (status `RUNNING`) → one `SourceExecutionLog` per source → connectors run in parallel (bounded thread pool, per-source timeout and rate limit) → normalize → fingerprint and dedup → persist `JobListing` with `first_seen_at` → matching (batched calls to the in-process ai module) → notifications → status `COMPLETED`, `PARTIAL` (some sources failed) or `FAILED`. Cancellation sets a flag checked between stages.

**Idempotency:** a search run twice with identical criteria must not duplicate listings, matches or notifications (unique constraints plus upserts).

## 16. CV security and privacy

CVs contain personal data; treat them as the most sensitive asset.

- **Storage:** files in a private volume (or private bucket), never under a web-served path. Random UUID file names; original filename kept only as metadata. No public URLs; downloads stream through an authenticated backend endpoint that checks ownership.
- **Encryption:** TLS in transit; encryption at rest (encrypted disk/bucket, or application-level AES-256-GCM with a key from env or secret store, never in the repo).
- **Upload validation:** allow-list PDF, DOCX, DOC only; verify magic bytes, not just extension or MIME; max size (default 5 MB); reject macros and embedded executables; parse in a restricted subprocess (non-root container, no network access for the parser). Optional ClamAV scan behind a feature flag.
- **Access control:** single owner account; every CV query is still scoped by `user_id` so the code is safe if more users are added; unauthenticated access to any CV endpoint is rejected (covered by tests).
- **Immutability:** the original file is never modified; the parsed profile is a separate editable record with version history.
- **Data minimization with AI providers:** before sending CV text to an external LLM, strip direct identifiers (name, email, phone, address, LinkedIn URL) and use placeholders; matching needs skills and experience, not identity. Local model mode (Ollama) sends nothing outside the host.
- **Logging:** never log CV content, parsed text or tokens; log ids and metadata only. Audit entries for upload, download, delete, activate, export.
- **Retention and rights:** export-my-data and delete-everything commands; deleting a CV removes the file, parsed text and embeddings (applications keep only a title snapshot).
- **Auth and secrets:** see section 12 (Argon2id, httpOnly cookies, rotating refresh token, login rate limit, optional TOTP). Telegram bot token and LLM key stored encrypted or in env only.
- **Dependency hygiene:** Dependabot/Renovate, pip-audit and Trivy image scan in CI.

## 17. Authorized job-source connectors

Each `JobSource` row stores: `integration_type`, `terms_url`, `robots_checked_at`, `rate_limit_per_min`, `enabled_by_default`, `legal_status` (`PERMITTED`, `LINK_ONLY`, `MANUAL_ONLY`, `UNVERIFIED`). **A connector is activated only when `legal_status = PERMITTED`.** `UNVERIFIED` sources behave as `LINK_ONLY` until a maintainer reviews their terms and records the result.

**Connector interface:** `capabilities()` (supports keyword search, location, date filter, pagination), `fetch(query, cursor)`, `normalize(raw)`, `healthCheck()`. Every connector sets a descriptive User-Agent, honors rate limits and caching headers, and returns a typed failure (`AUTH`, `RATE_LIMITED`, `TIMEOUT`, `BLOCKED`, `PARSE_ERROR`) instead of an empty list.

| Source | Default integration | Notes |
| --- | --- | --- |
| France Travail | Official API (OAuth, client credentials) | Requires developer account and registered app. |
| EURES | Official/public portal or API access if granted; otherwise link-only | Verify current access conditions before enabling. |
| RemoteOK, Remotive, We Work Remotely | Public API/RSS feeds | Follow each feed's attribution and usage terms; link back to the original posting. |
| Welcome to the Jungle, Wellfound, Make it in Germany | Official API/feed or partner access if available; otherwise link-only | Do not scrape. |
| LinkedIn Jobs, Indeed | Link-only + manual import (official partner APIs only if the user holds valid access) | No scraping, no session or cookie reuse. |
| Keejob, Tanitjobs and other Tunisian boards | Link-only + manual import, unless the site offers an RSS/API or written permission | Record permission in `terms_url` notes before enabling. |
| Company career pages | Per-company opt-in; use public structured data (ATS JSON feeds such as Greenhouse/Lever/Ashby public boards, schema.org `JobPosting`) | Check robots.txt and terms for each domain. |

**Link-only mode:** generate a deep search URL from the profile (keywords, location, date filter) and open it in a new tab; show a clear badge "Manual source".

**Manual import:** paste a job URL or description, or upload a CSV; the in-process AI extractor extracts fields (`POST /jobs/import`), the listing is stored with `source = MANUAL` and goes through dedup, novelty and matching like any other.

**Forbidden:** CAPTCHA bypass, proxy rotation to evade blocks, fake user agents, logging in with the user's credentials, headless-browser scraping of sites that prohibit it. If a source starts returning `BLOCKED`, the connector disables itself and the UI shows it as degraded.

## 18. AI engine choice

**Principle:** deterministic code for what can be computed, LLM only for language understanding, behind an abstraction.

**Pipeline split:**

1. **CV parsing:** text extraction with PyMuPDF/pdfplumber (PDF) and python-docx (DOCX); OCR fallback (Tesseract) for scanned PDFs. Section detection with rules, then structured extraction via LLM with a strict JSON schema (Pydantic validation). Each extracted field carries its source text span; fields without evidence stay null.
2. **Skill normalization:** a curated skills taxonomy (aliases such as `Spring Boot` = `SpringBoot`, `K8s` = `Kubernetes`) stored in the database and editable; used for both CV and job skills.
3. **Job extraction:** from description to required skills (mandatory vs optional), years of experience, seniority, languages, visa wording, work mode. Rule-based regexes first, LLM for ambiguous parts.
4. **Matching score (0-100), explainable:** weighted sum of sub-scores: mandatory skills 35, optional skills 10, experience and seniority 20, domain/title relevance 10, languages 10, location and work mode 5, education 5, visa 5. Weights are configurable per search profile. Hard penalties or caps when a mandatory requirement is missing (for example, max seniority exceeded by more than 1 year caps the score at 60). Embedding similarity (multilingual sentence-transformers or provider embeddings in pgvector) is used only for candidate retrieval and semantic skill matching, never as the sole score.
5. **Explanation:** the LLM only phrases "why it matches" and "what is missing" from the computed sub-scores and evidence; it cannot change the score.

**Provider abstraction (`LlmProvider`):** implementations selected by env var `LLM_PROVIDER`: `anthropic` (Claude), `openai`, `ollama` (local models such as Qwen or Llama for full privacy), `none` (rule-based fallback with lower extraction quality). Default recommendation: a hosted frontier model for CV parsing quality, small/cheap model for bulk job extraction, local embeddings for privacy and cost.

**Reliability:** temperature 0 for extraction, JSON-schema constrained output with retry on invalid JSON, response caching keyed by content hash, token and cost budget per execution with a visible counter, prompt versions stored with each `JobMatch` (`model`, `prompt_version`, `taxonomy_version`).

**Language handling:** CVs and jobs in French, English (and some Arabic/German); keep original text, normalize skills to English canonical names.

## 19. Testing strategy

**Backend (pytest, pytest-asyncio, testcontainers-python, respx):**

- Unit tests: URL normalization, fingerprinting, dedup merge rules, novelty (`first_seen_at` never changes on re-collection, repost detection), experience-level extraction, visa classification (no "confirmed" without evidence), scoring weights and caps.
- Integration tests with a real PostgreSQL (testcontainers-python): Alembic migrations from scratch, repositories, orchestrator end-to-end with fake connectors (success, partial failure, timeout, cancellation), idempotent re-run, worker resume after a simulated crash.
- Security tests: unauthenticated requests rejected on every CV and search endpoint; upload of a renamed `.exe` or oversized file rejected; logs contain no CV text; login rate limit works.
- Connector contract tests: each connector runs against recorded fixtures (respx); a test asserts that failures surface as typed errors, never as empty success.
- Static checks: Ruff, mypy, pip-audit.

* E-mail connector integration tests (`linkedin_email`): recorded alert e-mails as fixtures, a fake IMAP/Gmail client, idempotent re-read of the same messages, unparsable e-mail reported, missing alerts for 48 hours flagged, provisional score recomputed after manual import, credentials never present in logs.

**AI module (pytest):**

- Golden set: at least 10 anonymized CVs (French and English, one-column, two-column, scanned) with expected JSON; track field-level precision/recall and fail CI below a threshold.
- Hallucination test: CV missing a section must yield null, not invented values.
- Matching tests: fixed CV and job pairs with expected score ranges and expected "missing" lists; mandatory-vs-optional behavior; LLM mocked in CI, a small live smoke test run manually.

**Frontend (Jest or Karma, Cypress or Playwright):**

- Component tests for configuration forms, source cards, results table, match explanation drawer.
- E2E scenario: login → upload CV → edit and validate profile → enable two sources → start search (fake connectors) → see new results with scores → re-run and verify no duplicates and nothing marked "new" twice.
- Visual check of key pages against the mockup (screenshot comparison with tolerance).

**Quality gates in CI:** build, lint, unit and integration tests, coverage target 70 % on backend services and 80 % on dedup/novelty/scoring, dependency and image scan, Docker images build.

## 20. Docker deployment

**Files:** `docker-compose.yml` (production-like), `docker-compose.override.yml` (dev with hot reload), `.env.example`, one `Dockerfile` per service.

**Images:**

- Backend and worker: one multi-stage image (build wheels, then `python:3.12-slim`), non-root user, `uvicorn` for the API, `python -m app.worker` for the worker, `/health` endpoint.
- Frontend: multi-stage (Node build, then Nginx unprivileged) with gzip, caching headers, SPA fallback, security headers.
- Pin image tags and Python dependencies (lock file); no `latest`; scan with Trivy.
- Optional ML models (local embeddings or Ollama) live in a mounted volume, not in the image.

**Compose rules:**

- Named volumes for `postgres-data` and `cv-storage`; only `frontend` (80/443) publishes ports; `postgres` and `backend` stay on an internal network.
- `healthcheck` on every service and `depends_on` with `condition: service_healthy`.
- Resource limits (CPU, memory), `restart: unless-stopped`, log rotation.
- Secrets via env file or Docker secrets (`DB_PASSWORD`, `JWT_SECRET`, `CV_ENCRYPTION_KEY`, `TELEGRAM_*`, `LLM_API_KEY`); `.env` is git-ignored; startup fails fast if a required secret is missing or still equals the example value.
- Alembic migrations run automatically at backend startup (`alembic upgrade head`); seed data (sources, domains, skills taxonomy) via migrations.

**Operations:**

- `make up`, `make down`, `make test`, `make logs`, `make backup` shortcuts.
- Nightly `pg_dump` plus CV storage backup to a mounted location, with a documented restore procedure (tested once).
- Reverse proxy with Let's Encrypt (Caddy or Traefik) for the production profile.
- Observability: Prometheus metrics endpoint (prometheus-fastapi-instrumentator), structured JSON logs with correlation id, optional Prometheus/Grafana profile (`--profile monitoring`).
- CI/CD (GitHub Actions): build and test on every PR, build and push images on tags, optional deploy step over SSH with `docker compose pull && up -d`.

**Definition of done for deployment:** on a clean machine, `cp .env.example .env`, fill secrets, `docker compose up -d` brings up a healthy stack; the seeded sources appear, a CV can be uploaded, and a search with fake connectors completes.

## 21. Connector verification before activation

No connector may be enabled from memory or assumption. API availability, access conditions and terms change, so verification is a mandatory step per source.

- **Source verification checklist** (stored per `JobSource`, filled before `legal_status` can become `PERMITTED`): official API or feed URL, access method (open, key, OAuth, partner-only), current terms of use URL and review date, robots.txt result, allowed usage (storage, redistribution, attribution), rate limits, reviewer, and the evidence (link or saved excerpt).
- **Codex/Claude Code must fetch the current official documentation and terms** of each source before writing its connector, cite the pages consulted in the connector's README, and state clearly when access requires an account, partnership or paid plan that the user does not have. If it cannot confirm that automated collection is permitted, it implements `LINK_ONLY` and `MANUAL_IMPORT` only.
- **Re-verification:** `robots_checked_at` and `terms_reviewed_at` older than 90 days mark the source `UNVERIFIED` in the UI and downgrade it to link-only until reviewed.
- **Runtime monitoring:** a source returning repeated `BLOCKED`, `AUTH` or schema changes is auto-disabled and flagged for review.

## 22. Asynchronous tasks, resume and long searches

- **Persisted job queue:** every search is a `SearchExecution` made of per-source tasks stored in the database (`PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`, `TIMED_OUT`) with `attempt`, `next_retry_at`, `cursor` (pagination checkpoint), `heartbeat_at` and `locked_by`. Workers claim tasks with `SELECT ... FOR UPDATE SKIP LOCKED`.
- **Resume after interruption:** on backend restart, tasks stuck in `RUNNING` with an expired heartbeat (default 2 minutes) are re-queued from their last checkpoint. Processing is idempotent (upserts keyed by source id and fingerprint), so a resumed task never duplicates listings, matches or notifications.
- **Retries:** exponential backoff with jitter, max 3 attempts per task, no retry on permanent errors (`BLOCKED`, `AUTH`). Respect `Retry-After`.
- **Long searches:** hard limits per source (max pages, max listings, max duration, defaults 10 pages / 500 listings / 3 minutes) and per execution (default 15 minutes). When a limit is hit, the execution ends as `PARTIAL` with an explicit reason, never as a silent truncation.
- **Staged pipeline:** collection, enrichment and matching are separate stages with their own queues, so matching can continue or be re-run without re-collecting. Matching is batched and rate-limited, and LLM spend is capped per execution.
- **Cancellation:** user cancel sets a flag; workers stop at the next checkpoint; already stored results are kept and the execution ends as `CANCELLED`.
- **Overlap control:** one active execution per search profile; a scheduled run is skipped (and logged) if the previous one is still running. Scheduling runs only in the worker process (APScheduler); before each tick it takes a PostgreSQL advisory lock (pg\_try\_advisory\_lock), so a second worker or a restart never double-runs a scheduled search; tasks are claimed with SELECT ... FOR UPDATE SKIP LOCKED and v1 runs a single worker replica.
- **User feedback:** SSE progress shows per-source state, counters and the last error; after a page reload or reconnect the UI restores the current state from the database, not from memory.

## 23. Matching score calibration

Scores must be trustworthy before they are used for ranking or Telegram alerts.

- **Calibration set:** build a labeled dataset of at least 50 real (anonymized) job postings across the target domains (Java/Spring/Angular, DevOps, Data Engineering, AI, BA), each labeled by the user as `STRONG`, `GOOD`, `WEAK` or `NO` match against their validated profile, with notes on mandatory gaps. Store it in `/calibration` with a loader and a documented format; the user can add labels from the results page ("rate this match").
- **Metrics:** rank correlation (Spearman) between score and label, precision at top 10, rate of `NO` jobs scored above 60, rate of `STRONG` jobs scored below 60. CI fails if these regress beyond agreed thresholds (initial targets: Spearman at least 0.6, zero `NO` jobs above 70).
- **Known traps to test explicitly:** title says "Junior" but requires 5+ years; senior title with junior requirements; keyword stuffing; requirements in another language; optional skills listed as required; remote versus country-restricted roles; visa wording such as "must already have the right to work".
- **Tuning:** weights and caps are configuration, tuned against the calibration set, versioned (`scoring_version`) and stored on each `JobMatch`. Changing weights triggers a re-score preview that shows how rankings change before applying.
- **Confidence:** each score has a confidence level (low when the description is short or parsing is uncertain); low-confidence jobs are labeled and excluded from Telegram alerts by default.
- **Feedback loop:** user ratings and "not relevant" actions feed the calibration set; they never silently retrain or change the scoring without a versioned, reviewable change.
- **Display rule:** show the score together with its sub-scores and mandatory gaps; never show a high score when a mandatory requirement is missing (cap applies).

## 24. Working agreement for Codex / Claude Code

These rules apply to the coding agent during the whole build.

1. **Plan first.** Before writing code, output a short plan for the current phase (scope, files, migrations, risks, tests) and wait for approval.
2. **Phase gates.** At the end of each phase in section 13, stop and report: what was built, commands to run it, test results (real output, not assumptions), known limitations, and the proposed next step. Do not start the next phase until the user confirms.
3. **Architecture changes need confirmation.** Ask before: adding or removing a service, changing the database engine, changing the auth model, introducing a new major dependency or framework, changing the API contract in a breaking way, altering the data model of existing tables, or deviating from this specification or the mockup. Present options with trade-offs and a recommendation, then wait.
4. **No silent scope changes.** If the specification is ambiguous or conflicts with reality (an API no longer exists, a source forbids automated access), stop and report instead of improvising.
5. **Small, reviewable steps.** Commit per logical unit with clear messages; migrations are append-only (never edit an applied migration); the build and tests must pass before each commit.
6. **Evidence over claims.** Never state that something works without running it. Include failing tests honestly and fix them or flag them.
7. **Security defaults.** Never commit secrets, never log CV content, never add a connector that is not `PERMITTED`.
8. **Keep a `DECISIONS.md`** recording each significant decision, the alternatives considered and the date, plus a `TODO.md` of deferred items.

## 25. LinkedIn through e-mail alerts (automatic, no scraping)

This section refines the LinkedIn row of section 17. JobHunter discovers LinkedIn jobs by reading the owner's LinkedIn job-alert e-mails, never by crawling LinkedIn.

**Setup (once, by the owner):** create saved searches on LinkedIn with e-mail alerts, one per search profile (for example Java Junior Portugal, Data Engineer Europe, DevOps Remote). Send them to a dedicated mailbox or label (Gmail or IMAP).

**Connector `linkedin_email`:**

- Integration type `EMAIL_ALERT`, `legal_status` (starts as UNVERIFIED and becomes PERMITTED only after the section 21 checklist is completed for this connector: the owner reviews LinkedIn's terms on job alerts and the mailbox provider's API/OAuth conditions, and the result is recorded; discovery itself makes no request to LinkedIn).
- Mailbox access: Gmail API (OAuth, read-only scope) or IMAP with an app password, limited to the dedicated label/folder. Credentials stored encrypted, never logged. Connection test button in the Sources page.
- Polling by the worker every 15-60 minutes (configurable). Each e-mail is processed once (message id stored) and never modified or deleted unless the owner enables "mark as read".
- Parser: extract per job the title, company, location, posting link and any snippet shown; resolve and normalize the job URL (strip tracking parameters, keep the LinkedIn job id as `source_job_id`). Parsing rules live in versioned templates, because LinkedIn changes its e-mail layout; if an e-mail cannot be parsed, store it as `PARSE_ERROR` in `SourceExecutionLog` and show it in the UI, never skip it silently.
- Listings enter the normal pipeline: dedup across sources, `first_seen_at` set from the e-mail reception time (publication date shown as unknown when not in the e-mail), eligibility filters, matching, Telegram.

**Limits and how they are handled:**

- E-mails contain only a short summary, so the first score is **provisional** and marked `confidence: low` (based on title, company, location and snippet). Per section 23, low-confidence jobs are excluded from Telegram matching alerts by default; the owner can enable "provisional alerts" in the notification settings, in which case the message states that the score is provisional. They still appear in the dashboard.
- Full description: the owner opens the link and uses manual import (paste text or the manual capture button) to attach the complete description. The score is then **recomputed** with normal confidence, the listing keeps its original `first_seen_at`, and a Telegram alert is sent at that point if it qualifies. The app never fetches the LinkedIn job page automatically.
- LinkedIn decides what it sends; coverage is not exhaustive. The Sources page shows the last e-mail received and the number of jobs parsed per day, and warns when no alert e-mail arrived for more than 48 hours (alerts may have been disabled).

**Forbidden (unchanged):** scraping LinkedIn pages, headless browsers or bots using the owner's session, automatic browsing by a browser extension, third-party LinkedIn scraping services enabled by default. An optional browser extension may exist only as a manual "send this job to JobHunter" button that reads the page the owner is viewing after a click.

**Acceptance criteria:** with a test mailbox containing recorded LinkedIn alert e-mails (fixtures), the connector creates the expected listings, never processes the same e-mail twice, reports unparsable e-mails visibly, and the resulting jobs appear as new with a provisional low-confidence score. No Telegram alert is sent for them by default; with provisional alerts enabled one is sent, and importing the full description recomputes the score without changing `first_seen_at`. The connector cannot run while its `legal_status` is not `PERMITTED`.

## 26. Agent memory and progress tracking

The coding agent has no reliable memory between sessions, so the project itself must remember. These files live in the repository and are the single source of truth for where the work stands. They extend section 24.

**Files (all under `docs/`, except the agent entry files at the root):**

- `CLAUDE.md` and `AGENTS.md` (root, identical short content, max about 60 lines): stack, module map, run and test commands, the non-negotiable rules (no unverified connector, no CV content in logs, ask before architecture changes), and the instruction "read `docs/PROGRESS.md` first, update it last".
- `docs/SPEC.md`: this Master Prompt, never edited by the agent; changes to it are proposed to the owner.
- `docs/PROGRESS.md`: current state (below).
- `docs/DECISIONS.md`: dated decision log (decision, alternatives, reason, who approved).
- `docs/TODO.md`: deferred items, known bugs, open questions for the owner.
- `docs/CHANGELOG.md`: one line per completed task.
- `docs/sources/<connector>.md`: per-connector verification evidence (section 21).

**`docs/PROGRESS.md` format:**

```text
# Progress
Last updated: <date> by <agent/session>
Current phase: 3 - Search configuration and orchestrator
Status: IN_PROGRESS (waiting for owner validation: no)

## Phase checklist
[x] 1 Scaffolding, Docker, CI, auth, base migrations
[x] 2 Source registry and connector framework
[ ] 3 Search configuration, profiles, orchestrator, dedup, novelty
    [x] 3.1 SearchConfiguration model and migration
    [x] 3.2 Profiles API
    [ ] 3.3 Orchestrator and worker queue   <- NEXT
    [ ] 3.4 Results page
[ ] 4 CV upload, parser, profile validation
...

## Last session
Done: <what, with file/module names>
Tests: <command and real result: passed/failed counts>
Not done / blocked: <why>
Next step: <one precise action>

## Open questions for the owner
- ...
```

**Rules:**

1. **Session start:** read `CLAUDE.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md` and `docs/TODO.md`, then state in two lines where the project stands and what comes next. Do not rely on chat history.
2. **After every completed task (not only every phase):** tick the item, update "Last session" and "Next step", add one line to `CHANGELOG.md`, and commit the code and these files together (`feat(search): orchestrator queue [3.3]`).
3. **On every decision or deviation:** write it to `DECISIONS.md` before continuing; anything that changes architecture still needs the owner's confirmation first (section 24).
4. **On failure or interruption:** record what was attempted, the error and the state of the working tree in "Not done / blocked", so the next session can resume exactly there. Never mark an item done unless its tests ran and passed; record the real command output summary.
5. **Phase end:** write a phase report in `docs/reports/phase-N.md` (built, how to run, tests, limits, risks), set the status to `WAITING_FOR_VALIDATION`, and stop until the owner replies.
6. **Hygiene:** no secrets, CV content or personal data in any of these files; keep `PROGRESS.md` under about 150 lines by moving finished phase details into `docs/reports/`.

**Application-side progress (what the owner sees in the app):** each search execution already records per-source status, counters and errors (sections 8 and 22); the dashboard also shows the last execution, the next scheduled run and the health of each source. These records are stored in PostgreSQL, so progress survives restarts.

## 27. Kickoff prompts and CLAUDE.md (ready to copy)

Use these short prompts instead of pasting the whole specification. Save this document as `docs/SPEC.md` first. Send one prompt at a time and wait for the agent's report before sending the next.

### 27.1 CLAUDE.md / AGENTS.md (root of the repository)

```markdown
# JobHunter AI - agent instructions

Project: configurable IT job search app for one owner. Full spec: docs/SPEC.md (never edit it).

## Stack
FastAPI (Python 3.12) modular monolith + worker, Angular, PostgreSQL 16, Docker Compose.
Backend modules live in backend/app/modules/<module>/ (see SPEC section 15). One folder per
module, one folder per connector. Modules import each other only via __init__.py.

## Commands
(fill in during phase 1: run, test, lint, type-check, migrate)

## Non-negotiable rules
- Read docs/PROGRESS.md, docs/DECISIONS.md, docs/TODO.md at the start of every session.
- Update docs/PROGRESS.md and docs/CHANGELOG.md after every completed task, and commit them with the code.
- Plan first, then wait for owner approval. Stop at the end of each phase and write docs/reports/phase-N.md.
- Ask before any architecture change (new service, new major dependency, data model change, breaking API change).
- Never enable a connector whose legal_status is not PERMITTED. Never scrape LinkedIn.
- Never log CV content, tokens or secrets. Never commit secrets.
- Never state something works without running it; report real test output.
- Never invent CV data; never claim visa sponsorship without evidence.
- The UI follows the mockup folder from SPEC section 3.
```

### 27.2 Step 0: read the project and the mockup

```text
Lis docs/SPEC.md en entier. Ne code rien pour l'instant.
1) Resume-moi le projet en 10 lignes pour montrer que tu l'as compris.
2) Ouvre le dossier de la maquette indique en section 3 et fais le rapport demande (type, pages, composants, styles, ecrans couverts et manquants).
3) Liste les points ambigus ou contradictoires du SPEC et propose une reponse pour chacun.
4) Cree CLAUDE.md, AGENTS.md et le dossier docs/ (PROGRESS.md, DECISIONS.md, TODO.md, CHANGELOG.md) avec le contenu initial.
Arrete-toi apres ce rapport et attends ma validation.
```

### 27.3 Phase prompts (one per phase, same pattern)

```text
Phase N validee. Lis CLAUDE.md et docs/PROGRESS.md, puis propose le plan detaille de la phase N+1 (fichiers, migrations, tests, risques). Attends mon accord avant de coder. Ensuite, travaille tache par tache : apres chaque tache, mets a jour PROGRESS.md et CHANGELOG.md, lance les tests, commite. A la fin de la phase, ecris docs/reports/phase-N+1.md et arrete-toi.
```

Content of each phase (from section 13), to append to the prompt above:

1. **Phase 1:** repository scaffolding, Docker Compose (frontend, backend, worker, postgres), CI, owner authentication, base migrations, design tokens and layout from the mockup, `/health`, architecture tests (import-linter).
2. **Phase 2:** source registry with `legal_status` and verification checklist, connector framework, 2 or 3 permitted connectors verified against their current documentation and terms, link-only and manual import.
3. **Phase 3:** search configuration and profiles, orchestrator and worker queue with resume, deduplication, novelty tracking, results page and Sources page in Angular.
4. **Phase 4:** CV upload and private storage, parser, candidate profile editor and validation, CV management page.
5. **Phase 5:** CV-based search (modes A, B, C), AI matching with explanations, calibration set loader and metrics, `linkedin_email` connector (only after its verification is recorded).
6. **Phase 6:** Telegram notifications and preferences, scheduled and daily searches, search history and logs.
7. **Phase 7:** applications tracker, hardening, full test pass, documentation (README, runbook), backup and restore check.

### 27.4 Prompts for recurring situations

**Resume after an interruption or a new session:**

```text
Nouvelle session. Lis CLAUDE.md, docs/PROGRESS.md, docs/DECISIONS.md et docs/TODO.md. Dis-moi en 3 lignes ou en est le projet et quelle est la prochaine tache, puis continue a partir de "Next step" sans refaire ce qui est coche.
```

**Validate a phase:**

```text
J'ai lu docs/reports/phase-N.md. Corrige ces points : <liste>. Quand c'est corrige et teste, mets a jour PROGRESS.md et dis-moi que la phase est prete a etre validee.
```

**Control check (use it at the end of every phase):**

```text
Fais un audit de conformite avec docs/SPEC.md : liste les regles non respectees ou non testees (connecteurs non verifies, CV dans les logs, doublons, nouveaute, scores sans explication, erreurs de source masquees). Donne le resultat des tests reels et corrige sans changer l'architecture.
```

**Architecture question from the agent:** the agent must present options with a recommendation and wait; answer with the chosen option, and ask it to record it in `docs/DECISIONS.md`.
