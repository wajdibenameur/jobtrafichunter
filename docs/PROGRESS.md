# Progress

Last updated: 2026-11-08 by Codex / Apify Phase A
Current task: LinkedIn via Apify - inspection and proposed integration plan (D-022)
Status: PHASE_A_COMPLETE_WAITING_FOR_B_APPROVAL

## Phase checklist

- [x] 0 Documentation and original phase plans approved.
- [x] 1 Local Python 3.11/auth/TLS/PostgreSQL/Angular foundation validated.
- [x] 2 Manual sources and confirmed URL/CSV import validated (D-017).
- [x] 3 Approved local scope delivered; validation still pending (D-021).
    - Profiles, provenance, conservative deduplication, queue and Angular results.
- [ ] 4 Private CVs, parsing, editing and profile validation.
- [ ] 5 CV matching/calibration; no matching module implemented yet.
- [ ] 6 Telegram, scheduling, history and logs.
- [ ] 7 Applications, hardening, local backup/restore.

## Apify feature - explicit A/B/C workflow

- [x] A Inspect sources/search/listings, profiles, queue/worker, migrations and UI.
- [x] A Review public official API/terms and record evidence.
- [x] A Propose files, additive migration, budget/consent and recovery design.
- [x] A Recommend a separate LinkedIn - Apify card INSIDE Sources; no extra menu.
- [ ] B Owner approval of docs/reports/apify-phase-a.md.
- [ ] B Generic API client, guarded UI/workflow and simulated tests after approval.
- [ ] Source-specific adapter only after Actor/method permission is verified.
- [ ] C Separate explicit approval for a real 10-job run and concrete budget.

## Last session

Delivered docs/reports/apify-phase-a.md and docs/sources/linkedin-apify.md.
Profile storage is in search; no independent profiles/CV/matching implementation.
Reuse PostgreSQL claims, fencing, cancel/resume, import/dedup and result snapshots.
Existing local task deadlines/poll attempts and manual-only source guards need
explicit adaptation, not a second queue. Preserve all original imports/manual modes.
Plan includes persisted billing consent, run/dataset IDs, offsets and ingest receipts.
An ambiguous initial POST must not be retried automatically: reconcile first.
Proposed additional source observations preserve both manual and Apify provenance
for an already known canonical URL; no overwrite of source or first_seen_at.
Actor ID/build/schema/terms and permission are not established. LinkedIn/Apify
official documents do not establish permission for this project; keep UNVERIFIED.
The card/toggles/configuration are PLANNED, not implemented. No provider token or
account read, no paid or authenticated Apify call, no Actor run, no MCP operation.
No application code, dependency, migration or secret changed. Original template
and pre-existing angular.json analytics change preserved and excluded from commit.
SPEC unchanged. Documentation checks only; no application test suite rerun.
Previous phase 3 evidence (historical): 105 backend / 21 Angular / 9 E2E passed;
this is not Apify test evidence. Docker/hosting remain out of scope (D-012).
Next: review the Phase A plan; do not implement B or execute C without owner approval.

## Points for the owner

- Approve/revise the Sources card and additive Phase B plan.
- Identify an Actor with a permitted collection method, without sharing its token.
- Matching CV is absent: approve collection-only scope explicitly, or wait for CV/matching.
