# Progress

Last updated: 2026-11-08 by Codex / CV security foundation
Current task: Phase 4 approved - private CV storage and isolated parsing
Status: IN_PROGRESS

## Phase checklist

- [x] 0 Documentation and original phase plans approved.
- [x] 1 Local Python 3.11/auth/TLS/PostgreSQL/Angular foundation validated.
- [x] 2 Manual sources and confirmed URL/CSV import validated (D-017).
- [x] 3 Local scope delivered (D-021) and owner-validated (D-024).
    - Profiles, provenance, conservative deduplication, queue and Angular results.
- [ ] 4 Private CVs, parsing, editing and profile validation.
    - Plan approved (D-024); storage and isolation foundations tested.
    - Pending: format inspection, PostgreSQL/API, candidate profile and Angular.
- [ ] 5 CV matching/calibration; no matching module implemented yet.
- [ ] 6 Telegram, scheduling, history and logs.
- [ ] 7 Applications, hardening, local backup/restore.

## Apify feature - explicit A/B/C workflow

- [x] A Inspect existing modules/queue/UI and review official documents (D-022).
- [x] A Propose additive integration, consent/budget and recovery design.
- [x] A Recommend a separate LinkedIn - Apify card INSIDE Sources; no extra menu.
- [x] Owner choice: wait for CV and matching, reject collection-only scope (D-023).
- [ ] B Implementation deferred until CV/matching; revisit plan and approval then.
- [ ] Source-specific Actor/method permission verified; currently UNVERIFIED.
- [ ] C Separate explicit approval for a real 10-job run and concrete budget.

## Last session

Owner "ok" validates phase 3 and PLAN-PHASE-4.md (D-024); no further plan gate.
Added cv/vault.py: encrypted opaque original bytes/filename, bound owner/doc/version,
fresh per-envelope derived key, atomic no-replace publication, bounded read/size,
UUID-only paths, symlink/junction rejection and idempotent authorized purge primitive.
Added native Windows AppContainer launcher with zero network capabilities,
explicit inherited pipes, suspended launch, verified container token, Job Object
memory/CPU/process bounds and kill-on-close. Python wrapper bounds output/time.
Setup copies only Python runtime/stdlib into ignored .cache, grants package SID
read/execute there only, and prepares the local Windows AppContainer profile.
Actual synthetic probes deny private-canary read, runtime write, loopback network
and child process; memory/output/deadline limits tested. No real CV read or parsed.
Fixed minimal Windows environment setup and over-output pipe shutdown deadlock.
Report: reports/cv-security-foundation.md. No HTTP upload/parser/profile/UI yet.
Validation: 122 passed in 83.30s using .env.test; Ruff check/format passed;
mypy passed (78 files). New targeted tests: 17 passed in 3.63s.
Two native probes require Windows and prepared runtime; not Linux evidence.
No dependency/migration/secret changed; SPEC/template/angular.json preserved.
No authenticated Apify request, Actor run or paid execution. Matching remains phase 5.
Historical frontend phase 3: 21 Angular / 9 E2E passed; not rerun for backend foundations.
Docker/hosting remain out of scope (D-012).

## Next step / owner review

Continue approved phase 4: review/pin PDF dependency, bounded isolated PDF/DOCX
inspection and extraction, then CV persistence/API, profiles and Angular.
DOC/OCR tools absent; expose unavailable capabilities honestly rather than fallback
to unisolated parsing. No user labels invented; calibrated quality needs owner fixtures.
After phase 4 delivery, seek validation before proposing phase 5 matching.
Revisit Apify B after CV/matching, with source permission and separate approval C.
