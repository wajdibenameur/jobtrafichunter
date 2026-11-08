# AI Job Agent — audit préalable

Date : 2026-11-08. Statut : AUDIT_COMPLETED / IMPLEMENTATION_NOT_APPROVED.
Enregistrement documentaire autorisé par D-027. Aucun nouveau code applicatif.
Plan : [PLAN-AI-JOB-AGENT.md](../PLAN-AI-JOB-AGENT.md).

## Documents et état du dépôt

PROGRESS, DECISIONS, TODO, README, rapports et plans existants consultés, ainsi
que SPEC, notamment les sections 15–19 et 22–27. SPEC reste immuable.
Les noms exacts PHASE1.md/PHASE2.md et variantes recherchées sont absents.
Les équivalents sont [phase-1.md](phase-1.md) et [phase-2.md](phase-2.md) ;
ne pas créer de copies concurrentes. Décisions D-017/D-024 : phases 2/3 validées.
Phase 4 livrée selon D-026 et [son rapport](phase-4.md), validation encore attendue.

Le suivi était resté aux fondations CV alors que le code et le rapport décrivaient
la livraison complète. La présente mise à jour corrige cet état sans attribuer
une nouvelle validation au propriétaire. Le dépôt contient déjà des changements
de phase 4 non commités ; l'audit porte sur cet arbre de travail, pas seulement HEAD.
Les changements préexistants du template et d'angular.json sont à préserver.

## Inventaire fonctionnel

Chemins backend relatifs à `backend/app/modules/`, frontend à
`frontEnd/jobhunter/src/app/`.

| Fonctionnalité | État actuel | Fichiers existants | Travail nécessaire |
| --- | --- | --- | --- |
| Profils de recherche | EXISTANTE ET FONCTIONNELLE | search/service.py, schemas.py ; pages/search-profiles | Étendre les critères, garder les profils |
| Queue/worker | EXISTANTE ET FONCTIONNELLE | search/queue.py, ../worker.py | Étendre les étapes sans seconde queue |
| Reprise/annulation | EXISTANTE ET FONCTIONNELLE | search/queue.py, executions.py | Réutiliser leases, checkpoints et résultats persistants |
| Déduplication/provenance | EXISTANTE ET FONCTIONNELLE | listings/dedup.py, catalog.py, repository.py | Préserver imports et relations |
| Liens/import manuel/CSV | EXISTANTE ET FONCTIONNELLE | sources/, listings/csv_import.py ; pages/sources | Garder les quatre sites et sources personnalisées |
| Filtres temporels demandés | EXISTANTE MAIS INCOMPLÈTE | search/filters.py, schemas.py ; shared/criteria-editor.* | 2 h/6 h, radios, dates strictes et compatibilité |
| CV privés/profil candidat | EXISTANTE ET FONCTIONNELLE dans le périmètre livré | cv/, profile/, ai/inspection.py ; pages/cvs | Calibration et extraction sémantique limitées |
| Matching CV | ABSENTE | Aucun module matching implémenté | Scoring, explications, cache et calibration |
| CV adapté | ABSENTE | Le coffre original cv/ est réutilisable par interface publique | Génération, validation, versions et exports |
| Lettre | ABSENTE | Aucun générateur documentaire | Génération, édition et exports |
| Alertes/Telegram/planification | ABSENTE | Aucun module notifications implémenté | Préférences, ordonnanceur worker, historique et envoi |
| Suivi des candidatures | ABSENTE | Aucun module applications implémenté | Statuts, documents utilisés et événements |
| Postuler | EXISTANTE MAIS INCOMPLÈTE | listings/models.py application_url ; pages/results/results.html | Utiliser URL candidature, confirmation distincte |
| Suivi documentaire | À CORRIGER, correction documentaire D-027 | PROGRESS, README, plans/rapports | Synchroniser les états, conserver l'historique |

L'annuaire réel contient auth, ai, cv, profile, sources, search et listings.
Les noms matching/notifications/applications dans AGENTS et les tests de frontières
sont une architecture cible, pas une preuve d'implémentation. documents est absent.
Aucun LlmProvider ni générateur DOCX/PDF n'est intégré ; aucune IA externe activée.

## Sémantique et limites à préserver

- publication_days : 0/1/3/7/30, défaut 0 (toutes dates) ; nouveauté distincte
  all/today/24h/3d/7d/30d, today en Europe/Paris. Les sélecteurs sont des listes,
  pas des radios. Le backend et Angular ont le même défaut actuel.
- Les 7/30 jours sont glissants. Une date exactement au cutoff est actuellement
  incluse. Les publications futures sont rejetées lorsqu'une fenêtre est active.
- Une publication inconnue est conservée et signalée avec unknown_policy=include.
  L'exclusion stricte 2/6/24 h et le défaut 24 h sont donc des changements proposés.
- published_at, first_seen_at et last_seen_at existent en DateTime timezone=True.
  L'import exige un fuseau pour published_at ; il ne vérifie pas la date auprès
  du site. Ne jamais remplacer une publication absente par la date d'import.
- La recherche ne traite que les imports locaux : borne 500 imports/100 candidats
  par identité, état PARTIAL explicite, snapshots et imports originaux conservés.
  Pas de collecte fournisseur, matching ou notification cachés derrière le worker.
- CV PDF/DOCX privés de 5 Mio, AppContainer Windows, profils avec preuves,
  édition/validation/activation séparées. DOC/OCR absents ; sections d'expérience
  à relire, aucune compétence/année/visa inventé, aucun score existant.
- application_url est déjà persistée avec repli sur original_url à l'import ;
  l'interface Résultats ouvre encore original_url. Aucun clic ne prouve un envoi.

## Vérifications exécutées pendant l'audit

| Commande/contrôle | Résultat réel |
| --- | --- |
| backend : python -m ruff check . | Réussi |
| python -m ruff format --check . | 116 fichiers conformes |
| python -m mypy app | 97 fichiers, aucune erreur |
| python -m pytest -q --tb=short, .env.test | 131 passed in 148.13s, aucun skip |
| alembic current / heads | 0008_candidate_profiles (head) |
| alembic check | No new upgrade operations detected |
| scripts/frontend.ps1 typecheck / build | Réussis |
| scripts/frontend.ps1 test | 24 SUCCESS |
| backend : python scripts/frontend_e2e.py | 10 passed (30.2s), schéma/identifiants nettoyés |

Build/tests ont produit leurs artefacts locaux ; aucun code/document/migration
n'a été modifié pendant l'audit. Aucun appel payant ni navigation fournisseur.
Tests synthétiques : ils ne prouvent pas la qualité d'un futur matching réel.
GitHub CI et PostgreSQL 16 non exécutés ; isolation native vérifiée sur Windows.
SHA-256 SPEC : `09775636636C8683682C37FB7BCBB18B44F829EB18D65E83DABE511674D1184D`.

## Arbitrages et dépendances

D-012 local sans Docker, D-015 quatre sites manuels et D-023 report Apify restent
applicables. Une nouvelle collecte exige des preuves officielles et PERMITTED ;
un accord financier C distinct reste nécessaire pour un run Apify réel.
L'extension documentaire ne modifie pas SPEC et ne vaut pas approbation du code.

Ordre proposé : clôture/relecture de phase 4 et consolidation → filtres → matching
calibré → alertes → CV adapté → lettre → dossier/suivi → validation globale.
La génération peut utiliser les imports manuels ; les alertes de nouvelles offres
externes restent limitées tant qu'aucun connecteur autorisé n'est disponible.
Les détails de fichiers, migrations, tests et frontières à approuver sont dans le plan.
