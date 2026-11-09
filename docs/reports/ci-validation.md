# Vérification de la CI GitHub

Date : 2026-11-09. Décision : D-035. Statut : VERIFIED_LINUX_AND_WINDOWS.
Périmètre : corriger le workflow existant après publication, sans nouveau lot fonctionnel.

## Diagnostic et corrections

1. Le run main a68de8a échoue au démarrage PostgreSQL, avant les tests : assertion
   systemd `postgresql@16-jobhunter-ci.service`. Le cluster de test est renommé
   `jobhunter_ci`, sans tiret, puis contrôlé avec pg_isready sur le port 55432.
   Le moteur, la base applicative personnelle et les migrations ne changent pas.
   [Contrainte officielle](https://manpages.debian.org/testing/postgresql-common/pg_createcluster.1.en.html).
2. Le run a7e4c55 démarre PostgreSQL 16 et obtient 267 tests backend réussis,
   5 exclusions natives Windows documentées, couverture 90,02 %, audit Python
   réussi et 37 tests Angular réussis. Il échoue ensuite sur deux parcours E2E.
3. Le parcours CV exigeait le parseur AppContainer natif sous Ubuntu. Conserver
   ses assertions sur Windows ; sous Linux, vérifier réellement le refus sécurisé :
   capacités ready=false, upload désactivé, tentative PDF synthétique refusée 503.
   Aucun faux parseur ou contournement de l'isolation.
4. Le parcours Scraping sélectionnait parfois le champ de l'ancienne page après
   un clic de navigation, ce qui pouvait annuler la navigation en cours. Attendre
   explicitement l'URL /search avant la sélection, sans sleep ni retry de test.

## Plateformes conservées

- Ubuntu 24.04 : PostgreSQL 16 natif, lint/format/mypy, tests et couverture,
  audits Python/npm, typage/build, Karma et parcours navigateur avec refus CV natif.
- Windows Server 2025 : Python 3.11, cluster isolé créé par le helper existant,
  véritable AppContainer préparé par setup_cv_sandbox.py, suite backend complète
  et parcours navigateur incluant l'analyse CV. Arrêt du cluster en étape always.
- Les binaires PostgreSQL 17 sont fournis via PGBIN par
  [l'image officielle](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md).
  Aucun Docker ou service système supplémentaire, aucune base personnelle touchée.
- L'URL aléatoire du cluster est masquée avant transmission dans GITHUB_ENV ;
  pas de secret dans les commits, caches publics ou sorties de diagnostic.
- Les exclusions de tests correspondent à la plateforme : le contrat natif est
  exécuté dans le job Windows, le refus de plateforme non supportée dans Linux.
  Ne pas présenter une exclusion comme une réussite du contrat natif.

## Vérification

| Contrôle | Résultat |
| --- | --- |
| Format YAML et TypeScript / typage app-spec-E2E local | Réussis |
| E2E Windows local après corrections | 12 passed (37.8s), 1 cas Linux exclu explicitement |
| PostgreSQL et préparation AppContainer sur runner Windows | Réussis |
| Job Linux final | SUCCESS ; 267 passed / 5 exclus natifs Windows en 82,09 s ; couverture 90,04 % |
| Audits Linux Python et npm runtime | Réussis, aucune vulnérabilité connue signalée |
| Karma Linux | 37 SUCCESS |
| Playwright Linux | 12 passed (19.3s), 1 parcours natif Windows exclu ; refus CV sécurisé testé |
| Job Windows final | SUCCESS ; 272 passed en 93,35 s, aucun skip backend |
| Playwright Windows | 12 passed (28.6s), 1 cas Linux exclu ; parcours natif CV réel réussi |

Commit de code/workflow/tests : 73bd53a.
[Run à deux plateformes](https://github.com/wajdibenameur/jobtrafichunter/actions/runs/42611520631).
Les schémas et identifiants du harness E2E sont jetables et nettoyés ; les logs de
diagnostic locaux restent dans .cache, ignoré par Git.

Le commit suivant consigne uniquement les résultats dans la documentation ;
`[skip ci]` évite de relancer les mêmes suites sans changement de code, de test ou
de workflow. Le run référencé valide précisément 73bd53a, pas un SHA documentaire
non exécuté. [Mécanisme GitHub](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs).

Les PR Dependabot ne sont ni fusionnées ni utilisées pour résoudre ce correctif.
Aucune nouvelle dépendance, changement applicatif, source activée ou collecte réelle.
Les validations de phase 4 CV et de livraison Scraping lot 5 restent indépendantes.
