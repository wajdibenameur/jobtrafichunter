# JobHunter AI

Plateforme de recherche d'emploi configurable pour un propriétaire unique.
Backend FastAPI modulaire, PostgreSQL et frontend Angular standalone.

Dépôt public : [wajdibenameur/jobtrafichunter](https://github.com/wajdibenameur/jobtrafichunter).

État : phase 3 validée ; phase 4 CV/profil candidat livrée, en attente de validation.
Python **3.11** selon
instruction du propriétaire. Le projet reste entièrement local, sans Docker.
Connexion, compte, Sources, Profils, Recherche, Résultats et préparation Scraping
sont reliés à FastAPI. LinkedIn,
Indeed, Keejob et Tanitjobs proposent des liens de recherche et l’import manuel
d’offres, avec aperçu CSV et confirmation. Les recherches filtrent ces imports,
avec queue PostgreSQL et déduplication conservatrice. Voir [le rapport](docs/reports/phase-3.md).
Voir [le suivi](docs/PROGRESS.md), [les décisions](docs/DECISIONS.md) et
[le cahier des charges](docs/SPEC.md).

La nouvelle demande AI Job Agent a été auditée : [état réel et contrôles](docs/reports/ai-job-agent-audit.md),
[plan proposé en sept lots](docs/PLAN-AI-JOB-AGENT.md). Matching, alertes, CV adaptés,
lettres et dossiers restent à développer. L'accord D-027 portait uniquement sur
la documentation ; le plan AI Job Agent et la livraison de phase 4 restent à valider.

Scraping Engine indépendant d'Apify : [audit](docs/reports/scraping-engine-audit.md),
[revue des sources](docs/sources/scraping-review.md) et
[plan en huit lots](docs/PLAN-SCRAPING-ENGINE.md). Infrastructure du lot 2 livrée
selon D-029 : [livraison et limites](docs/reports/scraping-lot-2.md), validée D-030.
L'extraction JSON-LD du lot 3 est validée D-031. La [page Scraping du lot 4](docs/reports/scraping-lot-4.md)
est validée D-032 : profils/critères enregistrables, radios 2 h/6 h/24 h/7 j/30 j et
historique local réutilisé. Les anciens profils conservent leurs règles ; nouveau
profil Angular à 24 h par défaut. Redémarrer l'API pour charger publication_minutes.
Le [plan détaillé du lot 5](docs/PLAN-SCRAPING-LOT-5.md) est approuvé D-033 :
[queue/worker, checkpoints, budgets et ingestion atomique](docs/reports/scraping-lot-5.md)
implémentés dans l'arbre local et vérifiés sur connecteurs simulés. Actions/volume
conditionnés aux capacités serveur ; aucune source réelle éligible/enregistrée,
donc ils restent indisponibles dans l'installation normale. Fréquence hors périmètre.
Les migrations 0009–0011 suivent la base CV 0007/0008, versionnée séparément dans
2b34645 pour publication D-034. Les validations fonctionnelles restent distinctes.
Aucune migration de ce lot appliquée à la base personnelle ; après revue des
migrations, appliquer `alembic upgrade head` avant de redémarrer API et worker.
Aucun adaptateur fournisseur ou collecte activés. Les fonctionnalités communes
restantes avec AI Job Agent seront réalisées une seule fois après validation des plans.

## Installation locale — PowerShell

Pour récupérer le dépôt :

```powershell
git clone https://github.com/wajdibenameur/jobtrafichunter.git
cd jobtrafichunter
$env:JOBHUNTER_TEMPLATE_OPTIONAL = '1'
```

Le template commercial n'est pas distribué. Cette variable permet au frontend
d'utiliser l'illustration CSS de remplacement. Voir aussi le
[rapport de publication](docs/reports/github-publication.md).

Depuis la racine du projet :

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
- Registre protégé : `/api/sources` ; liens via `/{id}/search-link`.
- Import : `/api/jobs/import/preview`, `/api/jobs/import` ; liste `/api/jobs`.
- Profils et recherche locale : `/api/search/profiles`, `/api/search/executions`,
  progression `/api/search/executions/{id}/events` et résultats `/{id}/results`.

Toutes les requêtes mutantes exigent `Origin: https://localhost:8443`, y compris
les clients CLI utilisant directement l'API ; pour le frontend, ajouter aussi
`https://localhost:4200` à `ALLOWED_ORIGINS`, comme dans `.env.example`.
Le mot de passe du propriétaire est saisi interactivement,
jamais en argument CLI. La création est verrouillée dès qu'un propriétaire existe.

## Frontend Angular

Depuis la racine, après démarrage HTTPS du backend :

```powershell
.\scripts\frontend.ps1 install
.\scripts\frontend.ps1 start
```

Ouvrir **https://localhost:4200**. Le helper sélectionne le Node portable du projet
ou utilise une version Node compatible installée. L'interface propose connexion,
compte, navigation responsive et FR/EN. Les fonctionnalités métier non disponibles
sont indiquées « Bientôt ». Aucun compte de démonstration n'est installé dans la
base réelle. Voir [le README frontend](frontEnd/jobhunter/README.md).

Pour la recherche locale, lancer aussi le worker dans un terminal distinct depuis
`backend` (avec le même `.env` que l’API) :

```cmd
.venv\Scripts\python.exe -m app.worker
```

Dans **Profils de recherche**, enregistrer les critères et au moins une source,
puis **Recherche → Lancer la recherche locale**. Le worker traite les imports
existants ; les résultats et leur progression persistent après rechargement.
Les champs inconnus restent signalés. Le mode CV, les scores IA et notifications
ne sont pas encore disponibles. `--once` vérifie la DB et traite un cycle borné.

Dans **Sources**, le filtre « Sites tunisiens » affiche Keejob et Tanitjobs.
La sélection et les mots-clés/lieux sont persistants ; ils n’activent pas de
collecte automatique. Ouvrir le lien préparé, puis coller les données de l’offre
ou vérifier un CSV avant confirmation. Les inconnus restent inconnus et un lien
réimporté conserve sa première découverte. Le serveur ne visite pas l’offre.

Build et vérifications depuis la racine :

```powershell
.\scripts\frontend.ps1 typecheck
.\scripts\frontend.ps1 build
.\scripts\frontend.ps1 test
```

Après build, les tests de bout en bout utilisent `backend/.env.test` :

```powershell
cd backend
.venv\Scripts\python.exe scripts/frontend_e2e.py
```

Le helper lance une API HTTPS et un propriétaire jetable dans un schéma isolé,
exécute Chrome sans interface puis nettoie ses données. Captures et logs restent
locaux dans `.cache/frontend-e2e`. Le template commercial est conservé intact et
hors Git ; seule son illustration est copiée localement. Poppins est fourni sous OFL.

## CV privés et profil candidat

La page **Mes CV** accepte les PDF textuels et DOCX (5 Mio maximum), conserve
les originaux chiffrés et immuables, et affiche un aperçu textuel sûr. Les PDF
sans texte exploitable sont signalés ; OCR et conversion des DOC historiques
restent indisponibles. Les fichiers protégés, actifs ou dépassant les bornes
de traitement sont refusés. L’extraction par règles doit être relue ; elle
ne calcule pas des années d’expérience ou un besoin de visa à votre place.

Depuis `backend`, avec Python 3.11 et les dépendances verrouillées installées,
arrêter l’API avant de préparer ou mettre à jour son runtime d’analyse :

```cmd
.venv\Scripts\python.exe scripts\setup_cv_sandbox.py
.venv\Scripts\python.exe -m alembic upgrade head
```

La préparation Windows compile un petit lanceur avec le compilateur .NET présent,
copie Python et pypdf dans `.cache/cv-sandbox`, crée un profil AppContainer local
au compte Windows et limite les permissions de ce profil. Aucun service,
conteneur, clé de chiffrement ou paramètre réseau global n’est ajouté/modifié.
Exécuter la préparation et l’API avec le même compte Windows. L’analyse refuse
de démarrer si son isolation effective n’est pas vérifiée. Les chemins peuvent
être configurés via `CV_STORAGE_PATH` et `CV_SANDBOX_PATH` ; aucun fichier CV ne
doit être placé dans les assets ou un répertoire servi par HTTP. Ne pas changer
la clé existante : elle protège aussi les profils et textes extraits en base.

Redémarrer ensuite l’API HTTPS et le worker avec les commandes ci-dessus, puis
ouvrir **Mes CV**. Choisir « Nouveau document » ou le document à versionner,
envoyer le fichier, préparer le profil, corriger les faits et enregistrer un
brouillon. La validation avec relecture et l’activation sont deux actions séparées.
Une correction crée une révision ; elle ne remplace pas le profil validé actif.
Les préférences sont distinctes des mentions du document et les preuves sont
consultables. L’export contient la version sélectionnée et ses profils, avec
l’original en base64 ; ce n’est pas un export de tout le compte.

Le worker reprend les intentions de stockage interrompues après cinq minutes.
Un original non publié est signalé comme échec si le fichier manque, jamais
comme succès. La suppression confirmée retire toutes les versions du document,
leurs profils et fichiers ; l’audit ne garde que les identifiants/actions.
Matching, scores et recherche CV restent pour la phase 5. Apify reste reporté.
Rapport et limites : [phase 4](docs/reports/phase-4.md).

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
Les résultats de CI distante sont consultables dans
[GitHub Actions](https://github.com/wajdibenameur/jobtrafichunter/actions) ; les
vérifications locales ne sont pas présentées comme une réussite CI distante.

## Architecture et limites

`backend/app/core` fournit settings, sécurité et accès DB ; `shared` porte les
primitives communes. Le module `auth` possède ses tables et expose son contrat
dans `__init__.py`. Les tests AST contrôlent frontières et dépendances autorisées.
Les migrations sont transactionnelles et protégées contre les courses par un
verrou PostgreSQL ; une migration appliquée ne doit plus être modifiée.

Aucun connecteur automatisé fournisseur, matching ou Telegram livré.
Parsing CV local Windows et profil candidat validé : voir la section CV ci-dessus.
Le dashboard affiche les vrais imports et la dernière exécution locale. La queue
traite les imports avec heartbeat, reprise, annulation et snapshots de résultats.
Les regroupements ne suppriment aucun import original ; les ambiguïtés restent
signalées. Les recherches sont bornées à 500 imports récents et 100 candidats par
identité ; une limite atteinte produit un état PARTIAL explicite.
Aucune permission de collecte n'est présumée. Le template Velson reste dans son
dépôt local indépendant, exclu du dépôt racine tant que sa licence n'est pas étudiée.
