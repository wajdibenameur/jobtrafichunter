# Progress

Last updated: 2026-11-07 by Codex / livraison frontend et cl?ture locale phase 1
Current phase: 1 - Socle local backend et frontend pr?t pour validation
Status: WAITING_FOR_VALIDATION (rapport de phase 1 ; Docker diff?r? par propri?taire)

## Phase checklist

- [x] 0 Documentation initiale et plan approuv?s (? DONC COMMANCER ?).
- [ ] 1 Validation du socle local selon `reports/phase-1.md`. <- NEXT
    - [x] 1.1 Python 3.11, d?pendances verrouill?es, structure et d?p?t racine.
    - [x] 1.2 Auth propri?taire, migration initiale, API et s?curit?.
    - [x] 1.3 Tests PostgreSQL r?els, Ruff/mypy, audit d?pendances, README.
    - [x] 1.4 Worker avec sonde DB ; queue et handlers en phase 3.
    - [x] 1.5 Analyse Velson (sources) ; r?f?rence originale pr?serv?e.
    - [x] 1.6 Audit accept? par la continuation du propri?taire (? contenue ?).
    - [x] 1.7 Angular standalone strict, layout/connexion/compte, FR/EN et tests.
    - [x] 1.8 Build, Karma, parcours E2E et revue des captures desktop/mobile.
    - [ ] 1.9 CI GitHub et PostgreSQL 16 : pipeline pr?par?, ex?cution non r?alis?e.
    - [ ] Docker / Compose / images : report explicite, pas d?clar? livr?.
- [ ] 2 Sources, v?rifications et framework de connecteurs.
- [ ] 3 Configuration, profils, orchestrateur, queue, d?duplication, r?sultats.
- [ ] 4 CV priv?s, parsing, ?dition et validation du profil.
- [ ] 5 Recherche CV, matching explicable, calibration et linkedin_email v?rifi?.
- [ ] 6 Telegram, planification, historique et logs.
- [ ] 7 Candidatures, durcissement, tests complets, documentation et restauration.

## Last session

Configuration locale complémentaire : `.env` préparé et validé avec le schéma
`jobhunter_app` de la base locale existante (rôle sans CREATEDB), secrets générés
ou conservés sans affichage, migration 0001_auth appliquée dans ce schéma.
Contrôles réels : current_schema correct, santé API 200, compte protégé 401,
origine frontend HTTPS acceptée. Compte propriétaire encore absent ; lancer
`python -m app.setup owner` interactivement. Fichiers .env et sauvegarde hors Git.
Décision D-011 ; aucune modification du fichier .env.test ni du modèle métier.

Done: `frontEnd/jobhunter` sous Angular 22, Node portable 22.22.3 ; connexion et
compte FastAPI, session avec refresh partag?, guards, FR/EN, layout mobile/clavier,
th?me Velson, Poppins OFL, build/preview HTTPS et helper PowerShell. CI ?tendue.
Helper `backend/scripts/frontend_e2e.py` : sch?ma et propri?taire jetables avec
`.env.test`, API HTTPS, build de production, Chrome, nettoyage garanti.
Rapport de phase : `reports/phase-1.md` ; commandes dans les README.
Tests: backend `.env.test` : 43 passed in 22.94s ; Angular Karma : 14 SUCCESS ;
E2E : 5 passed (11.1s). Typecheck app/tests/E2E PASS ; build production PASS
(291.05 kB initial). Ruff PASS (32 fichiers format?s), mypy PASS (22 fichiers).
Audit npm runtime : 0 vuln?rabilit?. Audit Python pr?c?dent : aucun avis connu.
Captures inspect?es : connexion desktop/mobile, dashboard desktop/mobile et compte.
Corrections : CSS critique bloqu? par CSP, focus apr?s fermeture du menu mobile,
distinction d?connexion volontaire/session expir?e. Aucun secret local affich?.
Not done / blocked: aucun remote Git configur? ; CI GitHub/PG16 non ex?cut?s.
Docker reste diff?r?. Pas de baseline pixel automatis?e du template original.
Modules m?tier, recherche et CV non impl?ment?s ; leurs liens affichent ? Bient?t ?.
Aucun compte propri?taire r?el install? automatiquement. Les fixtures E2E et leur
fichier d'identifiants ont ?t? nettoy?s ; serveurs de test arr?t?s.
Next step: validation du rapport de phase 1 par le propri?taire, puis plan de
phase 2 (sources et connecteurs). Ne pas commencer la phase 2 sans confirmation.

## Open questions for the owner

- Valider le p?rim?tre local de phase 1 avec Docker diff?r? et CI externe ? ex?cuter.
- Clarifier les droits du template avant redistribution de ses assets commerciaux.
