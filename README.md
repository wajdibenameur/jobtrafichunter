# JobHunter AI

Plateforme de recherche d'emploi configurable pour un propriétaire unique.
Backend FastAPI modulaire, PostgreSQL et frontend Angular à venir.

État : socle backend de phase 1. Python **3.11** selon instruction du propriétaire.
Docker est reporté ; Velson sera analysé au début du travail frontend.
Voir [le suivi](docs/PROGRESS.md), [les décisions](docs/DECISIONS.md) et
[le cahier des charges](docs/SPEC.md).

## Installation locale — PowerShell

Depuis la racine :

```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.lock
Copy-Item .env.example .env
.venv\Scripts\python.exe -m app.setup secrets
```

Reporter les deux valeurs générées dans `.env` et configurer `DATABASE_URL`
avec une base PostgreSQL dédiée. Le compte PostgreSQL doit pouvoir créer les
tables et prendre les verrous consultatifs. Ne pas utiliser une base existante
contenant d'autres applications. Les secrets ne doivent jamais être copiés dans
le chat ou Git. Les exemples `CHANGE_ME` sont refusés au démarrage.

Puis :

```powershell
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m app.setup owner
.venv\Scripts\python.exe -m app.setup tls
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8443 --ssl-keyfile ../local-data/tls/localhost.key --ssl-certfile ../local-data/tls/localhost.crt --no-access-log --no-proxy-headers
```

Le certificat local est autosigné, valable trente jours et non installé dans le
magasin système. Le navigateur demande de lui faire confiance pour le développement.
Les cookies restent `Secure` ; l'API locale utilise donc HTTPS.

- Santé : `https://localhost:8443/health` (503 si la base est indisponible).
- Swagger : `https://localhost:8443/docs` (assets Swagger chargés depuis jsDelivr).
- Schéma OpenAPI : `https://localhost:8443/openapi.json`.
- Auth : `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/me`.
- Compte protégé : `/api/account`.

Toutes les requêtes mutantes exigent `Origin: https://localhost:8443`, y compris
les clients CLI ; les origines supplémentaires doivent être ajoutées explicitement
à `ALLOWED_ORIGINS`. Le mot de passe du propriétaire est saisi interactivement,
jamais en argument CLI. La création est verrouillée dès qu'un propriétaire existe.

## Vérifications

Depuis `backend` :

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m mypy app
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip_audit -r requirements.lock --no-deps --disable-pip --cache-dir ../.cache/pip-audit
```

Sans base de test, les tests d'intégration sont explicitement ignorés. Pour les
exécuter, créer `backend/.env.test` d'après `.env.test.example`. La base doit avoir
un nom finissant par `_test`. Chaque test applique les migrations dans un schéma
aléatoire dédié, supprimé ensuite ; aucun schéma existant n'est nettoyé.

Autre possibilité sous Windows avec les binaires PostgreSQL déjà installés :

```powershell
.venv\Scripts\python.exe scripts/local_postgres.py start
$env:JOBHUNTER_TEST_ENV = '.env.test.local'
.venv\Scripts\python.exe -m pytest -q --cov=app --cov-report=term-missing
.venv\Scripts\python.exe scripts/local_postgres.py stop
```

Ce helper crée son propre cluster dans `.cache/postgres-tests`, son port local
et `.env.test.local`, sans toucher au serveur PostgreSQL système ni à `.env.test`.
`PG_BIN` permet de choisir le dossier des binaires ; par défaut il utilise le
PostgreSQL 17 installé localement. La CI prévoit une vérification PostgreSQL 16.
La configuration CI n'a pas encore été exécutée sur GitHub.

## Architecture et limites

`backend/app/core` fournit settings, sécurité et accès DB ; `shared` porte les
primitives communes. Le module `auth` possède ses tables et expose son contrat
dans `__init__.py`. Les tests AST contrôlent frontières et dépendances autorisées.
Les migrations sont transactionnelles et protégées contre les courses par un
verrou PostgreSQL ; une migration appliquée ne doit plus être modifiée.

Aucun connecteur, parsing CV, matching, Telegram ou écran métier n'est encore
implémenté. `python -m app.worker --once` fournit une sonde DB et le processus
worker possède un arrêt propre ; la queue et ses handlers arrivent en phase 3.
Aucune permission de collecte n'est présumée. Le template Velson reste dans son
dépôt local indépendant, exclu du dépôt racine tant que sa licence n'est pas étudiée.
