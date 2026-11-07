# Progress

Last updated: 2026-11-07 by Codex / pr?paration phase 2
Current phase: 2 - Plan sources et connecteurs pr?par?, avant impl?mentation
Status: IN_PROGRESS (phase 2 approved; manual sources per D-015)

## Phase checklist

- [x] 0 Documentation initiale et plan approuv?s.
- [x] 1 Socle local valid? par continuation du propri?taire (D-013).
    - [x] Backend Python 3.11, auth, migration et PostgreSQL locaux.
    - [x] Angular standalone, layout/connexion/compte, FR/EN et tests navigateur.
    - [x] Configuration .env locale et connexion confirm?e par le propri?taire.
    - CI externe / PostgreSQL 16 pr?par?s mais non ex?cut?s ; pas de remote Git.
    - Hors p?rim?tre : Docker, Compose, images et h?bergement (D-012).
- [ ] 2 Sources, v?rifications et framework de connecteurs.
    - [x] 2.0 Plan ?crit et pr?-v?rification documentaire des candidats.
    - [x] 2.0b Phase 2 approved by owner: oui vasi.
    - [x] 2.1 Source registry, owner preferences, manual connector and migration 0002.
    - [ ] 2.2 Framework, transport et v?rification compl?te des connecteurs.
    - [ ] 2.3 Persistent manual import and CSV preview. <- NEXT
    - [ ] 2.4 Page Sources Angular, tests et rapport.
- [ ] 3 Configuration, profils, orchestrateur, queue, d?duplication, r?sultats.
- [ ] 4 CV priv?s, parsing, ?dition et validation du profil.
- [ ] 5 Recherche CV, matching explicable, calibration, linkedin_email v?rifi?.
- [ ] 6 Telegram, planification, historique et logs.
- [ ] 7 Candidatures, durcissement, tests et sauvegarde/restauration locales.

## Last session

Done: phase 2 approved. Owner chose LinkedIn, Indeed, Keejob and Tanitjobs in
manual/link workflows (D-015); JobTech/Jobicy selection superseded.
Built source registry, owner-scoped preferences/custom sources, encoded links,
request principal, isolated business sessions and migration 0002_sources.
Tests: backend pytest: 64 passed in 38.48s; Ruff and strict mypy checked.
Manual connector fetch raises an explicit MANUAL_ONLY error; no network calls.
Not done: manual listing persistence/CSV and Angular Sources page remain next.
No automated provider connector expected under owner's selected scope.
Pre-existing angular.json analytics change preserved and excluded from commits.
Next step: build listings/import module and migration 0003, then Sources UI.

## Open questions for the owner

None required for current manual scope. Docker and hosting remain out of scope.
