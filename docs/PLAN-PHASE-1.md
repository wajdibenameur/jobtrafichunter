# Plan proposé — Phase 1

Date : 2026-11-07. Statut : APPROVED / IN_PROGRESS (« DONC COMMANCER »).
Dérogations ultérieures : Python 3.11 et projet exclusivement local ; Docker
retiré du périmètre par le propriétaire (D-012).
Livraison backend : `reports/phase-1-backend.md`. Le frontend reste à réaliser.

## Périmètre

Poser le socle FastAPI/Python 3.11, PostgreSQL, worker partageant le code backend,
authentification mono-propriétaire, migrations, tests d'architecture et CI.
L'analyse Velson et le layout Angular seront abordés au début du lot frontend,
conformément à l'instruction utilisateur. La phase 1 ne sera complète qu'après
ce lot et ses vérifications ; aucun frontend factice ne sera déclaré livré.

## 1. Structure et outillage backend

- Normaliser le dossier backend après validation ; préserver la maquette existante.
- Créer `backend/pyproject.toml`, le verrou de dépendances et la configuration
  Ruff, mypy strict, pytest et import-linter.
- Créer `backend/app/main.py`, `core/`, `shared/` et les frontières des modules.
- Définir les erreurs JSON, correlation ids, logs sans secrets, settings validés,
  sessions SQLAlchemy async et `/health` avec état de la base.
- Définir `.gitignore` et le dépôt racine en préservant le dépôt imbriqué.

## 2. Base et authentification

- `backend/alembic.ini`, `backend/alembic/env.py`, migration initiale auth
  (propriétaire, sessions de rafraîchissement, compteurs/verrouillage de connexion).
- `backend/app/modules/auth/{api,service,repository,models,schemas,events}.py`
  et `__init__.py`, avec tests au sein du module.
- Installation du propriétaire via commande unique verrouillée après création.
- Argon2id, accès 15 minutes, refresh rotatif stocké sous forme de hash,
  révocation, cookies httpOnly/Secure/SameSite=Strict et limitation des tentatives.
- Protection des mutations par vérification d'origine et politique CORS stricte.
- Les tables métier seront ajoutées avec leurs modules, via migrations append-only.
  Confirmer ce découpage de « base migrations » avant la première migration.

## 3. Exécution locale et worker (sans Docker)

- API et worker exécutés localement dans l'environnement Python 3.11 du projet.
- Migrations Alembic protégées par verrou PostgreSQL, `.env` privé et commandes
  CMD/PowerShell documentées ; aucun Dockerfile ni fichier Compose à créer.
- `backend/app/worker.py` avec arrêt propre et sonde DB ; worker métier en phase 3.
- HTTPS local, contrôle des secrets requis et tests de santé API/base.

## 4. Lot frontend, après analyse différée

- Examiner Velson, sa licence et ses modifications locales ; produire le rapport
  des dix écrans, tokens et composants et obtenir sa validation.
- Choisir la version stable officiellement supportée d'Angular au moment du lot.
- Créer le shell standalone, routes lazy, client API typé, connexion propriétaire,
  FR/EN et états d'erreur/chargement en conservant le design validé.
- Préparer build Angular, proxy local `/api`, fallback SPA et headers de sécurité.

## 5. Vérifications et livraison

- Tests unitaires auth ; intégration PostgreSQL réel : migration vierge,
  création unique du propriétaire, expiration, rotation/rejeu et verrouillage.
- Tests de frontières intermodules, refus des requêtes non authentifiées,
  absence de secrets dans les logs et vérification des settings.
- Build et tests frontend après son lot ; vérification visuelle contre Velson.
- CI `.github/workflows/ci.yml` : lint, typage, tests, audits de dépendances et
  build Angular, sans images ; rapport des commandes et résultats réels.
- Documenter les commandes dans README et consignes agents ; écrire
  `docs/reports/phase-1.md`, mettre à jour PROGRESS/CHANGELOG et attendre validation.

## Risques et limites à résoudre

- Git imbriqué et modifications existantes : aucun reset, nettoyage ou ajout global.
- Python local 3.11 : conserver la version explicitement demandée.
- Compatibilité de l'ancien template avec Angular choisi et licence à contrôler.
- Docker/Compose hors périmètre : aucune vérification de conteneur à prévoir.
- Pas de connecteur, parsing CV, matching ni notification métier en phase 1.

## Résultat du lot backend

Socle et migration auth implémentés et vérifiés ; worker limité au cycle de vie
et à une sonde DB. PostgreSQL 17.10 a servi aux tests locaux, sans modifier le
serveur système. La CI PostgreSQL 16 est préparée, mais non exécutée sur GitHub.
Docker, conteneurs, réseaux/volumes et scans d'images sont hors périmètre.
Le rapport Velson a été accepté par la continuation du propriétaire ; layout,
connexion, compte et FR/EN sont livrés et testés. Voir `reports/phase-1.md`.
Le périmètre local de phase 1 est prêt pour validation ; Docker n'est pas requis,
et la CI GitHub/PostgreSQL 16 reste à exécuter.
