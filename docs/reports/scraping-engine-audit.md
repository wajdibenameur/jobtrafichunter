# Scraping Engine — audit préalable

Date : 2026-11-08. Statut : AUDIT_COMPLETED / IMPLEMENTATION_NOT_APPROVED.
Enregistrement autorisé par « ouui ajouté au fichier » (D-028).
État observé avant le développement D-029 : le [lot 2](scraping-lot-2.md) est
désormais livré et attend validation ; l'inventaire ci-dessous reste historique.
Voir le [plan proposé](../PLAN-SCRAPING-ENGINE.md) et les
[preuves documentaires des sources](../sources/scraping-review.md).

## Référentiel et état réel

PROGRESS, DECISIONS, TODO, README, rapports des phases 1/2 et sections pertinentes
de SPEC consultés. PHASE1.md/PHASE2.md et leurs variantes exactes recherchées sont
absents ; leurs équivalents sont reports/phase-1.md et reports/phase-2.md.
Phase 3 validée ; livraison CV de phase 4 encore en attente de validation.
Le code de phase 4 existe en partie hors commit : l'audit porte sur l'arbre de
travail, pas uniquement HEAD. Conserver ces changements et angular.json/template.

| Fonctionnalité | État | Réutilisation / manque |
| --- | --- | --- |
| Profils de recherche | EXISTANTE ET FONCTIONNELLE | search/service.py, schemas.py |
| Registre/préférences/liens | EXISTANTE ET FONCTIONNELLE | sources/service.py, repository.py, page Sources |
| Interface connecteurs | EXISTANTE MAIS INCOMPLÈTE | contracts.py, registry.py ; manuel seulement |
| Import URL/CSV | EXISTANTE ET FONCTIONNELLE | listings/service.py, csv_import.py ; conserver le parcours |
| Déduplication/provenance | EXISTANTE ET FONCTIONNELLE | listings/dedup.py, catalog.py ; originaux préservés |
| Queue/reprise/annulation | EXISTANTE ET FONCTIONNELLE pour le local | search/queue.py, executions.py, app/worker.py |
| Transport HTTP/extraction JSON-LD | ABSENTE | À développer dans les connecteurs |
| Filtres temporels demandés | EXISTANTE MAIS INCOMPLÈTE | 1/3/7/30 jours, défaut toutes dates ; radios 2/6 h absentes |
| Page Scraping | ABSENTE | Ajouter un parcours au shell, réutiliser résultats/historique |
| CV/profil validé | EXISTANTE ET FONCTIONNELLE dans le périmètre livré | cv/, profile/, ai/ ; phase 4 non encore validée |
| Matching/notifications | ABSENTE | Réaliser une fois les modules du plan AI Job Agent |
| CV adapté/lettre/suivi | ABSENTE, planifiée seulement | Ne pas créer une seconde génération documentaire |

Chemins backend relatifs à backend/app/modules/, sauf app/worker.py.

## Constats techniques

- JobSourceConnector possède déjà fetch/normalize/capabilities/health_check.
  Étendre ce contrat typé, pas le remplacer par un second search retournant list[dict].
- La source personnalisée actuelle reste LINK_ONLY. Aucun connecteur automatique
  n'est enregistré ; SourceService refuse actuellement son activation, même si
  une base est modifiée directement. Ne pas enlever ce verrou sans contrôle complet.
- verified_automation exige PERMITTED, preuves complètes et dates de revue <90 jours.
  Un toggle utilisateur n'accorde aucune permission.
- SearchTask est unique par exécution, avec stage/cursor/snapshot et lease ; les
  logs source actuels sont minimaux. Prévoir des checkpoints par source sans
  second worker ou seconde architecture de queue.
- public_https_url bloque certains formats dangereux, mais ne valide pas la
  résolution DNS ni l'IP de connexion : insuffisant pour le futur transport HTTP.
- published_at/first_seen_at/last_seen_at existent. Ne pas substituer collecte à
  publication ; date seule ou sans fuseau ne devient pas une heure UTC inventée.
  Les filtres stricts et le défaut 24 h restent proposés, avec compatibilité historique.
- Type de contrat absent du modèle courant. NormalizedListing ne contient encore
  que titre/entreprise/description/URL ; étendre avec des champs optionnels validés.
- httpx existe en dépendance de développement, pas runtime ; beautifulsoup4 serait
  nouvelle. Vérifier versions/licences et verrous avant installation approuvée.

## Évidence de tests

Pendant l'audit Scraping : 131 tests collectés en 1,05 s ; Ruff réussi ; mypy
réussi sur 97 fichiers. Une collecte de tests n'est pas une exécution réussie.
Dernière suite complète : 131 backend en 148,13 s, 24 Angular, 10 E2E en 30,2 s ;
build/types et Alembic 0008 sans drift, selon l'[audit précédent](ai-job-agent-audit.md).
Ces suites complètes n'ont pas été relancées pour ce nouvel audit documentaire.
Les parcours actuels ne prouvent aucun fonctionnement d'un collecteur absent.

## Limites et autorisations

Consultation de documentation et pages publiques uniquement ; aucune collecte
enregistrée, aucun appel Apify facturable et aucun connecteur activé.
Le rapport « DevOps Jobs in Tunisia — 7 November 2026 » n'a pas été fourni ni
vérifié. Ses observations ne constituent pas une preuve technique ou une permission.
La présence de JSON-LD, RSS, Markdown ou d'une API accessible n'autorise pas tous
les usages. Aucun statut PERMITTED attribué par cet audit.

L'extension indépendante d'Apify ne supprime pas D-012/D-015/D-023 : local Python
3.11 sans Docker, quatre parcours manuels conservés, Apify différé. Matching,
alertes et documents sont communs au plan AI Job Agent, pas des modules parallèles.
Accord documentaire D-028 seulement ; développement, migrations, dépendances et
permissions des sources restent à faire approuver selon le plan.
