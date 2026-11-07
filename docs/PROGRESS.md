# Progress

Last updated: 2026-11-07 by Codex / périmètre exclusivement local
Current phase: 1 - Socle local livré, connexion confirmée par le propriétaire
Status: WAITING_FOR_VALIDATION (phase 1 locale ; Docker hors périmètre)

## Phase checklist

- [x] 0 Documentation initiale et plan approuvés.
- [ ] 1 Validation du socle local selon `reports/phase-1.md`. <- NEXT
    - [x] 1.1 Python 3.11, dépendances verrouillées, structure et dépôt racine.
    - [x] 1.2 Auth propriétaire, migration initiale, API et sécurité.
    - [x] 1.3 Tests PostgreSQL réels, Ruff/mypy, audits et README.
    - [x] 1.4 Worker avec sonde DB ; queue et handlers prévus en phase 3.
    - [x] 1.5 Analyse Velson ; référence originale préservée.
    - [x] 1.6 Audit accepté par la continuation du propriétaire.
    - [x] 1.7 Angular standalone, layout/connexion/compte, FR/EN.
    - [x] 1.8 Build, Karma, E2E et revue des captures desktop/mobile.
    - [x] 1.9 Configuration `.env` locale, schéma applicatif et migration.
    - [x] 1.10 Connexion frontend/backend testée avec succès par le propriétaire.
    - [ ] CI GitHub / compatibilité PostgreSQL 16 : préparées, non exécutées.
    - Hors périmètre : Docker, Compose, images et hébergement (D-012).
- [ ] 2 Sources, vérifications et framework de connecteurs.
- [ ] 3 Configuration, profils, orchestrateur, queue, déduplication, résultats.
- [ ] 4 CV privés, parsing, édition et validation du profil.
- [ ] 5 Recherche CV, matching explicable, calibration, linkedin_email vérifié.
- [ ] 6 Telegram, planification, historique et logs.
- [ ] 7 Candidatures, durcissement, tests, documentation et sauvegarde/restauration locales.

## Last session

Done: instruction « pour docker pas besoin on reste en local » enregistrée D-012.
Docker n'est plus reporté : il est retiré du périmètre, sans nouveau service ni
changement du modèle de sécurité. README, consignes, plan et TODO mis à jour.
Le propriétaire confirme avoir testé la connexion avec succès sur sa machine.
Configuration locale active : `.env` privé, schéma `jobhunter_app`, migration
0001_auth appliquée ; origine frontend HTTPS autorisée et secrets hors Git.
Tests précédents exécutés : 43 backend, 14 Angular, 5 E2E ; build/typecheck,
Ruff/mypy et audits validés. Santé API 200 et accès non authentifié 401 vérifiés.
Cette tâche ne change que la documentation et un commentaire CI : aucun test
applicatif relancé. Contrôles documentaires : consignes identiques, SPEC inchangé,
cohérence du périmètre local et diff vérifiés avant commit.
Not done / blocked: pas de remote Git ; CI externe non exécutée. Pas de baseline
pixel automatisée du template original. Modules métier absents ; liens « Bientôt ».
La modification préexistante de `frontEnd/jobhunter/angular.json` est préservée.
Next step: validation du rapport de phase 1 locale, puis plan de phase 2
(sources et connecteurs), sans Docker. Ne pas commencer la phase 2 sans confirmation.

## Open questions for the owner

- Validation du rapport local de phase 1 avant la phase 2.
- Droits du template à clarifier uniquement avant redistribution de ses assets.
