# Progress

Last updated: 2026-11-07 by Codex / lot backend phase 1
Current phase: 1 - Socle backend vérifié, préalable frontend
Status: WAITING_FOR_VALIDATION (rapport Velson uniquement ; phase 1 incomplète)

## Phase checklist

- [x] 0.1 Lire le cahier des charges et la section 27.
- [x] 0.2 Copier SPEC sans modification et créer les consignes agents identiques.
- [x] 0.3 Créer suivi, décisions, TODO, changelog et modèle de preuve des sources.
- [x] 0.4 Écrire le rapport initial et le plan proposé pour la phase 1.
- [x] 0.5 Rapport et plan phase 1 validés : « DONC COMMANCER ».
- [ ] 1 Socle complet (backend + frontend ; Docker différé par propriétaire).
    - [x] 1.1 Python 3.11, dépendances verrouillées, structure et dépôt racine.
    - [x] 1.2 Auth propriétaire, migration initiale, API et headers de sécurité.
    - [x] 1.3 Tests PostgreSQL réels, Ruff/mypy, audit dépendances, README.
    - [x] 1.4 Entrée worker avec sonde DB ; sans queue ni handlers métier.
    - [x] 1.5 Analyse des sources Velson et rapport des écrans/tokens/risques.
    - [ ] 1.6 Validation du rapport Velson avant intégration frontend. <- NEXT
    - [ ] 1.7 Layout Angular standalone, connexion API, FR/EN et tests visuels.
    - [ ] 1.8 Exécution CI GitHub et vérification PostgreSQL 16.
    - [ ] Docker / Compose / images : report explicite, pas déclaré livré.
- [ ] 2 Sources, vérifications et framework de connecteurs.
- [ ] 3 Configuration, profils, orchestrateur, queue, déduplication, résultats.
- [ ] 4 CV privés, parsing, édition et validation du profil.
- [ ] 5 Recherche CV, matching explicable et calibration, linkedin_email vérifié.
- [ ] 6 Telegram, planification, historique et logs.
- [ ] 7 Candidatures, durcissement, tests complets, documentation et restauration.

## Last session

Done: `backend/app/core`, module auth complet, migration `0001_auth`, CLI setup/TLS,
worker de base, helper PostgreSQL isolé, verrous runtime/dev, tests, README et CI
préparée. Rapports : `reports/phase-1-backend.md` et `reports/velson-audit.md`.
Tests: Python 3.11.9 / PostgreSQL 17.10 : 43 passed, couverture 85.32 % ;
Ruff check PASS ; 31 fichiers formatés ; mypy PASS (22 fichiers) ; compileall PASS.
Audit runtime PASS sans vulnérabilité connue après correction cryptography 50.0.2.
SPEC conserve son SHA-256 initial ; consignes agents identiques, 48 lignes.
Not done / blocked: frontend en attente de validation SPEC §3 ; aucune modification
du template. CI préparée mais non lancée sur GitHub ; PG16, Docker, navigateur et
modules métier non vérifiés. Base réelle/propriétaire non configurés automatiquement.
L'installation Python 3.12 lancée avant correction utilisateur n'est pas utilisée.
Échecs intermédiaires réseau/cache et démarrage fixture résolus ; voir rapport.
Premier staging Git refusé par le sandbox (index.lock), relance autorisée réussie.
Contrôle du staging PASS : aucun secret local généré ni template de référence.
Instance PostgreSQL de test arrêtée ; serveur système laissé intact.
Next step: faire valider `reports/velson-audit.md`, puis implémenter le lot Angular
du plan approuvé. Ne pas démarrer la phase 2 avant validation de la phase 1.

## Open questions for the owner

- Valider la reprise du layout et de la connexion selon `reports/velson-audit.md`.
- Conditions de licence du template à clarifier avant toute redistribution.
