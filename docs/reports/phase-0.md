# Rapport de démarrage — Étape 0

Date : 2026-11-07. État : WAITING_FOR_VALIDATION.
Références : SPEC sections 24, 26 et 27.2 ; instruction utilisateur reportant
Velson au début du frontend. Aucun code applicatif modifié.

## Compréhension du projet en dix lignes

1. JobHunter AI est un outil de recherche d'emploi IT pour un propriétaire unique.
2. FastAPI et son worker partagent un monolithe modulaire, avec PostgreSQL 16.
3. Angular affiche une interface issue de Velson, à analyser lors du lot frontend.
4. Sources, domaines, lieux et critères sont configurables et persistés en base.
5. La collecte utilise uniquement des intégrations autorisées ; sinon liens/import.
6. Les recherches asynchrones reprennent après incident et exposent leurs erreurs.
7. Les offres sont normalisées et dédupliquées sans réinitialiser first_seen_at.
8. Les CV restent privés et immuables ; leur profil doit être validé par l'utilisateur.
9. Les scores déterministes expliquent correspondances, manques et confiance.
10. Telegram, suivi des candidatures, tests et exploitation complètent les sept phases.

## État réellement observé

- Racine : dossiers `Backend` (vide) et `frontEnd` ; aucun dépôt Git racine.
- Documents de suivi et consignes absents au début de cette session.
- La référence `frontEnd/velson_template` existe : package Angular 18.2,
  nom `xsupply-front`, architecture NgModule ; dépôt Git imbriqué avec des
  modifications préexistantes, y compris dans les sources et le cache.
- Audit détaillé des pages, styles, assets, licence et couvertures des dix écrans
  volontairement différé. Les premières lectures ne constituent pas cet audit.
- Versions des commandes observées : Node 22.21.1, npm 11.6.1, Python 3.11.9,
  Docker CLI 27.2.0. Moteur Docker, Compose et PostgreSQL non vérifiés.

## Ambiguïtés et propositions

Les propositions suivantes ne sont pas encore approuvées.

| Sujet | Proposition et raison | Moment de décision |
| --- | --- | --- |
| `app/ai` versus `app/modules/ai` | Appliquer l'annexe 15 : module interne `app/modules/ai`, sans microservice. | Plan phase 1 |
| `Backend` versus `backend` | Normaliser vers `backend` pour Docker/Linux avant tout code. | Début phase 1 |
| Angular stable versus template Angular 18 | Préserver la référence et vérifier la version stable supportée au début du frontend ; migration standalone planifiée ensuite. | Lot frontend |
| Audit de maquette préalable | Dérogation déjà autorisée : report au frontend ; ne pas changer le design avant son audit. | Décidé par propriétaire |
| Événements versus dépendances sans cycles | Contrats publics et câblage dans le point de composition ; handlers sans imports internes croisés. | Tests architecture phase 1 |
| `healthCheck` versus `health_check` | Interface Python snake_case `health_check`, documentée et commune aux connecteurs. | Phase 2 |
| Déduplication et reposts | Séparer identité stable, liens sources et occurrences ; first_seen_at de l'identité ne change jamais. Ne pas imposer unicité du fingerprint à chaque occurrence de repost. | Modèle phase 3 à valider |
| Nouveau dans plusieurs exécutions | Distinguer date de découverte, relation au run et déduplication des alertes ; une collecte répétée ne rend jamais une offre nouvelle. | Phase 3 |
| Cookies Secure et HTTP local | Prévoir HTTPS local plutôt que diminuer silencieusement les garanties des cookies. | Infra phase 1 |
| Parseur sans réseau et backend avec réseau | Une simple subprocess ne garantit pas l'isolement réseau ; choisir et tester une isolation OS sans ajouter implicitement un service. | Avant phase 4 |
| DOC historique | PDF/DOCX ont des outils prévus ; identifier et approuver un parseur DOC isolé, sans promettre ce support avant test. | Avant phase 4 |
| Secrets Telegram par utilisateur versus env | Env pour bootstrap ; configuration utilisateur chiffrée et réponses API masquées. | Avant phase 6 |
| Source permise versus import manuel | Contrôle PERMITTED sur collecte automatisée ; import explicite utilisateur séparé, sans récupération automatique de la page. | Phase 2 |
| Premier statut RUNNING versus queue PENDING | Exécution créée PENDING, devient RUNNING à la prise en charge ; statuts tâches distincts et documentés. | Phase 3 |
| Calibration réelle et golden CVs | Besoin de données anonymisées et labels propriétaire ; fixtures synthétiques clairement signalées et insuffisantes pour déclarer l'acceptation réelle. | Phases 4–5 |
| Limites coût et plafonds de score | Définir les paramètres versionnés et seuils avec tests ; ne pas inventer des valeurs prétendument approuvées. | Phase 5 |
| Commits et dépôt imbriqué | Préparer le dépôt racine avec exclusion/protection du template selon sa licence ; ne pas embarquer automatiquement son `.git` ni ses modifications. | Phase 1 |

## Fichiers créés

- `AGENTS.md` et `CLAUDE.md` : consignes identiques et courtes.
- `docs/SPEC.md` : copie du document source, sans édition.
- `docs/PROGRESS.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md` : suivi initial.
- `docs/sources/README.md` : modèle de preuve, aucune permission présumée.
- `docs/PLAN-PHASE-1.md` : périmètre, fichiers, migrations, risques et contrôles proposés.
- Ce rapport `docs/reports/phase-0.md`.

## Vérifications

- Lecture des sections 1 à 27, notamment annexes sécurité, file persistée et phases.
- Contrôle PowerShell exécuté (`Test-Path`, `Get-FileHash`, `Get-Content`) :
  neuf documents présents avant création du suivi final ; SPEC identique à
  l'original ; AGENTS/CLAUDE identiques et sous la limite de 60 lignes. Résultat PASS.
- SHA-256 SPEC : `09775636636C8683682C37FB7BCBB18B44F829EB18D65E83DABE511674D1184D`.
- Aucun build ni test applicatif lancé : l'étape 0 ne crée pas d'application.
- Aucun commit effectué : dépôt racine absent, politique du template à établir.

## Prochaine étape

Faire valider ce rapport et `docs/PLAN-PHASE-1.md` avant l'implémentation.
Cette pause est demandée explicitement par SPEC sections 24.1 et 27.2.
La phase 1 et l'analyse détaillée Velson restent non réalisées.
