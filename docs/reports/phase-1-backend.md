# Phase 1 — livraison du lot backend local

Date : 2026-11-07. Statut : BACKEND_VERIFIED / PHASE_1_IN_PROGRESS.
La phase 1 entière n'est pas terminée. Docker est différé sur instruction du
propriétaire ; le frontend attend la validation de l'audit Velson.

## Réalisé

- Python 3.11.9 local, environnement dédié, dépendances runtime/dev verrouillées
  avec hashes ; dossier normalisé `backend` et dépôt racine initialisé.
- FastAPI avec `/health`, OpenAPI/Swagger, erreurs JSON sans echo des entrées,
  logs JSON sans contenu sensible, correlation id, CORS/origines stricts, headers
  et limite 16 Ko sur les corps mutables, y compris sans Content-Length.
- Module auth : API, service, repository, modèles, schemas, événements et interface
  publique ; tests AST des frontières et dépendances autorisées.
- Propriétaire unique créé par CLI avec saisie masquée ; Argon2id ; accès 15 min,
  refresh rotatif hashé, cookies Secure/httpOnly/SameSite=Strict ; révocation de
  la famille sur réutilisation ; verrouillage compte et limitation par client.
- Migration `0001_auth` transactionnelle avec verrou consultatif PostgreSQL ;
  tables app_users, auth_sessions, refresh_tokens et login_buckets.
- CLI de secrets et certificat TLS local autosigné ; son certificat et sa clé
  sont vérifiés par test, sans écraser une clé préexistante.
- Entrée worker avec sonde PostgreSQL, boucle d'attente et arrêt par signal ;
  aucun traitement de recherche avant la phase 3.
- README de lancement local, `.env` exemples sans secrets réels, CI et Dependabot.
  Le template et les fichiers sensibles/locaux sont exclus du dépôt racine.

## Exécution

Suivre le README racine : installation depuis `requirements-dev.lock`, configurer
`backend/.env`, `python -m alembic upgrade head`, `python -m app.setup owner`,
`python -m app.setup tls`, puis Uvicorn HTTPS avec `--factory`, `--no-access-log`
et `--no-proxy-headers`. Aucun compte réel n'a été installé sans le propriétaire.
Toutes les requêtes mutantes exigent un Origin autorisé.

## Vérifications réellement exécutées

Depuis `backend` avec `.venv/Scripts/python.exe` :

| Commande | Résultat |
| --- | --- |
| `-m ruff check .` | All checks passed! |
| `-m ruff format --check .` | 31 files already formatted |
| `-m mypy app` | Success: no issues found in 22 source files |
| `-m compileall -q app alembic` | Code retour 0 |
| `-m pytest -q --cov=app --cov-report=term-missing --cov-fail-under=70` avec JOBHUNTER_TEST_ENV=.env.test.local | 43 passed ; couverture 85.32 % |
| `-m pip_audit -r requirements.lock --no-deps --disable-pip --cache-dir ../.cache/pip-audit` | No known vulnerabilities found |
| `-m app.setup --help`, `-m app.worker --help` | Code retour 0 |

Les neuf tests d'intégration emploient une véritable instance PostgreSQL 17.10,
avec schéma aléatoire neuf et migration Alembic à chaque test. Ils couvrent :
propriétaire unique et concurrence setup, compteurs persistés et verrouillage,
compte inconnu limité, rotation et rejeu, refresh concurrent, expiration, flux
HTTP connexion/refresh/logout/révocation et santé, lifecycle API et sonde worker.
La couverture du service auth est 83 %, celle du repository 100 %.

La CI PostgreSQL 16 a été écrite mais pas exécutée sur GitHub. Aucun build Docker,
test navigateur frontend, test CV ou connecteur n'a été exécuté.

## Échecs rencontrés et corrigés

- Accès réseau/cache uv restreint : installation relancée avec autorisation et
  cache local. Aucun usage de Python 3.12 après la correction du propriétaire.
- Authentification du serveur système sans mot de passe impossible : serveur
  existant conservé ; instance de test distincte, sans modifier `.env.test`.
- Premier démarrage PostgreSQL isolé restreint ; relancé avec autorisation.
  Huit erreurs de connexion ont été observées avant le démarrage effectif, puis
  les tests ont été relancés avec succès sur l'instance disponible.
- Capture des pipes hérités de pg_ctl sous Windows : helper corrigé en redirigeant
  vers DEVNULL et en masquant la fenêtre du processus.
- Audit initial : avis cryptography 48.0.1 ; passage à 50.0.2, verrous régénérés,
  audit et tests à nouveau exécutés avec succès.

## Limites et prochaines étapes

- Attendre la validation du rapport `velson-audit.md` avant intégration du design.
- Ajouter le lot Angular et ses tests : connexion réelle, layout, API typée, FR/EN.
- Traiter licence, dépendances de démo et ancien environnement de la référence.
- Les sources, CV, matching, recherches, Telegram et candidatures restent à leurs
  phases respectives ; aucun connecteur ni compte fournisseur n'est activé.
- TOTP optionnel, audit d'accès CV et export/suppression métier restent à implémenter.
- La queue persistée, ses handlers et la santé du worker pour Docker sont à venir.
- Aucun déploiement production ni test PostgreSQL 16 local n'est revendiqué.

Références d'implémentation consultées : [cookies FastAPI](https://fastapi.tiangolo.com/advanced/response-cookies/),
[sessions SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html),
[Alembic](https://alembic.sqlalchemy.org/en/latest/cookbook.html),
[checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python).
